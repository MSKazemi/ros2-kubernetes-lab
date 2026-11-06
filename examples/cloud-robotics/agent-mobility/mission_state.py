"""Portable mission-state contract ``mission-state/v1`` (SIMULATION, non-actuating).

This module defines the document that one *simulated* executor hands to another,
the typed rejection reasons, and the validators. It performs no I/O, opens no
network connection, and never touches a robot or ROS 2.

The SHA-256 ``integrity.digest`` only detects accidental modification. It is not
a signature, MAC or proof of origin. Nothing here is a trust boundary.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

SCHEMA = "mission-state/v1"
ID_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.:-]{0,63}$")
NONCE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
ROLLBACK_POLICIES = ("reissue_to_origin", "park")
UNIT_KEYS = ("length", "angle", "time")


class Reason:
    """Typed rejection reasons. The string value is the stable, documented code."""

    # document shape
    MALFORMED_DOCUMENT = "MALFORMED_DOCUMENT"
    MISSING_FIELD = "MISSING_FIELD"
    UNKNOWN_FIELD = "UNKNOWN_FIELD"
    WRONG_TYPE = "WRONG_TYPE"
    BAD_VALUE = "BAD_VALUE"
    BAD_IDENTIFIER = "BAD_IDENTIFIER"
    UNSUPPORTED_SCHEMA_VERSION = "UNSUPPORTED_SCHEMA_VERSION"
    NOT_SIMULATED = "NOT_SIMULATED"
    DIGEST_MISMATCH = "DIGEST_MISMATCH"
    PROGRESS_INCONSISTENT = "PROGRESS_INCONSISTENT"
    INCONSISTENT_BUNDLE = "INCONSISTENT_BUNDLE"
    # freshness
    BUNDLE_EXPIRED = "BUNDLE_EXPIRED"
    BUNDLE_FROM_FUTURE = "BUNDLE_FROM_FUTURE"
    # handoff parties, ownership, replay
    SAME_EXECUTOR = "SAME_EXECUTOR"
    WRONG_DESTINATION = "WRONG_DESTINATION"
    REPLAYED_NONCE = "REPLAYED_NONCE"
    STALE_SEQUENCE = "STALE_SEQUENCE"
    STALE_EPOCH = "STALE_EPOCH"
    WRONG_STATE_OWNER = "WRONG_STATE_OWNER"
    STALE_CHECKPOINT = "STALE_CHECKPOINT"
    MISSION_COMPLETE = "MISSION_COMPLETE"
    # compatibility and capability
    SCHEMA_NOT_SUPPORTED = "SCHEMA_NOT_SUPPORTED"
    ROBOT_CLASS_MISMATCH = "ROBOT_CLASS_MISMATCH"
    FRAME_MISMATCH = "FRAME_MISMATCH"
    MAP_REVISION_MISMATCH = "MAP_REVISION_MISMATCH"
    UNITS_MISMATCH = "UNITS_MISMATCH"
    MISSING_CAPABILITY = "MISSING_CAPABILITY"
    MISSING_SENSOR = "MISSING_SENSOR"
    SENSOR_TYPE_MISMATCH = "SENSOR_TYPE_MISMATCH"
    SENSOR_UNITS_MISMATCH = "SENSOR_UNITS_MISMATCH"
    ACTION_COMMAND_UNSUPPORTED = "ACTION_COMMAND_UNSUPPORTED"
    ACTION_SPACE_MISMATCH = "ACTION_SPACE_MISMATCH"
    ACTION_UNITS_MISMATCH = "ACTION_UNITS_MISMATCH"
    # effect gate (simulated, non-actuating sink)
    MALFORMED_EFFECT = "MALFORMED_EFFECT"
    STALE_EXECUTOR = "STALE_EXECUTOR"
    UNKNOWN_EPOCH = "UNKNOWN_EPOCH"
    NOT_STATE_OWNER = "NOT_STATE_OWNER"
    LEASE_EXPIRED = "LEASE_EXPIRED"
    REPLAYED_EFFECT = "REPLAYED_EFFECT"
    EFFECT_SEQUENCE_GAP = "EFFECT_SEQUENCE_GAP"
    EFFECT_SEQUENCE_REGRESSION = "EFFECT_SEQUENCE_REGRESSION"
    WRONG_NEXT_STEP = "WRONG_NEXT_STEP"

    @classmethod
    def all(cls) -> frozenset[str]:
        return frozenset(v for k, v in vars(cls).items() if k.isupper() and isinstance(v, str))

    @classmethod
    def bundle_reasons(cls) -> frozenset[str]:
        """Reasons raised while validating a handoff bundle (everything but the effect gate)."""
        return cls.all() - cls.effect_reasons()

    @classmethod
    def effect_reasons(cls) -> frozenset[str]:
        return frozenset({
            cls.MALFORMED_EFFECT, cls.STALE_EXECUTOR, cls.UNKNOWN_EPOCH, cls.NOT_STATE_OWNER,
            cls.LEASE_EXPIRED, cls.REPLAYED_EFFECT, cls.EFFECT_SEQUENCE_GAP,
            cls.EFFECT_SEQUENCE_REGRESSION, cls.WRONG_NEXT_STEP,
        })


class Rejection(Exception):
    """A typed, deterministic refusal. ``reason`` is a :class:`Reason` value."""

    def __init__(self, reason: str, field_name: str = "", detail: str = ""):
        super().__init__(f"{reason}: {field_name} {detail}".strip())
        self.reason = reason
        self.field = field_name
        self.detail = detail


# --------------------------------------------------------------------------- helpers
def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_digest(bundle: dict[str, Any]) -> str:
    """SHA-256 over the canonical JSON of the bundle with ``integrity`` removed."""
    body = {k: v for k, v in bundle.items() if k != "integrity"}
    return hashlib.sha256(canonical_json(body).encode("ascii")).hexdigest()


def seal(bundle: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with ``integrity`` recomputed."""
    out = copy.deepcopy(bundle)
    out["integrity"] = {"algorithm": "sha256", "digest": compute_digest(out)}
    return out


