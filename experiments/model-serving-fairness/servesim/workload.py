"""Deterministic request generation.

Each client has three independent random streams (arrivals, model choice,
service-time jitter) seeded from ``"<seed>|<client id>|<stream>"``. Python's
``random.Random`` seeds ``str`` inputs deterministically (SHA-512), so results
do not depend on PYTHONHASHSEED. Because service times are sampled here, once
per request, every scheduler sees an identical workload for a given seed.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

from .config import ClientSpec, SimConfig


@dataclass
class Request:
    id: int
    client: str
    model: str
    arrival: float
    deadline: float          # absolute time
    service: float           # sampled warm service seconds (excludes model load)
    # --- mutable state filled in by the engine ---
    status: str = "new"      # new | queued | running | done | rejected | dropped
    first_start: Optional[float] = None
    finish: Optional[float] = None
    drop_time: Optional[float] = None
    attempts: int = 0


def _arrival_times(client: ClientSpec, rng: random.Random, duration: float) -> List[float]:
    a = client.arrival
    if a.kind == "fixed":
        return sorted(a.get("times"))
    times: List[float] = []
    if a.kind == "periodic":
        period, offset, jitter = a.get("period"), a.get("offset"), a.get("jitter")
        k = 0
        while True:
            base = offset + k * period
            if base >= duration:
                break
            t = base + (rng.random() * jitter * period if jitter else 0.0)
            if t < duration:
                times.append(t)
            k += 1
    elif a.kind == "poisson":
        t = a.get("start")
        end = min(a.get("end"), duration)
        rate = a.get("rate")
        while True:
            t += rng.expovariate(rate)
            if t >= end:
                break
            times.append(t)
    else:  # bursty
        interval, size, gap, offset = (a.get("burst_interval"), a.get("burst_size"),
                                       a.get("burst_gap"), a.get("offset"))
        k = 0
        while True:
            start = offset + k * interval
            if start >= duration:
                break
            for j in range(size):
                t = start + j * gap
                if t < duration:
                    times.append(t)
            k += 1
    return sorted(times)


def generate_requests(cfg: SimConfig) -> List[Request]:
    """Return all requests, sorted by (arrival, client order, per-client index)."""
    staged = []
    for ci, client in enumerate(cfg.clients):
        arr_rng = random.Random(f"{cfg.seed}|{client.id}|arrivals")
        mod_rng = random.Random(f"{cfg.seed}|{client.id}|models")
        svc_rng = random.Random(f"{cfg.seed}|{client.id}|service")
        ids = [m for m, _ in client.models]
        weights = [w for _, w in client.models]
        for k, t in enumerate(_arrival_times(client, arr_rng, cfg.duration)):
            model = mod_rng.choices(ids, weights=weights, k=1)[0]
            spec = cfg.models[model]
            u = svc_rng.random()
            service = spec.service_time * (1.0 + spec.service_jitter * (2.0 * u - 1.0))
            staged.append((t, ci, k, client, model, service))
    staged.sort(key=lambda s: (s[0], s[1], s[2]))
    return [Request(id=i, client=c.id, model=m, arrival=t, deadline=t + c.deadline, service=svc)
            for i, (t, _ci, _k, c, m, svc) in enumerate(staged)]
