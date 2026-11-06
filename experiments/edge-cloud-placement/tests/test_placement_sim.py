"""Tests for the SIMULATION in placement_sim.py. Standard library unittest only.

Most scenarios use zero jitter and zero random faults so expected counts can be
derived by hand; random behaviour is only used for the determinism tests.
"""

import contextlib
import copy
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import placement_sim as ps  # noqa: E402

N = 20


def base_config(**overrides):
    """Fault-free, jitter-free baseline: local 100 ms; remote RTT = 2*20 + 10 = 50 ms."""
    cfg = {
        "schema_version": 1,
        "seed": 7,
        "stream": {"num_requests": N, "interval_ms": 1000, "deadline_ms": 200},
        "local": {"memory_mb": 4096, "model_memory_mb": 1024,
                  "compute_base_ms": 100, "compute_jitter_ms": 0},
        "remote": {"model_memory_mb": 8192, "memory_mb": 16384,
                   "compute_base_ms": 10, "compute_jitter_ms": 0},
        "network": {"one_way_base_ms": 20, "one_way_jitter_ms": 0},
        "predictor": {"prior_rtt_ms": 50, "alpha": 0.5, "margin_ms": 10,
                      "probe_interval_ms": 3000},
    }
    for path, value in overrides.items():
        node = cfg
        keys = path.split(".")
        for k in keys[:-1]:
            node = node[k]
        node[keys[-1]] = value
    return cfg


def run(cfg, policy):
    c = ps.validate_config(cfg)
    return ps.run_policy(c, policy)


class HappyPathTests(unittest.TestCase):
    def test_all_policies_fully_on_time_without_faults(self):
        for policy in ps.POLICY_NAMES:
            s, _ = run(base_config(), policy)
            self.assertEqual(s["on_time_applied"], N, policy)
            self.assertEqual(s["deadline_miss"], 0, policy)
            self.assertEqual(s["stale_rejected"], 0, policy)
            self.assertEqual(s["on_time_rate"], 1.0, policy)

    def test_latencies_match_hand_computation(self):
        s, _ = run(base_config(), "always_local")
        self.assertEqual(s["simulated_latency_ms"]["p50"], 100)
        s, _ = run(base_config(), "always_remote")
        self.assertEqual(s["simulated_latency_ms"]["p50"], 50)

    def test_response_exactly_at_deadline_is_on_time(self):
        cfg = base_config(**{"stream.deadline_ms": 100})   # local finishes at exactly 100
        s, _ = run(cfg, "always_local")
        self.assertEqual(s["on_time_applied"], N)
        cfg = base_config(**{"stream.deadline_ms": 99})
        s, _ = run(cfg, "always_local")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["rejected_by_reason"]["late_after_deadline"], N)

    def test_deadline_aware_prefers_remote_when_it_fits_and_local_when_not(self):
        s, _ = run(base_config(), "deadline_aware")
        self.assertEqual(s["routed_remote"], N)
        # Budget 55 < prior 50 + margin 10 -> predictor says no -> local (which then misses).
        s, log = run(base_config(**{"stream.deadline_ms": 55}), "deadline_aware")
        routes = [r for r in log if r["kind"] == "route"]
        self.assertEqual(routes[1]["target"], "local")
        self.assertEqual(routes[1]["why"], "predicted_miss")


