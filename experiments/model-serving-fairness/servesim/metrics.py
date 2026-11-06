"""Metrics computed from a finished simulation. Every number is SIMULATED.

Definitions
-----------
latency          finish - arrival (queueing + model load if any + service), for
                 completed requests only.
percentile       nearest-rank: for integer p in 1..100 and n sorted values,
                 rank = ceil(p * n / 100) (integer arithmetic), value = sorted[rank - 1].
on time          completed with finish <= deadline (inclusive).
deadline miss    late completion, OR dropped as expired, OR unfinished at the
rate             end whose deadline already passed; divided by ADMITTED requests
                 (arrivals - rejected). ``goodput_rate`` = on_time / arrivals
                 counts rejected requests against the system.
Jain index       (sum x)^2 / (n * sum x^2) over per-client goodput ratios
                 x_i = on_time_i / arrivals_i (clients with no arrivals are
                 excluded). 1.0 = perfectly even, 1/n = one client gets everything.
                 If every x_i is 0 the index is defined as 1.0 (all equally
                 starved); read it together with ``goodput_rate``.
queue wait       first_start - arrival; for requests never started, the time
                 until they were dropped or the simulation ended.
starved request  queue wait > ``starvation_wait`` (config, seconds).
cache hit rate   hits / (hits + misses), counted per dispatch (an aborted and
                 retried request is counted at each dispatch).
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence

from .engine import SimResult

LABEL = "SIMULATED"
_ROUND = 6


def _r(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, _ROUND)


def percentile_nearest_rank(values: Iterable[float], p: int) -> Optional[float]:
    """Nearest-rank percentile; ``p`` must be an integer in 1..100. Empty -> None."""
    if isinstance(p, bool) or not isinstance(p, int) or not 1 <= p <= 100:
        raise ValueError("p must be an integer in 1..100")
    vals = sorted(values)
    if not vals:
        return None
    rank = -(-p * len(vals) // 100)      # ceil(p*n/100) without float error
    return vals[max(1, rank) - 1]


def jain_index(xs: Sequence[float]) -> Optional[float]:
    """Jain's fairness index. Empty -> None; all zeros -> 1.0 (see module doc)."""
    if any(x < 0 for x in xs):
        raise ValueError("allocations must be non-negative")
    n = len(xs)
    if n == 0:
        return None
    sq = sum(x * x for x in xs)
    if sq == 0:
        return 1.0
    return (sum(xs) ** 2) / (n * sq)


def _latency_block(lats: List[float]) -> Dict[str, Optional[float]]:
    return {
        "count": len(lats),
        "p50": _r(percentile_nearest_rank(lats, 50)),
        "p95": _r(percentile_nearest_rank(lats, 95)),
        "p99": _r(percentile_nearest_rank(lats, 99)),
        "mean": _r(sum(lats) / len(lats)) if lats else None,
        "max": _r(max(lats)) if lats else None,
    }


def _client_block(reqs, end_time: float, starvation_wait: float) -> Dict:
    arrivals = len(reqs)
    rejected = sum(r.status == "rejected" for r in reqs)
    dropped = sum(r.status == "dropped" for r in reqs)
    done = [r for r in reqs if r.status == "done"]
    on_time = sum(r.finish <= r.deadline for r in done)
    late = len(done) - on_time
    unfinished = [r for r in reqs if r.status in ("new", "queued", "running")]
    unfinished_expired = sum(r.deadline < end_time for r in unfinished)
    admitted = arrivals - rejected
    waits = []
    for r in reqs:
        if r.status == "rejected":
            continue
        if r.first_start is not None:
            waits.append(r.first_start - r.arrival)
        elif r.status == "dropped":
            waits.append(r.drop_time - r.arrival)
        else:
            waits.append(end_time - r.arrival)
    starved = sum(w > starvation_wait for w in waits)
    misses = late + dropped + unfinished_expired
    return {
        "arrivals": arrivals,
        "rejected": rejected,
        "dropped": dropped,
        "completed": len(done),
        "on_time": on_time,
        "late": late,
        "unfinished": len(unfinished),
        "deadline_miss_rate": _r(misses / admitted) if admitted else None,
        "goodput_ratio": _r(on_time / arrivals) if arrivals else None,
        "latency_s": _latency_block([r.finish - r.arrival for r in done]),
        "max_queue_wait_s": _r(max(waits)) if waits else None,
        "starved_requests": starved,
        "starved_fraction": _r(starved / admitted) if admitted else None,
        "no_service": bool(arrivals and not done),
    }


def summarize(result: SimResult) -> Dict:
    """Return the stable summary dict for one run (see README for field list)."""
    cfg = result.config
    by_client: Dict[str, list] = {c.id: [] for c in cfg.clients}
    for r in result.requests:
        by_client[r.client].append(r)
    clients = {cid: _client_block(rs, result.end_time, cfg.starvation_wait)
               for cid, rs in by_client.items()}

    reqs = result.requests
    arrivals = len(reqs)
    rejected = sum(r.status == "rejected" for r in reqs)
    dropped = sum(r.status == "dropped" for r in reqs)
    done = [r for r in reqs if r.status == "done"]
    on_time = sum(r.finish <= r.deadline for r in done)
    unfinished = [r for r in reqs if r.status in ("new", "queued", "running")]
    admitted = arrivals - rejected
    misses = (len(done) - on_time) + dropped + sum(r.deadline < result.end_time for r in unfinished)

    quiet_ids = {c.id for c in cfg.clients if not c.noisy}
    quiet = [r for r in reqs if r.client in quiet_ids and r.status != "rejected"]
    quiet_misses = sum(
        (r.status == "done" and r.finish > r.deadline) or r.status == "dropped" or
        (r.status in ("new", "queued", "running") and r.deadline < result.end_time)
        for r in quiet)

    goodputs = [c["goodput_ratio"] for c in clients.values() if c["goodput_ratio"] is not None]
    lookups = result.hits + result.misses
    cap = cfg.workers * result.end_time
    return {
        "label": LABEL,
        "seed": cfg.seed,
        "scheduler": cfg.scheduler,
        "placement": cfg.placement,
        "worker_failures": [{"worker": f.worker, "start": f.start, "end": f.end}
                            for f in cfg.failures],
        "end_time_s": _r(result.end_time),
        "totals": {
            "arrivals": arrivals,
            "admitted": admitted,
            "rejected": rejected,
            "dropped": dropped,
            "completed": len(done),
            "on_time": on_time,
            "late": len(done) - on_time,
            "unfinished": len(unfinished),
            "retried_after_worker_failure": result.retried,
        },
        "deadline_miss_rate": _r(misses / admitted) if admitted else None,
        "goodput_rate": _r(on_time / arrivals) if arrivals else None,
        "quiet_clients_deadline_miss_rate": _r(quiet_misses / len(quiet)) if quiet else None,
        "latency_s": _latency_block([r.finish - r.arrival for r in done]),
        "jain_goodput_index": _r(jain_index(goodputs)),
        "starved_requests": sum(c["starved_requests"] for c in clients.values()),
        "clients_with_no_service": sorted(cid for cid, c in clients.items() if c["no_service"]),
        "cache": {
            "hits": result.hits,
            "misses": result.misses,
            "hit_rate": _r(result.hits / lookups) if lookups else None,
            "evictions": result.evictions,
        },
        "worker_busy_fraction": _r(result.busy_time / cap) if cap > 0 else None,
        "clients": clients,
    }
