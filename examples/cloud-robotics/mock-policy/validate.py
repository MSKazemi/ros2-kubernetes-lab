"""Fail-closed validator for the simulated observation/action contract v1.

Python standard library only. This module is independent of any policy or
model code: it never imports ``mock_policy`` and treats every message as
untrusted data. A rejection is returned as a typed ``ValidationResult``; the
public methods never raise on bad input (unexpected internal errors also
become a rejection with reason ``INTERNAL_ERROR``).

SIMULATED EDUCATIONAL CONTRACT. It does not control any robot and is not a
safety-certified gate. ``source_id`` is a self-declared label checked against
an allow-list; it is NOT authentication (no signatures, no SROS 2).
"""

from __future__ import annotations

import base64
import binascii
import enum
import math
import re
from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Optional

import contract as c


class RejectReason(str, enum.Enum):
    """Typed reason for a rejection (stable strings, safe to log)."""

    MALFORMED_MESSAGE = "MALFORMED_MESSAGE"
    MISSING_FIELD = "MISSING_FIELD"
    WRONG_TYPE = "WRONG_TYPE"
    UNSUPPORTED_VERSION = "UNSUPPORTED_VERSION"
    NOT_SIMULATED = "NOT_SIMULATED"
    NON_FINITE_VALUE = "NON_FINITE_VALUE"
    TIMESTAMP_OUT_OF_BOUNDS = "TIMESTAMP_OUT_OF_BOUNDS"
    TIMESTAMP_NOT_MONOTONIC = "TIMESTAMP_NOT_MONOTONIC"
    DUPLICATE_SEQUENCE = "DUPLICATE_SEQUENCE"
    OUT_OF_ORDER_SEQUENCE = "OUT_OF_ORDER_SEQUENCE"
    MISSING_CAMERA = "MISSING_CAMERA"
    UNKNOWN_CAMERA = "UNKNOWN_CAMERA"
    CAMERA_KEY_MISMATCH = "CAMERA_KEY_MISMATCH"
    BAD_CAMERA_SHAPE = "BAD_CAMERA_SHAPE"
    BAD_CAMERA_DATA = "BAD_CAMERA_DATA"
    WRONG_STATE_NAMES = "WRONG_STATE_NAMES"
    WRONG_UNITS = "WRONG_UNITS"
    WRONG_DIMENSION = "WRONG_DIMENSION"
    OUT_OF_LIMITS = "OUT_OF_LIMITS"
    STALE_ACTION = "STALE_ACTION"
    EXPIRED_TTL = "EXPIRED_TTL"
    FUTURE_TIMESTAMP = "FUTURE_TIMESTAMP"
    STALE_OBSERVATION = "STALE_OBSERVATION"
    UNKNOWN_OBSERVATION = "UNKNOWN_OBSERVATION"
    UNAUTHORIZED_SOURCE = "UNAUTHORIZED_SOURCE"
    UNAUTHORIZED_COMMAND = "UNAUTHORIZED_COMMAND"
    INTERNAL_ERROR = "INTERNAL_ERROR"


@dataclass(frozen=True)
class ValidationResult:
    """Outcome of one validation. ``ok`` is True only if the message passed."""

    ok: bool
    reason: Optional[RejectReason] = None
    field: str = ""
    detail: str = ""

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason.value if self.reason else None,
            "field": self.field,
            "detail": self.detail,
        }


_ACCEPT = ValidationResult(ok=True)


class _Reject(Exception):
    """Internal control flow only; never escapes the public methods."""

    def __init__(self, reason: RejectReason, field: str, detail: str):
        super().__init__(reason.value)
        self.result = ValidationResult(False, reason, field, detail)


@dataclass(frozen=True)
class ContractConfig:
    """Validator settings. The default allow-list is empty, so by default every
    action is rejected (fail closed) until a source is explicitly allowed."""

    allowed_sources: frozenset = frozenset()
    max_action_age_ms: int = 200
    max_future_skew_ms: int = 5
    observation_registry_size: int = 64

    def __post_init__(self) -> None:
        for name in ("max_action_age_ms", "max_future_skew_ms", "observation_registry_size"):
            v = getattr(self, name)
            if isinstance(v, bool) or not isinstance(v, int) or v < 0:
                raise ValueError(f"{name} must be a non-negative int")
        if self.observation_registry_size < 1:
            raise ValueError("observation_registry_size must be >= 1")


_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")


def _fail(reason: RejectReason, field: str, detail: str):
    raise _Reject(reason, field, detail)


