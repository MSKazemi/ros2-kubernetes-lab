"""Queue disciplines. Each scheduler holds waiting requests and ``pop`` returns
the next one to dispatch.

fifo  First-in first-out, ordered by (arrival time, request id).
edf   Earliest deadline first, ordered by (absolute deadline, arrival, id).
drr   Deficit Round Robin (Shreedhar & Varghese, 1995) over per-client queues.
      Cost of a request = its sampled warm service time in seconds (model load
      time is NOT charged). Each visit to a backlogged client adds
      ``quantum * client.weight`` seconds of deficit; the client is served
      while its head request cost <= deficit. A client whose queue empties
      leaves the ring and its deficit is reset to 0. Within a client, requests
      are served in (arrival, id) order.

A request pushed again after a worker failure keeps its original arrival time
and id, so it re-enters at its natural position.
"""

from __future__ import annotations

import heapq
from typing import Dict, List, Optional

from .config import SimConfig
from .workload import Request


class Scheduler:
    name = "base"

    def push(self, req: Request) -> None:
        raise NotImplementedError

    def pop(self, now: float) -> Optional[Request]:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError


class FifoScheduler(Scheduler):
    name = "fifo"

    def __init__(self) -> None:
        self._heap: List = []

    def push(self, req: Request) -> None:
        heapq.heappush(self._heap, (req.arrival, req.id, req))

    def pop(self, now: float) -> Optional[Request]:
        return heapq.heappop(self._heap)[2] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)


class EdfScheduler(Scheduler):
    name = "edf"

    def __init__(self) -> None:
        self._heap: List = []

    def push(self, req: Request) -> None:
        heapq.heappush(self._heap, (req.deadline, req.arrival, req.id, req))

    def pop(self, now: float) -> Optional[Request]:
        return heapq.heappop(self._heap)[3] if self._heap else None

    def __len__(self) -> int:
        return len(self._heap)


class DrrScheduler(Scheduler):
    name = "drr"

    def __init__(self, quantum: float, weights: Dict[str, float]) -> None:
        if not quantum > 0:
            raise ValueError("quantum must be > 0")
        self.quantum = quantum
        self.weights = dict(weights)
        self._queues: Dict[str, List] = {}      # client -> heap of (arrival, id, req)
        self._ring: List[str] = []              # backlogged clients, in activation order
        self._deficit: Dict[str, float] = {}
        self._cur = 0                           # index into _ring of the client whose turn it is
        self._turn_open = False                 # quantum already granted for this turn?
        self._n = 0

    def push(self, req: Request) -> None:
        q = self._queues.setdefault(req.client, [])
        if not q:
            self._ring.append(req.client)
            self._deficit[req.client] = 0.0
        heapq.heappush(q, (req.arrival, req.id, req))
        self._n += 1

    def pop(self, now: float) -> Optional[Request]:
        if self._n == 0:
            return None
        while True:
            client = self._ring[self._cur]
            if not self._turn_open:
                self._deficit[client] += self.quantum * self.weights.get(client, 1.0)
                self._turn_open = True
            q = self._queues[client]
            head = q[0][2]
            if head.service <= self._deficit[client] + 1e-12:
                heapq.heappop(q)
                self._n -= 1
                self._deficit[client] -= head.service
                if not q:
                    # client leaves the ring; the next client slides into this index
                    self._deficit[client] = 0.0
                    del self._ring[self._cur]
                    self._turn_open = False
                    if self._ring:
                        self._cur %= len(self._ring)
                    else:
                        self._cur = 0
                return head
            # head does not fit: end this client's turn
            self._turn_open = False
            self._cur = (self._cur + 1) % len(self._ring)

    def __len__(self) -> int:
        return self._n


def make_scheduler(cfg: SimConfig) -> Scheduler:
    if cfg.scheduler == "fifo":
        return FifoScheduler()
    if cfg.scheduler == "edf":
        return EdfScheduler()
    if cfg.scheduler == "drr":
        return DrrScheduler(cfg.drr_quantum, {c.id: c.weight for c in cfg.clients})
    raise ValueError(f"unknown scheduler {cfg.scheduler!r}")
