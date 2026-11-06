"""Effect gate, epoch fencing, stale-executor rejection, replay and rollback."""

import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from support import SCRIPTS, fg, hs, load, make_sim, ms, valid_pair


class ScriptFixtureTests(unittest.TestCase):
    def test_each_script_fixture_meets_all_expectations(self):
        self.assertGreaterEqual(len(SCRIPTS), 10)
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                rep = hs.run_script(load(path))
                bad = [o for o in rep["ops"] if not o["ok"]]
                self.assertEqual(bad, [])
                self.assertTrue(rep["final_ok"], rep["final"])
                self.assertTrue(rep["simulation"] and rep["synthetic"] and rep["non_actuating"])

    def test_every_effect_gate_reason_is_expected_by_some_script(self):
        covered = set()
        for p in SCRIPTS:
            covered |= hs.expected_reasons(load(p))
        self.assertEqual(sorted(ms.Reason.effect_reasons() - covered), [])

    def test_all_outcomes_are_exercised(self):
        seen = set()
        for p in SCRIPTS:
            for op in load(p)["ops"]:
                if op["op"] == "handoff":
                    seen.add(op["expect"].split(":")[0])
        self.assertEqual(seen, set(hs.OUTCOMES))

    def test_runs_are_deterministic(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                a = hs.run_script(load(path))
                b = hs.run_script(load(path))
                self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))

    def test_ledger_never_contains_a_duplicate_or_out_of_order_step(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                rep = hs.run_script(load(path))
                done = rep["final"]["completed"]
                self.assertEqual(done, fg.STEPS[:len(done)])
                self.assertEqual(rep["final"]["duplicate_effects_in_ledger"], 0)

    def test_epoch_in_trace_never_decreases(self):
        for path in SCRIPTS:
            with self.subTest(script=path.name):
                epochs = [e["epoch"] for e in hs.run_script(load(path))["trace"]
                          if e["event"] in ("commit", "rollback", "parked")]
                self.assertEqual(epochs, sorted(epochs))
                self.assertEqual(len(set(epochs)), len(epochs))

    def test_a_wrong_expectation_is_reported_not_hidden(self):
        script = load(SCRIPTS[0])
        script = copy.deepcopy(script)
        script["ops"][0]["expect"] = "STALE_EXECUTOR"
        rep = hs.run_script(script)
        self.assertFalse(rep["ok"])
        self.assertFalse(rep["ops"][0]["ok"])

    def test_wrong_final_state_is_reported(self):
        script = copy.deepcopy(load(SCRIPTS[0]))
        script["expect_final"]["epoch"] = 99
        self.assertFalse(hs.run_script(script)["ok"])

    def test_non_script_fixture_is_refused(self):
        with self.assertRaises(ValueError):
            hs.run_script({"fixture_kind": "bundle-check"})


class StaleExecutorTests(unittest.TestCase):
    def test_old_epoch_executor_is_rejected_after_takeover(self):
        sim = make_sim()
        sim.step("cloud-01")
        self.assertEqual(sim.handoff("edge-01", deliver_fence=False)["verdict"], "COMPLETED")
        self.assertEqual(sim.step("cloud-01"), ms.Reason.STALE_EXECUTOR)
        self.assertEqual(sim.sink.completed, ["wp-01"])
        self.assertEqual(sim.step("edge-01"), "ACCEPTED")

    def test_stale_executor_is_rejected_even_with_correct_step_and_sequence(self):
        sim = make_sim()
        sim.step("cloud-01")
        sim.handoff("edge-01", deliver_fence=False)
        verdict = sim.raw_effect(fg.effect("cloud-01", 1, 1, "wp-02", "perfect-forgery-01"))
        self.assertEqual(verdict, ms.Reason.STALE_EXECUTOR)

    def test_fenced_origin_refuses_locally(self):
        sim = make_sim()
        sim.handoff("edge-01")
        self.assertEqual(sim.step("cloud-01"), "SELF_FENCED")

    def test_old_epoch_wins_nothing_after_rollback_either(self):
        sim = make_sim()
        sim.step("cloud-01")
        res = sim.handoff("edge-01", fault="ack_lost", steps_before_ack_loss=1)
        self.assertEqual((res["outcome"], res["epoch"]), ("ROLLED_BACK", 3))
        self.assertEqual(sim.step("edge-01"), ms.Reason.STALE_EXECUTOR)

    def test_executor_not_named_in_the_grant_is_not_owner(self):
        sim = make_sim()
        self.assertEqual(sim.raw_effect(fg.effect("edge-01", 1, 0, "wp-01", "x-0001")), ms.Reason.NOT_STATE_OWNER)

    def test_sink_refuses_to_install_a_non_monotonic_grant(self):
        sim = make_sim()
        with self.assertRaises(ValueError):
            sim.sink.install_grant("edge-01", 1, 99)
        sim.handoff("edge-01")
        with self.assertRaises(ValueError):
            sim.sink.install_grant("cloud-01", sim.epoch, 99)


class ReplayTests(unittest.TestCase):
    def test_replayed_bundle_is_rejected_and_changes_nothing(self):
        sim = make_sim()
        sim.step("cloud-01")
        sim.handoff("edge-01")
        before = (sim.owner, sim.epoch, sim.last_sequence)
        res = sim.replay_last_bundle()
        self.assertEqual(res["verdict"], "REJECTED:REPLAYED_NONCE")
        self.assertEqual(before, (sim.owner, sim.epoch, sim.last_sequence))

    def test_replayed_effect_is_rejected_once_and_ledger_unchanged(self):
        sim = make_sim()
        sim.step("cloud-01")
        n = len(sim.sink.ledger)
        self.assertEqual(sim.replay_last_effect("cloud-01"), ms.Reason.REPLAYED_EFFECT)
        self.assertEqual(len(sim.sink.ledger), n)

    def test_old_bundle_with_fresh_nonce_is_stale_after_takeover(self):
        sim = make_sim()
        sim.step("cloud-01")
        stale = sim.build_bundle("edge-01")          # sealed under epoch 1
        sim.handoff("edge-01")                       # advances to epoch 2
        forged = copy.deepcopy(stale)
        forged["handoff"]["nonce"] = "fresh-nonce-0001"
        forged["handoff"]["sequence"] = 5
        res = sim.submit_bundle(ms.seal(forged))
        self.assertEqual(res["verdict"], "REJECTED:STALE_EPOCH")

    def test_stale_checkpoint_after_progress(self):
        sim = make_sim()
        sim.step("cloud-01")
        bundle = sim.build_bundle("edge-01")
        sim.step("cloud-01")                         # ledger moves on after the checkpoint was sealed
        self.assertEqual(sim.submit_bundle(bundle)["verdict"], "REJECTED:STALE_CHECKPOINT")


class RollbackTests(unittest.TestCase):
    def test_rollback_issues_a_new_higher_epoch_to_origin(self):
        sim = make_sim()
        res = sim.handoff("edge-01", fault="destination_crash")
        self.assertEqual((res["outcome"], res["owner"], res["epoch"]), ("ROLLED_BACK", "cloud-01", 3))

    def test_rollback_resumes_from_ledger_not_from_bundle(self):
        sim = make_sim()
        sim.step("cloud-01")
        sim.handoff("edge-01", fault="ack_lost", steps_before_ack_loss=2)
        rollback = [e for e in sim.trace if e["event"] == "rollback"][0]
        self.assertEqual(rollback["resume_cursor"], 3)
        self.assertEqual(sim.sink.completed, ["wp-01", "wp-02", "wp-03"])
        sim.step("cloud-01")
        sim.step("cloud-01")
        self.assertEqual(sim.sink.completed, fg.STEPS)

    def test_effects_committed_before_rollback_are_kept_not_undone(self):
        sim = make_sim()
        sim.handoff("edge-01", fault="ack_lost", steps_before_ack_loss=1)
        self.assertEqual([e["executor"] for e in sim.sink.ledger], ["edge-01"])

    def test_abort_before_commit_keeps_epoch_and_does_not_consume_nonce(self):
        sim = make_sim()
        res = sim.handoff("edge-01", fault="destination_unreachable")
        self.assertEqual((res["outcome"], res["owner"], res["epoch"]), ("ABORTED", "cloud-01", 1))
        self.assertEqual(sim.seen_nonces, set())
        self.assertEqual(sim.last_sequence, 0)
        self.assertEqual(sim.step("cloud-01"), "ACCEPTED")

    def test_park_fails_closed(self):
        sim = make_sim()
        sim.step("cloud-01")
        res = sim.handoff("edge-01", fault="destination_crash", origin_available=False)
        self.assertEqual((res["outcome"], res["owner"]), ("PARKED", None))
        for who in ("cloud-01", "edge-01"):
            self.assertNotEqual(sim.step(who), "ACCEPTED")
        self.assertEqual(sim.raw_effect(fg.effect("cloud-01", sim.epoch, 0, "wp-02", "claim-0001")),
                         ms.Reason.NOT_STATE_OWNER)
        self.assertEqual(sim.sink.completed, ["wp-01"])

    def test_incompatible_destination_leaves_state_untouched(self):
        sim = make_sim()
        sim.step("cloud-01")
        before = (sim.owner, sim.epoch, sim.last_sequence, set(sim.seen_nonces), list(sim.sink.ledger))
        res = sim.handoff("edge-mm")
        self.assertEqual(res["verdict"], "REJECTED:SENSOR_UNITS_MISMATCH")
        self.assertEqual(before, (sim.owner, sim.epoch, sim.last_sequence, set(sim.seen_nonces), list(sim.sink.ledger)))

    def test_unknown_fault_is_a_programming_error(self):
        sim = make_sim()
        with self.assertRaises(ValueError):
            sim.handoff("edge-01", fault="meteor")


def _mut(path, value, reseal=False):
    """Return a factory for a valid bundle with one value replaced (no reseal: shape is checked first)."""
    def build():
        bundle = fg.base_bundle()
        if path is None:
            return value
        *parents, last = path.split(".")
        node = bundle
        for part in parents:
            node = node[part]
        node[last] = value
        return ms.seal(bundle) if reseal else bundle
    return build


R = ms.Reason
MALFORMED_BUNDLES = [
    # the bundle itself
    ("bundle None", _mut(None, None), R.MALFORMED_DOCUMENT),
    ("bundle list", _mut(None, []), R.MALFORMED_DOCUMENT),
    ("bundle str", _mut(None, "bundle"), R.MALFORMED_DOCUMENT),
    ("bundle int", _mut(None, 7), R.MALFORMED_DOCUMENT),
    ("bundle empty dict", _mut(None, {}), R.MISSING_FIELD),
    # handoff container
    ("handoff null", _mut("handoff", None), R.WRONG_TYPE),
    ("handoff str", _mut("handoff", "x"), R.WRONG_TYPE),
    ("handoff list", _mut("handoff", ["x"]), R.WRONG_TYPE),
    ("handoff int", _mut("handoff", 5), R.WRONG_TYPE),
    ("handoff empty", _mut("handoff", {}), R.MISSING_FIELD),
    # destination value
    ("to_executor list", _mut("handoff.to_executor", ["x"]), R.WRONG_TYPE),
    ("to_executor dict", _mut("handoff.to_executor", {"a": 1}), R.WRONG_TYPE),
    ("to_executor int", _mut("handoff.to_executor", 5), R.WRONG_TYPE),
    ("to_executor None", _mut("handoff.to_executor", None), R.WRONG_TYPE),
    ("to_executor bad identifier", _mut("handoff.to_executor", "bad id"), R.BAD_IDENTIFIER),
    ("to_executor unknown executor", _mut("handoff.to_executor", "ghost-01", reseal=True), R.WRONG_DESTINATION),
    # other nested containers and scalars
    ("mission null", _mut("mission", None), R.WRONG_TYPE),
    ("mission steps str", _mut("mission.steps", "wp-01"), R.WRONG_TYPE),
    ("progress completed str", _mut("progress.completed", "wp-01"), R.WRONG_TYPE),
    ("progress completed dict item", _mut("progress.completed", [{"a": 1}, "wp-02"]), R.WRONG_TYPE),
    ("effect ids nested list", _mut("progress.committed_effect_ids", [["a"], "b"]), R.WRONG_TYPE),
    ("ownership list", _mut("ownership", []), R.WRONG_TYPE),
    ("ownership owner list", _mut("ownership.state_owner", ["cloud-01"]), R.WRONG_TYPE),
    ("requirements null", _mut("requirements", None), R.WRONG_TYPE),
    ("requirements sensors int item", _mut("requirements.sensors", [1]), R.WRONG_TYPE),
    ("requirements sensor name list", _mut("requirements.sensors",
                                           [{"name": ["a"], "type": "range", "units": "m"}]), R.WRONG_TYPE),
    ("requirements units null", _mut("requirements.units", None), R.WRONG_TYPE),
    ("requirements capabilities nested", _mut("requirements.capabilities", [["a"]]), R.WRONG_TYPE),
    ("rollback null", _mut("rollback", None), R.WRONG_TYPE),
    ("rollback policy list", _mut("rollback.on_failure", ["park"]), R.BAD_VALUE),
    ("rollback policy dict", _mut("rollback.on_failure", {"park": 1}), R.BAD_VALUE),
    ("integrity null", _mut("integrity", None), R.WRONG_TYPE),
    ("integrity digest int", _mut("integrity.digest", 5), R.WRONG_TYPE),
    ("integrity digest list", _mut("integrity.digest", ["a"]), R.WRONG_TYPE),
    ("schema list", _mut("schema", ["mission-state/v1"]), R.UNSUPPORTED_SCHEMA_VERSION),
    ("schema dict", _mut("schema", {"v": 1}), R.UNSUPPORTED_SCHEMA_VERSION),
    ("simulated string", _mut("simulated", "true"), R.NOT_SIMULATED),
    ("nonce list", _mut("handoff.nonce", ["nonce-abcdef"]), R.WRONG_TYPE),
    ("sequence float", _mut("handoff.sequence", 1.0), R.WRONG_TYPE),
    ("sequence bool", _mut("handoff.sequence", True), R.WRONG_TYPE),
]


class MalformedBundleTests(unittest.TestCase):
    """A malformed bundle is a typed rejection: no exception, and no coordinator state changes."""

    @staticmethod
    def snapshot(sim):
        return (sim.owner, sim.epoch, sim.last_sequence, frozenset(sim.seen_nonces), list(sim.sink.ledger),
                sim.sink.epoch, sim.sink.owner, sim.sink.last_seq, sim.lease_expires_tick,
                {k: (e.active, e.epoch, e.next_seq) for k, e in sim.executors.items()})

    def test_table_is_broad(self):
        self.assertGreaterEqual(len(MALFORMED_BUNDLES), 35)

    def test_submit_bundle_returns_typed_rejection_and_changes_nothing(self):
        for label, build, reason in MALFORMED_BUNDLES:
            with self.subTest(case=label):
                sim = make_sim()
                sim.step("cloud-01")
                before = self.snapshot(sim)
                res = sim.submit_bundle(build())          # must not raise
                self.assertEqual(res["outcome"], "REJECTED")
                self.assertEqual(res["reason"], reason)
                self.assertEqual(res["verdict"], f"REJECTED:{reason}")
                self.assertIn(reason, ms.Reason.all())
                self.assertEqual(before, self.snapshot(sim))
                self.assertEqual(sim.owner, "cloud-01")
                self.assertEqual(sim.epoch, 1)
                self.assertEqual(sim.seen_nonces, set())
                self.assertIsNone(sim.last_bundle)

    def test_rejected_malformed_bundle_does_not_burn_the_nonce(self):
        sim = make_sim()
        sim.step("cloud-01")
        good = sim.build_bundle("edge-01")
        bad = copy.deepcopy(good)
        bad["handoff"] = None
        self.assertEqual(sim.submit_bundle(bad)["outcome"], "REJECTED")
        self.assertEqual(sim.submit_bundle(good)["outcome"], "COMPLETED")

    def test_validate_for_commit_raises_only_typed_rejections(self):
        for label, build, reason in MALFORMED_BUNDLES:
            if reason == R.WRONG_DESTINATION:
                continue  # needs the simulator's executor table
            with self.subTest(case=label):
                _, ctx = valid_pair()
                with self.assertRaises(ms.Rejection) as cm:
                    ms.validate_for_commit(build(), ctx)
                self.assertEqual(cm.exception.reason, reason)

    def test_handoff_api_with_malformed_destination_never_raises(self):
        for dest in (["edge-01"], {"a": 1}, 5, None, "bad id", "ghost-01"):
            with self.subTest(dest=dest):
                sim = make_sim()
                before = self.snapshot(sim)
                res = sim.handoff(dest)
                self.assertEqual(res["outcome"], "REJECTED")
                self.assertEqual(before, self.snapshot(sim))

    def test_malformed_renew_epoch_is_typed(self):
        sim = make_sim()
        for epoch in ("1", [1], 1.5, True):
            with self.subTest(epoch=epoch):
                self.assertEqual(sim.renew("cloud-01", epoch), ms.Reason.MALFORMED_EFFECT)

    def test_clis_reject_non_object_json_with_exit_two(self):
        import validate_bundle as vb
        for text in ("[]", "null", '"x"', "5"):
            with self.subTest(text=text), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "f.json"
                p.write_text(text, encoding="utf-8")
                for main in (hs.main, vb.main):
                    out, err = io.StringIO(), io.StringIO()
                    with redirect_stdout(out), redirect_stderr(err):
                        self.assertEqual(main([str(p)]), 2)


class IdDerivationTests(unittest.TestCase):
    """Derived handoff_id / nonce / effect_id satisfy the validator's patterns for ANY accepted task_id."""

    LONG_A = "t" + "a" * 61 + "1"      # 63 chars
    LONG_B = "t" + "a" * 61 + "2"      # differs only in the part that must be cut
    TASK_IDS = ["task.1", "mission:7", "task_1", "t" * 63, "t" * 64, LONG_A, LONG_B, "t" + "b" * 63,
                "a.b:c-d_e", "A"]

    def drive(self, task_id):
        """Five consecutive handoffs (cloud <-> edge) interleaved with four steps."""
        sim = make_sim(task_id=task_id)
        owner, other = "cloud-01", "edge-01"
        nonces, handoff_ids = [], []
        for i in range(5):
            res = sim.handoff(other)
            self.assertEqual(res["verdict"], "COMPLETED", (task_id, i, res))
            nonces.append(sim.last_bundle["handoff"]["nonce"])
            handoff_ids.append(sim.last_bundle["handoff"]["handoff_id"])
            owner, other = other, owner
            if i < 4:
                self.assertEqual(sim.step(owner), "ACCEPTED", (task_id, i))
        return sim, nonces, handoff_ids

    def test_every_pattern_and_limit_is_satisfied_for_awkward_task_ids(self):
        for task_id in self.TASK_IDS:
            with self.subTest(task_id=task_id):
                self.assertRegex(task_id, ms.ID_RE)
                sim, nonces, handoff_ids = self.drive(task_id)
                self.assertEqual(len(set(nonces)), 5)           # no spurious REPLAYED_NONCE
                self.assertEqual(len(set(handoff_ids)), 5)
                for n in nonces:
                    self.assertRegex(n, ms.NONCE_RE)
                for h in handoff_ids:
                    self.assertRegex(h, ms.ID_RE)
                ids = sim.sink.effect_ids
                self.assertEqual(len(ids), 4)
                self.assertEqual(len(set(ids)), 4)
                for eid in ids:
                    self.assertRegex(eid, ms.ID_RE)

    def test_task_ids_differing_only_in_the_cut_part_stay_distinct(self):
        firsts = {}
        for task_id in (self.LONG_A, self.LONG_B, "task.1", "task_1"):
            sim = make_sim(task_id=task_id)
            b = sim.build_bundle("edge-01")
            sim.step("cloud-01")
            firsts[task_id] = (b["handoff"]["nonce"], b["handoff"]["handoff_id"], sim.sink.effect_ids[0])
        for i, (ta, a) in enumerate(firsts.items()):
            for tb, b in list(firsts.items())[i + 1:]:
                for x, y in zip(a, b):
                    self.assertNotEqual(x, y, (ta, tb))

    def test_counter_is_never_truncated(self):
        sim = make_sim(task_id="t" * 64)
        b = sim.build_bundle("edge-01")
        self.assertTrue(b["handoff"]["nonce"].endswith("-0001"))
        self.assertTrue(b["handoff"]["handoff_id"].endswith("-h001"))
        sim.step("cloud-01")
        self.assertTrue(sim.sink.effect_ids[0].endswith("-e1-s0"))

    def test_long_executor_ids_still_give_valid_effect_ids(self):
        long_cloud = "c" + "x" * 63
        sim = make_sim(task_id="t" * 64, initial_owner=long_cloud,
                       executors=[fg.profile(long_cloud), fg.profile("edge-01")])
        self.assertEqual(sim.step(long_cloud), "ACCEPTED")
        self.assertRegex(sim.sink.effect_ids[0], ms.ID_RE)

    def test_fit_token_properties(self):
        pat = hs._ID_UNSAFE
        self.assertEqual(hs.fit_token("inspection-001", 59, pat), "inspection-001")        # unchanged
        self.assertEqual(hs.fit_token("a.b", 59, hs._NONCE_UNSAFE)[:3], "a_b")
        long = hs.fit_token("x" * 100, 20, pat)
        self.assertEqual(len(long), 20)
        self.assertEqual(long, hs.fit_token("x" * 100, 20, pat))                              # deterministic
        self.assertNotEqual(long, hs.fit_token("x" * 99 + "y", 20, pat))
        with self.assertRaises(ValueError):
            hs.fit_token("abc", 5, pat)

    def test_invalid_task_id_is_a_setup_error(self):
        for bad in ("1task", "bad id", "", "t" * 65, None, 5, ["t"]):
            with self.subTest(task_id=bad), self.assertRaises(ValueError):
                make_sim(task_id=bad)


def _script(mutate=None):
    script = copy.deepcopy(load(next(p for p in SCRIPTS if p.name == "handoff-happy-path.json")))
    if mutate:
        mutate(script)
    return script


def _op(**kw):
    return lambda sc: sc["ops"].insert(0, kw)


class ScriptValidationTests(unittest.TestCase):
    """Malformed scripts are ValueError (CLI exit 2) before anything runs; the clock never goes backwards."""

    BAD_TICKS = [-5, -1, 2.5, 1.0, True, False, "3", None, [1], {"n": 1}, 10 ** 18, hs.MAX_TICKS + 1]

    def test_bad_tick_values_are_script_errors(self):
        for n in self.BAD_TICKS:
            with self.subTest(n=n):
                with self.assertRaises(ValueError):
                    hs.run_script(_script(_op(op="tick", n=n)))
                sim = make_sim()
                with self.assertRaises(ValueError):
                    sim.tick(n)
                self.assertEqual(sim.now, 0)

    def test_tick_missing_n_or_with_expect_is_a_script_error(self):
        for op in ({"op": "tick"}, {"op": "tick", "n": 1, "expect": "x"}, {"op": "tick", "n": 1, "extra": 1}):
            with self.subTest(op=op), self.assertRaises(ValueError):
                hs.run_script(_script(_op(**op)))

    def test_zero_is_allowed_and_is_a_no_op(self):
        sim = make_sim()
        sim.tick(0)
        self.assertEqual(sim.now, 0)
        self.assertTrue(hs.run_script(_script(_op(op="tick", n=0)))["ok"])

    def test_clock_upper_bound(self):
        sim = make_sim()
        sim.tick(hs.MAX_TICKS)
        self.assertEqual(sim.now, hs.MAX_TICKS)
        with self.assertRaises(ValueError):
            sim.tick(1)
        self.assertEqual(sim.now, hs.MAX_TICKS)

    def test_other_malformed_ops_and_setup_are_script_errors(self):
        def op_at(i, **kw):
            def fn(sc):
                sc["ops"][i].update(kw)
            return fn
        def drop(i, key):
            return lambda sc: sc["ops"][i].pop(key)
        def setup(**kw):
            return lambda sc: sc["setup"].update(kw)
        cases = {
            "unknown op": _op(op="teleport", expect="x"),
            "op not a string": _op(op=["step"], expect="x"),
            "op not an object": lambda sc: sc["ops"].insert(0, "step"),
            "ops not a list": lambda sc: sc.update(ops={"a": 1}),
            "step without expect": drop(0, "expect"),
            "expect not a string": op_at(0, expect=5),
            "expect null": op_at(0, expect=None),
            "step without executor": drop(0, "executor"),
            "executor unknown": op_at(0, executor="ghost-01"),
            "executor list": op_at(0, executor=["cloud-01"]),
            "executor int": op_at(0, executor=5),
            "extra key": op_at(0, surprise=1),
            "handoff to list": _op(op="handoff", to=["edge-01"], expect="x"),
            "handoff fault unknown": _op(op="handoff", to="edge-01", fault="meteor", expect="x"),
            "handoff fault list": _op(op="handoff", to="edge-01", fault=["ack_lost"], expect="x"),
            "deliver_fence int": _op(op="handoff", to="edge-01", deliver_fence=1, expect="x"),
            "origin_available str": _op(op="handoff", to="edge-01", origin_available="no", expect="x"),
            "on_failure unknown": _op(op="handoff", to="edge-01", on_failure="explode", expect="x"),
            "steps_before_ack_loss negative": _op(op="handoff", to="edge-01", steps_before_ack_loss=-1, expect="x"),
            "steps_before_ack_loss bool": _op(op="handoff", to="edge-01", steps_before_ack_loss=True, expect="x"),
            "steps_before_ack_loss float": _op(op="handoff", to="edge-01", steps_before_ack_loss=1.0, expect="x"),
            "steps_before_ack_loss huge": _op(op="handoff", to="edge-01", steps_before_ack_loss=10 ** 18, expect="x"),
            "steps_before_ack_loss above steps": _op(op="handoff", to="edge-01", steps_before_ack_loss=6, expect="x"),
            "raw_effect missing effect": _op(op="raw_effect", expect="x"),
            "renew executor unknown": _op(op="renew", executor="ghost-01", expect="x"),
            "setup lease negative": setup(lease_ticks=-1),
            "setup lease bool": setup(lease_ticks=True),
            "setup lease str": setup(lease_ticks="5"),
            "setup lease float": setup(lease_ticks=2.5),
            "setup lease huge": setup(lease_ticks=10 ** 18),
            "setup bundle_ttl negative": setup(bundle_ttl=-3),
            "setup extra key": setup(surprise=1),
            "setup task_id invalid": setup(task_id="bad id"),
            "setup steps duplicate": setup(steps=["wp-01", "wp-01"]),
            "setup steps empty": setup(steps=[]),
            "setup steps not list": setup(steps="wp-01"),
            "setup owner unknown": setup(initial_owner="ghost-01"),
            "setup owner list": setup(initial_owner=["cloud-01"]),
            "setup executors not list": setup(executors={"a": 1}),
            "setup executor profile invalid": setup(executors=[{"executor_id": "cloud-01"}]),
            "setup executor entry not object": setup(executors=["cloud-01"]),
            "setup requirements not object": setup(requirements=[]),
            "setup null": lambda sc: sc.update(setup=None),
            "expect_final unknown key": lambda sc: sc["expect_final"].update(surprise=1),
            "expect_final not object": lambda sc: sc.update(expect_final=[]),
            "name missing": lambda sc: sc.pop("name"),
            "name not string": lambda sc: sc.update(name=5),
            "unknown top-level key": lambda sc: sc.update(surprise=1),
        }
        for label, mutate in cases.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                hs.run_script(_script(mutate))

    def test_valid_scripts_still_pass_after_strict_validation(self):
        for path in SCRIPTS:
            self.assertTrue(hs.run_script(load(path))["ok"], path.name)

    def test_cli_exits_two_for_bad_tick_and_other_script_errors(self):
        for label, mutate in (("tick -5", _op(op="tick", n=-5)), ("tick 2.5", _op(op="tick", n=2.5)),
                              ("tick true", _op(op="tick", n=True)), ("tick str", _op(op="tick", n="3")),
                              ("tick null", _op(op="tick", n=None)), ("tick huge", _op(op="tick", n=10 ** 18)),
                              ("bad profile", lambda sc: sc["setup"].update(executors=[{"executor_id": "x"}]))):
            with self.subTest(case=label), tempfile.TemporaryDirectory() as tmp:
                p = Path(tmp) / "s.json"
                p.write_text(json.dumps(_script(mutate)), encoding="utf-8")
                out, err = io.StringIO(), io.StringIO()
                with redirect_stdout(out), redirect_stderr(err):
                    self.assertEqual(hs.main([str(p)]), 2)
                self.assertEqual(out.getvalue(), "")


class CheckOrderTests(unittest.TestCase):
    """Pins a documented multi-fault difference between the simulator and validate_for_commit."""

    def test_unknown_destination_precedes_expiry_in_simulator_only(self):
        sim = make_sim()
        unknown = sim.build_bundle("ghost-01")
        known = sim.build_bundle("edge-01")
        sim.tick(20)                                  # both bundles are now past expires_tick (10)
        self.assertGreater(sim.now, unknown["handoff"]["expires_tick"])
        # simulator: destination lookup comes right after shape and digest
        self.assertEqual(sim.submit_bundle(unknown)["verdict"], "REJECTED:WRONG_DESTINATION")
        # validator with a known destination: freshness is reached and reported
        ctx = sim._context(sim.executors["edge-01"].profile)
        with self.assertRaises(ms.Rejection) as cm:
            ms.validate_for_commit(known, ctx)
        self.assertEqual(cm.exception.reason, ms.Reason.BUNDLE_EXPIRED)
        # single fault: the simulator agrees with the validator
        self.assertEqual(sim.submit_bundle(known)["verdict"], "REJECTED:BUNDLE_EXPIRED")


class SinkTests(unittest.TestCase):
    def test_malformed_effects_never_raise(self):
        sim = make_sim()
        for bad in (None, 3, [], {}, {"executor": "cloud-01"},
                    fg.effect("cloud-01", "1", 0, "wp-01", "x-0001"),
                    fg.effect("cloud-01", 1, -1, "wp-01", "x-0001"),
                    fg.effect("cloud-01", True, 0, "wp-01", "x-0001"),
                    fg.effect("bad id", 1, 0, "wp-01", "x-0001")):
            with self.subTest(effect=bad):
                self.assertEqual(sim.sink.submit(bad, 0), ms.Reason.MALFORMED_EFFECT)
        self.assertEqual(sim.sink.ledger, [])

    def test_rejected_effects_do_not_change_sink_state(self):
        sim = make_sim()
        snap = (list(sim.sink.ledger), set(sim.sink.accepted_ids), sim.sink.last_seq)
        sim.sink.submit(fg.effect("cloud-01", 1, 5, "wp-01", "x-0001"), 0)
        self.assertEqual(snap, (list(sim.sink.ledger), set(sim.sink.accepted_ids), sim.sink.last_seq))

    def test_lease_boundary_is_inclusive(self):
        sim = make_sim(lease_ticks=5)
        sim.tick(5)
        self.assertEqual(sim.step("cloud-01"), "ACCEPTED")
        sim.tick(1)
        self.assertEqual(sim.step("cloud-01"), ms.Reason.LEASE_EXPIRED)

    def test_expired_lease_cannot_be_renewed(self):
        sim = make_sim(lease_ticks=5)
        sim.tick(6)
        self.assertEqual(sim.renew("cloud-01"), ms.Reason.LEASE_EXPIRED)

    def test_non_owner_cannot_renew(self):
        sim = make_sim()
        self.assertEqual(sim.renew("edge-01", epoch=1), ms.Reason.NOT_STATE_OWNER)


class SimulationOnlyTests(unittest.TestCase):
    def test_modules_import_nothing_that_could_actuate_or_reach_a_network(self):
        banned = {"socket", "subprocess", "http", "urllib", "requests", "rclpy", "ctypes", "multiprocessing",
                  "asyncio", "threading", "random", "time", "datetime", "os"}
        for name in ("mission_state", "handoff_sim", "validate_bundle", "fixture_gen"):
            src = (Path(__file__).resolve().parent.parent / f"{name}.py").read_text(encoding="utf-8")
            imported = set()
            for line in src.splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0] in ("import", "from"):
                    imported.add(parts[1].split(".")[0])
            self.assertEqual(sorted(imported & banned), [], name)

    def test_bundles_and_reports_are_labelled_simulated(self):
        self.assertIs(fg.base_bundle()["simulated"], True)
        rep = hs.run_script(load(SCRIPTS[0]))
        self.assertEqual(rep["time_unit"], "logical_tick")


class CliTests(unittest.TestCase):
    def run_cli(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = hs.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_default_run_exits_zero(self):
        code, out, _ = self.run_cli([])
        self.assertEqual(code, 0)
        reports = [json.loads(l) for l in out.splitlines()]
        self.assertEqual(len(reports), len(SCRIPTS))
        self.assertTrue(all("trace" not in r for r in reports))

    def test_trace_flag_includes_events(self):
        code, out, _ = self.run_cli(["--trace", str(SCRIPTS[0])])
        self.assertEqual(code, 0)
        self.assertIn("trace", json.loads(out))

    def test_failed_expectation_exits_one(self):
        script = copy.deepcopy(load(SCRIPTS[0]))
        script["expect_final"]["epoch"] = 99
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.json"
            p.write_text(json.dumps(script), encoding="utf-8")
            self.assertEqual(self.run_cli([str(p)])[0], 1)

    def test_invalid_input_exits_two(self):
        self.assertEqual(self.run_cli(["/nonexistent/script.json"])[0], 2)
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "s.json"
            p.write_text(json.dumps({"fixture_kind": "nope"}), encoding="utf-8")
            self.assertEqual(self.run_cli([str(p)])[0], 2)


if __name__ == "__main__":
    unittest.main()
