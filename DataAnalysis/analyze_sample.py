#!/usr/bin/env python3
"""Offline summary of one committed Prometheus sample (standard library only).

Reads ONE file from DataAnalysis/dataset/ (no network, no cluster, no Prometheus)
and writes a deterministic per-series summary CSV.

Usage (from anywhere):
    python3 DataAnalysis/analyze_sample.py --list
    python3 DataAnalysis/analyze_sample.py --out-dir DataAnalysis/output
    python3 DataAnalysis/analyze_sample.py --sample container_memory_usage_bytes_pod --out-dir /tmp/x

Semantics (see DataAnalysis/dataset/README.md for the data dictionary):
  * The committed files hold the result of *PromQL queries*, not raw cAdvisor
    counters. CPU values are already a 1-minute rate in CPU cores
    (CPU-seconds per second), network values are bytes per second, memory is a
    byte gauge. This tool therefore reports the unit of every file and NEVER
    converts CPU values to a "percent utilization": the number of cores the
    series could use (node size, CPU limits) is not recorded in the data.
  * Nothing is smoothed, interpolated, resampled or summed across series.
    Gaps (consecutive samples more than MAX_STEP_S apart) are only counted.
  * counter_to_rate() is provided (and tested) for readers who pull RAW
    cumulative counters; none of the committed files needs it.

Provenance/limits: single recording of 2024-04-20 from the historical Foxy-era
lab cluster. This is sample data, not a benchmark.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DATASET_DIR = Path(__file__).resolve().parent / "dataset"
DEFAULT_OUT_DIR = Path(__file__).resolve().parent / "output"  # ignored by version control
DEFAULT_SAMPLE ="container_cpu_usage_seconds_total"
MAX_STEP_S = 120  # nominal step is 60 s; a larger distance counts as a gap

# file stem (without a trailing "_pod") -> (kind, unit). Inferred from the
# notebook queries; the files themselves do not record their query.
METRICS = {
    "container_cpu_usage_seconds_total": ("rate", "CPU cores (1-min rate of CPU seconds)"),
    "container_memory_usage_bytes": ("gauge", "bytes (gauge)"),
    "container_network_receive_bytes_total": ("rate", "bytes per second (1-min rate)"),
    "container_network_transmit_bytes_total": ("rate", "bytes per second (1-min rate)"),
    "container_fs_usage_bytes": ("gauge", "bytes (gauge)"),
}

CSV_COLUMNS = [
    "sample", "namespace", "pod", "unit", "n_samples", "n_unparsable",
    "first_utc", "last_utc", "min", "max", "mean", "n_gaps", "longest_gap_s",
]


class SampleError(ValueError):
    """The input does not have the documented {namespace: [series]} layout."""


def list_samples(dataset_dir: Path) -> list[str]:
    return sorted(p.stem for p in dataset_dir.glob("*.json"))


def metric_info(sample: str) -> tuple[str, str]:
    stem = sample[:-4] if sample.endswith("_pod") else sample
    if stem not in METRICS:
        raise SampleError(f"unknown metric for sample {sample!r}; known: {sorted(METRICS)}")
    return METRICS[stem]


def resolve_sample(dataset_dir: Path, sample: str) -> Path:
    """Map a sample NAME to a file inside dataset_dir (local files only)."""
    if "/" in sample or "\\" in sample or "://" in sample or sample.startswith("."):
        raise SampleError("--sample takes a file stem such as 'container_cpu_usage_seconds_total'")
    path = dataset_dir / f"{sample}.json"
    if not path.is_file():
        raise SampleError(f"{path} not found; use --list to see the available samples")
    return path


def load_sample(path: Path) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    if not isinstance(data, dict):
        raise SampleError(f"{path.name}: top level must be an object keyed by namespace")
    for namespace, series_list in data.items():
        if not isinstance(series_list, list):
            raise SampleError(f"{path.name}: namespace {namespace!r} must map to a list of series")
        for series in series_list:
            if not isinstance(series, dict) or "values" not in series:
                raise SampleError(f"{path.name}: a series in {namespace!r} has no 'values'")
    return data


def parse_values(values) -> tuple[list[tuple[int, float]], int]:
    """Return ([(epoch_s, float)], n_unparsable). Timestamps are ints; values are strings.

    Prometheus can emit "NaN"/"+Inf"; such points are dropped and counted, never
    silently kept (they would poison min/max/mean).
    """
    points, bad = [], 0
    for item in values:
        try:
            ts, raw = item
            ts = int(ts)
            val = float(raw)
        except (TypeError, ValueError):
            bad += 1
            continue
        if not math.isfinite(val):
            bad += 1
            continue
        points.append((ts, val))
    return points, bad


def gap_stats(timestamps: list[int], max_step: int = MAX_STEP_S) -> tuple[int, int]:
    """(number of gaps, longest gap in seconds) over consecutive sorted timestamps."""
    n_gaps, longest = 0, 0
    for prev, cur in zip(timestamps, timestamps[1:]):
        step = cur - prev
        if step > max_step:
            n_gaps += 1
        longest = max(longest, step)
    return n_gaps, (longest if n_gaps else 0)


def counter_to_rate(points: list[tuple[int, float]]) -> list[tuple[int, float]]:
    """Per-second rate from RAW cumulative counter samples [(epoch_s, counter)].

    Output has one point per interval, stamped at the interval end. A decrease
    is treated as a counter reset (the new value counts as the increase since the
    reset, as Prometheus rate() does); an interval with dt <= 0 is skipped.
    """
    rates = []
    for (t0, v0), (t1, v1) in zip(points, points[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        inc = v1 - v0 if v1 >= v0 else v1
        rates.append((t1, inc / dt))
    return rates


def looks_like_raw_counter(points: list[tuple[int, float]], min_points: int = 10) -> bool:
    """Heuristic: a long, strictly growing series is probably a cumulative counter."""
    if len(points) < min_points:
        return False
    vals = [v for _, v in points]
    return all(b >= a for a, b in zip(vals, vals[1:])) and vals[-1] > vals[0] and vals[0] > 0


def _utc(ts: int) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _fmt(x: float) -> str:
    return f"{x:.9g}"


def summarize(sample: str, data: dict) -> tuple[list[dict], list[str]]:
    """Build summary rows (sorted input order is preserved) and warnings."""
    kind, unit = metric_info(sample)
    rows, warnings = [], []
    for namespace, series_list in data.items():
        if not series_list:  # empty list = no data for this namespace
            rows.append({"sample": sample, "namespace": namespace, "pod": "", "unit": unit,
                         "n_samples": 0, "n_unparsable": 0, "first_utc": "", "last_utc": "",
                         "min": "", "max": "", "mean": "", "n_gaps": 0, "longest_gap_s": 0})
            continue
        for series in series_list:
            labels = series.get("metric") or {}
            pod = labels.get("pod", "")  # '' when the label is absent (namespace-level files)
            points, bad = parse_values(series["values"])
            points.sort()
            if kind == "rate" and looks_like_raw_counter(points):
                warnings.append(
                    f"{namespace}/{pod or '<sum>'}: values look like a raw cumulative counter, "
                    "but this file is documented as a rate; check the source before reading it "
                    "as cores or bytes/s (see counter_to_rate)")
            row = {"sample": sample, "namespace": namespace, "pod": pod, "unit": unit,
                   "n_samples": len(points), "n_unparsable": bad}
            if points:
                vals = [v for _, v in points]
                n_gaps, longest = gap_stats([t for t, _ in points])
                row.update(first_utc=_utc(points[0][0]), last_utc=_utc(points[-1][0]),
                           min=_fmt(min(vals)), max=_fmt(max(vals)),
                           mean=_fmt(math.fsum(vals) / len(vals)),
                           n_gaps=n_gaps, longest_gap_s=longest)
            else:
                row.update(first_utc="", last_utc="", min="", max="", mean="",
                           n_gaps=0, longest_gap_s=0)
            rows.append(row)
    return rows, warnings


PROVENANCE = """\
Provenance and limitations of the files in this folder (read before quoting any number)

