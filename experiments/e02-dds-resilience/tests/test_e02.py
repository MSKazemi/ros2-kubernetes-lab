import json
import os
import tempfile
import unittest

import sys

from ddsres import checks, matrix as mx, synth
from ddsres.seqprobe import parse_seqprobe
from ddsres.metrics import InsufficientSamplesError, analyze, nearest_rank
from ddsres.trace import (
    Adapter,
    ClockDomainError,
    EmptyTraceError,
    NonMonotonicClockError,
    TraceError,
    TruncatedTraceError,
    load_trace,
    parse_lines,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FIXTURES = os.path.join(HERE, "fixtures")
CLOCK = "c"


def build(records, footer=True, header=True):
    """Make native-format lines from record dicts (header/footer added)."""
    lines = []
    if header:
        lines.append(json.dumps({"type": "header", "schema": "rrl.trace/1", "synthetic": True, "default_clock": CLOCK}))
    lines += [json.dumps(r) for r in records]
    if footer:
        lines.append(json.dumps({"type": "footer", "records": len(records)}))
    return [l + "\n" for l in lines]


def S(seq, t, clock=None):
    r = {"type": "send", "seq": seq, "t_ns": t}
    if clock:
        r["clock"] = clock
    return r


def R(seq, t, clock=None):
    r = {"type": "recv", "seq": seq, "t_ns": t}
    if clock:
        r["clock"] = clock
    return r


def M(name, t):
    return {"type": "marker", "name": name, "t_ns": t}


def run(records, **kw):
    return analyze(parse_lines(build(records)), **kw)


class Percentile(unittest.TestCase):
    def test_nearest_rank_known_values(self):
        data = list(range(1, 101))  # 1..100
        self.assertEqual(nearest_rank(data, 50), 50)
        self.assertEqual(nearest_rank(data, 95), 95)
        self.assertEqual(nearest_rank(data, 99), 99)
        self.assertEqual(nearest_rank([10, 20, 30, 40, 50], 50), 30)  # ceil(2.5)=3
        self.assertEqual(nearest_rank([5, 1, 3], 100), 5)  # unsorted input

    def test_n_less_than_two_errors(self):
        with self.assertRaises(InsufficientSamplesError):
            nearest_rank([], 50)
        with self.assertRaises(InsufficientSamplesError):
            nearest_rank([1], 50)

    def test_bad_p(self):
        for p in (0, -1, 101):
            with self.assertRaises(ValueError):
                nearest_rank([1, 2], p)


class Basics(unittest.TestCase):
    def test_perfect_run(self):
        recs = [x for i in range(10) for x in (S(i, i * 100), R(i, i * 100 + 5))]
        r = run(recs)
        self.assertEqual(r["delivery_completeness"], 1.0)
        self.assertEqual(r["loss_ratio"], 0.0)
        self.assertEqual(r["counts"]["duplicate_copies"], 0)
        self.assertEqual(r["reorder"]["count"], 0)
        self.assertEqual(r["latency"]["p50_ns"], 5)
        self.assertFalse(r["latency"]["p99_resolved"])
        self.assertTrue(any("p99 equals the maximum" in w for w in r["warnings"]))

    def test_loss_duplicates_reorder(self):
        recs = [S(0, 0), S(1, 100), S(2, 200), S(3, 300), S(4, 400),
                R(0, 10), R(2, 210), R(1, 220), R(2, 230), R(4, 410)]  # 3 lost, 2 dup, 1 reordered
        r = run(recs)
        self.assertEqual(r["counts"]["lost"], 1)
        self.assertAlmostEqual(r["delivery_completeness"], 0.8)
        self.assertEqual(r["counts"]["duplicate_copies"], 1)
        self.assertAlmostEqual(r["duplicate_ratio"], 1 / 5)
        self.assertEqual(r["reorder"]["count"], 1)  # seq 1 after seq 2 (RFC 4737)
        # latency uses the first delivery of seq 2 (10), not the duplicate
        self.assertEqual(r["latency"]["n"], 4)
        self.assertEqual(r["latency"]["p50_ns"], 10)
        self.assertEqual(r["latency"]["p99_ns"], 120)

    def test_reorder_with_gaps_is_not_reordered(self):
        recs = [S(i, i) for i in range(4)] + [R(0, 10), R(3, 11)]  # gap, still in order
        self.assertEqual(run(recs)["reorder"]["count"], 0)

    def test_unsolicited_recv_excluded_with_warning(self):
        r = run([S(0, 0), S(1, 1), R(0, 5), R(1, 6), R(99, 7)])
        self.assertEqual(r["counts"]["unsolicited"], 1)
        self.assertEqual(r["delivery_completeness"], 1.0)
        self.assertTrue(r["warnings"])

    def test_all_lost(self):
        r = run([S(0, 0), S(1, 1), S(2, 2)])
        self.assertEqual(r["delivery_completeness"], 0.0)
        self.assertEqual(r["loss_ratio"], 1.0)
        self.assertIsNone(r["latency"])
        self.assertIn("insufficient_samples", r["latency_unavailable_reason"])
        self.assertIsNone(r["duplicate_ratio"])
        self.assertIsNone(r["reorder"]["ratio"])
        with self.assertRaises(InsufficientSamplesError):
            run([S(0, 0), S(1, 1)], require_latency=True)

    def test_single_latency_sample_is_null_not_error(self):
        r = run([S(0, 0), S(1, 1), R(0, 5)])
        self.assertIsNone(r["latency"])
        self.assertIn("n=1", r["latency_unavailable_reason"])

    def test_negative_latency_same_clock_rejected(self):
        with self.assertRaises(TraceError):
            run([S(0, 100), R(0, 50), S(1, 200), R(1, 250)])


class Faults(unittest.TestCase):
    def test_restart_recovery(self):
        recs = [S(0, 0), R(0, 5), M("restart_begin", 100), M("restart_end", 300),
                S(1, 150), S(2, 350), R(2, 420)]
        w = run(recs)["fault_windows"][0]
        self.assertEqual(w["name"], "restart")
        self.assertTrue(w["recovered"])
        self.assertEqual(w["recovery_time_ns"], 120)  # 420 - 300
        self.assertEqual(w["delivery_gap_ns"], 415)  # 420 - 5

    def test_restart_gap_never_recovers(self):
        recs = [S(0, 0), R(0, 5), M("restart_begin", 100), S(1, 150), M("restart_end", 300), S(2, 350)]
        w = run(recs)["fault_windows"][0]
        self.assertIs(w["recovered"], False)
        self.assertIsNone(w["recovery_time_ns"])
        self.assertIsNone(w["delivery_gap_ns"])  # nothing received after begin

    def test_missing_end_marker_gives_null(self):
        w = run([S(0, 0), R(0, 5), M("restart_begin", 100), S(1, 150), R(1, 160)])["fault_windows"][0]
        self.assertIsNone(w["recovered"])
        self.assertIsNone(w["recovery_time_ns"])
        self.assertEqual(w["delivery_gap_ns"], 155)

    def test_end_before_begin_and_orphan_end(self):
        with self.assertRaises(TraceError):
            run([S(0, 0), M("restart_end", 10), M("restart_begin", 20)])  # marker stream is monotonic; pairs invert
        with self.assertRaises(TraceError):
            run([S(0, 0), M("restart_end", 10)])

    def test_two_restarts_paired_in_order(self):
        recs = [S(0, 0), M("restart_begin", 10), M("restart_end", 20), R(0, 30),
                M("restart_begin", 40), M("restart_end", 50)]
        ws = run(recs)["fault_windows"]
        self.assertEqual(len(ws), 2)
        self.assertEqual(ws[0]["recovery_time_ns"], 10)
        self.assertIs(ws[1]["recovered"], False)


class Resources(unittest.TestCase):
    def test_absent_is_null(self):
        r = run([S(0, 0), R(0, 1)])
        self.assertEqual(r["resources"], {"cpu_pct": None, "mem_bytes": None})

    def test_present_is_summarised(self):
        res = [{"type": "resource", "t_ns": 1, "node": "sub", "cpu_pct": 10.0, "mem_bytes": 100},
               {"type": "resource", "t_ns": 2, "node": "sub", "cpu_pct": 30.0, "mem_bytes": None}]
        r = run([S(0, 0), R(0, 1)] + res)
        self.assertEqual(r["resources"]["cpu_pct"], {"n": 2, "min": 10.0, "mean": 20.0, "max": 30.0})
        self.assertEqual(r["resources"]["mem_bytes"]["n"], 1)

    def test_bad_resource_rejected(self):
        with self.assertRaises(TraceError):
            run([S(0, 0), {"type": "resource", "t_ns": 1, "cpu_pct": -1}])


class Negative(unittest.TestCase):
    def test_empty_inputs(self):
        with self.assertRaises(EmptyTraceError):
            parse_lines([])  # zero bytes
        with self.assertRaises(TraceError):
            parse_lines(['{"type":"send","seq":0,"t_ns":1,"clock":"c"}\n'])  # no header
        with self.assertRaises(EmptyTraceError):
            parse_lines(build([]))  # header + footer only
        with self.assertRaises(EmptyTraceError):
            parse_lines(build([R(0, 1)]))  # receives but no sends

    def test_non_monotonic_clock(self):
        with self.assertRaises(NonMonotonicClockError):
            parse_lines(build([S(0, 100), S(1, 50)]))
        with self.assertRaises(NonMonotonicClockError):
            parse_lines(build([S(0, 0), R(0, 100), R(1, 50)]))

    def test_non_monotonic_across_clocks_is_separate_streams(self):
        parse_lines(build([S(0, 100, "a"), S(1, 50, "b")]))  # different clocks: no ordering claim

    def test_mixed_clock_domains(self):
        recs = [S(0, 0, "pub"), S(1, 10, "pub"), R(0, 5, "sub"), R(1, 15, "sub")]
        with self.assertRaises(ClockDomainError):
            run(recs)
        r = run(recs, on_mixed_clock="null")
        self.assertIsNone(r["latency"])
        self.assertEqual(r["latency_unavailable_reason"], "mixed_clock_domains")
        self.assertEqual(r["delivery_completeness"], 1.0)  # seq-based metrics still valid

    def test_mixed_clock_nulls_fault_times(self):
        recs = [S(0, 0, "a"), R(0, 5, "b"), M("restart_begin", 1), M("restart_end", 2)]
        recs[2]["clock"], recs[3]["clock"] = "a", "a"
        w = run(recs, on_mixed_clock="null")["fault_windows"][0]
        self.assertIsNone(w["recovery_time_ns"])
        self.assertIsNone(w["delivery_gap_ns"])

    def test_truncated_file(self):
        lines = build([S(0, 0), R(0, 5), S(1, 10)])
        with self.assertRaises(TruncatedTraceError):  # footer missing
            parse_lines(lines[:-1])
        with self.assertRaises(TruncatedTraceError):  # cut mid-line
            parse_lines(lines[:3] + [lines[3][:12]])
        bad = lines[:-1] + [json.dumps({"type": "footer", "records": 99}) + "\n"]
        with self.assertRaises(TruncatedTraceError):  # count mismatch
            parse_lines(bad)

    def test_truncated_file_on_disk(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "t.jsonl")
            text = "".join(build([S(0, 0), R(0, 5)]))
            with open(p, "w") as fh:
                fh.write(text[: len(text) // 2])
            with self.assertRaises(TruncatedTraceError):
                load_trace(p)

    def test_garbage_in_the_middle_is_not_truncation(self):
        lines = build([S(0, 0), R(0, 5)])
        lines.insert(2, "not json\n")
        with self.assertRaises(TraceError) as cm:
            parse_lines(lines)
        self.assertNotIsInstance(cm.exception, TruncatedTraceError)

    def test_schema_and_field_validation(self):
        with self.assertRaises(TraceError):
            parse_lines(['{"type":"header","schema":"other/9"}\n'])
        with self.assertRaises(TraceError):
            parse_lines(build([{"type": "send", "seq": True, "t_ns": 1}]))
        with self.assertRaises(TraceError):
            parse_lines(build([{"type": "send", "seq": 0, "t_ns": -1}]))
        with self.assertRaises(TraceError):
            parse_lines(build([S(0, 0), S(0, 1)]))  # duplicate send seq
        with self.assertRaises(TraceError):
            parse_lines(build([{"type": "send", "seq": 0, "t_ns": 1}], header=True)[:1]
                        + ['{"type":"send","seq":1,"t_ns":2,"clock":""}\n'])

    def test_no_clock_anywhere(self):
        lines = ['{"type":"header","schema":"rrl.trace/1"}\n', '{"type":"send","seq":0,"t_ns":1}\n',
                 '{"type":"footer","records":1}\n']
        with self.assertRaises(TraceError):
            parse_lines(lines)

    def test_data_after_footer(self):
        lines = build([S(0, 0)]) + [json.dumps(S(1, 1)) + "\n"]
        with self.assertRaises(TraceError):
            parse_lines(lines)


FLAT = Adapter(name="flat-test", kind_field="event", kind_map={"published": "send", "received": "recv"},
               seq_field="seq", time_field="t_ns", clock_field="clock")


class AdapterTests(unittest.TestCase):
    def test_provisional_adapter_maps_and_ignores_unknown(self):
        lines = [json.dumps(x) + "\n" for x in (
            {"event": "published", "seq": 0, "t_ns": 10, "clock": "mono"},
            {"event": "log", "msg": "hello"},
            {"event": "received", "seq": 0, "t_ns": 25, "clock": "mono"},
            {"event": "published", "seq": 1, "t_ns": 20, "clock": "mono"},
            {"event": "received", "seq": 1, "t_ns": 40, "clock": "mono"},
        )]
        r = analyze(parse_lines(lines, adapter=FLAT))
        self.assertEqual(r["delivery_completeness"], 1.0)
        self.assertIsNone(r["synthetic"])  # unknown provenance is not claimed synthetic
        self.assertEqual(r["latency"]["p50_ns"], 15)

    def test_adapter_truncation_detected_by_bad_last_line(self):
        lines = [json.dumps({"event": "published", "seq": 0, "t_ns": 1, "clock": "m"}) + "\n", '{"event": "rec']
        with self.assertRaises(TruncatedTraceError):
            parse_lines(lines, adapter=FLAT)


class MatrixAndFixtures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m = mx.load_matrix()

    def test_matrix_covers_cross_product_and_flags_live_runs(self):
        self.assertEqual(len(self.m["cells"]), 12)
        self.assertEqual(self.m["live_recipe_common"]["status"], "NOT RUN")
        self.assertIn("safe local context", self.m["live_recipe_common"]["requires"])
        self.assertIn("NOT RUN", mx.recipe_text(self.m, "reliable__loss"))

    def test_matrix_validation_rejects_gaps(self):
        broken = json.loads(json.dumps(self.m))
        broken["cells"].pop()
        with self.assertRaises(mx.MatrixError):
            mx.validate_matrix(broken)
        broken = json.loads(json.dumps(self.m))
        broken["live_recipe_common"]["status"] = "done"
        with self.assertRaises(mx.MatrixError):
            mx.validate_matrix(broken)

    def test_generator_is_deterministic(self):
        self.assertEqual(synth.render_all(self.m), synth.render_all(self.m))

    def test_committed_fixtures_match_generator_byte_for_byte(self):
        for name, text in synth.render_all(self.m).items():
            with open(os.path.join(FIXTURES, name), "r", encoding="utf-8") as fh:
                self.assertEqual(fh.read(), text, f"{name} is stale; run: python3 experiments/e02-dds-resilience/run.py generate")

    def test_every_fixture_is_labelled_synthetic(self):
        for cell in self.m["cells"]:
            with open(os.path.join(FIXTURES, synth.fixture_name(cell)), encoding="utf-8") as fh:
                head = json.loads(fh.readline())
            self.assertIs(head["synthetic"], True)
            self.assertTrue(head["label"].startswith("SYNTHETIC"))
        with open(os.path.join(FIXTURES, "MANIFEST.json"), encoding="utf-8") as fh:
            self.assertTrue(json.load(fh)["label"].startswith("SYNTHETIC"))

    def test_seed_changes_output(self):
        other = json.loads(json.dumps(self.m))
        cell = next(c for c in other["cells"] if c["id"] == "best_effort__loss")
        cell["seed"] += 1
        self.assertNotEqual(synth.generate_cell(self.m, next(c for c in self.m["cells"] if c["id"] == "best_effort__loss")),
                            synth.generate_cell(other, cell))

    def test_synthetic_checks_hold_on_every_fixture(self):
        for cell in self.m["cells"]:
            res = analyze(load_trace(os.path.join(FIXTURES, synth.fixture_name(cell))))
            self.assertEqual(checks.evaluate(res, cell["synthetic_checks"]), [], cell["id"])
            self.assertTrue(res["synthetic"])
            self.assertIn("SYNTHETIC", res["disclaimer"])
            self.assertEqual(res["resources"], {"cpu_pct": None, "mem_bytes": None})

    def test_checks_report_absent_values(self):
        res = run([S(0, 0), S(1, 1)])
        self.assertTrue(checks.evaluate(res, {"latency_p50_ms": {"ge": 0}}))



def sp(event, role, node, seq=None, ts=0, clock="wall", sent_ts=None, sent_clock=None, run="r1", topic="/t"):
    return json.dumps({
        "schema_version": 1, "event": event, "role": role, "run_id": run, "node": node, "topic": topic,
        "seq": seq, "payload_bytes": None if seq is None else 8, "ts_ns": ts, "clock": clock,
        "sent_ts_ns": sent_ts, "sent_clock": sent_clock, "detail": None,
    }) + "\n"


def sp_run(clock="wall", n=3, drop=(), lat=1000):
    lines = [sp("start", "publisher", "pub", clock=clock), sp("start", "subscriber", "sub", clock=clock)]
    for i in range(n):
        t = 10_000 + i * 100
        lines.append(sp("send", "publisher", "pub", i, t, clock))
        if i not in drop:
            lines.append(sp("recv", "subscriber", "sub", i, t + lat, clock, t, clock))
    lines += [sp("stop", "publisher", "pub", clock=clock), sp("stop", "subscriber", "sub", clock=clock)]
    return lines


class SeqProbeReader(unittest.TestCase):
    def test_wall_clock_run(self):
        tr = parse_seqprobe([("both.jsonl", sp_run(n=4, drop=(2,)))])
        r = analyze(tr)
        self.assertAlmostEqual(r["delivery_completeness"], 0.75)
        self.assertEqual(r["latency"]["n"], 3)
        self.assertEqual(r["latency"]["p50_ns"], 1000)
        self.assertTrue(any("clock synchronisation" in w for w in r["warnings"]))
        self.assertIsNone(r["synthetic"])

    def test_two_files(self):
        lines = sp_run()
        pub = [l for l in lines if '"role":' in l and json.loads(l)["role"] == "publisher"]
        sub = [l for l in lines if json.loads(l)["role"] == "subscriber"]
        r = analyze(parse_seqprobe([("p", pub), ("s", sub)]))
        self.assertEqual(r["delivery_completeness"], 1.0)

    def test_monotonic_on_two_nodes_is_mixed_domain(self):
        tr = parse_seqprobe([("both", sp_run(clock="monotonic"))])
        with self.assertRaises(ClockDomainError):
            analyze(tr)
        r = analyze(tr, on_mixed_clock="null")
        self.assertIsNone(r["latency"])
        self.assertEqual(r["delivery_completeness"], 1.0)

    def test_truncated_log_missing_stop(self):
        with self.assertRaises(TruncatedTraceError):
            parse_seqprobe([("both", sp_run()[:-1])])
        lines = sp_run()
        lines[-1] = lines[-1][:20]
        with self.assertRaises(TruncatedTraceError):
            parse_seqprobe([("both", lines)])

    def test_publisher_log_missing_is_empty(self):
        sub_only = [l for l in sp_run() if json.loads(l)["role"] == "subscriber"]
        with self.assertRaises(EmptyTraceError):
            parse_seqprobe([("s", sub_only)])

    def test_non_monotonic_wall_clock(self):
        lines = sp_run()
        lines.insert(4, sp("send", "publisher", "pub", 9, 1, "wall"))  # earlier than previous send
        with self.assertRaises(NonMonotonicClockError):
            parse_seqprobe([("both", lines)])

    def test_unsupported_schema_and_wrong_pairing(self):
        bad = sp_run()
        bad[2] = bad[2].replace('"schema_version": 1', '"schema_version": 2')
        with self.assertRaises(TraceError):
            parse_seqprobe([("both", bad)])
        mism = sp_run()
        i = next(k for k, l in enumerate(mism) if json.loads(l)["event"] == "recv")
        rec = json.loads(mism[i]); rec["sent_ts_ns"] += 1
        mism[i] = json.dumps(rec) + "\n"
        with self.assertRaises(TraceError):
            parse_seqprobe([("both", mism)])

    def test_two_runs_rejected(self):
        with self.assertRaises(TraceError):
            parse_seqprobe([("a", sp_run()), ("b", [l.replace('"r1"', '"r2"') for l in sp_run()])])

    def test_marker_file_gives_recovery(self):
        lines = sp_run(n=6, drop=(2, 3), lat=10)
        markers = [json.dumps({"name": "restart_begin", "t_ns": 10_150, "clock": "wall"}) + "\n",
                   json.dumps({"name": "restart_end", "t_ns": 10_350, "clock": "wall"}) + "\n"]
        r = analyze(parse_seqprobe([("both", lines)], ("m", markers)))
        w = r["fault_windows"][0]
        self.assertTrue(w["recovered"])
        self.assertEqual(w["recovery_time_ns"], 10_410 - 10_350)  # first recv at/after end is seq 4

    def test_contract_with_real_seqprobe_writer(self):
        probe = os.path.join(HERE, "..", "..", "examples", "ros2-sequence-probe")
        if not os.path.isdir(os.path.join(probe, "seqprobe")):
            self.skipTest("examples/ros2-sequence-probe not present in this tree")
        sys.path.insert(0, probe)
        try:
            from seqprobe.synthetic import simulate
        finally:
            sys.path.remove(probe)
        events, _ = simulate(count=20, drop=[3], duplicate=[5], swap=[8])
        lines = [e.to_json_line() + "\n" for e in events]
        r = analyze(parse_seqprobe([("simulate", lines)]))
        self.assertEqual(r["counts"]["lost"], 1)
        self.assertEqual(r["counts"]["duplicate_copies"], 1)
        self.assertEqual(r["reorder"]["count"], 1)
        self.assertTrue(r["synthetic"])


if __name__ == "__main__":
    unittest.main()
