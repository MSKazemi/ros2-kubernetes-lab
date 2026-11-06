"""Discrete-event engine for one shared model-serving node.

Model (all parameters assumed, nothing measured):
  * ``workers`` identical single-request workers, each with its own model cache.
  * A request occupies a worker for ``load_cost`` (only on a cache miss) plus
    its sampled service time. The cache is updated at dispatch time.
  * Event order at equal timestamps: completion, worker_down, worker_up, arrival.
    After every event the dispatcher runs.
  * A worker going down aborts its in-flight request (re-queued with its
    original arrival time and deadline, counted as ``retried``) and clears the
    worker's cache. The worker is unavailable until its window ends.
  * Availability is an outage counter, not a flag: window start increments it,
    window end decrements it, and the worker is usable only at 0. So for
    back-to-back windows on one worker ([10,20] then [20,30]) the worker stays
    down across t=20 whatever order the two events run in (DOWN is processed
    before UP at an equal timestamp, and no dispatch can see the worker up).
  * Equal-timestamp consequences: a completion at the exact start of a failure
    window finishes normally (completion runs first); an arrival at the exact
    start of a window cannot use that worker (down runs before arrival); an
    arrival at the exact end of a window can (up runs before arrival).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .cache import ModelCache
from .config import SimConfig
from .schedulers import make_scheduler
from .workload import Request, generate_requests

_COMPLETION, _DOWN, _UP, _ARRIVAL = 0, 1, 2, 3


@dataclass
class _Worker:
    index: int
    cache: ModelCache
    outages: int = 0          # open failure windows; the worker is usable only when 0
    current: Optional[Request] = None
    started_at: float = 0.0
    epoch: int = 0
    busy_time: float = 0.0


@dataclass
class SimResult:
    config: SimConfig
    requests: List[Request]
    end_time: float
    hits: int
    misses: int
    evictions: int
    retried: int
    busy_time: float
    dispatch_log: List = field(default_factory=list)   # (time, request id, worker, hit)


class Simulation:
    def __init__(self, cfg: SimConfig, requests: Optional[List[Request]] = None):
        self.cfg = cfg
        self.requests = requests if requests is not None else generate_requests(cfg)
        self.sched = make_scheduler(cfg)
        self.workers = [_Worker(i, ModelCache(cfg.cache_capacity)) for i in range(cfg.workers)]
        self._events: List = []
        self._seq = 0
        self.hits = self.misses = self.retried = 0
        self.log: List = []

    def _push(self, t: float, kind: int, data) -> None:
        heapq.heappush(self._events, (t, kind, self._seq, data))
        self._seq += 1

    # ---- placement -------------------------------------------------------
    def _choose_worker(self, req: Request, idle: List[_Worker]) -> _Worker:
        if self.cfg.placement == "cache_aware":
            resident = [w for w in idle if req.model in w.cache]
            if resident:
                return resident[0]
            size = self.cfg.models[req.model].size
            roomy = [w for w in idle if w.cache.free() + 1e-12 >= size]
            if roomy:
                return roomy[0]
        return idle[0]          # first_idle (and cache_aware fallback): lowest index

    # ---- dispatch --------------------------------------------------------
    def _dispatch(self, now: float) -> None:
        while len(self.sched):
            idle = [w for w in self.workers if w.outages == 0 and w.current is None]
            if not idle:
                return
            req = self.sched.pop(now)
            if self.cfg.drop_expired and req.deadline < now:
                req.status, req.drop_time = "dropped", now
                continue
            w = self._choose_worker(req, idle)
            spec = self.cfg.models[req.model]
            hit = w.cache.access(req.model, spec.size)
            if hit:
                self.hits += 1
            else:
                self.misses += 1
            occupancy = req.service + (0.0 if hit else spec.load_cost)
            req.status = "running"
            req.attempts += 1
            if req.first_start is None:
                req.first_start = now
            w.current, w.started_at = req, now
            self.log.append((now, req.id, w.index, hit))
            self._push(now + occupancy, _COMPLETION, (w, w.epoch, req))

    # ---- run -------------------------------------------------------------
    def run(self) -> SimResult:
        cfg = self.cfg
        for req in self.requests:
            self._push(req.arrival, _ARRIVAL, req)
        for f in cfg.failures:
            self._push(f.start, _DOWN, self.workers[f.worker])
            self._push(f.end, _UP, self.workers[f.worker])

        last_completion = 0.0
        while self._events:
            t, kind, _seq, data = heapq.heappop(self._events)
            if not cfg.drain and t > cfg.duration:
                break
            if kind == _COMPLETION:
                w, epoch, req = data
                if epoch != w.epoch:
                    continue                      # stale: worker failed meanwhile
                req.status, req.finish = "done", t
                w.busy_time += t - w.started_at
                w.current = None
                last_completion = max(last_completion, t)
            elif kind == _DOWN:
                w = data
                w.outages += 1
                if w.current is not None:
                    req = w.current
                    w.busy_time += t - w.started_at
                    w.epoch += 1
                    w.current = None
                    req.status = "queued"
                    self.retried += 1
                    self.sched.push(req)
                w.cache.clear()
            elif kind == _UP:
                data.outages -= 1
            else:  # arrival
                req = data
                cap = cfg.queue_capacity
                if cap is not None and len(self.sched) >= cap:
                    req.status = "rejected"
                else:
                    req.status = "queued"
                    self.sched.push(req)
            self._dispatch(t)

        if cfg.drain:
            end_time = max(cfg.duration, last_completion)
        else:
            end_time = cfg.duration
        busy = sum(w.busy_time for w in self.workers)
        # a still-running request at the horizon contributes its partial busy time
        for w in self.workers:
            if w.current is not None:
                busy += max(0.0, end_time - w.started_at)
        evictions = sum(w.cache.evictions for w in self.workers)
        return SimResult(cfg, self.requests, end_time, self.hits, self.misses, evictions,
                         self.retried, busy, self.log)


def simulate(cfg: SimConfig, requests: Optional[List[Request]] = None) -> SimResult:
    """Run one simulation. Pass ``requests`` only if they are fresh (unmutated)."""
    return Simulation(cfg, requests).run()
