"""Bundle validation: every fixture yields its expected verdict; every bundle reason is covered."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from support import BUNDLES, SCRIPTS, fg, hs, load, ms, valid_pair, vb


class FixtureVerdictTests(unittest.TestCase):
    def test_fixture_directory_is_not_empty(self):
        self.assertGreaterEqual(len(BUNDLES), 30)

    def test_each_bundle_fixture_matches_expectation(self):
        for path in BUNDLES:
            with self.subTest(fixture=path.name):
                rep = vb.check_fixture(load(path))
                self.assertTrue(rep["matches"], rep)
                self.assertEqual(rep["accepted"], rep["reason"] is None)

    def test_exactly_one_accepting_control_fixture(self):
        accepted = [p.name for p in BUNDLES if load(p)["expect"]["ok"]]
        self.assertEqual(accepted, ["valid-handoff.json"])

    def test_every_rejection_reason_has_a_fixture(self):
        """Every Reason is exercised by a bundle fixture or by a handoff-script expectation."""
        covered = {load(p)["expect"]["reason"] for p in BUNDLES} - {None}
        for p in SCRIPTS:
            covered |= hs.expected_reasons(load(p))
        missing = sorted(ms.Reason.all() - covered)
        self.assertEqual(missing, [], f"reasons without a fixture: {missing}")

    def test_bundle_reasons_are_covered_by_bundle_fixtures_or_sim_constructed_bundles(self):
        in_bundles = {load(p)["expect"]["reason"] for p in BUNDLES} - {None}
        self.assertEqual(sorted(ms.Reason.bundle_reasons() - in_bundles), [])

    def test_reason_codes_are_unique_and_match_their_names(self):
        for name, value in vars(ms.Reason).items():
            if name.isupper() and isinstance(value, str):
                self.assertEqual(name, value)


class ValidatorBehaviourTests(unittest.TestCase):
    def test_valid_pair_is_accepted_and_context_untouched(self):
        bundle, ctx = valid_pair()
        before = (ctx.epoch, ctx.last_sequence, ctx.seen_nonces, ctx.ledger_effect_ids)
        doc = ms.validate_for_commit(bundle, ctx)
        self.assertEqual(doc["handoff"]["to_executor"], "edge-01")
        self.assertEqual(before, (ctx.epoch, ctx.last_sequence, ctx.seen_nonces, ctx.ledger_effect_ids))

    def test_rejection_does_not_consume_the_nonce(self):
        bundle, ctx = valid_pair()
        bundle["handoff"]["sequence"] = 0
        with self.assertRaises(ms.Rejection):
            ms.validate_for_commit(bundle, ctx)
        self.assertEqual(ctx.seen_nonces, frozenset())

    def test_digest_ignores_key_order_but_detects_any_value_change(self):
        bundle = fg.base_bundle()
        reordered = json.loads(json.dumps(bundle, sort_keys=True))
        self.assertEqual(ms.compute_digest(bundle), ms.compute_digest(reordered))
        tampered = copy.deepcopy(bundle)
        tampered["progress"]["cursor"] = 3
        self.assertNotEqual(ms.compute_digest(bundle), ms.compute_digest(tampered))

    def test_bool_is_not_accepted_as_integer(self):
        bundle, ctx = valid_pair()
        bundle["ownership"]["epoch"] = True
        with self.assertRaises(ms.Rejection) as cm:
            ms.validate_for_commit(ms.seal(bundle), ctx)
        self.assertEqual(cm.exception.reason, ms.Reason.WRONG_TYPE)

    def test_epoch_zero_and_negative_cursor_rejected(self):
        for path, value in (("ownership.epoch", 0), ("progress.cursor", -1)):
            with self.subTest(path=path):
                bundle, ctx = valid_pair()
                head, tail = path.split(".")
                bundle[head][tail] = value
                with self.assertRaises(ms.Rejection) as cm:
                    ms.validate_for_commit(ms.seal(bundle), ctx)
                self.assertEqual(cm.exception.reason, ms.Reason.BAD_VALUE)

    def test_expiry_boundaries_are_inclusive(self):
        for now, ok in ((4, True), (14, True), (3, False), (15, False)):
            with self.subTest(now=now):
                bundle, ctx = valid_pair()
                ctx.now_tick = now
                if ok:
                    ms.validate_for_commit(bundle, ctx)
                else:
                    with self.assertRaises(ms.Rejection):
                        ms.validate_for_commit(bundle, ctx)

    def test_replay_is_reported_before_stale_epoch(self):
        bundle, ctx = valid_pair()
        ctx.seen_nonces = frozenset({bundle["handoff"]["nonce"]})
        ctx.epoch = 2
        ctx.last_sequence = 1
        with self.assertRaises(ms.Rejection) as cm:
            ms.validate_for_commit(bundle, ctx)
        self.assertEqual(cm.exception.reason, ms.Reason.REPLAYED_NONCE)


class CompatibilityTests(unittest.TestCase):
    def test_compatible_profile_has_no_violations(self):
        self.assertEqual(ms.compatibility_violations(fg.base_bundle(), fg.profile("edge-01")), [])

    def test_all_violations_are_listed_in_documented_order(self):
        prof = fg.profile("edge-01", units={"length": "mm", "angle": "deg", "time": "s"},
                          capabilities=[], sensors=[], actions=[])
        reasons = [r for r, _ in ms.compatibility_violations(fg.base_bundle(), prof)]
        self.assertEqual(reasons, [ms.Reason.UNITS_MISMATCH, ms.Reason.UNITS_MISMATCH,
                                   ms.Reason.MISSING_CAPABILITY, ms.Reason.MISSING_CAPABILITY,
                                   ms.Reason.MISSING_SENSOR, ms.Reason.MISSING_SENSOR,
                                   ms.Reason.ACTION_COMMAND_UNSUPPORTED])

    def test_extra_destination_capabilities_are_fine(self):
        prof = fg.profile("edge-01", capabilities=["inspect_waypoint", "report_status", "other", "more"])
        self.assertEqual(ms.compatibility_violations(fg.base_bundle(), prof), [])

    def test_malformed_profile_is_a_typed_rejection(self):
        with self.assertRaises(ms.Rejection):
            ms.validate_profile({"executor_id": "edge-01"})


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = vb.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_default_run_exits_zero_and_prints_one_line_per_fixture(self):
        code, out, _ = self.run_cli([])
        self.assertEqual(code, 0)
        lines = [json.loads(l) for l in out.splitlines()]
        self.assertEqual(len(lines), len(BUNDLES))
        self.assertTrue(all(l["simulation"] and l["synthetic"] for l in lines))

    def test_wrong_expectation_exits_one(self):
        fixture = load(BUNDLES[0])
        fixture["expect"] = {"ok": True, "reason": None} if fixture["expect"]["ok"] is False else \
            {"ok": False, "reason": ms.Reason.STALE_EPOCH}
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "x.json"
            p.write_text(json.dumps(fixture), encoding="utf-8")
            code, out, _ = self.run_cli([str(p)])
        self.assertEqual(code, 1)
        self.assertFalse(json.loads(out)["matches"])

    def test_missing_and_invalid_inputs_exit_two(self):
        self.assertEqual(self.run_cli(["/nonexistent/fixture.json"])[0], 2)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text("{not json", encoding="utf-8")
            self.assertEqual(self.run_cli([str(p)])[0], 2)
            p.write_text(json.dumps({"fixture_kind": "other"}), encoding="utf-8")
            self.assertEqual(self.run_cli([str(p)])[0], 2)


class FixtureDriftTests(unittest.TestCase):
    def test_committed_fixtures_match_generator(self):
        for path, doc in fg.all_fixtures().items():
            with self.subTest(fixture=path.name):
                self.assertTrue(path.exists())
                self.assertEqual(path.read_text(encoding="utf-8"), fg.render(doc))

    def test_no_unexpected_fixture_files(self):
        expected = {p for p in fg.all_fixtures()}
        present = set(BUNDLES) | set(SCRIPTS)
        self.assertEqual(sorted(p.name for p in present - expected), [])

    def test_all_fixtures_are_labelled_synthetic(self):
        for path in list(BUNDLES) + list(SCRIPTS):
            self.assertIs(load(path)["synthetic"], True, path.name)


if __name__ == "__main__":
    unittest.main()