def _is_int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def _fields(msg: Any, allowed: tuple, where: str) -> None:
    if not isinstance(msg, dict):
        _fail(RejectReason.MALFORMED_MESSAGE, where, "message must be a JSON object")
    for k in msg:
        if not isinstance(k, str):
            _fail(RejectReason.MALFORMED_MESSAGE, where, "non-string key")
    for k in allowed:
        if k not in msg:
            _fail(RejectReason.MISSING_FIELD, f"{where}.{k}".strip("."), "required field missing")
    for k in msg:
        if k not in allowed:
            _fail(RejectReason.MALFORMED_MESSAGE, f"{where}.{k}".strip("."), "unknown field")


def _ident(v: Any, field: str) -> str:
    if not isinstance(v, str):
        _fail(RejectReason.WRONG_TYPE, field, "expected string")
    if _ID_RE.fullmatch(v) is None:
        _fail(RejectReason.MALFORMED_MESSAGE, field, "identifier has invalid characters or length")
    return v


def _int_in(v: Any, field: str, lo: int, hi: int, reason: RejectReason) -> int:
    if isinstance(v, float) and not math.isfinite(v):
        _fail(RejectReason.NON_FINITE_VALUE, field, "not a finite number")
    if not _is_int(v):
        _fail(RejectReason.WRONG_TYPE, field, "expected integer")
    if v < lo or v > hi:
        _fail(reason, field, "integer outside the allowed bounds")
    return v


def _timestamp(v: Any, field: str) -> int:
    return _int_in(v, field, 0, c.MAX_TIMESTAMP_NS, RejectReason.TIMESTAMP_OUT_OF_BOUNDS)


def _sequence(v: Any, field: str) -> int:
    return _int_in(v, field, 0, c.MAX_SEQUENCE_ID, RejectReason.MALFORMED_MESSAGE)


def _ttl(v: Any, field: str) -> int:
    return _int_in(v, field, 1, c.MAX_TTL_MS, RejectReason.MALFORMED_MESSAGE)


def _header(msg: dict) -> None:
    if not isinstance(msg["contract_version"], str):
        _fail(RejectReason.WRONG_TYPE, "contract_version", "expected string")
    if msg["contract_version"] != c.CONTRACT_VERSION:
        _fail(RejectReason.UNSUPPORTED_VERSION, "contract_version", "unsupported contract version")
    if msg["simulated"] is not True:
        _fail(RejectReason.NOT_SIMULATED, "simulated", "this contract only carries simulated messages")


def _check_values(values: Any, field: str) -> None:
    """Dimension, finiteness and per-joint limit check for an ordered vector."""
    if not isinstance(values, list):
        _fail(RejectReason.WRONG_TYPE, field, "expected list")
    if len(values) != c.ACTION_DIM:
        _fail(RejectReason.WRONG_DIMENSION, field, f"expected {c.ACTION_DIM} values")
    for i, v in enumerate(values):
        f = f"{field}[{i}]"
        if isinstance(v, bool) or not isinstance(v, (int, float)):
            _fail(RejectReason.WRONG_TYPE, f, "expected number")
        if isinstance(v, float) and not math.isfinite(v):
            _fail(RejectReason.NON_FINITE_VALUE, f, "NaN or infinity")
    for i, v in enumerate(values):
        lo, hi = c.JOINT_LIMITS[i]
        if v < lo or v > hi:
            _fail(RejectReason.OUT_OF_LIMITS, f"{field}[{i}]", f"outside limits of {c.JOINT_NAMES[i]}")


def _check_units(units: Any, field: str) -> None:
    if not isinstance(units, list):
        _fail(RejectReason.WRONG_TYPE, field, "expected list")
    if len(units) != c.ACTION_DIM:
        _fail(RejectReason.WRONG_DIMENSION, field, f"expected {c.ACTION_DIM} units")
    for i, u in enumerate(units):
        if not isinstance(u, str):
            _fail(RejectReason.WRONG_TYPE, f"{field}[{i}]", "expected string")
        if u != c.JOINT_UNITS[i]:
            _fail(RejectReason.WRONG_UNITS, f"{field}[{i}]", f"expected unit of {c.JOINT_NAMES[i]}")


