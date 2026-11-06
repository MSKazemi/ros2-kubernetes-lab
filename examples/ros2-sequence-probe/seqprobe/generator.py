"""Deterministic message plan: which sequence IDs are sent, at which offsets from the start."""

from dataclasses import dataclass

from .payload import build_payload


@dataclass(frozen=True)
class PlannedMessage:
    seq: int
    offset_ns: int  # intended send time relative to the first send (monotonic nanoseconds)


def plan(cfg):
    """Yield ``cfg.count`` messages, seq 0..count-1, spaced exactly ``cfg.period_ns`` apart.

    Offsets are ``seq * period_ns`` (no accumulated drift in the plan itself). The plan is
    a pure function of the config; the *achieved* send times depend on the host scheduler.
    """
    period = cfg.period_ns
    for seq in range(cfg.count):
        yield PlannedMessage(seq=seq, offset_ns=seq * period)


def payload_for(cfg, seq, sent_ts_ns):
    return build_payload(cfg.run_id, seq, sent_ts_ns, cfg.clock, cfg.payload_bytes, cfg.seed)
