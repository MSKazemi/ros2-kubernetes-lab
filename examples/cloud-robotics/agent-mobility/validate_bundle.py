#!/usr/bin/env python3
"""Validate SYNTHETIC ``bundle-check`` fixtures with the mission-state/v1 validator.

    python3 validate_bundle.py                       # every fixture in fixtures/bundles/
    python3 validate_bundle.py fixtures/bundles/stale-epoch.json

Exit codes: 0 every verdict matched its fixture's expectation, 1 at least one mismatch,
2 unreadable or structurally invalid fixture file. Output is one JSON object per fixture.
Non-actuating: reads files, prints verdicts, nothing else.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import mission_state as ms
from mission_state import Rejection

HERE = Path(__file__).resolve().parent
BUNDLE_DIR = HERE / "fixtures" / "bundles"
KIND = "bundle-check"


def check_fixture(fixture: dict[str, Any]) -> dict[str, Any]:
    """Run one bundle-check fixture. Raises ValueError if the fixture file itself is invalid."""
    if not isinstance(fixture, dict):
        raise ValueError("fixture must be a JSON object")
    if (fixture.get("fixture_kind") != KIND or fixture.get("synthetic") is not True
            or set(fixture) != {"fixture_kind", "synthetic", "name", "description", "expect", "context", "bundle"}):
        raise ValueError("not a synthetic bundle-check fixture")
    try:
        ctx = ms.CommitContext.from_json(fixture["context"])
    except Rejection as exc:
        raise ValueError(f"fixture context invalid: {exc}") from exc
    except (KeyError, TypeError) as exc:
        raise ValueError(f"fixture context invalid: {exc!r}") from exc
    try:
        ms.validate_for_commit(fixture["bundle"], ctx)
        ok, reason, field_name = True, None, ""
    except Rejection as exc:
        ok, reason, field_name = False, exc.reason, exc.field
    want = fixture["expect"]
    return {"name": fixture["name"], "simulation": True, "synthetic": True, "accepted": ok,
            "reason": reason, "field": field_name, "expected": want,
            "matches": want == {"ok": ok, "reason": reason}}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("fixtures", nargs="*", type=Path)
    args = parser.parse_args(argv)
    paths = args.fixtures or sorted(BUNDLE_DIR.glob("*.json"))
    reports = []
    try:
        for path in paths:
            reports.append(check_fixture(json.loads(path.read_text(encoding="utf-8"))))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(f"validate_bundle: invalid input: {exc}", file=sys.stderr)
        return 2
    for rep in reports:
        print(json.dumps(rep, sort_keys=True))
    return 0 if all(r["matches"] for r in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