def _fail(reason: str, where: str, detail: str = "") -> None:
    raise Rejection(reason, where, detail)


def _exact(obj: Any, keys: Iterable[str], where: str) -> dict[str, Any]:
    if not isinstance(obj, dict):
        _fail(Reason.MALFORMED_DOCUMENT if where == "bundle" else Reason.WRONG_TYPE, where, "expected object")
    expected = set(keys)
    missing = sorted(expected - set(obj))
    if missing:
        _fail(Reason.MISSING_FIELD, where, ",".join(missing))
    extra = sorted(set(obj) - expected)
    if extra:
        _fail(Reason.UNKNOWN_FIELD, where, ",".join(extra))
    return obj


def _ident(value: Any, where: str) -> str:
    if not isinstance(value, str):
        _fail(Reason.WRONG_TYPE, where, "expected string")
    if ID_RE.fullmatch(value) is None:
        _fail(Reason.BAD_IDENTIFIER, where, "does not match identifier pattern")
    return value


def _int(value: Any, where: str, minimum: int = 0) -> int:
    if type(value) is not int:
        _fail(Reason.WRONG_TYPE, where, "expected integer")
    if value < minimum:
        _fail(Reason.BAD_VALUE, where, f"must be >= {minimum}")
    return value


def _id_list(value: Any, where: str, *, allow_empty: bool) -> list[str]:
    if not isinstance(value, list):
        _fail(Reason.WRONG_TYPE, where, "expected list")
    if not value and not allow_empty:
        _fail(Reason.BAD_VALUE, where, "must not be empty")
    for item in value:
        _ident(item, where)
    if len(set(value)) != len(value):
        _fail(Reason.BAD_VALUE, where, "duplicate entries")
    return value


