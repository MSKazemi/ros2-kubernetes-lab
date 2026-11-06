"""Regression tests for identifier validation (review finding on PR #122).

A bare ``$`` regex anchor also matches before a trailing newline, so ``re.match("^...$", "abc\\n")``
succeeds. These tests make sure run_id, node, topic and the payload fields reject newlines, NUL,
spaces, non-ASCII lookalikes and similar at every entry point, with the module's normal error type
and exit code 2 on the command line.
"""
import contextlib
import io
import json
import os
import tempfile
import unittest

from seqprobe.__main__ import main
from seqprobe.config import (GeneratorConfig, SubscriberConfig, PublisherConfig, check_run_id,
                             check_node, check_topic)
from seqprobe.errors import ConfigError, LogFormatError, PayloadError
from seqprobe.events import Event, check_fields, parse_line, read_events
from seqprobe.payload import build_payload, decode_payload
from seqprobe.synthetic import simulate

BAD_RUN_IDS = [
    "abc\n", "a\nbc", "\nabc", "abc\r\n", "abc ", " abc", "a b", "abc\t", "abc\x00", "a\x00bc",
    "abc;", "a;b", "",
    "x" * 33,
    "٣٣",          # Arabic-Indic digits (str.isdigit() is True for these)
    "r１",               # fullwidth digit one
    "ａｂｃ",    # fullwidth letters
    "r²",               # superscript two (isdigit() True, int() fails)
    "r​1",              # zero-width space (not str.isspace())
    "café",
]
BAD_NAMES = ["", "n\n", "\nn", "a\nb", "n ", " n", "a b", "n\x00", "a\x00b", "n\t", "ñ",
             "a b", "a​b", "a b", "\x7f", "n\x1b[0m"]
GOOD_NAMES = ["seqprobe_pub", "node-1", "/seqprobe", "/robot/cmd_vel", "~/x", "/a{b}", "A.b"]


def valid_record(**over):
    ev = Event(event="recv", role="subscriber", run_id="r1", node="sub", topic="/t", ts_ns=10,
               clock="wall", seq=0, payload_bytes=64, sent_ts_ns=5, sent_clock="wall")
    obj = ev.to_dict()
    obj.update(over)
    return obj


def raw_payload(run_id="r1", seq="0000000001", ts="0" * 19 + "5", clock="wall", pad="abcdef"):
    """Assemble a payload by hand, bypassing build_payload's own validation."""
    return f"SQP1;{run_id};{seq};{ts};{clock};{pad}"


class RunIdTests(unittest.TestCase):
    def test_config_checks_reject(self):
        for bad in BAD_RUN_IDS:
            with self.subTest(run_id=bad):
                with self.assertRaises(ConfigError):
                    check_run_id(bad)
                with self.assertRaises(ConfigError):
                    GeneratorConfig(run_id=bad)
                with self.assertRaises(ConfigError):
                    SubscriberConfig(run_id=bad)

    def test_non_string_run_ids_reject(self):
        for bad in (None, 5, b"r1", ["r1"]):
            with self.assertRaises(ConfigError):
                check_run_id(bad)

    def test_events_check_fields_reject(self):
        for bad in BAD_RUN_IDS:
            with self.subTest(run_id=bad):
                with self.assertRaises(LogFormatError):
                    check_fields(valid_record(run_id=bad))
                with self.assertRaises(LogFormatError):
                    parse_line(json.dumps(valid_record(run_id=bad)), 7)
                with self.assertRaises(LogFormatError):
                    Event(**{**valid_record(run_id=bad)})

    def test_trailing_newline_escaped_in_json_is_rejected_from_a_file(self):
        line = '{"schema_version":1,"event":"recv","role":"subscriber","run_id":"r1\\n",' \
               '"node":"s","topic":"/t","seq":0,"payload_bytes":64,"ts_ns":1,"clock":"wall",' \
               '"sent_ts_ns":1,"sent_clock":"wall","detail":null}'
        with self.assertRaises(LogFormatError):
            read_events([line])

    def test_payload_decode_rejects(self):
        for bad in BAD_RUN_IDS:
            with self.subTest(run_id=bad):
                with self.assertRaises(PayloadError):
                    decode_payload(raw_payload(run_id=bad))

    def test_build_payload_refuses_run_ids_that_could_not_be_decoded(self):
        for bad in BAD_RUN_IDS:
            with self.subTest(run_id=bad):
                with self.assertRaises(ConfigError):
                    build_payload(bad, 0, 0, "wall", 200, seed=0)

    def test_valid_run_ids_still_accepted(self):
        for good in ("r1", "A", "run_01-b", "x" * 32):
            check_run_id(good)
            p = build_payload(good, 3, 4, "wall", 200, seed=0)
            self.assertEqual(decode_payload(p).run_id, good)
            check_fields(valid_record(run_id=good))


