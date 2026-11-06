"""Metrics computed ONLY from the records of a supplied trace.

Definitions (also in the README):

* ``delivery_completeness`` = distinct sent seqs that were received at least once / distinct sent seqs.
* ``loss_ratio`` = 1 - delivery_completeness.
* ``duplicate_copies`` = received records beyond the first for a seq;
  ``duplicate_ratio`` = duplicate_copies / solicited_received, where solicited_received =
  received records whose seq was sent (received_total minus unsolicited); null if that is 0.
* ``reorder`` follows RFC 4737 (type-P-reordered): walking first deliveries in file
  (arrival) order with ``NextExp`` starting at the smallest sent seq, a delivery with
  ``seq >= NextExp`` sets ``NextExp = seq + 1``; otherwise it counts as reordered.
* ``latency`` = first receive time of a seq - its send time, same clock domain only. If any sample
  is negative (clock skew), percentiles are null, ``latency_diagnostics`` gives the counts and the
  minimum, a warning is added, and every clock-independent metric is still produced.
  Percentiles use the nearest-rank method: the value at 1-based rank ``ceil(p/100 * n)``
  of the ascending samples (always an actual sample, no interpolation).
* ``fault_windows`` pair ``<name>_begin`` / ``<name>_end`` markers. For each window:
  ``delivery_gap_ns`` = first receive strictly after begin - last receive at or before begin;
  ``recovery_time_ns`` = first receive at or after end - end (null if end marker absent,
  ``recovered`` false if nothing arrived after end). A stale buffered message arriving after
  end counts as resumed delivery; this is a property of the definition, not of any middleware.
* ``resources``: min/mean/max of ``cpu_pct`` / ``mem_bytes`` only if such samples are present.

Nothing is estimated, interpolated or defaulted: absent inputs give ``null``.
"""

from __future__ import annotations

import math
import re
from typing import Any, Dict, List, Optional, Sequence

from .trace import ClockDomainError, EmptyTraceError, Trace, TraceError

DISCLAIMER_SYNTHETIC = (
    "SYNTHETIC input: values describe a deterministic generated fixture and the "
    "assumptions of the generator, not any middleware, network or cluster."
)


class InsufficientSamplesError(ValueError):
    """Too few samples to compute the requested statistic."""


def nearest_rank(samples: Sequence[float], p: float) -> float:
    """Nearest-rank percentile; raises on fewer than 2 samples or p outside (0, 100]."""
    n = len(samples)
    if n < 2:
        raise InsufficientSamplesError(f"percentile needs at least 2 samples, got {n}")
    if not (0 < p <= 100):
        raise ValueError(f"percentile must be in (0, 100], got {p}")
    ordered = sorted(samples)
    rank = math.ceil(p / 100.0 * n)
    return ordered[rank - 1]


def _summary(values: List[float]) -> Optional[Dict[str, Any]]:
    if not values:
        return None
    return {"n": len(values), "min": min(values), "mean": sum(values) / len(values), "max": max(values)}


def _fault_windows(trace: Trace, recv_times: List[int]) -> List[Dict[str, Any]]:
    begins: Dict[str, List[int]] = {}
    ends: Dict[str, List[int]] = {}
    for m in trace.markers:
        mt = re.fullmatch(r"([A-Za-z0-9_]+?)_(begin|end)", m.name)
        if not mt:
            continue
        (begins if mt.group(2) == "begin" else ends).setdefault(mt.group(1), []).append(m.t_ns)
    out: List[Dict[str, Any]] = []
    for name in sorted(set(begins) | set(ends)):
        b, e = begins.get(name, []), ends.get(name, [])
        if len(e) > len(b):
            raise TraceError(f"fault {name!r}: {len(e)} end marker(s) but only {len(b)} begin marker(s)")
        for i, bt in enumerate(b):
            et = e[i] if i < len(e) else None
            if et is not None and et < bt:
                raise TraceError(f"fault {name!r}: end marker precedes begin marker")
            before = [t for t in recv_times if t <= bt]
            after = [t for t in recv_times if t > bt]
            gap = (min(after) - max(before)) if before and after else None
            rec: Dict[str, Any] = {
                "name": name,
                "begin_t_ns": bt,
                "end_t_ns": et,
                "delivery_gap_ns": gap,
                "recovered": None,
                "recovery_time_ns": None,
            }
            if et is not None:
                post = [t for t in recv_times if t >= et]
                rec["recovered"] = bool(post)
                rec["recovery_time_ns"] = (min(post) - et) if post else None
            out.append(rec)
    return out


