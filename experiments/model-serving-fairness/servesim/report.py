"""Batch runner logic and deterministic JSON / Markdown rendering."""

from __future__ import annotations

import copy
import json
from typing import Dict, List, Sequence

from .config import parse_config
from .engine import simulate
from .metrics import LABEL, summarize

DISCLAIMER = (
    "SIMULATED results from a CPU-only discrete-event model. No GPU, no real model "
    "latency; service times, load costs, cache sizes and arrival rates are assumed "
    "parameters. These are illustrations, not benchmarks."
)
SCHEMA_VERSION = 1


def run_matrix(raw_config: Dict, seeds: Sequence[int], schedulers: Sequence[str],
               placements: Sequence[str], extra_failures: Sequence[Dict] = ()) -> Dict:
    """Run every (seed, scheduler, placement) combination and return the report dict."""
    base = copy.deepcopy(raw_config)
    if extra_failures:
        base["failures"] = list(base.get("failures", [])) + list(extra_failures)
    parse_config(base)                      # fail early on a bad base config
    runs: List[Dict] = []
    for seed in seeds:
        for sched in schedulers:
            for place in placements:
                raw = copy.deepcopy(base)
                raw.update({"seed": seed, "scheduler": sched, "placement": place})
                runs.append(summarize(simulate(parse_config(raw))))
    return {
        "label": LABEL,
        "schema_version": SCHEMA_VERSION,
        "disclaimer": DISCLAIMER,
        "scenario": base.get("name", "unnamed"),
        "seeds": list(seeds),
        "schedulers": list(schedulers),
        "placements": list(placements),
        "config": base,
        "runs": runs,
    }


def to_json(report: Dict) -> str:
    return json.dumps(report, indent=2, sort_keys=True) + "\n"


def _f(x, nd=3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def _pct(x) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def render_markdown(report: Dict) -> str:
    out: List[str] = []
    out.append(f"# Model-serving fairness simulation ({report['label']})")
    out.append("")
    out.append(f"> {report['disclaimer']}")
    out.append("")
    out.append(f"Scenario: `{report['scenario']}` | seeds: {report['seeds']} | "
               f"schedulers: {report['schedulers']} | placements: {report['placements']}")
    fails = report["runs"][0]["worker_failures"] if report["runs"] else []
    out.append(f"Worker failure windows: {fails if fails else 'none'}")
    out.append("")
    out.append("## Summary (all values SIMULATED)")
    out.append("")
    out.append("| seed | scheduler | placement | miss rate | quiet-client miss | goodput | "
               "p50 s | p95 s | p99 s | Jain | cache hit | rejected | dropped | starved req |")
    out.append("|---:|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for r in report["runs"]:
        lat = r["latency_s"]
        out.append(
            f"| {r['seed']} | {r['scheduler']} | {r['placement']} | {_pct(r['deadline_miss_rate'])} | "
            f"{_pct(r['quiet_clients_deadline_miss_rate'])} | {_pct(r['goodput_rate'])} | "
            f"{_f(lat['p50'])} | {_f(lat['p95'])} | {_f(lat['p99'])} | "
            f"{_f(r['jain_goodput_index'])} | {_pct(r['cache']['hit_rate'])} | "
            f"{r['totals']['rejected']} | {r['totals']['dropped']} | {r['starved_requests']} |")
    out.append("")
    if report["runs"]:
        first_seed = report["seeds"][0]
        out.append(f"## Per-client detail, seed {first_seed}, placement "
                   f"`{report['placements'][0]}` (SIMULATED)")
        out.append("")
        out.append("| scheduler | client | arrivals | completed | miss rate | goodput | "
                   "p95 s | max wait s | starved req |")
        out.append("|---|---|---:|---:|---:|---:|---:|---:|---:|")
        for r in report["runs"]:
            if r["seed"] != first_seed or r["placement"] != report["placements"][0]:
                continue
            for cid in sorted(r["clients"]):
                c = r["clients"][cid]
                out.append(
                    f"| {r['scheduler']} | {cid} | {c['arrivals']} | {c['completed']} | "
                    f"{_pct(c['deadline_miss_rate'])} | {_pct(c['goodput_ratio'])} | "
                    f"{_f(c['latency_s']['p95'])} | {_f(c['max_queue_wait_s'])} | "
                    f"{c['starved_requests']} |")
        out.append("")
    out.append("Percentiles are nearest-rank over completed requests (latency = queueing + "
               "model load + service). Jain index is over per-client on-time/arrivals ratios.")
    out.append("")
    return "\n".join(out)