class StaleAndInvalidResponseTests(unittest.TestCase):
    def test_late_response_is_rejected_and_logged(self):
        cfg = base_config(**{"network.one_way_base_ms": 100})   # RTT 210 > 200
        s, log = run(cfg, "always_remote")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["stale_rejected"], N)
        self.assertEqual(s["rejected_by_reason"]["late_after_deadline"], N)
        self.assertEqual(s["deadline_miss_causes"]["late_response"], N)
        sinks = [r for r in log if r["kind"] == "sink"]
        self.assertTrue(all(r["decision"] == "rejected"
                            and r["reason"] == "late_after_deadline" for r in sinks))

    def test_duplicate_response_id_is_rejected(self):
        cfg = base_config(**{"network.duplicate_probability": 1.0})
        s, _ = run(cfg, "always_remote")
        self.assertEqual(s["on_time_applied"], N)
        self.assertEqual(s["rejected_by_reason"]["duplicate_response_id"], N)
        self.assertEqual(s["sink_decisions_total"], 2 * N)

    def test_unknown_request_id_is_rejected(self):
        cfg = base_config(**{"network.spurious_response_probability": 1.0})
        s, log = run(cfg, "always_local")
        self.assertEqual(s["rejected_by_reason"]["unknown_request_id"], N)
        self.assertEqual(s["on_time_applied"], N)          # real requests unaffected
        ghosts = [r for r in log if r["kind"] == "sink" and r["request_id"].startswith("ghost-")]
        self.assertEqual(len(ghosts), N)
        self.assertTrue(all(r["decision"] == "rejected" for r in ghosts))

    def test_local_only_request_rejects_remote_response(self):
        cfg = base_config(**{"stream.local_only_probability": 1.0})
        s, _ = run(cfg, "always_remote")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["rejected_by_reason"]["ineligible_source"], N)
        self.assertEqual(s["deadline_miss_causes"]["ineligible_source"], N)
        # Policies that respect the flag are unaffected.
        for policy in ("deadline_aware", "hedged_fallback", "always_local"):
            s, _ = run(cfg, policy)
            self.assertEqual(s["on_time_applied"], N, policy)
            self.assertEqual(s["routed_remote"], 0, policy)


class SinkUnitTests(unittest.TestCase):
    def setUp(self):
        cfg = ps.validate_config(base_config())
        self.requests, _ = ps.build_requests(cfg)
        self.sink = ps.NonActuatingSink(self.requests)

    def resp(self, i, uid=None, source="local"):
        rid = self.requests[i].request_id
        return ps.Response(uid or f"{rid}:{source}", rid, source, "action")

    def test_superseded_request_is_rejected(self):
        r0, r1 = self.requests[0], self.requests[1]
        # Request 1 is applied first (within its deadline) ...
        self.assertEqual(self.sink.submit(self.resp(1), r1.capture_ms + 50)["decision"], "would_apply")
        # ... then request 0's answer arrives, still before ITS deadline, but superseded.
        rec = self.sink.submit(self.resp(0), r0.capture_ms + 100)
        self.assertEqual((rec["decision"], rec["reason"]), ("rejected", "superseded_request"))

    def test_check_order_unknown_then_duplicate_then_late(self):
        r0 = self.requests[0]
        late = r0.deadline_abs_ms + 1
        rec = self.sink.submit(ps.Response("u", "nope", "remote", "action"), 5)
        self.assertEqual(rec["reason"], "unknown_request_id")
        self.assertEqual(self.sink.submit(self.resp(0), 10)["decision"], "would_apply")
        # Same ID again, and also late: duplicate wins because it is checked first.
        self.assertEqual(self.sink.submit(self.resp(0, uid="other"), late)["reason"],
                         "duplicate_response_id")
        # Re-delivery of the very same response uid is also a duplicate.
        self.assertEqual(self.sink.submit(self.resp(1, uid="same"), self.requests[1].capture_ms + 5)["decision"],
                         "would_apply")
        self.assertEqual(self.sink.submit(self.resp(1, uid="same"), self.requests[1].capture_ms + 6)["reason"],
                         "duplicate_response_id")

    def test_rejected_late_response_does_not_block_a_later_valid_one(self):
        r0 = self.requests[0]
        self.assertEqual(self.sink.submit(self.resp(0, source="remote"), r0.deadline_abs_ms + 1)["reason"],
                         "late_after_deadline")
        # Nothing was applied, so an on-time answer from another path is still accepted.
        self.assertEqual(self.sink.submit(self.resp(0, source="local"), r0.deadline_abs_ms)["decision"],
                         "would_apply")

    def test_sink_never_actuates(self):
        self.assertIs(ps.NonActuatingSink.actuated, False)
        self.sink.submit(self.resp(0), 10)
        self.assertTrue(all(r["actuated"] is False and r["label"] == "SIMULATION"
                            for r in self.sink.records))
        self.assertFalse(hasattr(self.sink, "send") or hasattr(self.sink, "actuate"))