def _check_camera(cam: Any, i: int) -> str:
    where = f"cameras[{i}]"
    _fields(cam, c.CAMERA_FIELDS, where)
    name = cam["name"]
    if not isinstance(name, str):
        _fail(RejectReason.WRONG_TYPE, f"{where}.name", "expected string")
    if name not in c.CAMERA_KEYS:
        _fail(RejectReason.UNKNOWN_CAMERA, f"{where}.name", "camera name not in the mapping")
    if not isinstance(cam["key"], str):
        _fail(RejectReason.WRONG_TYPE, f"{where}.key", "expected string")
    if cam["key"] != c.CAMERA_KEYS[name]:
        _fail(RejectReason.CAMERA_KEY_MISMATCH, f"{where}.key", "key does not match the camera mapping")
    w = _int_in(cam["width"], f"{where}.width", 1, c.MAX_CAMERA_DIM, RejectReason.BAD_CAMERA_SHAPE)
    h = _int_in(cam["height"], f"{where}.height", 1, c.MAX_CAMERA_DIM, RejectReason.BAD_CAMERA_SHAPE)
    enc = cam["encoding"]
    if not isinstance(enc, str):
        _fail(RejectReason.WRONG_TYPE, f"{where}.encoding", "expected string")
    if enc not in c.CAMERA_ENCODINGS:
        _fail(RejectReason.BAD_CAMERA_SHAPE, f"{where}.encoding", "unsupported encoding")
    expected = w * h * c.CAMERA_ENCODINGS[enc]
    if expected > c.MAX_CAMERA_BYTES:
        _fail(RejectReason.BAD_CAMERA_SHAPE, where, "image larger than the byte bound")
    data = cam["data_b64"]
    if not isinstance(data, str):
        _fail(RejectReason.WRONG_TYPE, f"{where}.data_b64", "expected string")
    if len(data) > (c.MAX_CAMERA_BYTES * 4) // 3 + 8:
        _fail(RejectReason.BAD_CAMERA_DATA, f"{where}.data_b64", "payload larger than the byte bound")
    try:
        raw = base64.b64decode(data.encode("ascii"), validate=True)
    except (binascii.Error, UnicodeEncodeError, ValueError):
        _fail(RejectReason.BAD_CAMERA_DATA, f"{where}.data_b64", "not valid base64")
    if len(raw) != expected:
        _fail(RejectReason.BAD_CAMERA_SHAPE, where, "byte length does not match width*height*channels")
    return name


