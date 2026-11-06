"""Validated configuration objects. Invalid values raise ConfigError (never silently clamped)."""

import math
import re
from dataclasses import dataclass, asdict

from .clocks import check_clock_name
from .errors import ConfigError

# Anchored with \A..\Z and always used with fullmatch(): a bare "$" also matches before a trailing
# newline, so "abc\n" would pass.
RUN_ID_RE = re.compile(r"\A[A-Za-z0-9_-]{1,32}\Z")
# Node and topic names: printable ASCII only (0x21-0x7e), so no whitespace, control characters
# (newline, NUL, ...) or non-ASCII characters.
NAME_RE = re.compile(r"\A[\x21-\x7e]+\Z")


def is_valid_run_id(value):
    return isinstance(value, str) and RUN_ID_RE.fullmatch(value) is not None


def is_valid_name(value):
    return isinstance(value, str) and NAME_RE.fullmatch(value) is not None
MAX_COUNT = 10**9 - 1  # seq is written with 10 digits
MAX_RATE_HZ = 100_000.0
MAX_PAYLOAD_BYTES = 1 << 20


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _positive_finite(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number (got {value!r})")
    if not math.isfinite(value) or value <= 0:
        raise ConfigError(f"{name} must be finite and > 0 (got {value!r})")
    return float(value)


def check_run_id(run_id):
    if not is_valid_run_id(run_id):
        raise ConfigError("run_id must match [A-Za-z0-9_-]{1,32} (got %r)" % (run_id,))
    return run_id


def check_topic(topic):
    if not is_valid_name(topic):
        raise ConfigError(f"topic must be non-empty printable ASCII without whitespace (got {topic!r})")
    return topic


def check_node(node):
    if not is_valid_name(node):
        raise ConfigError(f"node must be non-empty printable ASCII without whitespace (got {node!r})")
    return node


@dataclass(frozen=True)
class GeneratorConfig:
    """What the publisher sends: deterministic given these fields."""

    run_id: str
    count: int = 100
    rate_hz: float = 10.0
    payload_bytes: int = 64
    seed: int = 0
    clock: str = "wall"

    def __post_init__(self):
        from .payload import min_payload_bytes

        check_run_id(self.run_id)
        check_clock_name(self.clock)
        if not _is_int(self.count) or not (1 <= self.count <= MAX_COUNT):
            raise ConfigError(f"count must be an integer in 1..{MAX_COUNT} (got {self.count!r})")
        rate = _positive_finite(self.rate_hz, "rate_hz")
        if rate > MAX_RATE_HZ:
            raise ConfigError(f"rate_hz must be <= {MAX_RATE_HZ:g} (got {self.rate_hz!r})")
        object.__setattr__(self, "rate_hz", rate)
        if not _is_int(self.payload_bytes):
            raise ConfigError(f"payload_bytes must be an integer (got {self.payload_bytes!r})")
        lo = min_payload_bytes(self.run_id, self.clock)
        if not (lo <= self.payload_bytes <= MAX_PAYLOAD_BYTES):
            raise ConfigError(
                f"payload_bytes must be in {lo}..{MAX_PAYLOAD_BYTES} for run_id {self.run_id!r} "
                f"(got {self.payload_bytes!r})"
            )
        if not _is_int(self.seed):
            raise ConfigError(f"seed must be an integer (got {self.seed!r})")

    @property
    def period_ns(self):
        return max(1, round(1e9 / self.rate_hz))


@dataclass(frozen=True)
class PublisherConfig:
    generator: GeneratorConfig
    node: str = "seqprobe_pub"
    topic: str = "/seqprobe"
    start_delay_s: float = 0.0

    def __post_init__(self):
        check_node(self.node)
        check_topic(self.topic)
        if isinstance(self.start_delay_s, bool) or not isinstance(self.start_delay_s, (int, float)) \
                or not math.isfinite(self.start_delay_s) or self.start_delay_s < 0:
            raise ConfigError(f"start_delay_s must be finite and >= 0 (got {self.start_delay_s!r})")


@dataclass(frozen=True)
class SubscriberConfig:
    run_id: str
    expected_count: int = None  # None = unknown; completion can then not be established
    node: str = "seqprobe_sub"
    topic: str = "/seqprobe"
    clock: str = "wall"
    first_message_timeout_s: float = 30.0
    idle_timeout_s: float = 10.0
    overall_timeout_s: float = 300.0

    def __post_init__(self):
        check_run_id(self.run_id)
        check_node(self.node)
        check_topic(self.topic)
        check_clock_name(self.clock)
        if self.expected_count is not None and (
            not _is_int(self.expected_count) or not (1 <= self.expected_count <= MAX_COUNT)
        ):
            raise ConfigError(
                f"expected_count must be None or an integer in 1..{MAX_COUNT} (got {self.expected_count!r})"
            )
        for name in ("first_message_timeout_s", "idle_timeout_s", "overall_timeout_s"):
            object.__setattr__(self, name, _positive_finite(getattr(self, name), name))


def config_to_dict(cfg):
    """JSON-friendly dict of a config dataclass (used in the 'start' event detail)."""
    return asdict(cfg)
