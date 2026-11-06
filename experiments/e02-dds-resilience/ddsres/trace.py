"""Trace parsing and validation for the e02 DDS resilience harness.

Native format ``rrl.trace/1`` is JSON Lines, one object per line::

    {"type":"header","schema":"rrl.trace/1","synthetic":true,"label":"...", ...}
    {"type":"send","seq":0,"t_ns":1000000000,"clock":"sim_mono"}
    {"type":"recv","seq":0,"t_ns":1002100000,"clock":"sim_mono"}
    {"type":"marker","name":"restart_begin","t_ns":...,"clock":"sim_mono"}
    {"type":"resource","t_ns":...,"clock":"sim_mono","node":"sub","cpu_pct":12.5,"mem_bytes":1048576}
    {"type":"footer","records":N}

``records`` in the footer counts every line except the header and the footer.
A missing footer, a final line that is not valid JSON, or a count mismatch means
the file is truncated and is rejected.

Other flat JSONL layouts can be read through an :class:`Adapter` that maps
their field names onto the native ones; the sequence-probe schema has its own
reader, :mod:`ddsres.seqprobe`. Nothing here talks to a network, a cluster or a robot.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional

SCHEMA = "rrl.trace/1"


class TraceError(ValueError):
    """The trace is malformed or internally inconsistent."""


class EmptyTraceError(TraceError):
    """The trace has no usable send records."""


class TruncatedTraceError(TraceError):
    """The trace ended early (no footer, bad last line, or count mismatch)."""


class NonMonotonicClockError(TraceError):
    """Timestamps of one stream went backwards in file order."""


class ClockDomainError(TraceError):
    """Timestamps from different clock domains would have to be compared."""


@dataclass(frozen=True)
class Event:
    kind: str  # "send" | "recv"
    seq: int
    t_ns: int
    clock: str


@dataclass(frozen=True)
class Marker:
    name: str
    t_ns: int
    clock: str


@dataclass(frozen=True)
class Resource:
    t_ns: int
    clock: str
    node: Optional[str]
    cpu_pct: Optional[float]
    mem_bytes: Optional[int]


@dataclass
class Trace:
    header: Dict[str, Any]
    sends: List[Event] = field(default_factory=list)
    recvs: List[Event] = field(default_factory=list)  # file (arrival) order
    markers: List[Marker] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    source: str = "<memory>"
    notes: List[str] = field(default_factory=list)  # caveats the reader wants surfaced in analysis


_UNIT_TO_NS = {"ns": 1, "us": 1_000, "ms": 1_000_000, "s": 1_000_000_000}


@dataclass(frozen=True)
class Adapter:
    """Mapping from a foreign JSONL record layout to the native one.

    ``kind_map`` maps the foreign value of ``kind_field`` to ``send``, ``recv``
    or ``marker``; records with other kinds are ignored. Foreign traces without
    a header/footer are accepted only because ``require_footer`` is False for
    adapters, so truncation can only be detected from a bad last line.
    """

    name: str
    kind_field: str
    kind_map: Dict[str, str]
    seq_field: str
    time_field: str
    time_unit: str = "ns"
    clock_field: Optional[str] = None
    default_clock: Optional[str] = None
    marker_name_field: str = "name"

    def convert(self, rec: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        kind = self.kind_map.get(rec.get(self.kind_field))
        if kind is None:
            return None
        if self.time_unit not in _UNIT_TO_NS:
            raise TraceError(f"adapter {self.name}: unknown time_unit {self.time_unit!r}")
        raw_t = rec.get(self.time_field)
        if isinstance(raw_t, bool) or not isinstance(raw_t, (int, float)):
            raise TraceError(f"adapter {self.name}: bad time value {raw_t!r}")
        t_ns = int(round(raw_t * _UNIT_TO_NS[self.time_unit]))
        clock = rec.get(self.clock_field) if self.clock_field else None
        clock = clock if clock is not None else self.default_clock
        out: Dict[str, Any] = {"type": kind, "t_ns": t_ns, "clock": clock}
        if kind == "marker":
            out["name"] = rec.get(self.marker_name_field)
        else:
            out["seq"] = rec.get(self.seq_field)
        return out


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _need_int(rec: Dict[str, Any], key: str, lineno: int, minimum: int = 0) -> int:
    v = rec.get(key)
    if not _is_int(v) or v < minimum:
        raise TraceError(f"line {lineno}: field {key!r} must be an integer >= {minimum}, got {v!r}")
    return v


def _need_clock(rec: Dict[str, Any], header: Dict[str, Any], lineno: int) -> str:
    c = rec.get("clock", header.get("default_clock"))
    if not isinstance(c, str) or not c:
        raise TraceError(f"line {lineno}: record has no clock domain and the header has no default_clock")
    return c


def parse_lines(
    lines: Iterable[str],
    source: str = "<memory>",
    adapter: Optional[Adapter] = None,
    require_footer: Optional[bool] = None,
) -> Trace:
    """Parse and validate a trace. Raises a :class:`TraceError` subclass on any defect."""
    if require_footer is None:
        require_footer = adapter is None
    raw = list(lines)
    if not any(t.strip() for t in raw):
        raise EmptyTraceError(f"{source}: file is empty")
    trace = Trace(header={}, source=source)
    body_records = 0
    footer: Optional[Dict[str, Any]] = None
    last_t: Dict[Any, int] = {}

    def stream_check(key: Any, t_ns: int, lineno: int) -> None:
        prev = last_t.get(key)
        if prev is not None and t_ns < prev:
            raise NonMonotonicClockError(
                f"{source}: line {lineno}: timestamp {t_ns} < previous {prev} in stream {key}"
            )
        last_t[key] = t_ns

    seen_header = False
    last_nonempty = max((i for i, t in enumerate(raw, start=1) if t.strip()), default=0)
    for lineno, text in enumerate(raw, start=1):
        if not text.strip():
            continue
        if footer is not None:
            raise TraceError(f"{source}: line {lineno}: data after footer")
        try:
            rec = json.loads(text)
        except json.JSONDecodeError as exc:
            if lineno == last_nonempty:
                raise TruncatedTraceError(f"{source}: last line is not valid JSON ({exc.msg}); file truncated?")
            raise TraceError(f"{source}: line {lineno}: invalid JSON ({exc.msg})")
        if not isinstance(rec, dict):
            raise TraceError(f"{source}: line {lineno}: record is not a JSON object")

        if adapter is not None:
            converted = adapter.convert(rec)
            if converted is None:
                continue
            rec = converted

        rtype = rec.get("type")
        if rtype == "header":
            if seen_header or body_records:
                raise TraceError(f"{source}: line {lineno}: header must be the first record, once")
            if adapter is None and rec.get("schema") != SCHEMA:
                raise TraceError(f"{source}: line {lineno}: unsupported schema {rec.get('schema')!r} (want {SCHEMA})")
            trace.header = rec
            seen_header = True
            continue
        if adapter is None and not seen_header:
            raise TraceError(f"{source}: line {lineno}: first record must be a {SCHEMA} header")
        if rtype == "footer":
            footer = rec
            continue

        body_records += 1
        if rtype in ("send", "recv"):
            seq = _need_int(rec, "seq", lineno)
            t_ns = _need_int(rec, "t_ns", lineno)
            clock = _need_clock(rec, trace.header, lineno)
            stream_check((rtype, clock), t_ns, lineno)
            (trace.sends if rtype == "send" else trace.recvs).append(Event(rtype, seq, t_ns, clock))
        elif rtype == "marker":
            name = rec.get("name")
            if not isinstance(name, str) or not name:
                raise TraceError(f"line {lineno}: marker needs a non-empty name")
            t_ns = _need_int(rec, "t_ns", lineno)
            clock = _need_clock(rec, trace.header, lineno)
            stream_check(("marker", clock), t_ns, lineno)
            trace.markers.append(Marker(name, t_ns, clock))
        elif rtype == "resource":
            t_ns = _need_int(rec, "t_ns", lineno)
            clock = _need_clock(rec, trace.header, lineno)
            cpu = rec.get("cpu_pct")
            mem = rec.get("mem_bytes")
            if cpu is not None and (isinstance(cpu, bool) or not isinstance(cpu, (int, float)) or cpu < 0):
                raise TraceError(f"line {lineno}: cpu_pct must be a number >= 0 or null")
            if mem is not None and (not _is_int(mem) or mem < 0):
                raise TraceError(f"line {lineno}: mem_bytes must be an integer >= 0 or null")
            node = rec.get("node")
            stream_check(("resource", node, clock), t_ns, lineno)
            trace.resources.append(Resource(t_ns, clock, node, cpu, mem))
        else:
            raise TraceError(f"line {lineno}: unknown record type {rtype!r}")
    if require_footer:
        if footer is None:
            raise TruncatedTraceError(f"{source}: no footer record (file truncated?)")
        if footer.get("records") != body_records:
            raise TruncatedTraceError(
                f"{source}: footer says {footer.get('records')!r} records, found {body_records}"
            )
    if not trace.sends:
        raise EmptyTraceError(f"{source}: no send records; delivery metrics are undefined")
    seqs = [e.seq for e in trace.sends]
    if len(set(seqs)) != len(seqs):
        raise TraceError(f"{source}: duplicate send records for the same seq")
    return trace


def load_trace(path: str, adapter: Optional[Adapter] = None) -> Trace:
    with open(path, "r", encoding="utf-8") as fh:
        return parse_lines(fh.readlines(), source=path, adapter=adapter)
