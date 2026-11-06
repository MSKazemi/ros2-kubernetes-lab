"""Load and validate the scenario matrix (matrix/matrix.yaml)."""

from __future__ import annotations

import itertools
import os
from typing import Any, Dict

import yaml  # PyYAML; the only third-party dependency of this harness

DEFAULT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "matrix", "matrix.yaml")


class MatrixError(ValueError):
    pass


def load_matrix(path: str = DEFAULT_PATH) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        m = yaml.safe_load(fh)
    validate_matrix(m)
    return m


def validate_matrix(m: Dict[str, Any]) -> None:
    if not isinstance(m, dict) or m.get("schema") != "rrl.matrix/1":
        raise MatrixError("matrix schema must be rrl.matrix/1")
    axes = m.get("axes", {})
    rel, imp = axes.get("reliability"), axes.get("impairment")
    if not rel or not imp:
        raise MatrixError("axes.reliability and axes.impairment are required")
    expected = {f"{r}__{i}" for r, i in itertools.product(rel, imp)}
    cells = m.get("cells", [])
    ids = [c.get("id") for c in cells]
    if len(ids) != len(set(ids)):
        raise MatrixError("duplicate cell ids")
    if set(ids) != expected:
        raise MatrixError(f"cells do not cover the full cross product; missing={sorted(expected - set(ids))} extra={sorted(set(ids) - expected)}")
    seeds = [c.get("seed") for c in cells]
    if any(not isinstance(s, int) or isinstance(s, bool) for s in seeds) or len(set(seeds)) != len(seeds):
        raise MatrixError("every cell needs a distinct integer seed")
    for c in cells:
        if c["id"] != f"{c.get('reliability')}__{c.get('impairment')}":
            raise MatrixError(f"cell id {c['id']} does not match its axes")
        if not str(c.get("hypothesis", "")).strip():
            raise MatrixError(f"cell {c['id']} has no hypothesis")
        if not c.get("synthetic_checks"):
            raise MatrixError(f"cell {c['id']} has no synthetic_checks")
    if set(m.get("impairments", {})) != set(imp):
        raise MatrixError("impairments parameters must cover exactly the impairment axis")
    common = m.get("live_recipe_common", {})
    if common.get("status") != "NOT RUN" or "safe local context" not in str(common.get("requires", "")):
        raise MatrixError("live_recipe_common must be flagged 'NOT RUN' and require an explicit safe local context")
    if set(m.get("live_recipe", {})) != set(imp):
        raise MatrixError("live_recipe must cover every impairment")
    for r in rel:
        if r not in m.get("synthetic_model", {}):
            raise MatrixError(f"synthetic_model lacks reliability {r}")


def cell_ids(m: Dict[str, Any]):
    return [c["id"] for c in m["cells"]]


def recipe_text(m: Dict[str, Any], cell_id: str) -> str:
    """Return the documented live-run recipe for a cell as text. Never executes anything."""
    cell = next((c for c in m["cells"] if c["id"] == cell_id), None)
    if cell is None:
        raise MatrixError(f"unknown cell {cell_id}")
    common, rec = m["live_recipe_common"], m["live_recipe"][cell["impairment"]]
    lines = [
        f"CELL {cell_id}   [{common['status']}]",
        f"requires: {' '.join(str(common['requires']).split())}",
        f"hypothesis: {cell['hypothesis']}",
        f"impairment parameters: {m['impairments'][cell['impairment']]}",
        "steps:",
    ]
    lines += [f"  {i}. {s}" for i, s in enumerate(common["steps"], 1)]
    lines.append("impairment commands (documented only):")
    lines += [f"  $ {c}" for c in rec["commands"]] or ["  (none)"]
    lines.append(f"cleanup: {common['cleanup']}")
    return "\n".join(lines)
