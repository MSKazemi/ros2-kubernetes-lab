"""Command line: ``python3 -m seqprobe {analyze,simulate,plan} ...`` (no ROS needed).

Exit codes: 0 ok, 1 verdict not ok, 2 bad input / usage.
"""

import argparse
import json
import sys

from .errors import SeqProbeError


def _ints(text):
    try:
        return [int(x) for x in text.split(",") if x.strip()]
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected comma-separated integers, got {text!r}") from None


def _cmd_analyze(args):
    from .analysis import analyze_events, all_ok
    from .events import read_events

    with open(args.log, encoding="utf-8") as fh:
        events = read_events(fh)
    result = analyze_events(events, expected_count=args.expected_count)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if all_ok(result) else 1


def _cmd_simulate(args):
    from .synthetic import simulate

    events, verdict = simulate(run_id=args.run_id, count=args.count, rate_hz=args.rate_hz,
                               payload_bytes=args.payload_bytes, seed=args.seed, clock=args.clock,
                               drop=args.drop, duplicate=args.duplicate, swap=args.swap,
                               expect_count=not args.unknown_count)
    out = sys.stdout if args.out == "-" else open(args.out, "w", encoding="utf-8")
    try:
        for ev in events:
            out.write(ev.to_json_line() + "\n")
    finally:
        if out is not sys.stdout:
            out.close()
    print(f"SYNTHETIC log: {len(events)} events, completion={verdict.completion}, ok={verdict.ok}",
          file=sys.stderr)
    return 0


def _cmd_plan(args):
    from .config import GeneratorConfig
    from .generator import plan

    cfg = GeneratorConfig(run_id=args.run_id, count=args.count, rate_hz=args.rate_hz,
                          payload_bytes=args.payload_bytes, seed=args.seed, clock=args.clock)
    for m in plan(cfg):
        print(json.dumps({"seq": m.seq, "offset_ns": m.offset_ns}))
    return 0


def build_parser():
    p = argparse.ArgumentParser(prog="python3 -m seqprobe", description=__doc__.splitlines()[0])
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("analyze", help="verdict for each subscriber stream in a JSON-lines log")
    a.add_argument("log")
    a.add_argument("--expected-count", type=int, default=None)
    a.set_defaults(func=_cmd_analyze)

    def gen_args(sp):
        sp.add_argument("--run-id", default="synthetic")
        sp.add_argument("--count", type=int, default=10)
        sp.add_argument("--rate-hz", type=float, default=10.0)
        sp.add_argument("--payload-bytes", type=int, default=64)
        sp.add_argument("--seed", type=int, default=0)
        sp.add_argument("--clock", default="wall", choices=["monotonic", "wall", "ros"])

    s = sub.add_parser("simulate", help="write a SYNTHETIC log with injected faults (fixtures)")
    gen_args(s)
    s.add_argument("--drop", type=_ints, default=[], help="comma-separated seqs never delivered")
    s.add_argument("--duplicate", type=_ints, default=[], help="seqs delivered twice")
    s.add_argument("--swap", type=_ints, default=[], help="seqs delivered after seq+1")
    s.add_argument("--unknown-count", action="store_true", help="subscriber does not know the count")
    s.add_argument("--out", default="-")
    s.set_defaults(func=_cmd_simulate)

    pl = sub.add_parser("plan", help="print the deterministic send schedule")
    gen_args(pl)
    pl.set_defaults(func=_cmd_plan)
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except (SeqProbeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
