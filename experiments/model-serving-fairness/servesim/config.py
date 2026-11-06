"""Configuration parsing and validation for the model-serving simulation.

All inputs are plain JSON-compatible dicts. ``parse_config`` validates them and
returns frozen dataclasses. Unknown keys are rejected so typos fail loudly.
Every numeric parameter here is an ASSUMED value chosen by the experimenter;
nothing is measured.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

SCHEDULERS = ("fifo", "edf", "drr")
PLACEMENTS = ("first_idle", "cache_aware")
ARRIVAL_KINDS = ("fixed", "periodic", "poisson", "bursty")


class ConfigError(ValueError):
    """Raised for any invalid simulation configuration."""


def _num(value: Any, name: str, *, gt: Optional[float] = None, ge: Optional[float] = None,
         integer: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{name} must be a number, got {value!r}")
    if isinstance(value, float) and not math.isfinite(value):
        raise ConfigError(f"{name} must be finite, got {value!r}")
    if integer and int(value) != value:
        raise ConfigError(f"{name} must be an integer, got {value!r}")
    if gt is not None and not value > gt:
        raise ConfigError(f"{name} must be > {gt}, got {value!r}")
    if ge is not None and not value >= ge:
        raise ConfigError(f"{name} must be >= {ge}, got {value!r}")
    return int(value) if integer else float(value)


def _check_keys(raw: Any, allowed: set, required: set, where: str) -> None:
    if not isinstance(raw, dict):
        raise ConfigError(f"{where} must be an object, got {type(raw).__name__}")
    unknown = set(raw) - allowed
    if unknown:
        raise ConfigError(f"{where}: unknown keys {sorted(unknown)}")
    missing = required - set(raw)
    if missing:
        raise ConfigError(f"{where}: missing keys {sorted(missing)}")


def _name(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{where} must be a non-empty string, got {value!r}")
    return value


@dataclass(frozen=True)
class ModelSpec:
    id: str
    service_time: float      # assumed mean seconds of service on a warm worker
    load_cost: float         # assumed seconds added on a cache miss
    size: float              # assumed cache units occupied while resident
    service_jitter: float    # service ~ U(mean*(1-j), mean*(1+j))


@dataclass(frozen=True)
class ArrivalSpec:
    kind: str
    params: Tuple[Tuple[str, Any], ...]

    def get(self, key: str, default: Any = None) -> Any:
        return dict(self.params).get(key, default)


@dataclass(frozen=True)
class ClientSpec:
    id: str
    arrival: ArrivalSpec
    models: Tuple[Tuple[str, float], ...]   # (model id, weight)
    deadline: float                          # relative seconds
    weight: float                            # DRR weight
    noisy: bool                              # label only; used for the quiet-client aggregate


@dataclass(frozen=True)
class FailureWindow:
    worker: int
    start: float
    end: float


@dataclass(frozen=True)
class SimConfig:
    seed: int
    duration: float
    workers: int
    cache_capacity: float
    models: Dict[str, ModelSpec]
    clients: Tuple[ClientSpec, ...]
    scheduler: str = "fifo"
    placement: str = "first_idle"
    drr_quantum: float = 0.1
    queue_capacity: Optional[int] = None
    drop_expired: bool = False
    drain: bool = True
    starvation_wait: float = 5.0
    failures: Tuple[FailureWindow, ...] = field(default_factory=tuple)
    name: str = "unnamed"


def _parse_arrival(raw: Any, where: str, duration: float) -> ArrivalSpec:
    if not isinstance(raw, dict) or "kind" not in raw:
        raise ConfigError(f"{where}: arrival must be an object with 'kind'")
    kind = raw["kind"]
    if kind not in ARRIVAL_KINDS:
        raise ConfigError(f"{where}: unknown arrival kind {kind!r}; expected one of {ARRIVAL_KINDS}")
    body = {k: v for k, v in raw.items() if k != "kind"}
    out: Dict[str, Any] = {}
    if kind == "fixed":
        _check_keys(body, {"times"}, {"times"}, where)
        times = body["times"]
        if not isinstance(times, list):
            raise ConfigError(f"{where}.times must be a list")
        out["times"] = [_num(t, f"{where}.times[]", ge=0) for t in times]
        if any(t >= duration for t in out["times"]):
            raise ConfigError(f"{where}.times must all be < duration ({duration})")
    elif kind == "periodic":
        _check_keys(body, {"period", "offset", "jitter"}, {"period"}, where)
        out["period"] = _num(body["period"], f"{where}.period", gt=0)
        out["offset"] = _num(body.get("offset", 0.0), f"{where}.offset", ge=0)
        out["jitter"] = _num(body.get("jitter", 0.0), f"{where}.jitter", ge=0)
        if out["jitter"] >= 1:
            raise ConfigError(f"{where}.jitter must be < 1 (fraction of the period)")
    elif kind == "poisson":
        _check_keys(body, {"rate", "start", "end"}, {"rate"}, where)
        out["rate"] = _num(body["rate"], f"{where}.rate", gt=0)
        out["start"] = _num(body.get("start", 0.0), f"{where}.start", ge=0)
        out["end"] = _num(body.get("end", duration), f"{where}.end", gt=0)
        if out["end"] <= out["start"]:
            raise ConfigError(f"{where}: end must be > start")
    else:  # bursty
        _check_keys(body, {"burst_interval", "burst_size", "burst_gap", "offset"},
                    {"burst_interval", "burst_size"}, where)
        out["burst_interval"] = _num(body["burst_interval"], f"{where}.burst_interval", gt=0)
        out["burst_size"] = _num(body["burst_size"], f"{where}.burst_size", ge=1, integer=True)
        out["burst_gap"] = _num(body.get("burst_gap", 0.0), f"{where}.burst_gap", ge=0)
        out["offset"] = _num(body.get("offset", 0.0), f"{where}.offset", ge=0)
    return ArrivalSpec(kind, tuple(sorted(out.items())))


def parse_config(raw: Any) -> SimConfig:
    """Validate a raw dict and return a SimConfig. Raises ConfigError."""
    allowed = {"name", "seed", "duration", "workers", "cache_capacity", "models", "clients",
               "scheduler", "placement", "drr_quantum", "queue_capacity", "drop_expired",
               "drain", "starvation_wait", "failures"}
    _check_keys(raw, allowed, {"seed", "duration", "workers", "cache_capacity", "models", "clients"},
                "config")
    seed = _num(raw["seed"], "seed", integer=True)
    duration = _num(raw["duration"], "duration", gt=0)
    workers = _num(raw["workers"], "workers", ge=1, integer=True)
    cache_capacity = _num(raw["cache_capacity"], "cache_capacity", gt=0)

    scheduler = raw.get("scheduler", "fifo")
    if scheduler not in SCHEDULERS:
        raise ConfigError(f"scheduler must be one of {SCHEDULERS}, got {scheduler!r}")
    placement = raw.get("placement", "first_idle")
    if placement not in PLACEMENTS:
        raise ConfigError(f"placement must be one of {PLACEMENTS}, got {placement!r}")
    drr_quantum = _num(raw.get("drr_quantum", 0.1), "drr_quantum", gt=0)
    queue_capacity = raw.get("queue_capacity")
    if queue_capacity is not None:
        queue_capacity = _num(queue_capacity, "queue_capacity", ge=1, integer=True)
    for flag in ("drop_expired", "drain"):
        if flag in raw and not isinstance(raw[flag], bool):
            raise ConfigError(f"{flag} must be a boolean")
    starvation_wait = _num(raw.get("starvation_wait", 5.0), "starvation_wait", gt=0)

    models_raw = raw["models"]
    if not isinstance(models_raw, dict) or not models_raw:
        raise ConfigError("models must be a non-empty object keyed by model id")
    models: Dict[str, ModelSpec] = {}
    for mid, m in models_raw.items():
        _name(mid, "model id")
        _check_keys(m, {"service_time", "load_cost", "size", "service_jitter"},
                    {"service_time"}, f"models.{mid}")
        spec = ModelSpec(
            id=mid,
            service_time=_num(m["service_time"], f"models.{mid}.service_time", gt=0),
            load_cost=_num(m.get("load_cost", 0.0), f"models.{mid}.load_cost", ge=0),
            size=_num(m.get("size", 1.0), f"models.{mid}.size", gt=0),
            service_jitter=_num(m.get("service_jitter", 0.0), f"models.{mid}.service_jitter", ge=0),
        )
        if spec.service_jitter >= 1:
            raise ConfigError(f"models.{mid}.service_jitter must be < 1")
        if spec.size > cache_capacity:
            raise ConfigError(
                f"models.{mid}.size ({spec.size}) exceeds cache_capacity ({cache_capacity})")
        models[mid] = spec

    clients_raw = raw["clients"]
    if not isinstance(clients_raw, list) or not clients_raw:
        raise ConfigError("clients must be a non-empty list")
    clients = []
    seen = set()
    for i, c in enumerate(clients_raw):
        where = f"clients[{i}]"
        _check_keys(c, {"id", "arrival", "models", "deadline", "weight", "noisy"},
                    {"id", "arrival", "models", "deadline"}, where)
        cid = _name(c["id"], f"{where}.id")
        if cid in seen:
            raise ConfigError(f"duplicate client id {cid!r}")
        seen.add(cid)
        mix = c["models"]
        if isinstance(mix, list):
            mix = {m: 1.0 for m in mix}
        if not isinstance(mix, dict) or not mix:
            raise ConfigError(f"{where}.models must be a non-empty list or {{model: weight}} object")
        mix_t = []
        for mid, w in mix.items():
            if mid not in models:
                raise ConfigError(f"{where}: unknown model {mid!r}")
            mix_t.append((mid, _num(w, f"{where}.models.{mid}", gt=0)))
        noisy = c.get("noisy", False)
        if not isinstance(noisy, bool):
            raise ConfigError(f"{where}.noisy must be a boolean")
        clients.append(ClientSpec(
            id=cid,
            arrival=_parse_arrival(c["arrival"], f"{where}.arrival", duration),
            models=tuple(mix_t),
            deadline=_num(c["deadline"], f"{where}.deadline", gt=0),
            weight=_num(c.get("weight", 1.0), f"{where}.weight", gt=0),
            noisy=noisy,
        ))

    failures = []
    for i, f in enumerate(raw.get("failures", [])):
        where = f"failures[{i}]"
        _check_keys(f, {"worker", "start", "end"}, {"worker", "start", "end"}, where)
        w = _num(f["worker"], f"{where}.worker", ge=0, integer=True)
        if w >= workers:
            raise ConfigError(f"{where}.worker {w} out of range (workers={workers})")
        s = _num(f["start"], f"{where}.start", ge=0)
        e = _num(f["end"], f"{where}.end", gt=0)
        if e <= s:
            raise ConfigError(f"{where}: end must be > start")
        failures.append(FailureWindow(w, s, e))
    by_worker: Dict[int, list] = {}
    for f in failures:
        by_worker.setdefault(f.worker, []).append(f)
    for w, wins in by_worker.items():
        wins.sort(key=lambda x: x.start)
        for a, b in zip(wins, wins[1:]):
            if b.start < a.end:
                raise ConfigError(f"overlapping failure windows for worker {w}")

    name = raw.get("name", "unnamed")
    _name(name, "name")
    return SimConfig(
        seed=seed, duration=duration, workers=workers, cache_capacity=cache_capacity,
        models=models, clients=tuple(clients), scheduler=scheduler, placement=placement,
        drr_quantum=drr_quantum, queue_capacity=queue_capacity,
        drop_expired=raw.get("drop_expired", False), drain=raw.get("drain", True),
        starvation_wait=starvation_wait,
        failures=tuple(sorted(failures, key=lambda x: (x.start, x.worker))), name=name,
    )
