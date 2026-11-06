import json
import unittest

from seqprobe.errors import ClockMismatchError, LogFormatError
from seqprobe.events import Event, FIELDS, parse_line, read_events


def recv(**kw):
    base = dict(event="recv", role="subscriber", run_id="r1", node="sub", topic="/t", ts_ns=10,
                clock="wall", seq=0, payload_bytes=64, sent_ts_ns=5, sent_clock="wall")
    base.update(kw)
    return Event(**base)


def send(**kw):
    base = dict(event="send", role="publisher", run_id="r1", node="pub", topic="/t", ts_ns=5,
                clock="wall", seq=0, payload_bytes=64)
    base.update(kw)
    return Event(**base)


class EventTests(unittest.TestCase):
    def test_roundtrip_and_field_order(self):
        for ev in (recv(), send(), Event(event="start", role="publisher", run_id="r1", node="p",
                                         topic="/t", ts_ns=1, clock="monotonic", detail={"a": 1})):
            line = ev.to_json_line()
            self.assertEqual(list(json.loads(line).keys()), list(FIELDS))
            self.assertEqual(parse_line(line), ev)
            self.assertNotIn("\n", line)

    def test_writer_cannot_build_invalid_event(self):
        for kw in ({"seq": None}, {"sent_clock": None}, {"clock": "utc"}, {"ts_ns": -1}, {"seq": True}):
            with self.subTest(kw=kw):
                with self.assertRaises(LogFormatError):
                    recv(**kw)
        with self.assertRaises(LogFormatError):
            send(sent_ts_ns=3, sent_clock="wall")  # sender fields only belong on recv
        with self.assertRaises(LogFormatError):
            Event(event="recv", role="publisher", run_id="r1", node="n", topic="/t", ts_ns=1,
                  clock="wall", seq=0, payload_bytes=1, sent_ts_ns=1, sent_clock="wall")
        with self.assertRaises(LogFormatError):
            Event(event="stop", role="subscriber", run_id="r1", node="n", topic="/t", ts_ns=1,
                  clock="wall", seq=3)

    def test_malformed_lines_report_line_number(self):
        good = recv().to_json_line()
        obj = json.loads(good)
        cases = {
            "not json": "{nope",
            "array": "[1,2]",
            "truncated": good[:-5],
            "nan": good.replace('"ts_ns":10', '"ts_ns":NaN'),
            "missing field": json.dumps({k: v for k, v in obj.items() if k != "topic"}),
            "unknown field": json.dumps({**obj, "extra": 1}),
            "future schema": json.dumps({**obj, "schema_version": 2}),
            "float ts": json.dumps({**obj, "ts_ns": 1.5}),
            "bad event": json.dumps({**obj, "event": "receive"}),
        }
        for name, line in cases.items():
            with self.subTest(name):
                with self.assertRaises(LogFormatError) as cm:
                    read_events([good, line])
                self.assertEqual(cm.exception.line_no, 2)
                self.assertIn("line 2", str(cm.exception))

    def test_blank_lines_skipped(self):
        self.assertEqual(len(read_events(["", recv().to_json_line(), "  \n"])), 1)

    def test_clock_switch_inside_stream_is_rejected(self):
        a = recv(seq=0, clock="wall", sent_clock="wall").to_json_line()
        b = recv(seq=1, clock="monotonic", sent_clock="wall").to_json_line()
        with self.assertRaises(ClockMismatchError):
            read_events([a, b])

    def test_different_streams_may_use_different_clocks(self):
        lines = [recv(clock="wall").to_json_line(), send(clock="monotonic").to_json_line()]
        self.assertEqual(len(read_events(lines)), 2)

    def test_elapsed_since_requires_same_clock_domain(self):
        self.assertEqual(recv(ts_ns=30).elapsed_since(recv(ts_ns=10)), 20)
        with self.assertRaises(ClockMismatchError):
            recv(clock="wall").elapsed_since(send(clock="monotonic"))
        with self.assertRaises(ClockMismatchError):  # monotonic is per-node
            recv(clock="monotonic", node="sub").elapsed_since(send(clock="monotonic", node="pub"))
        # wall vs wall across nodes is allowed (accuracy depends on clock sync; not measured here)
        self.assertEqual(recv(clock="wall").elapsed_since(send(clock="wall")), 5)


if __name__ == "__main__":
    unittest.main()
