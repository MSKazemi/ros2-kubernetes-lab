"""Deterministic, CPU-only SIMULATION of edge/cloud inference placement policies.

SIMULATION ONLY. Every number this module produces is a SIMULATED model output
derived from the parameters in a JSON config and a fixed seed. Nothing here is a
measurement of a robot, a network, a ROS 2 / DDS stack, a Kubernetes cluster or a
cloud service, and nothing is ever sent to an actuator: decisions end in a
NonActuatingSink that only records "would_apply" or "rejected".

Standard library only. Time is integer logical milliseconds.

Model summary
-------------
* A perception->action request stream: request i is captured at ``i * interval_ms``
  and must be answered by its own absolute deadline.
* Two executors: LOCAL (single FIFO worker, always on the robot) and REMOTE (a
  cloud/edge-server model reached over a network with outage windows, loss,
  jitter, duplicated deliveries and spurious responses).
* REMOTE eligibility: the remote must have at least ``model_memory_mb`` free at the
  moment the request arrives; otherwise it answers with an explicit REJECT.
  The remote may also reject at random (``reject_probability``).
* Policies: always_local, always_remote, deadline_aware, hedged_fallback.
* The sink rejects (with a logged reason) unknown IDs, duplicate response IDs,
  responses from an ineligible source, responses after the deadline and responses
  for a superseded request.

All policies see the same per-request random draws (common random numbers), so
differences between policies come from the policy, not from different luck.
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import random
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
LABEL = "SIMULATION"
BANNER = (
    "SIMULATION: all values are SIMULATED model outputs computed from the config "
    "and seed. They are not measurements of any robot, network or cloud service. "
    "Nothing is actuated."
)

POLICY_NAMES = ("always_local", "always_remote", "deadline_aware", "hedged_fallback")

# Sink rejection reasons, in the order the sink evaluates them.
REJECT_REASONS = (
    "unknown_request_id",
    "duplicate_response_id",
    "ineligible_source",
    "late_after_deadline",
    "superseded_request",
)
STALE_REASONS = ("late_after_deadline", "superseded_request")

MISS_CAUSES = (
    "no_viable_executor",
    "ineligible_source",
    "remote_rejected",
    "late_response",
    "superseded_response",
    "no_response",
)


class ConfigError(ValueError):
    """Raised for any invalid simulation configuration."""


# --------------------------------------------------------------------------- #
# Configuration validation
# --------------------------------------------------------------------------- #

_MISSING = object()


def _is_number(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _num(
    section: str,
    d: dict,
    key: str,
    *,
    minimum: float | None = None,
    exclusive_min: bool = False,
    maximum: float | None = None,
    integer: bool = False,
    default: Any = _MISSING,
) -> Any:
    if key not in d:
        if default is _MISSING:
            raise ConfigError(f"{section}.{key} is required")
        return default
    v = d[key]
    if not _is_number(v):
        raise ConfigError(f"{section}.{key} must be a finite number, got {v!r}")
    if integer and (isinstance(v, float) and not v.is_integer()):
        raise ConfigError(f"{section}.{key} must be an integer, got {v!r}")
    if integer:
        v = int(v)
    if minimum is not None:
        if exclusive_min and not v > minimum:
            raise ConfigError(f"{section}.{key} must be > {minimum}, got {v!r}")
        if not exclusive_min and not v >= minimum:
            raise ConfigError(f"{section}.{key} must be >= {minimum}, got {v!r}")
    if maximum is not None and not v <= maximum:
        raise ConfigError(f"{section}.{key} must be <= {maximum}, got {v!r}")
    return v


def _prob(section: str, d: dict, key: str, default: Any = 0.0) -> float:
    return float(_num(section, d, key, minimum=0.0, maximum=1.0, default=default))


def _section(raw: dict, name: str, required: bool = True) -> dict:
    if name not in raw:
        if required:
            raise ConfigError(f"missing section '{name}'")
        return {}
    v = raw[name]
    if not isinstance(v, dict):
        raise ConfigError(f"section '{name}' must be an object")
    return v


def _only_keys(section: str, d: dict, allowed: set[str]) -> None:
    extra = sorted(set(d) - allowed)
    if extra:
        raise ConfigError(f"unknown key(s) in {section}: {', '.join(extra)}")


def validate_config(raw: Any) -> dict:
    """Validate ``raw`` and return a normalised, fully defaulted copy.

    Unknown keys are rejected so typos cannot silently change a run.
    """
    if not isinstance(raw, dict):
        raise ConfigError("config must be a JSON object")
    _only_keys(
        "config",
        raw,
        {"schema_version", "description", "seed", "stream", "local", "remote",
         "network", "predictor", "hedge", "policies"},
    )
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise ConfigError(
            f"schema_version must be {SCHEMA_VERSION}, got {raw.get('schema_version')!r}"
        )
    desc = raw.get("description", "")
    if not isinstance(desc, str):
        raise ConfigError("description must be a string")
    seed = raw.get("seed")
    if not _is_number(seed) or isinstance(seed, float):
        raise ConfigError(f"seed must be an integer, got {seed!r}")

    # stream ---------------------------------------------------------------
    s = _section(raw, "stream")
    _only_keys("stream", s, {"num_requests", "interval_ms", "deadline_ms", "local_only_probability"})
    stream = {
        "num_requests": _num("stream", s, "num_requests", minimum=1, maximum=200_000, integer=True),
        "interval_ms": _num("stream", s, "interval_ms", minimum=0, exclusive_min=True, integer=True),
        "local_only_probability": _prob("stream", s, "local_only_probability"),
    }
    dl = s.get("deadline_ms", _MISSING)
    if dl is _MISSING:
        raise ConfigError("stream.deadline_ms is required")
    if isinstance(dl, dict):
        _only_keys("stream.deadline_ms", dl, {"min", "max"})
        dmin = _num("stream.deadline_ms", dl, "min", minimum=0, exclusive_min=True, integer=True)
        dmax = _num("stream.deadline_ms", dl, "max", minimum=0, exclusive_min=True, integer=True)
        if dmax < dmin:
            raise ConfigError("stream.deadline_ms.max must be >= min")
    else:
        dmin = dmax = _num("stream", s, "deadline_ms", minimum=0, exclusive_min=True, integer=True)
    stream["deadline_min_ms"], stream["deadline_max_ms"] = dmin, dmax

    # local ----------------------------------------------------------------
    l = _section(raw, "local")
    _only_keys("local", l, {"memory_mb", "model_memory_mb", "compute_base_ms", "compute_jitter_ms"})
    local = {
        "memory_mb": _num("local", l, "memory_mb", minimum=0, integer=True),
        "model_memory_mb": _num("local", l, "model_memory_mb", minimum=0, integer=True),
        "compute_base_ms": _num("local", l, "compute_base_ms", minimum=0, integer=True),
        "compute_jitter_ms": _num("local", l, "compute_jitter_ms", minimum=0, integer=True, default=0),
    }

    # remote ---------------------------------------------------------------
    r = _section(raw, "remote")
    _only_keys(
        "remote", r,
        {"model_memory_mb", "memory_mb", "memory_schedule", "compute_base_ms",
         "compute_jitter_ms", "reject_probability", "advert_lag_ms"},
    )
    if ("memory_mb" in r) == ("memory_schedule" in r):
        raise ConfigError("remote needs exactly one of memory_mb or memory_schedule")
    if "memory_mb" in r:
        schedule = [(0, _num("remote", r, "memory_mb", minimum=0, integer=True))]
    else:
        ms = r["memory_schedule"]
        if not isinstance(ms, list) or not ms:
            raise ConfigError("remote.memory_schedule must be a non-empty list")
        schedule = []
        for i, item in enumerate(ms):
            if not isinstance(item, dict):
                raise ConfigError(f"remote.memory_schedule[{i}] must be an object")
            _only_keys(f"remote.memory_schedule[{i}]", item, {"from_ms", "memory_mb"})
            schedule.append((
                _num(f"remote.memory_schedule[{i}]", item, "from_ms", minimum=0, integer=True),
                _num(f"remote.memory_schedule[{i}]", item, "memory_mb", minimum=0, integer=True),
            ))
        if schedule[0][0] != 0:
            raise ConfigError("remote.memory_schedule[0].from_ms must be 0")
        if any(b[0] <= a[0] for a, b in zip(schedule, schedule[1:])):
            raise ConfigError("remote.memory_schedule from_ms must be strictly increasing")
    remote = {
        "model_memory_mb": _num("remote", r, "model_memory_mb", minimum=0, integer=True),
        "memory_schedule": schedule,
        "compute_base_ms": _num("remote", r, "compute_base_ms", minimum=0, integer=True),
        "compute_jitter_ms": _num("remote", r, "compute_jitter_ms", minimum=0, integer=True, default=0),
        "reject_probability": _prob("remote", r, "reject_probability"),
        "advert_lag_ms": _num("remote", r, "advert_lag_ms", minimum=0, integer=True, default=0),
    }

    # network --------------------------------------------------------------
    n = _section(raw, "network")
    _only_keys(
        "network", n,
        {"one_way_base_ms", "one_way_jitter_ms", "loss_probability", "duplicate_probability",
         "duplicate_extra_delay_max_ms", "spurious_response_probability", "outages",
         "recovery_ms", "recovery_delay_factor"},
    )
    outages_raw = n.get("outages", [])
    if not isinstance(outages_raw, list):
        raise ConfigError("network.outages must be a list")
    outages: list[tuple[int, int]] = []
    for i, o in enumerate(outages_raw):
        if not isinstance(o, dict):
            raise ConfigError(f"network.outages[{i}] must be an object")
        _only_keys(f"network.outages[{i}]", o, {"start_ms", "end_ms"})
        st = _num(f"network.outages[{i}]", o, "start_ms", minimum=0, integer=True)
        en = _num(f"network.outages[{i}]", o, "end_ms", minimum=0, integer=True)
        if en <= st:
            raise ConfigError(f"network.outages[{i}]: end_ms must be > start_ms")
        outages.append((st, en))
    outages.sort()
    if any(b[0] < a[1] for a, b in zip(outages, outages[1:])):
        raise ConfigError("network.outages must not overlap")
    network = {
        "one_way_base_ms": _num("network", n, "one_way_base_ms", minimum=0, integer=True),
        "one_way_jitter_ms": _num("network", n, "one_way_jitter_ms", minimum=0, integer=True, default=0),
        "loss_probability": _prob("network", n, "loss_probability"),
        "duplicate_probability": _prob("network", n, "duplicate_probability"),
        "duplicate_extra_delay_max_ms": _num(
            "network", n, "duplicate_extra_delay_max_ms", minimum=1, integer=True, default=50),
        "spurious_response_probability": _prob("network", n, "spurious_response_probability"),
        "outages": outages,
        "recovery_ms": _num("network", n, "recovery_ms", minimum=0, integer=True, default=0),
        "recovery_delay_factor": float(_num(
            "network", n, "recovery_delay_factor", minimum=1.0, default=1.0)),
    }

    # predictor / hedge ----------------------------------------------------
    p = _section(raw, "predictor", required=False)
    _only_keys("predictor", p, {"prior_rtt_ms", "alpha", "margin_ms", "probe_interval_ms"})
    predictor = {
        "prior_rtt_ms": float(_num("predictor", p, "prior_rtt_ms", minimum=0, default=100)),
        "alpha": float(_num("predictor", p, "alpha", minimum=0.0, exclusive_min=True, maximum=1.0, default=0.3)),
        "margin_ms": float(_num("predictor", p, "margin_ms", minimum=0, default=10)),
        "probe_interval_ms": _num("predictor", p, "probe_interval_ms", minimum=0,
                                  exclusive_min=True, integer=True, default=1000),
    }
    h = _section(raw, "hedge", required=False)
    _only_keys("hedge", h, {"delay_ms"})
    delay = h.get("delay_ms", None)
    if delay is not None:
        delay = _num("hedge", h, "delay_ms", minimum=0, integer=True)
    hedge = {"delay_ms": delay}

    # policies -------------------------------------------------------------
    pol = raw.get("policies", list(POLICY_NAMES))
    if not isinstance(pol, list) or not pol:
        raise ConfigError("policies must be a non-empty list")
    for name in pol:
        if name not in POLICY_NAMES:
            raise ConfigError(f"unknown policy {name!r}; known: {', '.join(POLICY_NAMES)}")
    if len(set(pol)) != len(pol):
        raise ConfigError("policies must not contain duplicates")

    return {
        "schema_version": SCHEMA_VERSION,
        "description": desc,
        "seed": int(seed),
        "stream": stream,
        "local": local,
        "remote": remote,
        "network": network,
        "predictor": predictor,
        "hedge": hedge,
        "policies": list(pol),
    }


def load_config(path: str | Path) -> Any:
    """Read the JSON file only; ``run_all`` / ``validate_config`` validate it."""
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"cannot read config {path}: {exc}") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"config {path} is not valid JSON: {exc}") from exc
    return raw


def config_digest(cfg: dict) -> str:
    return hashlib.sha256(json.dumps(cfg, sort_keys=True).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# Domain objects
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Request:
    index: int
    request_id: str
    capture_ms: int
    deadline_ms: int          # relative budget
    deadline_abs_ms: int      # capture + budget; a response AT this time is on time
    local_only: bool


@dataclass(frozen=True)
class Response:
    uid: str                  # identity of one logical response; network copies share it
    request_id: str
    source: str               # "local" | "remote"
    kind: str                 # "action" | "reject"
    reason: str = ""
    sent_ms: int = 0          # when the originating request left (for RTT)
    fallback: bool = False


@dataclass
class Draws:
    """Policy-independent random draws for one request (common random numbers)."""
    deadline_ms: int
    local_only: bool
    up_jitter: int
    down_jitter: int
    remote_jitter: int
    local_jitter: int
    up_lost: bool
    down_lost: bool
    reject: bool
    duplicate: bool
    dup_extra: int


def _rng(seed: int, tag: str, i: int) -> random.Random:
    # str seeds are hashed with SHA-512 by CPython, so this is stable across runs.
    return random.Random(f"{seed}:{tag}:{i}")


def build_requests(cfg: dict) -> tuple[list[Request], list[Draws]]:
    st, ln, rm, nw = cfg["stream"], cfg["local"], cfg["remote"], cfg["network"]
    requests: list[Request] = []
    draws: list[Draws] = []
    for i in range(st["num_requests"]):
        g = _rng(cfg["seed"], "req", i)
        budget = g.randint(st["deadline_min_ms"], st["deadline_max_ms"])
        local_only = g.random() < st["local_only_probability"]
        d = Draws(
            deadline_ms=budget,
            local_only=local_only,
            up_jitter=g.randint(0, nw["one_way_jitter_ms"]),
            down_jitter=g.randint(0, nw["one_way_jitter_ms"]),
            remote_jitter=g.randint(0, rm["compute_jitter_ms"]),
            local_jitter=g.randint(0, ln["compute_jitter_ms"]),
            up_lost=g.random() < nw["loss_probability"],
            down_lost=g.random() < nw["loss_probability"],
            reject=g.random() < rm["reject_probability"],
            duplicate=g.random() < nw["duplicate_probability"],
            dup_extra=g.randint(1, nw["duplicate_extra_delay_max_ms"]),
        )
        cap = i * st["interval_ms"]
        requests.append(Request(i, f"req-{i:06d}", cap, budget, cap + budget, local_only))
        draws.append(d)
    return requests, draws


# --------------------------------------------------------------------------- #
# Non-actuating sink
# --------------------------------------------------------------------------- #

class NonActuatingSink:
    """SIMULATION sink: records "would_apply" / "rejected" and nothing else.

    It has no output channel of any kind; ``actuated`` is permanently False and
    every record carries ``"actuated": false``.
    """

    actuated = False

    def __init__(self, requests: list[Request]) -> None:
        self._by_id = {r.request_id: r for r in requests}
        self.applied: dict[str, int] = {}          # request_id -> apply time
        self.applied_source: dict[str, str] = {}
        self.applied_fallback: dict[str, bool] = {}
        self._seen_uids: set[str] = set()
        self._latest_applied_index = -1
        self.records: list[dict] = []

    def submit(self, resp: Response, now_ms: int) -> dict:
        """Judge one action-bearing response. Check order is part of the contract:
        unknown id, duplicate, ineligible source, late, superseded."""
        req = self._by_id.get(resp.request_id)
        reason = ""
        if req is None:
            reason = "unknown_request_id"
        elif resp.uid in self._seen_uids or resp.request_id in self.applied:
            reason = "duplicate_response_id"
        elif req.local_only and resp.source != "local":
            reason = "ineligible_source"
        elif now_ms > req.deadline_abs_ms:
            reason = "late_after_deadline"
        elif req.index < self._latest_applied_index:
            reason = "superseded_request"
        self._seen_uids.add(resp.uid)
        rec: dict[str, Any] = {
            "label": LABEL,
            "kind": "sink",
            "t_ms": now_ms,
            "request_id": resp.request_id,
            "source": resp.source,
            "fallback": resp.fallback,
            "actuated": False,
        }
        if reason:
            rec["decision"] = "rejected"
            rec["reason"] = reason
        else:
            rec["decision"] = "would_apply"
            rec["latency_ms"] = now_ms - req.capture_ms
            self.applied[resp.request_id] = now_ms
            self.applied_source[resp.request_id] = resp.source
            self.applied_fallback[resp.request_id] = resp.fallback
            self._latest_applied_index = max(self._latest_applied_index, req.index)
        self.records.append(rec)
        return rec


# --------------------------------------------------------------------------- #
# Predictor used by the deadline-aware family
# --------------------------------------------------------------------------- #

class RttPredictor:
    """EWMA of OBSERVED remote round trips (send -> response, incl. processing).

    Only information the policy could have at decision time is used: responses
    that have already arrived. A timeout is a censored observation, so it raises
    the estimate to at least the missed deadline. Because that estimate then
    blocks the remote, a probe is allowed every ``probe_interval_ms`` so the
    policy can notice recovery after an outage.
    """

    def __init__(self, cfg: dict) -> None:
        p = cfg["predictor"]
        self.ewma = p["prior_rtt_ms"]
        self.alpha = p["alpha"]
        self.margin = p["margin_ms"]
        self.probe_interval = p["probe_interval_ms"]
        self.last_remote_send_ms: int | None = None
        self.blocked_until_ms = -1       # set by explicit ineligibility rejects

    def predicted(self) -> float:
        return self.ewma

    def fits(self, budget_ms: int) -> bool:
        return self.ewma + self.margin <= budget_ms

    def probe_due(self, now_ms: int) -> bool:
        return (self.last_remote_send_ms is None
                or now_ms - self.last_remote_send_ms >= self.probe_interval)

    def observe_rtt(self, rtt_ms: int) -> None:
        self.ewma += self.alpha * (rtt_ms - self.ewma)

    def observe_timeout(self, budget_ms: int) -> None:
        self.ewma = max(self.ewma, float(budget_ms))

    def observe_ineligible(self, now_ms: int) -> None:
        self.blocked_until_ms = now_ms + self.probe_interval


# --------------------------------------------------------------------------- #
# Simulation core
# --------------------------------------------------------------------------- #

# Event priorities at equal time: responses first, so an answer arriving exactly
# at the deadline is processed before the timeout/hedge that would otherwise fire.
_P_RESPONSE, _P_TIMER, _P_CAPTURE = 0, 1, 2


@dataclass(order=True)
class _Event:
    t: int
    prio: int
    n: int
    kind: str = field(compare=False)
    payload: Any = field(compare=False, default=None)


class Simulation:
    """One policy run over the configured request stream."""

    def __init__(self, cfg: dict, policy_name: str) -> None:
        if policy_name not in POLICY_NAMES:
            raise ConfigError(f"unknown policy {policy_name!r}")
        self.cfg = cfg
        self.policy_name = policy_name
        self.requests, self.draws = build_requests(cfg)
        self.by_id = {r.request_id: r for r in self.requests}
        self.sink = NonActuatingSink(self.requests)
        self.log: list[dict] = []
        self._heap: list[_Event] = []
        self._n = 0
        self.local_free_at = 0
        self.local_eligible = cfg["local"]["memory_mb"] >= cfg["local"]["model_memory_mb"]
        self.local_worst_ms = cfg["local"]["compute_base_ms"] + cfg["local"]["compute_jitter_ms"]
        self.predictor = RttPredictor(cfg)
        # counters / per-request bookkeeping
        self.routed_local = 0
        self.routed_remote = 0
        self.fallback_launched = 0
        self.remote_timeouts = 0
        self.remote_rejects: dict[str, int] = {}
        self.remote_answered: set[int] = set()
        self.fallback_for: set[int] = set()
        self.cause_flags: dict[int, set[str]] = {}
        self._uid_counter = 0

    # ---- scheduling ------------------------------------------------------
    def _push(self, t: int, prio: int, kind: str, payload: Any = None) -> None:
        self._n += 1
        heapq.heappush(self._heap, _Event(t, prio, self._n, kind, payload))

    def _record(self, t: int, kind: str, **fields: Any) -> None:
        self.log.append({"label": LABEL, "kind": kind, "t_ms": t, **fields})

    def _flag(self, req: Request, cause: str) -> None:
        self.cause_flags.setdefault(req.index, set()).add(cause)

    # ---- network model ---------------------------------------------------
    def in_outage(self, t: int) -> bool:
        return any(a <= t < b for a, b in self.cfg["network"]["outages"])

    def in_recovery(self, t: int) -> bool:
        nw = self.cfg["network"]
        return any(b <= t < b + nw["recovery_ms"] for _, b in nw["outages"])

    def in_disruption(self, t: int) -> bool:
        return self.in_outage(t) or self.in_recovery(t)

    def _one_way(self, t_send: int, jitter: int) -> int:
        nw = self.cfg["network"]
        d = nw["one_way_base_ms"] + jitter
        if self.in_recovery(t_send):
            d *= nw["recovery_delay_factor"]
        return int(round(d))

    def remote_memory_at(self, t: int) -> int:
        mem = 0
        for from_ms, mb in self.cfg["remote"]["memory_schedule"]:
            if from_ms <= t:
                mem = mb
        return mem

    def remote_eligible_known(self, now: int) -> bool:
        """Eligibility as the policy knows it: a capability advertisement that lags
        the true remote state by ``advert_lag_ms``."""
        rm = self.cfg["remote"]
        return self.remote_memory_at(max(0, now - rm["advert_lag_ms"])) >= rm["model_memory_mb"]

    # ---- executors -------------------------------------------------------
    def launch_local(self, req: Request, now: int, *, fallback: bool = False) -> None:
        ln = self.cfg["local"]
        start = max(now, self.local_free_at)
        finish = start + ln["compute_base_ms"] + self.draws[req.index].local_jitter
        self.local_free_at = finish
        self._uid_counter += 1
        resp = Response(f"{req.request_id}:local:{self._uid_counter}", req.request_id,
                        "local", "action", sent_ms=now, fallback=fallback)
        self._record(now, "local_launch", request_id=req.request_id, fallback=fallback,
                     finish_ms=finish)
        self._push(finish, _P_RESPONSE, "response", resp)

    def launch_remote(self, req: Request, now: int) -> None:
        d, rm, nw = self.draws[req.index], self.cfg["remote"], self.cfg["network"]
        self.predictor.last_remote_send_ms = now
        self._uid_counter += 1
        uid = f"{req.request_id}:remote:{self._uid_counter}"
        self._push(req.deadline_abs_ms, _P_TIMER, "timeout", req)
        if d.up_lost or self.in_outage(now):
            self._record(now, "remote_request_lost", request_id=req.request_id,
                         cause="outage" if self.in_outage(now) else "loss")
            return
        t_arrive = now + self._one_way(now, d.up_jitter)
        if self.remote_memory_at(t_arrive) < rm["model_memory_mb"]:
            kind, reason, t_reply = "reject", "ineligible_memory", t_arrive
        elif d.reject:
            kind, reason, t_reply = "reject", "overloaded", t_arrive
        else:
            kind, reason = "action", ""
            t_reply = t_arrive + rm["compute_base_ms"] + d.remote_jitter
        if d.down_lost or self.in_outage(t_reply):
            self._record(t_reply, "remote_reply_lost", request_id=req.request_id,
                         cause="outage" if self.in_outage(t_reply) else "loss")
            return
        t_back = t_reply + self._one_way(t_reply, d.down_jitter)
        resp = Response(uid, req.request_id, "remote", kind, reason, sent_ms=now)
        self._push(t_back, _P_RESPONSE, "response", resp)
        if kind == "action" and d.duplicate:
            self._push(t_back + d.dup_extra, _P_RESPONSE, "response", resp)

    # ---- main loop -------------------------------------------------------
    def run(self) -> None:
        self.policy = _make_policy(self.policy_name, self)
        for req in self.requests:
            self._push(req.capture_ms, _P_CAPTURE, "capture", req)
        self._schedule_spurious()
        while self._heap:
            ev = heapq.heappop(self._heap)
            if ev.kind == "capture":
                self.policy.on_capture(ev.payload, ev.t)
            elif ev.kind == "response":
                self._on_response(ev.payload, ev.t)
            elif ev.kind == "timeout":
                self._on_timeout(ev.payload, ev.t)
            elif ev.kind == "hedge":
                self.policy.on_hedge_timer(ev.payload, ev.t)

    def _schedule_spurious(self) -> None:
        nw, st = self.cfg["network"], self.cfg["stream"]
        p = nw["spurious_response_probability"]
        if p <= 0:
            return
        for i in range(st["num_requests"]):
            g = _rng(self.cfg["seed"], "spurious", i)
            if g.random() < p:
                t = i * st["interval_ms"] + g.randint(0, 3 * st["interval_ms"])
                resp = Response(f"ghost-{i:06d}:uid", f"ghost-{i:06d}", "remote", "action")
                self._push(t, _P_RESPONSE, "response", resp)

    def _on_timeout(self, req: Request, now: int) -> None:
        if req.index in self.remote_answered:
            return
        self.remote_timeouts += 1
        self._record(now, "remote_timeout", request_id=req.request_id)
        self.policy.on_remote_timeout(req, now)

    def _on_response(self, resp: Response, now: int) -> None:
        req = self.by_id.get(resp.request_id)
        if resp.kind == "reject":
            if req is None:
                return
            self.remote_answered.add(req.index)
            self.remote_rejects[resp.reason] = self.remote_rejects.get(resp.reason, 0) + 1
            self._flag(req, "remote_rejected")
            self._record(now, "remote_reject", request_id=resp.request_id, reason=resp.reason)
            self.policy.on_remote_reject(req, resp.reason, now)
            return
        if req is not None and resp.source == "remote":
            self.remote_answered.add(req.index)
            self.policy.on_remote_action(req, now - resp.sent_ms, now)
        rec = self.sink.submit(resp, now)
        if req is not None and rec["decision"] == "rejected":
            self._flag(req, {
                "late_after_deadline": "late_response",
                "superseded_request": "superseded_response",
                "ineligible_source": "ineligible_source",
            }.get(rec["reason"], "no_response"))
        self.log.append(rec)

    def mark_no_viable_executor(self, req: Request, now: int) -> None:
        self._flag(req, "no_viable_executor")
        self._record(now, "no_viable_executor", request_id=req.request_id)

    def note_route(self, req: Request, now: int, target: str, why: str) -> None:
        if target == "local":
            self.routed_local += 1
        else:
            self.routed_remote += 1
        self._record(now, "route", request_id=req.request_id, target=target, why=why,
                     predicted_rtt_ms=round(self.predictor.predicted(), 3))


# --------------------------------------------------------------------------- #
# Policies
# --------------------------------------------------------------------------- #

class _Policy:
    def __init__(self, sim: Simulation) -> None:
        self.sim = sim

    def on_capture(self, req: Request, now: int) -> None: ...
    def on_remote_action(self, req: Request, rtt_ms: int, now: int) -> None: ...
    def on_remote_timeout(self, req: Request, now: int) -> None: ...
    def on_remote_reject(self, req: Request, reason: str, now: int) -> None: ...
    def on_hedge_timer(self, req: Request, now: int) -> None: ...


class AlwaysLocal(_Policy):
    def on_capture(self, req: Request, now: int) -> None:
        if not self.sim.local_eligible:
            self.sim.mark_no_viable_executor(req, now)
            return
        self.sim.note_route(req, now, "local", "policy=always_local")
        self.sim.launch_local(req, now)


class AlwaysRemote(_Policy):
    """Naive offload: ignores deadlines, eligibility knowledge and local_only."""

    def on_capture(self, req: Request, now: int) -> None:
        self.sim.note_route(req, now, "remote", "policy=always_remote")
        self.sim.launch_remote(req, now)


class DeadlineAware(_Policy):
    """Remote only if predicted RTT + margin fits the request budget AND the remote
    is (as far as the policy knows) eligible. Single path: no fallback launches."""

    def choose(self, req: Request, now: int) -> tuple[str | None, str]:
        sim, pred = self.sim, self.sim.predictor
        remote_ok = (not req.local_only
                     and sim.remote_eligible_known(now)
                     and now >= pred.blocked_until_ms)
        if remote_ok and pred.fits(req.deadline_ms):
            return "remote", "predicted_fit"
        if remote_ok and pred.probe_due(now):
            return "remote", "probe"
        if sim.local_eligible:
            if req.local_only:
                why = "local_only"
            elif not remote_ok:
                why = "remote_ineligible_or_blocked"
            else:
                why = "predicted_miss"
            return "local", why
        if remote_ok:
            return "remote", "local_ineligible_best_effort"
        return None, "no_viable_executor"

    def on_capture(self, req: Request, now: int) -> None:
        target, why = self.choose(req, now)
        if target is None:
            self.sim.mark_no_viable_executor(req, now)
            return
        self.sim.note_route(req, now, target, why)
        if target == "local":
            self.sim.launch_local(req, now)
        else:
            self.sim.launch_remote(req, now)
            self.after_remote_launch(req, now)

    def after_remote_launch(self, req: Request, now: int) -> None:
        pass

    def on_remote_action(self, req: Request, rtt_ms: int, now: int) -> None:
        self.sim.predictor.observe_rtt(rtt_ms)

    def on_remote_timeout(self, req: Request, now: int) -> None:
        self.sim.predictor.observe_timeout(req.deadline_ms)

    def on_remote_reject(self, req: Request, reason: str, now: int) -> None:
        if reason == "ineligible_memory":
            self.sim.predictor.observe_ineligible(now)


class HedgedFallback(DeadlineAware):
    """Deadline-aware routing plus a local fallback: launched on an explicit remote
    reject, or by a hedge timer if no remote answer has arrived. A later duplicate
    from the slower path is rejected by the sink (duplicate_response_id)."""

    def _hedge_time(self, req: Request) -> int:
        """Hedge when the remote answer is overdue, but never later than the latest
        local start that still fits the budget at worst-case local compute time.
        ``hedge.delay_ms`` null means: predicted RTT + margin at launch time."""
        latest_start = req.deadline_abs_ms - self.sim.local_worst_ms
        delay = self.sim.cfg["hedge"]["delay_ms"]
        if delay is None:
            pred = self.sim.predictor
            delay = int(math.ceil(pred.predicted() + pred.margin))
        return max(req.capture_ms, min(req.capture_ms + delay, latest_start))

    def after_remote_launch(self, req: Request, now: int) -> None:
        if self.sim.local_eligible:
            self.sim._push(self._hedge_time(req), _P_TIMER, "hedge", req)

    def _launch_fallback(self, req: Request, now: int) -> None:
        sim = self.sim
        if (not sim.local_eligible
                or req.index in sim.fallback_for
                or req.request_id in sim.sink.applied
                or now + sim.cfg["local"]["compute_base_ms"] > req.deadline_abs_ms):
            return
        sim.fallback_for.add(req.index)
        sim.fallback_launched += 1
        sim.launch_local(req, now, fallback=True)

    def on_hedge_timer(self, req: Request, now: int) -> None:
        self._launch_fallback(req, now)

    def on_remote_reject(self, req: Request, reason: str, now: int) -> None:
        super().on_remote_reject(req, reason, now)
        self._launch_fallback(req, now)


def _make_policy(name: str, sim: Simulation) -> _Policy:
    return {
        "always_local": AlwaysLocal,
        "always_remote": AlwaysRemote,
        "deadline_aware": DeadlineAware,
        "hedged_fallback": HedgedFallback,
    }[name](sim)


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #

def percentile(values: list[int], q: float) -> int | None:
    """Nearest-rank percentile; None for an empty sample."""
    if not 0 < q <= 1:
        raise ValueError("q must be in (0, 1]")
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil(len(ordered) * q) - 1]


def _rate(num: int, den: int) -> float | None:
    return None if den == 0 else round(num / den, 6)


def summarise(sim: Simulation) -> dict:
    n = len(sim.requests)
    sink = sim.sink
    applied_ids = set(sink.applied)
    applied = len(applied_ids)
    rejected_by_reason = {r: 0 for r in REJECT_REASONS}
    for rec in sink.records:
        if rec["decision"] == "rejected":
            rejected_by_reason[rec["reason"]] += 1
    latencies = [rec["latency_ms"] for rec in sink.records if rec["decision"] == "would_apply"]
    causes = {c: 0 for c in MISS_CAUSES}
    dis_total = dis_ok = out_total = out_ok = 0
    for req in sim.requests:
        ok = req.request_id in applied_ids
        if sim.in_disruption(req.capture_ms):
            dis_total += 1
            dis_ok += ok
        else:
            out_total += 1
            out_ok += ok
        if ok:
            continue
        flags = sim.cause_flags.get(req.index, set())
        for c in MISS_CAUSES:
            if c in flags:
                causes[c] += 1
                break
        else:
            causes["no_response"] += 1
    fallback_count = sum(1 for v in sink.applied_fallback.values() if v)
    return {
        "policy": sim.policy_name,
        "requests_total": n,
        "on_time_applied": applied,
        "on_time_rate": _rate(applied, n),
        "deadline_miss": n - applied,
        "stale_rejected": sum(rejected_by_reason[r] for r in STALE_REASONS),
        "rejected_by_reason": rejected_by_reason,
        "sink_decisions_total": len(sink.records),
        "fallback_count": fallback_count,
        "fallback_launched": sim.fallback_launched,
        "routed_local": sim.routed_local,
        "routed_remote": sim.routed_remote,
        "applied_by_source": {
            "local": sum(1 for s in sink.applied_source.values() if s == "local"),
            "remote": sum(1 for s in sink.applied_source.values() if s == "remote"),
        },
        "remote_timeouts": sim.remote_timeouts,
        "remote_rejects": dict(sorted(sim.remote_rejects.items())),
        "deadline_miss_causes": causes,
        "simulated_latency_ms": {
            "mean": None if not latencies else round(sum(latencies) / len(latencies), 3),
            "p50": percentile(latencies, 0.50),
            "p95": percentile(latencies, 0.95),
            "max": max(latencies) if latencies else None,
        },
        "by_capture_time": {
            "during_outage_or_recovery": {
                "requests": dis_total, "on_time": dis_ok, "on_time_rate": _rate(dis_ok, dis_total)},
            "otherwise": {
                "requests": out_total, "on_time": out_ok, "on_time_rate": _rate(out_ok, out_total)},
        },
        "actuated": False,
    }


def run_policy(cfg: dict, policy_name: str) -> tuple[dict, list[dict]]:
    sim = Simulation(cfg, policy_name)
    sim.run()
    return summarise(sim), sim.log


def run_all(config: dict, policies: list[str] | None = None) -> tuple[dict, dict[str, list[dict]]]:
    """Validate the raw ``config`` and run every policy. Returns (report, logs-by-policy)."""
    cfg = validate_config(config)
    names = policies or cfg["policies"]
    summaries: dict[str, dict] = {}
    logs: dict[str, list[dict]] = {}
    for name in names:
        summaries[name], logs[name] = run_policy(cfg, name)
    report = {
        "label": LABEL,
        "banner": BANNER,
        "simulation": True,
        "measured": False,
        "schema_version": SCHEMA_VERSION,
        "seed": cfg["seed"],
        "config_sha256": config_digest(cfg),
        "description": cfg["description"],
        "policies": summaries,
    }
    return report, logs


def format_table(report: dict) -> str:
    cols = ("on_time_rate", "on_time_applied", "deadline_miss", "stale_rejected",
            "fallback_count", "routed_remote")
    lines = [BANNER, f"seed={report['seed']} config_sha256={report['config_sha256'][:12]}", ""]
    lines.append(f"{'policy':<16}" + "".join(f"{c:>17}" for c in cols))
    for name, s in report["policies"].items():
        row = f"{name:<16}"
        for c in cols:
            v = s[c]
            row += f"{v if not isinstance(v, float) else format(v, '.4f'):>17}"
        lines.append(row)
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="SIMULATION of edge/cloud placement policies (no network, no robot, "
                    "no actuation). Outputs are SIMULATED model outputs.")
    ap.add_argument("--config", required=True, help="path to JSON config")
    ap.add_argument("--out", help="write the JSON report here")
    ap.add_argument("--log-dir", help="write one <policy>.decisions.jsonl per policy here")
    ap.add_argument("--policy", action="append", choices=POLICY_NAMES,
                    help="restrict to this policy (repeatable)")
    ap.add_argument("--json", action="store_true", help="print JSON instead of a table")
    args = ap.parse_args(argv)
    try:
        cfg = load_config(args.config)
        report, logs = run_all(cfg, args.policy)
    except ConfigError as exc:
        print(f"config error: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    if args.log_dir:
        out = Path(args.log_dir)
        out.mkdir(parents=True, exist_ok=True)
        for name, recs in logs.items():
            with (out / f"{name}.decisions.jsonl").open("w", encoding="utf-8") as fh:
                for rec in recs:
                    fh.write(json.dumps(rec, sort_keys=True) + "\n")
    print(text if args.json else format_table(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
