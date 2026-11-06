#!/usr/bin/env python3
"""Run the model-serving fairness simulation and print / write a summary.

Examples (from the repository root):
  python3 experiments/model-serving-fairness/run_simulation.py
  python3 experiments/model-serving-fairness/run_simulation.py --seeds 1,2 \\
      --worker-down 0:30:50 --json-out out.json --markdown-out out.md

Everything produced is SIMULATED. Exit code 0 on success, 2 on invalid input.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from servesim.config import PLACEMENTS, SCHEDULERS, ConfigError  # noqa: E402
from servesim.report import render_markdown, run_matrix, to_json  # noqa: E402

DEFAULT_CONFIG = os.path.join(HERE, "data", "default_fleet.json")


def _csv(text: str) -> list:
    return [t.strip() for t in text.split(",") if t.strip()]


def _parse_down(spec: str) -> dict:
    try:
        w, s, e = spec.split(":")
        return {"worker": int(w), "start": float(s), "end": float(e)}
    except ValueError:
        raise ConfigError(f"--worker-down expects WORKER:START:END, got {spec!r}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", default=DEFAULT_CONFIG, help="scenario JSON (default: %(default)s)")
    ap.add_argument("--seeds", default="1,2,3", help="comma-separated integer seeds")
    ap.add_argument("--schedulers", default=",".join(SCHEDULERS))
    ap.add_argument("--placements", default=",".join(PLACEMENTS))
    ap.add_argument("--worker-down", action="append", default=[], metavar="W:START:END",
                    help="inject a worker-down window (repeatable)")
    ap.add_argument("--json-out", help="write the JSON report here ('-' for stdout)")
    ap.add_argument("--markdown-out", help="write the Markdown report here ('-' for stdout)")
    args = ap.parse_args(argv)

    try:
        with open(args.config, encoding="utf-8") as fh:
            raw = json.load(fh)
        seeds = [int(s) for s in _csv(args.seeds)]
        if not seeds:
            raise ConfigError("--seeds is empty")
        scheds, places = _csv(args.schedulers), _csv(args.placements)
        for s in scheds:
            if s not in SCHEDULERS:
                raise ConfigError(f"unknown scheduler {s!r}")
        for p in places:
            if p not in PLACEMENTS:
                raise ConfigError(f"unknown placement {p!r}")
        if not scheds or not places:
            raise ConfigError("--schedulers/--placements must not be empty")
        report = run_matrix(raw, seeds, scheds, places, [_parse_down(d) for d in args.worker_down])
    except (ConfigError, ValueError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    md, js = render_markdown(report), to_json(report)
    wrote = False
    for path, text in ((args.json_out, js), (args.markdown_out, md)):
        if path == "-":
            sys.stdout.write(text)
            wrote = True
        elif path:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            wrote = True
    if not wrote:
        sys.stdout.write(md)
    return 0


if __name__ == "__main__":
    sys.exit(main())