class EligibilityTests(unittest.TestCase):
    def test_ineligible_remote_is_rejected_by_remote_and_counted(self):
        cfg = base_config(**{"remote.memory_mb": 4096})   # needs 8192
        s, _ = run(cfg, "always_remote")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["remote_rejects"], {"ineligible_memory": N})
        self.assertEqual(s["deadline_miss_causes"]["remote_rejected"], N)

    def test_deadline_aware_routes_local_when_remote_known_ineligible(self):
        cfg = base_config(**{"remote.memory_mb": 4096})
        s, log = run(cfg, "deadline_aware")
        self.assertEqual(s["routed_remote"], 0)
        self.assertEqual(s["on_time_applied"], N)
        self.assertEqual({r["why"] for r in log if r["kind"] == "route"},
                         {"remote_ineligible_or_blocked"})

    def test_stale_capability_advert_is_recovered_by_hedged_fallback_only(self):
        # Remote loses memory at t=5000 but the advertisement lags by 3000 ms, so
        # requests captured in [5000, 8000) are sent remote and explicitly rejected.
        sched = [{"from_ms": 0, "memory_mb": 16384}, {"from_ms": 5000, "memory_mb": 1024}]
        cfg = base_config(**{"remote.memory_mb": 0, "remote.advert_lag_ms": 3000})
        del cfg["remote"]["memory_mb"]
        cfg["remote"]["memory_schedule"] = sched
        plain, _ = run(cfg, "deadline_aware")
        hedged, _ = run(cfg, "hedged_fallback")
        self.assertEqual(plain["remote_rejects"], {"ineligible_memory": 1})  # blocked after 1st reject
        self.assertEqual(plain["deadline_miss"], 1)
        self.assertEqual(hedged["deadline_miss"], 0)
        self.assertEqual(hedged["fallback_count"], 1)

    def test_local_ineligible_means_no_viable_executor(self):
        cfg = base_config(**{"local.memory_mb": 512})     # needs 1024
        s, _ = run(cfg, "always_local")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["deadline_miss_causes"]["no_viable_executor"], N)
        # With an eligible remote, deadline-aware still serves the stream.
        s, _ = run(cfg, "deadline_aware")
        self.assertEqual(s["on_time_applied"], N)

    def test_both_ineligible(self):
        cfg = base_config(**{"local.memory_mb": 512, "remote.memory_mb": 1024})
        s, _ = run(cfg, "deadline_aware")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["deadline_miss_causes"]["no_viable_executor"], N)

    def test_remote_random_reject_triggers_hedge_fallback(self):
        cfg = base_config(**{"remote.reject_probability": 1.0})
        s, _ = run(cfg, "hedged_fallback")
        self.assertEqual(s["remote_rejects"], {"overloaded": N})
        self.assertEqual(s["on_time_applied"], N)
        self.assertEqual(s["fallback_count"], N)
        s, _ = run(cfg, "deadline_aware")
        self.assertEqual(s["on_time_applied"], 0)


