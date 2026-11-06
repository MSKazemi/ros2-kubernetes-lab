"""The JSON-lines event schema (version 1) and its strict parser/serialiser.

One JSON object per line, keys in this fixed order, no unknown keys:

    schema_version  int   always 1
    event           str   start | send | recv | timeout | stop
    role            str   publisher | subscriber
    run_id          str   [A-Za-z0-9_-]{1,32}
    node            str   node name, no whitespace
    topic           str   topic name, no whitespace
    seq             int|null   >= 0; required for send and recv, null otherwise
    payload_bytes   int|null   >= 0; required for send and recv, null otherwise
    ts_ns           int   >= 0; time of the event on the clock named in ``clock``
    clock           str   monotonic | wall | ros   (see clocks.py)
    sent_ts_ns      int|null   recv only: the sender's timestamp copied out of the payload
    sent_clock      str|null   recv only: the clock ``sent_ts_ns`` was taken on
    detail          object|null   free-form per event type (config on start, verdict on stop)
"""

import json
from dataclasses import dataclass

from .clocks import CLOCKS, require_same_clock
from .config import RUN_ID_RE
from .errors import LogFormatError

SCHEMA_VERSION = 1
EVENTS = ("start", "send", "recv", "timeout", "stop")
ROLES = ("publisher", "subscriber")
FIELDS = ("schema_version", "event", "role", "run_id", "node", "topic", "seq",
          "payload_bytes", "ts_ns", "clock", "sent_ts_ns", "sent_clock", "detail")

_ROLE_EVENTS = {
    "publisher": ("start", "send", "stop"),
    "subscriber": ("start", "recv", "timeout", "stop"),
}


def _is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


@dataclass(frozen=True)
class Event:
    event: str
    role: str
    run_id: str
    node: str
    topic: str
    ts_ns: int
    clock: str
    seq: int = None
    payload_bytes: int = None
    sent_ts_ns: int = None
    sent_clock: str = None
    detail: dict = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self):
        # Writers cannot construct a record that the parser would reject.
        check_fields(self.to_dict())

    def to_dict(self):
        return {name: getattr(self, name) for name in FIELDS}

    def to_json_line(self):
        return json.dumps(self.to_dict(), separators=(",", ":"), allow_nan=False)

    def elapsed_since(self, earlier):
        """Nanoseconds between two events, only if they share a clock domain.

        Raises ClockMismatchError when the clocks differ or when two ``monotonic`` readings come
        from different nodes. This is an *elapsed time on one clock*, not a latency.
        """
        require_same_clock(self.clock, earlier.clock, self.node, earlier.node)
        return self.ts_ns - earlier.ts_ns


def check_fields(obj, line_no=None):
    """Raise LogFormatError unless the decoded JSON object conforms to schema v1."""

    def bad(msg):
        raise LogFormatError(msg, line_no)

    if not isinstance(obj, dict):
        bad("record is not a JSON object")
    missing = [f for f in FIELDS if f not in obj]
    if missing:
        bad("missing field(s): " + ", ".join(missing))
    unknown = [k for k in obj if k not in FIELDS]
    if unknown:
        bad("unknown field(s): " + ", ".join(sorted(map(str, unknown))))
    if obj["schema_version"] != SCHEMA_VERSION or not _is_int(obj["schema_version"]):
        bad(f"unsupported schema_version {obj['schema_version']!r} (this parser reads {SCHEMA_VERSION})")
    if obj["event"] not in EVENTS:
        bad(f"unknown event {obj['event']!r}")
    if obj["role"] not in ROLES:
        bad(f"unknown role {obj['role']!r}")
    if obj["event"] not in _ROLE_EVENTS[obj["role"]]:
        bad(f"event {obj['event']!r} is not valid for role {obj['role']!r}")
    if not isinstance(obj["run_id"], str) or not RUN_ID_RE.match(obj["run_id"]):
        bad("run_id must match [A-Za-z0-9_-]{1,32}")
    for key in ("node", "topic"):
        v = obj[key]
        if not isinstance(v, str) or not v or any(c.isspace() for c in v):
            bad(f"{key} must be a non-empty string without whitespace")
    if not _is_int(obj["ts_ns"]) or obj["ts_ns"] < 0:
        bad("ts_ns must be an integer >= 0")
    if obj["clock"] not in CLOCKS:
        bad(f"clock must be one of {', '.join(CLOCKS)}")
    for key in ("seq", "payload_bytes", "sent_ts_ns"):
        v = obj[key]
        if v is not None and (not _is_int(v) or v < 0):
            bad(f"{key} must be null or an integer >= 0")
    if obj["sent_clock"] is not None and obj["sent_clock"] not in CLOCKS:
        bad("sent_clock must be null or one of " + ", ".join(CLOCKS))
    if obj["detail"] is not None and not isinstance(obj["detail"], dict):
        bad("detail must be null or an object")

    ev = obj["event"]
    if ev in ("send", "recv"):
        if obj["seq"] is None or obj["payload_bytes"] is None:
            bad(f"{ev} events require seq and payload_bytes")
    else:
        if obj["seq"] is not None or obj["payload_bytes"] is not None:
            bad(f"{ev} events must have seq and payload_bytes = null")
    if ev == "recv":
        if obj["sent_ts_ns"] is None or obj["sent_clock"] is None:
            bad("recv events require sent_ts_ns and sent_clock")
    elif obj["sent_ts_ns"] is not None or obj["sent_clock"] is not None:
        bad(f"{ev} events must have sent_ts_ns and sent_clock = null")


def validate_fields(obj, line_no=None):
    """Validate a decoded JSON object against schema v1; return an Event."""
    check_fields(obj, line_no)
    return Event(**{name: obj[name] for name in FIELDS})


def parse_line(line, line_no=None):
    try:
        obj = json.loads(line, parse_constant=_reject_constant)
    except (ValueError, RecursionError) as exc:
        raise LogFormatError(f"invalid JSON ({exc})", line_no) from None
    return validate_fields(obj, line_no)


def _reject_constant(name):
    raise ValueError(f"non-finite number {name}")


def read_events(lines):
    """Parse an iterable of lines into a list of Events (blank lines skipped).

    Raises LogFormatError on the first malformed record, and ClockMismatchError if one stream
    (run_id, role, node, topic) switches clock domain part-way through.
    """
    from .errors import ClockMismatchError

    events = []
    stream_clock = {}
    for line_no, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        ev = parse_line(line, line_no)
        key = (ev.run_id, ev.role, ev.node, ev.topic)
        first = stream_clock.setdefault(key, (ev.clock, line_no))
        if first[0] != ev.clock:
            raise ClockMismatchError(
                f"line {line_no}: stream {key} uses clock {ev.clock!r} but line {first[1]} used {first[0]!r}"
            )
        events.append(ev)
    return events
