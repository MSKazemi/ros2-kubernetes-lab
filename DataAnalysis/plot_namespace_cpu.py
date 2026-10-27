#!/usr/bin/env python3
"""Plot the committed per-namespace CPU series from DataAnalysis/dataset/.

Input : DataAnalysis/dataset/container_cpu_usage_seconds_total.json
        (one series per namespace; values are CPU cores, i.e. the 1-minute rate
        of container_cpu_usage_seconds_total summed over the namespace).
Output: a PNG at the path given by --out (default: ./namespace_cpu.png).

Nothing is aggregated, smoothed or interpolated beyond what is in the file. The
line is *broken* wherever two consecutive samples are more than 2 minutes apart,
so the ~1.5 h hole in the recording is visible instead of being drawn over.

Requires matplotlib (not part of the Python standard library):
    python3 -m venv .venv && .venv/bin/pip install matplotlib
Run from anywhere:
    python3 DataAnalysis/plot_namespace_cpu.py --out /tmp/namespace_cpu.png
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # no display needed
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

DATASET = Path(__file__).resolve().parent / "dataset" / "container_cpu_usage_seconds_total.json"
MAX_STEP_S = 120  # break the line when consecutive samples are further apart than this


def load_points(series):
    """Return (datetime_utc, float) pairs, with None inserted at gaps."""
    xs, ys = [], []
    prev = None
    for ts, raw in series["values"]:
        if prev is not None and ts - prev > MAX_STEP_S:
            xs.append(datetime.fromtimestamp(prev + 1, timezone.utc))
            ys.append(None)  # None makes matplotlib break the line here
        xs.append(datetime.fromtimestamp(ts, timezone.utc))
        ys.append(float(raw))  # values are strings in the file
        prev = ts
    return xs, ys


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", default="namespace_cpu.png", help="output PNG path")
    args = parser.parse_args()

    with open(DATASET, encoding="utf-8") as fh:
        data = json.load(fh)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for namespace, series_list in data.items():
        if not series_list:  # kube-node-lease and kube-public are empty
            continue
        if namespace == "default":  # only 5 samples (~4 min); skip to keep the plot readable
            continue
        xs, ys = load_points(series_list[0])
        ax.plot(xs, ys, linewidth=1, label=namespace)

    ax.set_title("Namespace CPU usage, sample data of 2024-04-20 (UTC)")
    ax.set_xlabel("time (UTC)")
    ax.set_ylabel("CPU cores (1-min rate, summed per namespace)")
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    ax.grid(alpha=0.3)
    ax.legend(title="namespace")
    fig.tight_layout()
    fig.savefig(args.out, dpi=120)
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