class OutageTests(unittest.TestCase):
    TOTAL = [{"start_ms": 0, "end_ms": 10_000_000}]

    def test_total_outage(self):
        cfg = base_config(**{"network.outages": self.TOTAL})
        a, _ = run(cfg, "always_remote")
        self.assertEqual(a["on_time_applied"], 0)
        self.assertEqual(a["deadline_miss_causes"]["no_response"], N)
        self.assertEqual(a["remote_timeouts"], N)
        loc, _ = run(cfg, "always_local")
        self.assertEqual(loc["on_time_applied"], N)
        h, _ = run(cfg, "hedged_fallback")
        self.assertEqual(h["on_time_applied"], N)
        # Fallbacks cover the first request and each probe; once the predictor has
        # learned the remote is dead, later requests are routed local directly.
        self.assertGreaterEqual(h["fallback_count"], 1)
        self.assertLess(h["fallback_count"], N)
        self.assertEqual(h["fallback_count"], h["fallback_launched"])
        self.assertEqual(h["routed_local"] + h["routed_remote"], N)
        d, _ = run(cfg, "deadline_aware")
        # Misses only on the first request and on periodic probes (every >=3000 ms).
        self.assertGreater(d["on_time_applied"], a["on_time_applied"])
        self.assertLess(d["on_time_applied"], N)

    def test_outage_and_recovery_for_deadline_aware(self):
        # Outage covers captures at 2000..5999; probes resume after it ends.
        cfg = base_config(**{"network.outages": [{"start_ms": 2000, "end_ms": 6000}]})
        s, log = run(cfg, "deadline_aware")
        routes = {r["request_id"]: r for r in log if r["kind"] == "route"}
        late_routes = [routes[f"req-{i:06d}"] for i in range(8, N)]
        self.assertTrue(all(r["target"] == "remote" for r in late_routes))  # recovered
        self.assertGreater(s["remote_timeouts"], 0)
        self.assertEqual(s["by_capture_time"]["during_outage_or_recovery"]["requests"], 4)

    def test_recovery_window_slows_the_link(self):
        cfg = base_config(**{"network.outages": [{"start_ms": 0, "end_ms": 1}],
                             "network.recovery_ms": 5000,
                             "network.recovery_delay_factor": 10.0})
        s, _ = run(cfg, "always_remote")
        # req 0..: first request lost (outage at t=0). Requests 1..5 are in recovery:
        # one way 20*10=200 -> RTT >> 200 ms deadline -> late. Later ones are on time.
        self.assertGreaterEqual(s["rejected_by_reason"]["late_after_deadline"], 4)
        self.assertGreater(s["on_time_applied"], 0)

    def test_message_loss(self):
        cfg = base_config(**{"network.loss_probability": 1.0})
        s, _ = run(cfg, "always_remote")
        self.assertEqual(s["on_time_applied"], 0)
        self.assertEqual(s["remote_timeouts"], N)


class DeterminismTests(unittest.TestCase):
    def noisy(self, seed):
        cfg = ps.load_config(ROOT / "configs" / "default.json")
        cfg["seed"] = seed
        return cfg

    def test_same_seed_same_bytes(self):
        a, la = ps.run_all(self.noisy(5))
        b, lb = ps.run_all(self.noisy(5))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(json.dumps(la, sort_keys=True), json.dumps(lb, sort_keys=True))

    def test_different_seed_different_output(self):
        a, _ = ps.run_all(self.noisy(5))
        b, _ = ps.run_all(self.noisy(6))
        self.assertNotEqual(a["policies"], b["policies"])
        self.assertNotEqual(a["config_sha256"], b["config_sha256"])

    def test_policy_order_does_not_change_results(self):
        full, _ = ps.run_all(self.noisy(9))
        one, _ = ps.run_all(self.noisy(9), ["hedged_fallback"])
        self.assertEqual(full["policies"]["hedged_fallback"], one["policies"]["hedged_fallback"])

    def test_accounting_invariants_on_noisy_run(self):
        report, logs = ps.run_all(self.noisy(11))
        for name, s in report["policies"].items():
            self.assertEqual(s["on_time_applied"] + s["deadline_miss"], s["requests_total"], name)
            self.assertEqual(sum(s["deadline_miss_causes"].values()), s["deadline_miss"], name)
            applied = [r for r in logs[name] if r["kind"] == "sink" and r["decision"] == "would_apply"]
            self.assertEqual(len(applied), s["on_time_applied"], name)
            self.assertEqual(len({r["request_id"] for r in applied}), len(applied), name)
            self.assertTrue(all(r["actuated"] is False for r in logs[name] if r["kind"] == "sink"))
            self.assertLessEqual(s["fallback_count"], s["fallback_launched"], name)


