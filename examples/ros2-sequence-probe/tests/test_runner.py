import unittest

from seqprobe.clocks import Clocks
from seqprobe.config import GeneratorConfig, PublisherConfig, SubscriberConfig
from seqprobe.errors import ConfigError
from seqprobe.payload import build_payload
from seqprobe.runner import run_publisher, SubscriberSession
from seqprobe.sinks import ListSink
from seqprobe.synthetic import VirtualClocks


def pub_cfg(**kw):
    return PublisherConfig(generator=GeneratorConfig(run_id="r1", **kw))


class PublisherTests(unittest.TestCase):
    def test_sends_all_in_order_with_start_and_stop(self):
        sink, sent = ListSink(), []
        clocks = VirtualClocks()
        summary = run_publisher(pub_cfg(count=5, rate_hz=10), sent.append, sink, clocks)
        self.assertEqual(summary, {"sent": 5, "reason": "completed"})
        kinds = [e.event for e in sink.events]
        self.assertEqual(kinds, ["start"] + ["send"] * 5 + ["stop"])
        self.assertEqual([e.seq for e in sink.events if e.event == "send"], [0, 1, 2, 3, 4])
        self.assertEqual(len(sent), 5)
        ts = [e.ts_ns for e in sink.events if e.event == "send"]
        self.assertEqual([b - a for a, b in zip(ts, ts[1:])], [100_000_000] * 4)  # virtual time
        self.assertEqual(sink.events[0].detail["expected_count"], 5)
        self.assertFalse(sink.events[0].detail["synthetic"])

    def test_same_config_gives_identical_payloads(self):
        runs = []
        for _ in range(2):
            sent = []
            run_publisher(pub_cfg(count=3, seed=9), sent.append, ListSink(), VirtualClocks())
            runs.append(sent)
        self.assertEqual(runs[0], runs[1])

    def test_stop_request_ends_early(self):
        sink, sent = ListSink(), []
        flag = {"n": 0}

        def should_stop():
            flag["n"] += 1
            return flag["n"] > 2

        summary = run_publisher(pub_cfg(count=10), sent.append, sink, VirtualClocks(), should_stop)
        self.assertEqual(summary, {"sent": 2, "reason": "stopped"})
        self.assertEqual(sink.events[-1].detail, {"sent": 2, "reason": "stopped"})

    def test_send_failure_is_logged_and_raised(self):
        sink = ListSink()

        def boom(_):
            raise RuntimeError("transport down")

        with self.assertRaises(RuntimeError):
            run_publisher(pub_cfg(count=3), boom, sink, VirtualClocks())
        self.assertEqual(sink.events[-1].event, "stop")
        self.assertEqual(sink.events[-1].detail["reason"], "error")
        self.assertEqual([e.event for e in sink.events if e.event == "send"], [])

    def test_ros_clock_unavailable_without_ros(self):
        with self.assertRaises(ConfigError):
            run_publisher(pub_cfg(count=1, clock="ros"), lambda p: None, ListSink(), Clocks())


def sub(expected=3, **kw):
    sink = ListSink()
    clocks = VirtualClocks()
    s = SubscriberSession(SubscriberConfig(run_id="r1", expected_count=expected, **kw), sink, clocks)
    s.start()
    return s, sink, clocks


def payload(seq, run="r1"):
    return build_payload(run, seq, 1, "wall", 64, 0)


class SubscriberTests(unittest.TestCase):
    def test_complete_run(self):
        s, sink, _ = sub()
        for i in range(3):
            self.assertEqual(s.on_message(payload(i)), "in_order")
        self.assertEqual(s.poll(), "complete")
        v = s.finish()
        self.assertTrue(v.ok)
        self.assertEqual([e.event for e in sink.events], ["start", "recv", "recv", "recv", "stop"])
        recv = sink.events[1]
        self.assertEqual((recv.sent_clock, recv.sent_ts_ns, recv.payload_bytes), ("wall", 1, 64))

    def test_first_message_timeout(self):
        s, sink, clocks = sub(first_message_timeout_s=5, idle_timeout_s=1)
        clocks.advance_ns(4_000_000_000)
        self.assertEqual(s.poll(), "running")  # idle timeout does not apply before the first message
        clocks.advance_ns(1_000_000_000)
        self.assertEqual(s.poll(), "timeout")
        self.assertEqual(s.poll(), "timeout")
        self.assertEqual([e.event for e in sink.events].count("timeout"), 1)
        self.assertEqual(sink.events[-1].detail["reason"], "first_message")
        v = s.finish()
        self.assertEqual((v.completion, v.missing), ("timeout", 3))

    def test_idle_timeout_after_partial_receive(self):
        s, sink, clocks = sub(idle_timeout_s=2)
        s.on_message(payload(0))
        clocks.advance_ns(1_900_000_000)
        self.assertEqual(s.poll(), "running")
        clocks.advance_ns(200_000_000)
        self.assertEqual(s.poll(), "timeout")
        self.assertEqual(sink.events[-1].detail["reason"], "idle")
        self.assertEqual(s.finish().completion, "timeout")

    def test_overall_timeout_even_if_traffic_continues(self):
        s, sink, clocks = sub(expected=1000, idle_timeout_s=2, overall_timeout_s=3)
        states = []
        for i in range(5):
            clocks.advance_ns(1_000_000_000)
            s.on_message(payload(i))
            states.append(s.poll())
        self.assertEqual(states[:2], ["running", "running"])
        self.assertEqual(states[2], "timeout")
        timeouts = [e for e in sink.events if e.event == "timeout"]
        self.assertEqual([e.detail["reason"] for e in timeouts], ["overall"])

    def test_malformed_and_foreign_payloads_are_counted_not_tracked(self):
        s, sink, _ = sub()
        self.assertEqual(s.on_message("garbage"), "malformed")
        self.assertEqual(s.on_message(payload(0, run="other")), "foreign_run")
        self.assertEqual(s.tracker.received_total, 0)
        v = s.finish()
        self.assertEqual(sink.events[-1].detail["malformed"], 1)
        self.assertEqual(sink.events[-1].detail["foreign_run"], 1)
        self.assertEqual(v.unique, 0)

    def test_duplicates_and_reordering_are_logged_as_recv(self):
        s, sink, _ = sub(expected=3)
        for i in (0, 2, 1, 1):
            s.on_message(payload(i))
        self.assertEqual(len([e for e in sink.events if e.event == "recv"]), 4)
        v = s.finish()
        self.assertEqual((v.duplicates, v.reordered, v.completion, v.ok), (1, 1, "complete", False))

    def test_use_before_start_is_an_error(self):
        s = SubscriberSession(SubscriberConfig(run_id="r1", expected_count=1), ListSink(), VirtualClocks())
        with self.assertRaises(RuntimeError):
            s.on_message(payload(0))
        with self.assertRaises(RuntimeError):
            s.poll()

    def test_finish_twice_logs_one_stop(self):
        s, sink, _ = sub()
        s.finish(); s.finish()
        self.assertEqual([e.event for e in sink.events].count("stop"), 1)

    def test_unknown_count_never_completes(self):
        s, _, clocks = sub(expected=None, idle_timeout_s=1)
        for i in range(3):
            s.on_message(payload(i))
        self.assertEqual(s.poll(), "running")
        clocks.advance_ns(2_000_000_000)
        self.assertEqual(s.poll(), "timeout")
        v = s.finish()
        self.assertEqual(v.completion, "timeout")
        self.assertFalse(v.ok)


if __name__ == "__main__":
    unittest.main()
