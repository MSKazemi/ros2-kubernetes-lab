"""Reader for the schema-v1 event log written by examples/ros2-sequence-probe.

Only the fields documented in that component's ``seqprobe/events.py`` are used:
``schema_version, event, role, run_id, node, topic, seq, ts_ns, clock, sent_ts_ns, sent_clock``.
If that schema changes (``schema_version`` != 1) this reader refuses the file.

Mapping onto the harness trace:

* ``event=send`` (publisher)  -> send ``(seq, ts_ns)``
* ``event=recv`` (subscriber) -> recv ``(seq, ts_ns)``; ``sent_ts_ns/sent_clock`` is only used to
  cross-check the publisher's ``send`` record when both are present (mismatch = wrong log pair).
* ``start`` / ``timeout`` records are ignored; ``stop`` must be present for every (role, node)
  stream: it is the end-of-log sentinel, so a log without it is reported as truncated.

Clock domains: ``wall`` and ``ros`` map to the domains ``wall`` / ``ros``; ``monotonic`` maps to
``monotonic@<node>`` because monotonic origins differ per node, so a publisher/subscriber pair on
two nodes with ``monotonic`` is a mixed-domain trace (latency is refused, never faked).
``wall`` latency across nodes is only as accurate as the nodes' clock synchronisation, which is
NOT measured here; a note is attached to the analysis.

Fault markers are not part of the probe schema. An operator can supply a separate JSONL file with
lines ``{"name": "restart_begin", "t_ns": 123, "clock": "wall"}``.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .trace import Event, Marker, Trace, TraceError, TruncatedTraceError, EmptyTraceError

SUPPORTED_SCHEMA_VERSION = 1
_CLOCKS = ("monotonic", "wall", "ros")


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _domain(clock: str, node: str) -> str:
    return f"monotonic@{node}" if clock == "monotonic" else clock


def _read_records(lines: List[str], source: str) -> List[Tuple[int, Dict[str, Any]]]:
    last = max((i for i, t in enumerate(lines, 1) if t.strip()), default=0)
    out = []
    for no, text in enumerate(lines, 1):
        if not text.strip():
            continue
        try:
            rec = json.loads(text)
        except json.JSONDecodeError as exc:
            if no == last:
                raise TruncatedTraceError(f"{source}: last line is not valid JSON ({exc.msg}); log truncated?")
            raise TraceError(f"{source}: line {no}: invalid JSON ({exc.msg})")
        if not isinstance(rec, dict):
            raise TraceError(f"{source}: line {no}: record is not a JSON object")
        out.append((no, rec))
    return out


def parse_seqprobe(
    sources: Iterable[Tuple[str, List[str]]],
    markers: Optional[Tuple[str, List[str]]] = None,
) -> Trace:
    """Build a Trace from one or more probe logs (name, lines) and an optional marker log."""
    trace = Trace(header={"schema": "seqprobe/1", "synthetic": None}, source="")
    names: List[str] = []
    run_ids = set()
    topics = set()
    stops = set()
    streams = set()
    pub_nodes, sub_nodes = set(), set()
    send_ts: Dict[int, Tuple[int, str]] = {}
    send_where: Dict[int, str] = {}
    last_t: Dict[Any, int] = {}
    synthetic_flags = []
    recv_claims: List[Tuple[str, int, int, int, str]] = []

    for name, lines in sources:
        names.append(name)
        for no, rec in _read_records(lines, name):
            where = f"{name}: line {no}"
            if rec.get("schema_version") != SUPPORTED_SCHEMA_VERSION or not _is_int(rec.get("schema_version")):
                raise TraceError(f"{where}: unsupported schema_version {rec.get('schema_version')!r} (reader supports 1)")
            ev, role, node = rec.get("event"), rec.get("role"), rec.get("node")
            if ev not in ("start", "send", "recv", "timeout", "stop") or role not in ("publisher", "subscriber"):
                raise TraceError(f"{where}: unknown event/role {ev!r}/{role!r}")
            if not isinstance(node, str) or not node:
                raise TraceError(f"{where}: node must be a non-empty string")
            run_ids.add(rec.get("run_id"))
            topics.add(rec.get("topic"))
            streams.add((role, node))
            if ev == "stop":
                stops.add((role, node))
                continue
            if ev == "start":
                det = rec.get("detail")
                if isinstance(det, dict) and "synthetic" in det:
                    synthetic_flags.append(det["synthetic"])
                continue
            if ev == "timeout":
                continue
            seq, ts, clock = rec.get("seq"), rec.get("ts_ns"), rec.get("clock")
            if not _is_int(seq) or seq < 0 or not _is_int(ts) or ts < 0 or clock not in _CLOCKS:
                raise TraceError(f"{where}: send/recv need integer seq>=0, ts_ns>=0 and clock in {_CLOCKS}")
            if (ev == "send") != (role == "publisher"):
                raise TraceError(f"{where}: event {ev!r} is not valid for role {role!r}")
            dom = _domain(clock, node)
            if ev == "send" and seq in send_where:
                raise TraceError(
                    f"{where}: duplicate send for seq {seq}; first seen at {send_where[seq]} "
                    f"(log passed twice, or two runs/sessions concatenated?)"
                )
            key = (ev, dom)
            if key in last_t and ts < last_t[key]:
                from .trace import NonMonotonicClockError
                raise NonMonotonicClockError(f"{where}: ts_ns {ts} < previous {last_t[key]} in stream {key}")
            last_t[key] = ts
            if ev == "send":
                pub_nodes.add(node)
                trace.sends.append(Event("send", seq, ts, dom))
                send_ts[seq] = (ts, clock)
                send_where[seq] = where
            else:
                sub_nodes.add(node)
                trace.recvs.append(Event("recv", seq, ts, dom))
                recv_claims.append((where, seq, rec.get("sent_ts_ns"), 0, rec.get("sent_clock")))

    trace.source = ",".join(names) or "<memory>"
    if len(run_ids) > 1:
        raise TraceError(f"{trace.source}: logs from several run_ids {sorted(map(str, run_ids))}; analyze one run at a time")
    if len(topics) > 1:
        raise TraceError(f"{trace.source}: several topics {sorted(map(str, topics))}; analyze one topic at a time")
    if len(pub_nodes) > 1 or len(sub_nodes) > 1:
        raise TraceError(f"{trace.source}: more than one publisher or subscriber node; only one pair is supported")
    missing = sorted(streams - stops)
    if missing:
        raise TruncatedTraceError(f"{trace.source}: no stop event for stream(s) {missing}; log truncated?")
    for where, seq, sent_ts, _, sent_clock in recv_claims:
        if seq in send_ts and (sent_ts != send_ts[seq][0] or sent_clock != send_ts[seq][1]):
            raise TraceError(f"{where}: sent_ts_ns/sent_clock do not match the publisher's send record for seq {seq}; wrong log pair?")
    if not trace.sends:
        raise EmptyTraceError(f"{trace.source}: no send events (publisher log missing or empty); delivery metrics are undefined")

    trace.header["run_id"] = next(iter(run_ids), None)
    if synthetic_flags:
        trace.header["synthetic"] = all(f is True for f in synthetic_flags)
    pub_doms = {e.clock for e in trace.sends}
    if "wall" in pub_doms and sub_nodes and pub_nodes and pub_nodes != sub_nodes:
        trace.notes.append("wall-clock latency spans two nodes: accuracy is bounded by their clock synchronisation, which is not measured here")

    if markers is not None:
        mname, mlines = markers
        for no, rec in _read_records(mlines, mname):
            name, t, clock = rec.get("name"), rec.get("t_ns"), rec.get("clock")
            if not isinstance(name, str) or not name or not _is_int(t) or t < 0 or not isinstance(clock, str) or not clock:
                raise TraceError(f"{mname}: line {no}: marker needs name, integer t_ns>=0 and clock")
            if clock == "monotonic":
                raise TraceError(f"{mname}: line {no}: marker clock must name a domain such as 'wall' or 'monotonic@<node>'")
            trace.markers.append(Marker(name, t, clock))
        trace.markers.sort(key=lambda m: (m.clock, m.t_ns))
    return trace


def load_seqprobe(paths: List[str], markers_path: Optional[str] = None) -> Trace:
    def read(p: str) -> Tuple[str, List[str]]:
        with open(p, "r", encoding="utf-8") as fh:
            return p, fh.readlines()

    return parse_seqprobe([read(p) for p in paths], read(markers_path) if markers_path else None)
