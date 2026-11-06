"""Command line: validate the matrix, print recipes, generate fixtures, analyze traces.

No subcommand runs a live experiment, touches a network or talks to a cluster.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import List, Optional

from . import checks, matrix as mx, synth
from .metrics import analyze
from .seqprobe import load_seqprobe
from .trace import TraceError, load_trace

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(prog="ddsres", description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("validate-matrix", help="validate matrix/matrix.yaml")

    r = sub.add_parser("recipe", help="print the documented live-run recipe for a cell (NOT executed)")
    r.add_argument("cell")

    g = sub.add_parser("generate", help="write deterministic SYNTHETIC fixtures")
    g.add_argument("--out", default=os.path.join(HERE, "fixtures"))

    a = sub.add_parser("analyze", help="print metrics for trace files as JSON")
    a.add_argument("files", nargs="+")
    a.add_argument("--mixed-clock", choices=["error", "null"], default="error")

    s = sub.add_parser("analyze-seqprobe", help="analyze one run from examples/ros2-sequence-probe logs (publisher+subscriber, one file or two)")
    s.add_argument("logs", nargs="+")
    s.add_argument("--markers", help="optional JSONL of fault markers {name,t_ns,clock}")
    s.add_argument("--mixed-clock", choices=["error", "null"], default="error")

    c = sub.add_parser("check-fixtures", help="analyze every committed fixture and run its synthetic_checks")
    c.add_argument("--dir", default=os.path.join(HERE, "fixtures"))

    args = p.parse_args(argv)
    try:
        if args.cmd == "validate-matrix":
            m = mx.load_matrix()
            print(f"matrix OK: {len(m['cells'])} cells")
        elif args.cmd == "recipe":
            print(mx.recipe_text(mx.load_matrix(), args.cell))
        elif args.cmd == "generate":
            for path in synth.write_fixtures(mx.load_matrix(), args.out):
                print(path)
        elif args.cmd == "analyze":
            out = [analyze(load_trace(f), on_mixed_clock=args.mixed_clock) for f in args.files]
            print(json.dumps(out if len(out) > 1 else out[0], indent=2, sort_keys=True))
        elif args.cmd == "analyze-seqprobe":
            tr = load_seqprobe(args.logs, args.markers)
            print(json.dumps(analyze(tr, on_mixed_clock=args.mixed_clock), indent=2, sort_keys=True))
        elif args.cmd == "check-fixtures":
            m = mx.load_matrix()
            bad = 0
            for cell in m["cells"]:
                res = analyze(load_trace(os.path.join(args.dir, synth.fixture_name(cell))))
                fails = checks.evaluate(res, cell["synthetic_checks"])
                print(f"{'FAIL' if fails else 'ok  '} {cell['id']} {'; '.join(fails)}")
                bad += bool(fails)
            return 1 if bad else 0
    except (TraceError, mx.MatrixError, ValueError, OSError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    return 0
