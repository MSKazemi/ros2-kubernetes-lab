"""Payload wire format (ASCII text, identical for std_msgs/String and ByteMultiArray):

    SQP1;<run_id>;<seq:10 digits>;<sent_ts_ns:20 digits>;<sent_clock>;<padding>

The padding is deterministic (seeded by seed and seq) and brings the payload to exactly
``payload_bytes`` bytes. ``sent_ts_ns`` is taken on the sender's ``sent_clock`` immediately before
the publish call; it is not a latency measurement.
"""

import random
import re

from .clocks import CLOCKS
from .config import is_valid_run_id
from .errors import PayloadError, ConfigError

MAGIC = "SQP1"
SEQ_DIGITS = 10
TS_DIGITS = 20
_PAD_ALPHABET = "0123456789abcdef"
_SEQ_RE = re.compile(r"\A[0-9]{%d}\Z" % SEQ_DIGITS)
_TS_RE = re.compile(r"\A[0-9]{%d}\Z" % TS_DIGITS)
_PAD_RE = re.compile(r"\A[0-9a-f]*\Z")


def header(run_id, seq, sent_ts_ns, clock):
    return f"{MAGIC};{run_id};{seq:0{SEQ_DIGITS}d};{sent_ts_ns:0{TS_DIGITS}d};{clock}"


def min_payload_bytes(run_id, clock):
    """Smallest payload that fits the header plus the ';' before the (possibly empty) padding."""
    return len(header(run_id, 0, 0, clock)) + 1


def pad_for(seed, seq, length):
    if length <= 0:
        return ""
    rng = random.Random(f"seqprobe:{seed}:{seq}")  # str seeds are hashed deterministically
    return "".join(rng.choice(_PAD_ALPHABET) for _ in range(length))


def build_payload(run_id, seq, sent_ts_ns, clock, payload_bytes, seed):
    if not is_valid_run_id(run_id):
        raise ConfigError(f"invalid run_id {run_id!r}")
    if clock not in CLOCKS:
        raise ConfigError(f"unknown clock {clock!r}")
    if seq < 0 or seq >= 10**SEQ_DIGITS:
        raise ConfigError(f"seq out of range: {seq!r}")
    if sent_ts_ns < 0 or sent_ts_ns >= 10**TS_DIGITS:
        raise ConfigError(f"timestamp out of range: {sent_ts_ns!r}")
    head = header(run_id, seq, sent_ts_ns, clock) + ";"
    pad_len = payload_bytes - len(head)
    if pad_len < 0:
        raise ConfigError(f"payload_bytes {payload_bytes} is smaller than the header ({len(head)} bytes)")
    return head + pad_for(seed, seq, pad_len)


class DecodedPayload:
    __slots__ = ("run_id", "seq", "sent_ts_ns", "sent_clock", "payload_bytes")

    def __init__(self, run_id, seq, sent_ts_ns, sent_clock, payload_bytes):
        self.run_id = run_id
        self.seq = seq
        self.sent_ts_ns = sent_ts_ns
        self.sent_clock = sent_clock
        self.payload_bytes = payload_bytes

    def __repr__(self):
        return (f"DecodedPayload(run_id={self.run_id!r}, seq={self.seq}, "
                f"sent_ts_ns={self.sent_ts_ns}, sent_clock={self.sent_clock!r}, "
                f"payload_bytes={self.payload_bytes})")


def coerce_bytes(data):
    """Turn what rclpy hands back into bytes.

    std_msgs/String.data is ``str``. std_msgs/ByteMultiArray.data is a sequence whose elements are
    ``bytes`` of length 1 (rclpy ``byte[]``) or, depending on the rmw/message path, ints.
    """
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    if isinstance(data, str):
        return data.encode("utf-8")
    try:
        parts = []
        for item in data:
            if isinstance(item, (bytes, bytearray)):
                if len(item) != 1:
                    raise PayloadError("byte array element must have length 1")
                parts.append(bytes(item))
            elif isinstance(item, int) and not isinstance(item, bool) and 0 <= item <= 255:
                parts.append(bytes([item]))
            else:
                raise PayloadError(f"unsupported byte array element {item!r}")
        return b"".join(parts)
    except TypeError:
        raise PayloadError(f"unsupported payload type {type(data).__name__}") from None


def decode_payload(raw):
    """Parse a payload (str / bytes / byte list). Raises PayloadError on anything malformed."""
    data = coerce_bytes(raw)
    try:
        text = data.decode("ascii")
    except UnicodeDecodeError:
        raise PayloadError("payload is not ASCII") from None
    parts = text.split(";", 5)
    if len(parts) != 6:
        raise PayloadError("payload has too few fields")
    magic, run_id, seq_s, ts_s, clock, pad = parts
    if magic != MAGIC:
        raise PayloadError(f"bad magic {magic!r}")
    if not is_valid_run_id(run_id):
        raise PayloadError("bad run_id")
    if not _SEQ_RE.fullmatch(seq_s):
        raise PayloadError("bad seq field")
    if not _TS_RE.fullmatch(ts_s):
        raise PayloadError("bad timestamp field")
    if clock not in CLOCKS:
        raise PayloadError(f"bad clock {clock!r}")
    if not _PAD_RE.fullmatch(pad):
        raise PayloadError("bad padding")
    return DecodedPayload(run_id, int(seq_s), int(ts_s), clock, len(data))