class OutputLabelTests(unittest.TestCase):
    def test_report_and_log_are_labelled_simulation(self):
        report, logs = ps.run_all(base_config())
        self.assertEqual(report["label"], "SIMULATION")
        self.assertTrue(report["simulation"])
        self.assertIs(report["measured"], False)
        self.assertIn("SIMULATED", report["banner"])
        for recs in logs.values():
            self.assertTrue(all(r["label"] == "SIMULATION" for r in recs))
        self.assertIn("SIMULATION", ps.format_table(report))


class ConfigValidationTests(unittest.TestCase):
    def assertInvalid(self, cfg, fragment=""):
        with self.assertRaises(ps.ConfigError) as cm:
            ps.validate_config(cfg)
        self.assertIn(fragment, str(cm.exception))

    def test_deadline_zero_or_negative(self):
        self.assertInvalid(base_config(**{"stream.deadline_ms": 0}), "deadline_ms")
        self.assertInvalid(base_config(**{"stream.deadline_ms": -5}), "deadline_ms")
        self.assertInvalid(base_config(**{"stream.deadline_ms": {"min": 0, "max": 10}}), "min")
        self.assertInvalid(base_config(**{"stream.deadline_ms": {"min": 50, "max": 10}}), "max")
        with self.assertRaises(ps.ConfigError):
            ps.run_all(base_config(**{"stream.deadline_ms": 0}))

    def test_not_an_object_and_bad_version(self):
        self.assertInvalid([], "object")
        cfg = base_config()
        cfg["schema_version"] = 2
        self.assertInvalid(cfg, "schema_version")

    def test_missing_sections_and_keys(self):
        cfg = base_config()
        del cfg["network"]
        self.assertInvalid(cfg, "network")
        cfg = base_config()
        del cfg["local"]["compute_base_ms"]
        self.assertInvalid(cfg, "compute_base_ms")

    def test_unknown_keys_rejected(self):
        cfg = base_config()
        cfg["stream"]["deadlin_ms"] = 5
        self.assertInvalid(cfg, "unknown key")
        cfg = base_config()
        cfg["bogus"] = 1
        self.assertInvalid(cfg, "unknown key")

    def test_bad_numbers(self):
        for path, bad in [("network.loss_probability", 1.5), ("network.loss_probability", -0.1),
                          ("stream.num_requests", 0), ("stream.interval_ms", 0),
                          ("local.compute_base_ms", -1), ("remote.reject_probability", 2),
                          ("network.one_way_base_ms", True), ("network.one_way_base_ms", "10"),
                          ("network.one_way_base_ms", float("nan")),
                          ("network.one_way_base_ms", float("inf")),
                          ("stream.interval_ms", 1.5), ("network.recovery_delay_factor", 0.5)]:
            with self.subTest(path=path, bad=bad):
                self.assertInvalid(base_config(**{path: bad}))

    def test_seed_must_be_int(self):
        for bad in (1.5, "7", None, True):
            with self.subTest(bad=bad):
                self.assertInvalid(base_config(seed=bad), "seed")

    def test_outage_validation(self):
        self.assertInvalid(base_config(**{"network.outages": [{"start_ms": 10, "end_ms": 10}]}), "end_ms")
        self.assertInvalid(base_config(**{"network.outages": [{"start_ms": -1, "end_ms": 10}]}), "start_ms")
        self.assertInvalid(base_config(**{"network.outages": [
            {"start_ms": 0, "end_ms": 100}, {"start_ms": 50, "end_ms": 200}]}), "overlap")
        self.assertInvalid(base_config(**{"network.outages": "none"}), "list")

    def test_memory_config_validation(self):
        cfg = base_config()
        cfg["remote"]["memory_schedule"] = [{"from_ms": 0, "memory_mb": 1}]
        self.assertInvalid(cfg, "exactly one")
        cfg = base_config()
        del cfg["remote"]["memory_mb"]
        self.assertInvalid(cfg, "exactly one")
        cfg["remote"]["memory_schedule"] = [{"from_ms": 5, "memory_mb": 1}]
        self.assertInvalid(cfg, "from_ms must be 0")
        cfg["remote"]["memory_schedule"] = [{"from_ms": 0, "memory_mb": 1}, {"from_ms": 0, "memory_mb": 2}]
        self.assertInvalid(cfg, "increasing")

    def test_policy_validation(self):
        self.assertInvalid(base_config(policies=["nope"]), "unknown policy")
        self.assertInvalid(base_config(policies=[]), "non-empty")
        self.assertInvalid(base_config(policies=["always_local", "always_local"]), "duplicates")

    def test_valid_config_is_normalised_and_defaults_applied(self):
        cfg = ps.validate_config(base_config())
        self.assertEqual(cfg["policies"], list(ps.POLICY_NAMES))
        self.assertEqual(cfg["network"]["outages"], [])
        self.assertEqual(cfg["stream"]["deadline_min_ms"], 200)
        self.assertIsNone(cfg["hedge"]["delay_ms"])

    def test_shipped_default_config_is_valid(self):
        ps.validate_config(ps.load_config(ROOT / "configs" / "default.json"))

    def test_input_not_mutated(self):
        raw = base_config()
        before = copy.deepcopy(raw)
        ps.run_all(raw)
        self.assertEqual(raw, before)