- Source: JSON samples committed in DataAnalysis/dataset/, exported from the Prometheus
  server of the historical Vagrant/Foxy-era lab cluster on 2024-04-20 (UTC). This is a
  single recording, not a benchmark, and says nothing about the Jazzy image in ROS2/.
- Values are PromQL query results (1-minute rates or byte gauges), not raw counters; the
  unit column of each CSV says which. CPU values are cores, never a percentage.
- Unknown/unverified (not recorded in the data): the workload, cluster size, software
  versions, exact scrape interval, the cause of the ~1.5 h recording gap, and whether the
  memory query double-counts pod-level series.
- Nothing was smoothed, interpolated, resampled or summed; gaps are counted, not filled.
- Details: DataAnalysis/dataset/README.md
"""


def write_provenance(out_dir: Path) -> Path:
    path = out_dir / "PROVENANCE.txt"
    path.write_text(PROVENANCE, encoding="utf-8")
    return path


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_COLUMNS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sample", default=DEFAULT_SAMPLE,
                        help=f"dataset file stem (default: {DEFAULT_SAMPLE})")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR,
                        help="folder with the sample JSON files (default: the committed dataset/)")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR,
                        help="output folder (default: DataAnalysis/output, not tracked)")
    parser.add_argument("--list", action="store_true", help="list available samples and exit")
    args = parser.parse_args(argv)

    try:
        if args.list:
            for name in list_samples(args.dataset_dir):
                print(name)
            return 0
        path = resolve_sample(args.dataset_dir, args.sample)
        rows, warnings = summarize(args.sample, load_sample(path))
    except (SampleError, json.JSONDecodeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    for message in warnings:
        print(f"warning: {message}", file=sys.stderr)
    out = args.out_dir / f"{args.sample}_summary.csv"
    write_csv(rows, out)
    write_provenance(args.out_dir)
    print(f"read {path.name} (local file only); wrote {out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