def analyze(trace: Trace, on_mixed_clock: str = "error", require_latency: bool = False) -> Dict[str, Any]:
    """Compute all metrics for one trace.

    ``on_mixed_clock``: ``"error"`` raises :class:`ClockDomainError` when send/recv/marker
    records use more than one clock domain; ``"null"`` leaves latency and fault-window
    time metrics as null and records a warning. ``require_latency`` turns "fewer than 2
    latency samples" into an error instead of a null.
    """
    if on_mixed_clock not in ("error", "null"):
        raise ValueError("on_mixed_clock must be 'error' or 'null'")
    if not trace.sends:
        raise EmptyTraceError(f"{trace.source}: no send records")

    warnings: List[str] = list(trace.notes)
    sent = {e.seq: e for e in trace.sends}
    first_recv: Dict[int, Any] = {}
    seen_order: List[int] = []
    received_total = 0
    unsolicited = 0
    for e in trace.recvs:
        received_total += 1
        if e.seq not in sent:
            unsolicited += 1
            continue
        if e.seq not in first_recv:
            first_recv[e.seq] = e
            seen_order.append(e.seq)
        elif e.t_ns < first_recv[e.seq].t_ns:
            first_recv[e.seq] = e  # earliest by time defines latency
    received_unique = len(first_recv)
    n_sent = len(sent)
    completeness = received_unique / n_sent
    solicited_total = received_total - unsolicited
    duplicate_copies = solicited_total - received_unique
    if unsolicited:
        warnings.append(f"{unsolicited} received record(s) carry a seq that was never sent; excluded from metrics")

    # RFC 4737 reordering over first deliveries in arrival (file) order.
    reordered = 0
    next_exp = min(sent)
    for seq in seen_order:
        if seq >= next_exp:
            next_exp = seq + 1
        else:
            reordered += 1

    clocks = {e.clock for e in trace.sends} | {e.clock for e in trace.recvs} | {m.clock for m in trace.markers}
    mixed = len(clocks) > 1
    if mixed and on_mixed_clock == "error":
        raise ClockDomainError(
            f"{trace.source}: mixed clock domains {sorted(clocks)}; latency/recovery would compare unrelated clocks"
        )
    if mixed:
        warnings.append(f"mixed clock domains {sorted(clocks)}: latency and fault-window times set to null")

    latency: Optional[Dict[str, Any]] = None
    latency_reason: Optional[str] = None
    latency_diag: Optional[Dict[str, Any]] = None
    negative_found = False
    if mixed:
        latency_reason = "mixed_clock_domains"
    else:
        samples = [r.t_ns - sent[seq].t_ns for seq, r in first_recv.items()]
        negatives = [d for d in samples if d < 0]
        if negatives:
            # Same-domain labels do not guarantee synchronised clocks (wall/ros across nodes), so a
            # negative sample is a clock-quality finding, not a reason to drop clock-independent metrics.
            latency_diag = {"total_samples": len(samples), "negative_samples": len(negatives), "min_ns": min(samples)}
            msg = (f"{len(negatives)} of {len(samples)} latency samples are negative (min {min(samples)} ns): "
                   f"receive stamped before send within one clock domain, i.e. clock skew or unsynchronised clocks; "
                   f"latency percentiles set to null")
            if require_latency:
                raise TraceError(f"{trace.source}: {msg}")
            warnings.append(msg)
            latency_reason = "negative_latency_samples"
            samples = []
            negative_found = True
        if negative_found:
            pass
        elif len(samples) < 2:
            if require_latency:
                raise InsufficientSamplesError(f"only {len(samples)} latency sample(s); need at least 2")
            latency_reason = f"insufficient_samples (n={len(samples)})"
        else:
            latency = {
                "n": len(samples),
                "unit": "ns",
                "method": "nearest-rank",
                "p50_ns": nearest_rank(samples, 50),
                "p95_ns": nearest_rank(samples, 95),
                "p99_ns": nearest_rank(samples, 99),
                "p99_resolved": len(samples) >= 100,
            }
            if len(samples) < 100:
                warnings.append(f"n={len(samples)} < 100: nearest-rank p99 equals the maximum sample")

    if mixed:
        faults = [
            {**w, "delivery_gap_ns": None, "recovered": None, "recovery_time_ns": None}
            for w in _fault_windows(trace, [])
        ]
    else:
        faults = _fault_windows(trace, [e.t_ns for e in trace.recvs])

    cpu = [r.cpu_pct for r in trace.resources if r.cpu_pct is not None]
    mem = [r.mem_bytes for r in trace.resources if r.mem_bytes is not None]

    h = trace.header
    return {
        "source": trace.source,
        "synthetic": h.get("synthetic"),
        "disclaimer": DISCLAIMER_SYNTHETIC if h.get("synthetic") else None,
        "run_id": h.get("run_id"),
        "reliability": h.get("reliability"),
        "impairment": h.get("impairment"),
        "counts": {
            "sent_unique": n_sent,
            "received_total": received_total,
            "received_unique": received_unique,
            "lost": n_sent - received_unique,
            "unsolicited": unsolicited,
            "solicited_received": solicited_total,
            "duplicate_copies": duplicate_copies,
        },
        "delivery_completeness": completeness,
        "loss_ratio": 1.0 - completeness,
        "duplicate_ratio": (duplicate_copies / solicited_total) if solicited_total else None,
        "reorder": {
            "method": "RFC 4737 NextExp",
            "count": reordered,
            "ratio": (reordered / received_unique) if received_unique else None,
        },
        "latency": latency,
        "latency_unavailable_reason": latency_reason,
        "latency_diagnostics": latency_diag,
        "fault_windows": faults,
        "resources": {"cpu_pct": _summary(cpu), "mem_bytes": _summary(mem)},
        "warnings": warnings,
    }