class HelperTests(unittest.TestCase):
    def test_percentile(self):
        self.assertIsNone(ps.percentile([], 0.5))
        self.assertEqual(ps.percentile([5, 1, 3, 2, 4], 0.5), 3)
        self.assertEqual(ps.percentile([5, 1, 3, 2, 4], 0.95), 5)
        with self.assertRaises(ValueError):
            ps.percentile([1], 0)

    def test_no_applied_requests_give_null_latency(self):
        s, _ = run(base_config(**{"network.loss_probability": 1.0}), "always_remote")
        self.assertIsNone(s["simulated_latency_ms"]["mean"])
        self.assertIsNone(s["simulated_latency_ms"]["p95"])


class CliTests(unittest.TestCase):
    def test_cli_writes_report_and_logs(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "cfg.json"
            cfg_path.write_text(json.dumps(base_config()))
            out = Path(tmp) / "report.json"
            logs = Path(tmp) / "logs"
            with contextlib.redirect_stdout(io.StringIO()):
                rc = ps.main(["--config", str(cfg_path), "--out", str(out),
                              "--log-dir", str(logs), "--json"])
            self.assertEqual(rc, 0)
            report = json.loads(out.read_text())
            self.assertEqual(report["label"], "SIMULATION")
            self.assertEqual(sorted(p.name for p in logs.iterdir()),
                             sorted(f"{n}.decisions.jsonl" for n in ps.POLICY_NAMES))
            first = json.loads((logs / "always_local.decisions.jsonl").read_text().splitlines()[0])
            self.assertEqual(first["label"], "SIMULATION")

    def test_cli_invalid_config_exit_code_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "bad.json"
            p.write_text(json.dumps(base_config(**{"stream.deadline_ms": 0})))
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(ps.main(["--config", str(p)]), 2)
                p.write_text("{not json")
                self.assertEqual(ps.main(["--config", str(p)]), 2)
                self.assertEqual(ps.main(["--config", str(Path(tmp) / "missing.json")]), 2)

    def test_cli_policy_filter(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "cfg.json"
            p.write_text(json.dumps(base_config()))
            out = Path(tmp) / "r.json"
            with contextlib.redirect_stdout(io.StringIO()):
                ps.main(["--config", str(p), "--out", str(out), "--policy", "always_local"])
            self.assertEqual(list(json.loads(out.read_text())["policies"]), ["always_local"])


if __name__ == "__main__":
    unittest.main()