# --------------------------------------------------------------------------- structure
def validate_structure(doc: Any) -> dict[str, Any]:
    """Shape, types, identifiers and internal consistency. No coordinator context."""
    root = _exact(doc, ("schema", "simulated", "mission", "progress", "ownership", "handoff",
                        "requirements", "rollback", "integrity"), "bundle")
    if root["schema"] != SCHEMA:
        _fail(Reason.UNSUPPORTED_SCHEMA_VERSION, "schema", str(root["schema"])[:40])
    if root["simulated"] is not True:
        _fail(Reason.NOT_SIMULATED, "simulated", "must be the boolean true")

    mission = _exact(root["mission"], ("task_id", "mission_revision", "steps"), "mission")
    _ident(mission["task_id"], "mission.task_id")
    _int(mission["mission_revision"], "mission.mission_revision", 1)
    steps = _id_list(mission["steps"], "mission.steps", allow_empty=False)

    progress = _exact(root["progress"], ("cursor", "completed", "committed_effect_ids"), "progress")
    cursor = _int(progress["cursor"], "progress.cursor")
    completed = _id_list(progress["completed"], "progress.completed", allow_empty=True)
    effect_ids = _id_list(progress["committed_effect_ids"], "progress.committed_effect_ids", allow_empty=True)
    if cursor > len(steps) or completed != steps[:cursor] or len(effect_ids) != cursor:
        _fail(Reason.PROGRESS_INCONSISTENT, "progress",
              "completed must equal the step prefix of length cursor and one effect id per step")

    owner = _exact(root["ownership"], ("state_owner", "epoch", "lease_expires_tick"), "ownership")
    _ident(owner["state_owner"], "ownership.state_owner")
    _int(owner["epoch"], "ownership.epoch", 1)
    _int(owner["lease_expires_tick"], "ownership.lease_expires_tick")

    ho = _exact(root["handoff"], ("handoff_id", "nonce", "sequence", "from_executor", "to_executor",
                                  "issued_tick", "expires_tick"), "handoff")
    _ident(ho["handoff_id"], "handoff.handoff_id")
    if not isinstance(ho["nonce"], str):
        _fail(Reason.WRONG_TYPE, "handoff.nonce", "expected string")
    if NONCE_RE.fullmatch(ho["nonce"]) is None:
        _fail(Reason.BAD_VALUE, "handoff.nonce", "must match [A-Za-z0-9_-]{8,64}")
    _int(ho["sequence"], "handoff.sequence", 1)
    _ident(ho["from_executor"], "handoff.from_executor")
    _ident(ho["to_executor"], "handoff.to_executor")
    issued = _int(ho["issued_tick"], "handoff.issued_tick")
    expires = _int(ho["expires_tick"], "handoff.expires_tick")
    if expires < issued:
        _fail(Reason.BAD_VALUE, "handoff.expires_tick", "must be >= issued_tick")

    req = _exact(root["requirements"], ("robot_class", "frame_id", "map_revision", "units",
                                        "capabilities", "sensors", "action"), "requirements")
    for key in ("robot_class", "frame_id", "map_revision"):
        _ident(req[key], f"requirements.{key}")
    _units(req["units"], "requirements.units")
    _id_list(req["capabilities"], "requirements.capabilities", allow_empty=True)
    if not isinstance(req["sensors"], list):
        _fail(Reason.WRONG_TYPE, "requirements.sensors", "expected list")
    names = []
    for i, sensor in enumerate(req["sensors"]):
        s = _exact(sensor, ("name", "type", "units"), f"requirements.sensors[{i}]")
        names.append(_ident(s["name"], f"requirements.sensors[{i}].name"))
        _ident(s["type"], f"requirements.sensors[{i}].type")
        _ident(s["units"], f"requirements.sensors[{i}].units")
    if len(set(names)) != len(names):
        _fail(Reason.BAD_VALUE, "requirements.sensors", "duplicate sensor name")
    act = _exact(req["action"], ("command", "space", "units"), "requirements.action")
    for key in ("command", "space", "units"):
        _ident(act[key], f"requirements.action.{key}")

    rb = _exact(root["rollback"], ("on_failure", "origin_executor", "resume_from"), "rollback")
    if rb["on_failure"] not in ROLLBACK_POLICIES:
        _fail(Reason.BAD_VALUE, "rollback.on_failure", f"one of {ROLLBACK_POLICIES}")
    _ident(rb["origin_executor"], "rollback.origin_executor")
    if rb["resume_from"] != "effect_ledger":
        _fail(Reason.BAD_VALUE, "rollback.resume_from", "only 'effect_ledger' is defined in v1")

    integ = _exact(root["integrity"], ("algorithm", "digest"), "integrity")
    if integ["algorithm"] != "sha256":
        _fail(Reason.BAD_VALUE, "integrity.algorithm", "only sha256 is defined in v1")
    if not isinstance(integ["digest"], str):
        _fail(Reason.WRONG_TYPE, "integrity.digest", "expected string")

    if ho["from_executor"] != owner["state_owner"] or rb["origin_executor"] != ho["from_executor"]:
        _fail(Reason.INCONSISTENT_BUNDLE, "handoff.from_executor",
              "must equal ownership.state_owner and rollback.origin_executor")
    return root


