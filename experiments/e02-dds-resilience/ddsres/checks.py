"""Evaluate a cell's ``synthetic_checks`` against an analysis result.

These are PIPELINE sanity checks for SYNTHETIC fixtures only.
"""

from __future__ import annotations

import operator
from typing import Any, Dict, List, Optional

_OPS = {"eq": operator.eq, "lt": operator.lt, "gt": operator.gt, "le": operator.le, "ge": operator.ge}


def flatten(result: Dict[str, Any]) -> Dict[str, Optional[Any]]:
    lat = result.get("latency")
    flat: Dict[str, Optional[Any]] = {
        "delivery_completeness": result["delivery_completeness"],
        "loss_ratio": result["loss_ratio"],
        "duplicate_copies": result["counts"]["duplicate_copies"],
        "reorder_count": result["reorder"]["count"],
        "latency_p50_ms": lat["p50_ns"] / 1e6 if lat else None,
        "latency_p95_ms": lat["p95_ns"] / 1e6 if lat else None,
        "latency_p99_ms": lat["p99_ns"] / 1e6 if lat else None,
    }
    for w in result["fault_windows"]:
        flat[f"{w['name']}_recovered"] = w["recovered"]
        flat[f"{w['name']}_recovery_time_ms"] = None if w["recovery_time_ns"] is None else w["recovery_time_ns"] / 1e6
    return flat


def evaluate(result: Dict[str, Any], checks: Dict[str, Dict[str, Any]]) -> List[str]:
    """Return a list of failure messages (empty = all checks hold)."""
    flat = flatten(result)
    failures = []
    for key, cond in checks.items():
        (op, want), = cond.items()
        got = flat.get(key)
        if got is None:
            failures.append(f"{key}: value absent (null)")
        elif op not in _OPS:
            failures.append(f"{key}: unknown operator {op}")
        elif not _OPS[op](got, want):
            failures.append(f"{key}: {got!r} not {op} {want!r}")
    return failures
