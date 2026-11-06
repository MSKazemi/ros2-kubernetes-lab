"""Offline analysis of a parsed log: one sequence verdict per subscriber stream.

Counting only. No latency, jitter or throughput is derived, and no timestamps from different
clock domains are combined (``duration_ns`` below is last-minus-first on a single stream, which
by construction shares one node and one clock).
"""

from .errors import LogFormatError
from .tracker import SequenceTracker


def analyze_events(events, expected_count=None):
    """Return ``{"<run_id>|<node>|<topic>": {...verdict..., "timed_out": bool}}`` for each
    subscriber stream in ``events`` (a list of Event).

    ``expected_count`` precedence: the argument, then the subscriber's own start event, then the
    publisher start event of the same run_id. Streams with no subscriber events raise
    LogFormatError so an empty or publisher-only log is never reported as success.
    """
    pub_counts = {}
    streams = {}
    for ev in events:
        if ev.role == "publisher" and ev.event == "start" and ev.detail:
            n = ev.detail.get("expected_count")
            if isinstance(n, int) and not isinstance(n, bool):
                pub_counts[ev.run_id] = n
        if ev.role != "subscriber":
            continue
        key = (ev.run_id, ev.node, ev.topic)
        st = streams.setdefault(key, {"recv": [], "start_count": None, "timed_out": False})
        if ev.event == "start" and ev.detail:
            n = ev.detail.get("expected_count")
            if isinstance(n, int) and not isinstance(n, bool):
                st["start_count"] = n
        elif ev.event == "recv":
            st["recv"].append(ev)
        elif ev.event == "timeout":
            st["timed_out"] = True

    if not streams:
        raise LogFormatError("log contains no subscriber events to analyse")

    out = {}
    for (run_id, node, topic), st in streams.items():
        expected = expected_count
        if expected is None:
            expected = st["start_count"]
        if expected is None:
            expected = pub_counts.get(run_id)
        tracker = SequenceTracker(expected)
        for ev in st["recv"]:
            tracker.observe(ev.seq)
        result = tracker.verdict(timed_out=st["timed_out"]).to_dict()
        result["timed_out"] = st["timed_out"]
        result["duration_ns"] = _duration_ns(st["recv"])
        out[f"{run_id}|{node}|{topic}"] = result
    return out


def _duration_ns(recv_events):
    """Last recv ts minus first recv ts within the stream (same node, same clock), else None."""
    if len(recv_events) < 2:
        return None
    return recv_events[-1].elapsed_since(recv_events[0])


def all_ok(analysis):
    return bool(analysis) and all(v["ok"] for v in analysis.values())
