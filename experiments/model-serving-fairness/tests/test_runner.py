import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import run_simulation  # noqa: E402

SUMMARY_KEYS = {
    "label", "seed", "scheduler", "placement", "worker_failures", "end_time_s", "totals",
    "deadline_miss_rate", "goodput_rate", "quiet_clients_deadline_miss_rate", "latency_s",
    "jain_goodput_index", "starved_requests", "clients_with_no_service", "cache",
    "worker_busy_fraction", "clients",
}
CLIENT_KEYS = {
    "arrivals", "rejected", "dropped", "completed", "on_time", "late", "unfinished",
    "deadline_miss_rate", "goodput_ratio", "latency_s", "max_queue_wait_s", "starved_requests",
    "starved_fraction", "no_service",
}


def call(*argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = run_simulation.main(list(argv))
    return code, out.getvalue(), err.getvalue()


class RunnerTests(unittest.TestCase):
    def test_default_markdown_deterministic(self):
        c1, o1, _ = call("--seeds", "1")
        c2, o2, _ = call("--seeds", "1")
        self.assertEqual((c1, c2), (0, 0))
        self.assertEqual(o1, o2)
        self.assertIn("SIMULATED", o1)
        self.assertIn("| seed | scheduler | placement |", o1)

    def test_json_schema_stable(self):
        code, out, _ = call("--seeds", "1", "--schedulers", "fifo", "--placements", "first_idle",
                            "--json-out", "-")
        self.assertEqual(code, 0)
        rep = json.loads(out)
        self.assertEqual(set(rep), {"label", "schema_version", "disclaimer", "scenario", "seeds",
                                    "schedulers", "placements", "config", "runs"})
        run = rep["runs"][0]
        self.assertEqual(set(run), SUMMARY_KEYS)
        self.assertEqual(set(run["totals"]), {
            "arrivals", "admitted", "rejected", "dropped", "completed", "on_time", "late",
            "unfinished", "retried_after_worker_failure"})
        self.assertEqual(set(run["latency_s"]), {"count", "p50", "p95", "p99", "mean", "max"})
        self.assertEqual(set(run["cache"]), {"hits", "misses", "hit_rate", "evictions"})
        for c in run["clients"].values():
            self.assertEqual(set(c), CLIENT_KEYS)

    def test_files_written(self):
        with tempfile.TemporaryDirectory() as d:
            j, m = os.path.join(d, "o.json"), os.path.join(d, "o.md")
            code, out, _ = call("--seeds", "1", "--schedulers", "fifo", "--placements",
                                "first_idle", "--json-out", j, "--markdown-out", m)
            self.assertEqual((code, out), (0, ""))
            with open(j, encoding="utf-8") as fh:
                self.assertEqual(json.load(fh)["label"], "SIMULATED")
            with open(m, encoding="utf-8") as fh:
                self.assertTrue(fh.read().startswith("# Model-serving fairness simulation"))

    def test_worker_down_flag_recorded(self):
        code, out, _ = call("--seeds", "1", "--schedulers", "fifo", "--placements", "first_idle",
                            "--worker-down", "0:10:20", "--json-out", "-")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["runs"][0]["worker_failures"],
                         [{"worker": 0, "start": 10.0, "end": 20.0}])

    def test_invalid_inputs_exit_2(self):
        for argv in (["--schedulers", "lifo"], ["--placements", "random"], ["--seeds", "abc"],
                     ["--seeds", ""], ["--worker-down", "bad"], ["--worker-down", "9:1:2"],
                     ["--config", "/nonexistent/config.json"]):
            with self.subTest(argv=argv):
                code, out, err = call(*argv)
                self.assertEqual(code, 2)
                self.assertTrue(err.startswith("error:"))
                self.assertEqual(out, "")

    def test_shipped_scenarios_parse(self):
        for name in ("default_fleet.json", "cache_pressure.json"):
            with self.subTest(name=name):
                code, _, _ = call("--config", os.path.join(HERE, "data", name), "--seeds", "1",
                                  "--schedulers", "fifo", "--placements", "first_idle")
                self.assertEqual(code, 0)


    def test_worker_down_cli_adjacent_windows_keep_worker_down(self):
        # One worker, one request at t=25 (service 1.0). Windows 0:10:20 and 0:20:30 are
        # back-to-back, so the request cannot start before t=30 -> latency 6.0 s (not 1.0 s).
        cfg = {"name": "t", "seed": 1, "duration": 60.0, "workers": 1, "cache_capacity": 1.0,
               "models": {"m": {"service_time": 1.0}},
               "clients": [{"id": "c", "arrival": {"kind": "fixed", "times": [25.0]},
                            "models": ["m"], "deadline": 100.0}]}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cfg.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh)
            code, out, _ = call("--config", path, "--seeds", "1", "--schedulers", "fifo",
                                "--placements", "first_idle", "--worker-down", "0:10:20",
                                "--worker-down", "0:20:30", "--json-out", "-")
        self.assertEqual(code, 0)
        run = json.loads(out)["runs"][0]
        self.assertEqual(len(run["worker_failures"]), 2)
        self.assertEqual(run["latency_s"]["p50"], 6.0)

    def test_worker_down_cli_adjacent_to_config_window(self):
        cfg = {"name": "t", "seed": 1, "duration": 60.0, "workers": 1, "cache_capacity": 1.0,
               "models": {"m": {"service_time": 1.0}},
               "failures": [{"worker": 0, "start": 10.0, "end": 20.0}],
               "clients": [{"id": "c", "arrival": {"kind": "fixed", "times": [25.0]},
                            "models": ["m"], "deadline": 100.0}]}
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "cfg.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(cfg, fh)
            code, out, _ = call("--config", path, "--seeds", "1", "--schedulers", "fifo",
                                "--placements", "first_idle", "--worker-down", "0:20:30",
                                "--json-out", "-")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["runs"][0]["latency_s"]["p50"], 6.0)


if __name__ == "__main__":
    unittest.main()