def _units(value: Any, where: str) -> None:
    u = _exact(value, UNIT_KEYS, where)
    for key in UNIT_KEYS:
        _ident(u[key], f"{where}.{key}")


def validate_digest(bundle: dict[str, Any]) -> None:
    digest = bundle["integrity"]["digest"]
    if HEX64_RE.fullmatch(digest) is None or digest != compute_digest(bundle):
        _fail(Reason.DIGEST_MISMATCH, "integrity.digest", "does not match canonical content")


# --------------------------------------------------------------------------- compatibility
def validate_profile(profile: Any) -> dict[str, Any]:
    """Shape check for a destination capability profile (a caller bug, not a bundle fault)."""
    p = _exact(profile, ("executor_id", "supported_schemas", "robot_class", "frame_id", "map_revision",
                         "units", "capabilities", "sensors", "actions"), "profile")
    _ident(p["executor_id"], "profile.executor_id")
    if (not isinstance(p["supported_schemas"], list) or not p["supported_schemas"]
            or not all(isinstance(s, str) for s in p["supported_schemas"])):
        _fail(Reason.WRONG_TYPE, "profile.supported_schemas", "expected non-empty list of strings")
    for key in ("robot_class", "frame_id", "map_revision"):
        _ident(p[key], f"profile.{key}")
    _units(p["units"], "profile.units")
    _id_list(p["capabilities"], "profile.capabilities", allow_empty=True)
    for list_key, keys in (("sensors", ("name", "type", "units")), ("actions", ("command", "space", "units"))):
        if not isinstance(p[list_key], list):
            _fail(Reason.WRONG_TYPE, f"profile.{list_key}", "expected list")
        for i, item in enumerate(p[list_key]):
            entry = _exact(item, keys, f"profile.{list_key}[{i}]")
            for k in keys:
                _ident(entry[k], f"profile.{list_key}[{i}].{k}")
    return p


def compatibility_violations(bundle: dict[str, Any], profile: dict[str, Any]) -> list[tuple[str, str]]:
    """All (reason, detail) pairs by which ``profile`` cannot satisfy the bundle's requirements.

    Empty list means compatible. Order is fixed so the first entry is deterministic.
    """
    req = bundle["requirements"]
    out: list[tuple[str, str]] = []
    if bundle["schema"] not in profile["supported_schemas"]:
        out.append((Reason.SCHEMA_NOT_SUPPORTED, f"destination supports {profile['supported_schemas']}"))
    if req["robot_class"] != profile["robot_class"]:
        out.append((Reason.ROBOT_CLASS_MISMATCH, f"{req['robot_class']} != {profile['robot_class']}"))
    if req["frame_id"] != profile["frame_id"]:
        out.append((Reason.FRAME_MISMATCH, f"{req['frame_id']} != {profile['frame_id']}"))
    if req["map_revision"] != profile["map_revision"]:
        out.append((Reason.MAP_REVISION_MISMATCH, f"{req['map_revision']} != {profile['map_revision']}"))
    for key in UNIT_KEYS:
        if req["units"][key] != profile["units"][key]:
            out.append((Reason.UNITS_MISMATCH, f"{key}: {req['units'][key]} != {profile['units'][key]}"))
    for cap in req["capabilities"]:
        if cap not in profile["capabilities"]:
            out.append((Reason.MISSING_CAPABILITY, cap))
    have = {s["name"]: s for s in profile["sensors"]}
    for sensor in req["sensors"]:
        got = have.get(sensor["name"])
        if got is None:
            out.append((Reason.MISSING_SENSOR, sensor["name"]))
            continue
        if got["type"] != sensor["type"]:
            out.append((Reason.SENSOR_TYPE_MISMATCH, f"{sensor['name']}: {sensor['type']} != {got['type']}"))
        if got["units"] != sensor["units"]:
            out.append((Reason.SENSOR_UNITS_MISMATCH, f"{sensor['name']}: {sensor['units']} != {got['units']}"))
    want = req["action"]
    same_cmd = [a for a in profile["actions"] if a["command"] == want["command"]]
    if not same_cmd:
        out.append((Reason.ACTION_COMMAND_UNSUPPORTED, want["command"]))
    else:
        same_space = [a for a in same_cmd if a["space"] == want["space"]]
        if not same_space:
            out.append((Reason.ACTION_SPACE_MISMATCH, f"{want['space']} not offered for {want['command']}"))
        elif not any(a["units"] == want["units"] for a in same_space):
            out.append((Reason.ACTION_UNITS_MISMATCH, f"{want['units']} not offered for {want['space']}"))
    return out