class NameTests(unittest.TestCase):
    def test_node_and_topic_reject(self):
        g = GeneratorConfig(run_id="r1")
        for bad in BAD_NAMES:
            with self.subTest(name=bad):
                with self.assertRaises(ConfigError):
                    check_node(bad)
                with self.assertRaises(ConfigError):
                    check_topic(bad)
                with self.assertRaises(ConfigError):
                    PublisherConfig(generator=g, node=bad)
                with self.assertRaises(ConfigError):
                    SubscriberConfig(run_id="r1", topic=bad)
                with self.assertRaises(LogFormatError):
                    check_fields(valid_record(node=bad))
                with self.assertRaises(LogFormatError):
                    check_fields(valid_record(topic=bad))

    def test_non_string_names_reject(self):
        for bad in (None, 7, ["a"]):
            with self.assertRaises(ConfigError):
                check_node(bad)
            with self.assertRaises(LogFormatError):
                check_fields(valid_record(topic=bad))

    def test_ordinary_names_accepted(self):
        for good in GOOD_NAMES:
            check_node(good)
            check_topic(good)
            check_fields(valid_record(node=good, topic=good))


class PayloadFieldTests(unittest.TestCase):
    def test_baseline_hand_built_payload_is_accepted(self):
        self.assertEqual(decode_payload(raw_payload()).seq, 1)

    def test_bad_seq_and_timestamp_fields(self):
        bad_seq = ["000000000٣", "000000000²", "０" * 10, "0000000001\n", "000000001",
                   "00000000001", " 000000001", "-000000001", "+000000001", "0x00000001", "0000000_01"]
        for s in bad_seq:
            with self.subTest(seq=s):
                with self.assertRaises(PayloadError):
                    decode_payload(raw_payload(seq=s))
        bad_ts = ["٣" * 20, "0" * 19 + "²", "0" * 20 + "\n", "0" * 19, "0" * 21, " " + "0" * 19,
                  "-" + "0" * 19]
        for t in bad_ts:
            with self.subTest(ts=t):
                with self.assertRaises(PayloadError):
                    decode_payload(raw_payload(ts=t))

    def test_bad_padding(self):
        for pad in ("ab\n", "\nab", "ab\x00", "ab cd", "AB", "ab;cd", "g", "٣", "ab\r"):
            with self.subTest(pad=pad):
                with self.assertRaises(PayloadError):
                    decode_payload(raw_payload(pad=pad))

    def test_bad_clock_field(self):
        for clk in ("wall\n", "Wall", " wall", "wall ", "", "utc"):
            with self.subTest(clock=clk):
                with self.assertRaises(PayloadError):
                    decode_payload(raw_payload(clock=clk))

    def test_empty_padding_is_valid(self):
        self.assertEqual(decode_payload(raw_payload(pad="")).seq, 1)

    def test_generated_payloads_still_decode(self):
        for size in (60, 64, 1024):
            self.assertEqual(decode_payload(build_payload("r1", 5, 9, "monotonic", size, seed=2)).seq, 5)


class JsonTests(unittest.TestCase):
    def test_duplicate_keys_rejected(self):
        good = json.dumps(valid_record())
        dup = good[:-1] + ',"seq":99}'
        with self.assertRaises(LogFormatError) as cm:
            read_events([good, dup])
        self.assertEqual(cm.exception.line_no, 2)


class CliTests(unittest.TestCase):
    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_run_id_argument_rejected_with_exit_2(self):
        for bad in BAD_RUN_IDS:
            for cmd in ("simulate", "plan"):
                with self.subTest(run_id=bad, cmd=cmd):
                    code, _, err = self.run_cli(cmd, "--run-id", bad)
                    self.assertEqual(code, 2)
                    self.assertIn("error:", err)

    def test_valid_run_id_argument_still_works(self):
        self.assertEqual(self.run_cli("plan", "--count", "2", "--run-id", "r1")[0], 0)

    def test_integer_lists_are_ascii_only(self):
        for bad in ("٣", "1,²", "1;2", "-1", "1.5", "0x1", "1_0"):
            with self.subTest(arg=bad):
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as cm:
                    self.run_cli("simulate", "--drop", bad)
                self.assertEqual(cm.exception.code, 2)
        self.assertEqual(self.run_cli("simulate", "--count", "5", "--drop", "1, 2")[0], 0)

    def test_analyze_log_with_newline_run_id_exits_2(self):
        events, _ = simulate(count=3)
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "x.jsonl")
            with open(path, "w", encoding="utf-8") as fh:
                for ev in events:
                    obj = ev.to_dict()
                    obj["run_id"] = obj["run_id"] + "\n"
                    fh.write(json.dumps(obj) + "\n")
            code, _, err = self.run_cli("analyze", path)
            self.assertEqual(code, 2)
            self.assertIn("line 1", err)

    def test_adapters_reject_newline_run_id_with_exit_2(self):
        from tests.test_adapters_static import load
        for modname in ("publisher_node", "subscriber_node"):
            mod = load(modname)
            for bad in ("r1\n", "r1 ", "r٣"):
                with self.subTest(mod=modname, run_id=bad):
                    err = io.StringIO()
                    with contextlib.redirect_stderr(err):
                        self.assertEqual(mod.main(["--run-id", bad]), 2)
                    self.assertIn("error:", err.getvalue())

    def test_adapters_reject_bad_node_and_topic(self):
        from tests.test_adapters_static import load
        mod = load("publisher_node")
        for argv in (["--run-id", "r1", "--topic", "/a\nb"], ["--run-id", "r1", "--node-name", "n\x00"]):
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(mod.main(argv), 2)


if __name__ == "__main__":
    unittest.main()
