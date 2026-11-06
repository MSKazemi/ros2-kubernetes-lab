import contextlib
import io
import json
import os
import tempfile
import unittest

from seqprobe.__main__ import main
from seqprobe.analysis import analyze_events, all_ok
from seqprobe.errors import LogFormatError
from seqprobe.events import read_events
from seqprobe.synthetic import simulate


def lines(events):
    return [e.to_json_line() for e in events]


class SyntheticTests(unittest.TestCase):
    def test_clean(self):
        events, v = simulate(count=8)
        self.assertTrue(v.ok)
        self.assertTrue(all_ok(analyze_events(read_events(lines(events)))))
        self.assertTrue(all(e.detail["synthetic"] for e in events if e.event == "start"))

    def test_each_fault_is_detected(self):
        cases = {
            "gap": (dict(drop=[3]), dict(missing=1, duplicates=0, reordered=0, completion="timeout")),
            "tail": (dict(drop=[9]), dict(missing=1, completion="timeout")),
            "dup": (dict(duplicate=[2]), dict(duplicates=1, completion="complete")),
            "swap": (dict(swap=[4]), dict(reordered=1, completion="complete")),
        }
        for name, (faults, expect) in cases.items():
            with self.subTest(name):
                events, v = simulate(count=10, **faults)
                self.assertFalse(v.ok)
                # the offline analysis of the written log must agree with the live verdict
                (res,) = analyze_events(read_events(lines(events))).values()
                for key, value in expect.items():
                    self.assertEqual(res[key], value, key)
                    self.assertEqual(getattr(v, key), value, key)

    def test_nothing_delivered_times_out(self):
        events, v = simulate(count=4, drop=[0, 1, 2, 3])
        self.assertEqual((v.completion, v.unique, v.missing), ("timeout", 0, 4))
        self.assertEqual([e.event for e in events].count("timeout"), 1)

    def test_deterministic(self):
        a, _ = simulate(count=6, drop=[1], seed=5)
        b, _ = simulate(count=6, drop=[1], seed=5)
        self.assertEqual(lines(a), lines(b))

    def test_unknown_count_leaves_tail_loss_undetected(self):
        events, v = simulate(count=5, drop=[4], expect_count=False)
        self.assertEqual(v.missing, 0)
        self.assertFalse(v.tail_loss_detectable)
        self.assertFalse(v.ok)


class AnalysisTests(unittest.TestCase):
    def test_publisher_only_log_is_rejected(self):
        events, _ = simulate(count=3)
        pub_only = [e for e in events if e.role == "publisher"]
        with self.assertRaises(LogFormatError):
            analyze_events(pub_only)

    def test_expected_count_falls_back_to_publisher_start(self):
        events, _ = simulate(count=4, expect_count=False)
        (res,) = analyze_events(events).values()
        self.assertEqual(res["expected_count"], 4)

    def test_argument_overrides_logged_count(self):
        events, _ = simulate(count=4)
        (res,) = analyze_events(events, expected_count=6).values()
        self.assertEqual((res["expected_count"], res["missing"]), (6, 2))


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_simulate_then_analyze_exit_codes(self):
        with tempfile.TemporaryDirectory() as d:
            good, bad = os.path.join(d, "good.jsonl"), os.path.join(d, "bad.jsonl")
            self.assertEqual(self.run_cli("simulate", "--count", "5", "--out", good)[0], 0)
            self.assertEqual(self.run_cli("simulate", "--count", "5", "--drop", "2", "--out", bad)[0], 0)
            code, out, _ = self.run_cli("analyze", good)
            self.assertEqual(code, 0)
            self.assertTrue(list(json.loads(out).values())[0]["ok"])
            code, out, _ = self.run_cli("analyze", bad)
            self.assertEqual(code, 1)
            self.assertEqual(list(json.loads(out).values())[0]["missing_ranges"], [[2, 2]])

    def test_malformed_log_line_exits_2(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.jsonl")
            self.run_cli("simulate", "--count", "3", "--out", path)
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("{this is not json\n")
            code, _, err = self.run_cli("analyze", path)
            self.assertEqual(code, 2)
            self.assertIn("line", err)

    def test_missing_file_exits_2(self):
        self.assertEqual(self.run_cli("analyze", "/nonexistent/seqprobe.jsonl")[0], 2)

    def test_bad_arguments_exit_2(self):
        for argv in (("simulate", "--count", "0"), ("simulate", "--rate-hz", "-1"),
                     ("simulate", "--payload-bytes", "3"), ("plan", "--count", "0"),
                     ("simulate", "--rate-hz", "nan")):
            with self.subTest(argv=argv):
                self.assertEqual(self.run_cli(*argv)[0], 2)

    def test_plan_output(self):
        code, out, _ = self.run_cli("plan", "--count", "3", "--rate-hz", "2")
        self.assertEqual(code, 0)
        self.assertEqual([json.loads(l)["offset_ns"] for l in out.splitlines()],
                         [0, 500_000_000, 1_000_000_000])


if __name__ == "__main__":
    unittest.main()