class ContractValidator:
    """Stateful validator for one observation stream and one action stream.

    State (last sequence/timestamp, known observations) changes only when a
    message is accepted, so a rejected message can never advance it.
    """

    def __init__(self, config: Optional[ContractConfig] = None):
        self.config = config or ContractConfig()
        self._last_obs_seq = -1
        self._last_obs_ts = -1
        self._last_action_seq = -1
        self._observations: "OrderedDict[str, tuple]" = OrderedDict()

    # -- public API (never raises on bad input) ---------------------------

    def validate_observation(self, msg: Any) -> ValidationResult:
        try:
            self._check_observation(msg)
            return _ACCEPT
        except _Reject as r:
            return r.result
        except Exception:  # fail closed on any unexpected error
            return ValidationResult(False, RejectReason.INTERNAL_ERROR, "", "unexpected validator error")

    def validate_action(self, msg: Any, now_ns: Any) -> ValidationResult:
        """``now_ns`` is the receiver's monotonic clock in ns, supplied by the
        caller so results are deterministic and testable."""
        try:
            self._check_action(msg, now_ns)
            return _ACCEPT
        except _Reject as r:
            return r.result
        except Exception:
            return ValidationResult(False, RejectReason.INTERNAL_ERROR, "", "unexpected validator error")

    # -- checks -----------------------------------------------------------

    def _check_observation(self, msg: Any) -> None:
        _fields(msg, c.OBSERVATION_FIELDS, "")
        _header(msg)
        obs_id = _ident(msg["observation_id"], "observation_id")
        seq = _sequence(msg["sequence_id"], "sequence_id")
        ts = _timestamp(msg["source_timestamp_ns"], "source_timestamp_ns")
        _ident(msg["frame_name"], "frame_name")
        _ident(msg["task_id"], "task_id")
        ttl = _ttl(msg["ttl_ms"], "ttl_ms")

        cams = msg["cameras"]
        if not isinstance(cams, list):
            _fail(RejectReason.WRONG_TYPE, "cameras", "expected list")
        if len(cams) > len(c.CAMERA_KEYS) * 2:
            _fail(RejectReason.MALFORMED_MESSAGE, "cameras", "too many camera entries")
        seen = []
        for i, cam in enumerate(cams):
            name = _check_camera(cam, i)
            if name in seen:
                _fail(RejectReason.MALFORMED_MESSAGE, f"cameras[{i}].name", "duplicate camera")
            seen.append(name)
        for required in c.REQUIRED_CAMERAS:
            if required not in seen:
                _fail(RejectReason.MISSING_CAMERA, "cameras", f"required camera {required} missing")

        state = msg["state"]
        _fields(state, c.STATE_FIELDS, "state")
        names = state["names"]
        if not isinstance(names, list):
            _fail(RejectReason.WRONG_TYPE, "state.names", "expected list")
        if names != list(c.JOINT_NAMES):
            _fail(RejectReason.WRONG_STATE_NAMES, "state.names", "names or order differ from the contract")
        _check_units(state["units"], "state.units")
        _check_values(state["values"], "state.values")

        # Monotonic checks last; state is committed only after everything passed.
        if seq == self._last_obs_seq:
            _fail(RejectReason.DUPLICATE_SEQUENCE, "sequence_id", "sequence id already accepted")
        if seq < self._last_obs_seq:
            _fail(RejectReason.OUT_OF_ORDER_SEQUENCE, "sequence_id", "sequence id went backwards")
        if ts <= self._last_obs_ts:
            _fail(RejectReason.TIMESTAMP_NOT_MONOTONIC, "source_timestamp_ns", "timestamp not increasing")
        self._last_obs_seq = seq
        self._last_obs_ts = ts
        self._observations[obs_id] = (ts, ttl)
        while len(self._observations) > self.config.observation_registry_size:
            self._observations.popitem(last=False)

    def _check_action(self, msg: Any, now_ns: Any) -> None:
        cfg = self.config
        now = _timestamp(now_ns, "now_ns")
        _fields(msg, c.ACTION_FIELDS, "")
        _header(msg)

        source = _ident(msg["source_id"], "source_id")
        if source not in cfg.allowed_sources:
            _fail(RejectReason.UNAUTHORIZED_SOURCE, "source_id", "source is not on the allow-list")
        cmd = msg["command"]
        if not isinstance(cmd, str):
            _fail(RejectReason.WRONG_TYPE, "command", "expected string")
        if cmd not in c.ALLOWED_COMMANDS:
            _fail(RejectReason.UNAUTHORIZED_COMMAND, "command", "command is not on the allow-list")
        if not isinstance(msg["action_space"], str):
            _fail(RejectReason.WRONG_TYPE, "action_space", "expected string")
        if msg["action_space"] != c.ACTION_SPACE:
            _fail(RejectReason.UNAUTHORIZED_COMMAND, "action_space", "unsupported action space")

        seq = _sequence(msg["sequence_id"], "sequence_id")
        obs_id = _ident(msg["observation_id"], "observation_id")
        _ident(msg["task_id"], "task_id")
        _ident(msg["model_id"], "model_id")
        _ident(msg["model_revision"], "model_revision")
        created = _timestamp(msg["created_timestamp_ns"], "created_timestamp_ns")
        ttl = _ttl(msg["ttl_ms"], "ttl_ms")

        _check_units(msg["units"], "units")
        _check_values(msg["values"], "values")

        age_ns = now - created
        if age_ns < -cfg.max_future_skew_ms * 1_000_000:
            _fail(RejectReason.FUTURE_TIMESTAMP, "created_timestamp_ns", "action timestamp is in the future")
        if age_ns > cfg.max_action_age_ms * 1_000_000:
            _fail(RejectReason.STALE_ACTION, "created_timestamp_ns", "action older than the configured maximum age")
        if age_ns > ttl * 1_000_000:
            _fail(RejectReason.EXPIRED_TTL, "ttl_ms", "action older than its own ttl")

        known = self._observations.get(obs_id)
        if known is None:
            _fail(RejectReason.UNKNOWN_OBSERVATION, "observation_id", "no accepted observation with this id")
        obs_ts, obs_ttl = known
        if now - obs_ts > obs_ttl * 1_000_000:
            _fail(RejectReason.STALE_OBSERVATION, "observation_id", "source observation is past its ttl")

        if seq == self._last_action_seq:
            _fail(RejectReason.DUPLICATE_SEQUENCE, "sequence_id", "action sequence id already accepted (replay)")
        if seq < self._last_action_seq:
            _fail(RejectReason.OUT_OF_ORDER_SEQUENCE, "sequence_id", "action sequence id went backwards")
        self._last_action_seq = seq