# --------------------------------------------------------------------------- commit-time validation
@dataclass
class CommitContext:
    """What the coordinator knows at the moment it is asked to commit a handoff."""

    now_tick: int
    owner: str | None
    epoch: int
    last_sequence: int
    seen_nonces: frozenset[str]
    ledger_effect_ids: tuple[str, ...]
    destination: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "CommitContext":
        coord = data["coordinator"]
        return cls(now_tick=data["now_tick"], owner=coord["owner"], epoch=coord["epoch"],
                   last_sequence=coord["last_sequence"], seen_nonces=frozenset(coord["seen_nonces"]),
                   ledger_effect_ids=tuple(coord["ledger_effect_ids"]),
                   destination=validate_profile(data["destination_profile"]))


def validate_for_commit(bundle: Any, ctx: CommitContext) -> dict[str, Any]:
    """Run every check in the documented order; raise :class:`Rejection` on the first failure.

    Returns the validated bundle. This function never mutates ``ctx``.
    """
    doc = validate_structure(bundle)
    validate_digest(doc)
    ho, own, prog = doc["handoff"], doc["ownership"], doc["progress"]
    if prog["cursor"] >= len(doc["mission"]["steps"]):
        _fail(Reason.MISSION_COMPLETE, "progress.cursor", "no remaining mission work")
    if ctx.now_tick < ho["issued_tick"]:
        _fail(Reason.BUNDLE_FROM_FUTURE, "handoff.issued_tick", f"{ho['issued_tick']} > now {ctx.now_tick}")
    if ctx.now_tick > ho["expires_tick"]:
        _fail(Reason.BUNDLE_EXPIRED, "handoff.expires_tick", f"{ho['expires_tick']} < now {ctx.now_tick}")
    if ho["to_executor"] == ho["from_executor"]:
        _fail(Reason.SAME_EXECUTOR, "handoff.to_executor", "source and destination are identical")
    if ho["to_executor"] != ctx.destination["executor_id"]:
        _fail(Reason.WRONG_DESTINATION, "handoff.to_executor", "bundle is addressed to a different executor")
    if ho["nonce"] in ctx.seen_nonces:
        _fail(Reason.REPLAYED_NONCE, "handoff.nonce", "nonce already consumed")
    if ho["sequence"] <= ctx.last_sequence:
        _fail(Reason.STALE_SEQUENCE, "handoff.sequence", f"{ho['sequence']} <= last accepted {ctx.last_sequence}")
    if own["epoch"] != ctx.epoch:
        _fail(Reason.STALE_EPOCH, "ownership.epoch", f"bundle {own['epoch']} != current {ctx.epoch}")
    if own["state_owner"] != ctx.owner:
        _fail(Reason.WRONG_STATE_OWNER, "ownership.state_owner", "not the current state owner")
    if tuple(prog["committed_effect_ids"]) != ctx.ledger_effect_ids:
        _fail(Reason.STALE_CHECKPOINT, "progress", "does not match the authoritative effect ledger")
    violations = compatibility_violations(doc, ctx.destination)
    if violations:
        reason, detail = violations[0]
        raise Rejection(reason, "requirements", detail + (f" (+{len(violations) - 1} more)" if len(violations) > 1 else ""))
    return doc
