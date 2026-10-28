#!/usr/bin/env python3
"""Offline consistency checks for the proposed Hugging Face robotics model catalog.

No network access, model downloads, GPU jobs or credentials required.
This checks source files and planning claims, not actual runtime compatibility.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "integrations/huggingface/model-catalog.json"
SITE = ROOT / "site/scenarios/hugging-face-models.html"
SPACE = ROOT / "integrations/huggingface/spaces/robotics-model-research/index.html"
COMMIT = re.compile(r"^[0-9a-f]{40}$")
REPO_ID = re.compile(r"^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$")


def validate(doc: object, website: str, space: str) -> list[str]:
    """Return human-readable errors; require honest planning-only metadata."""
    errors: list[str] = []
    if not isinstance(doc, dict):
        return ["Catalog root must be an object"]
    if doc.get("schema_version") != "hf-robotics-catalog-v1":
        errors.append("Unexpected schema_version")
    if doc.get("catalog_status") != "research-shortlist":
        errors.append("Catalog status must be research-shortlist")
    entries = doc.get("models")
    if not isinstance(entries, list) or len(entries) < 5:
        return errors + ["models must be a list of >=5 entries"]
    seen: set[str] = set()
    for index, item in enumerate(entries):
        if not isinstance(item, dict):
            errors.append(f"models[{index}] is not an object")
            continue
        ident = item.get("repo_id")
        if not isinstance(ident, str) or not REPO_ID.fullmatch(ident):
            errors.append(f"models[{index}] has an invalid repo_id")
            continue
        if ident in seen:
            errors.append(f"Duplicate repo_id: {ident}")
        seen.add(ident)
        if item.get("family") not in {"policy", "perception"}:
            errors.append(f"{ident}: invalid family")
        if not all(isinstance(item.get(key), str) and item[key].strip()
                   for key in ("role", "track")):
            errors.append(f"{ident}: missing role or track")
        for key in ("revision", "processor_revision"):
            rev = item.get(key)
            if rev is not None and (not isinstance(rev, str) or not COMMIT.fullmatch(rev)):
                errors.append(f"{ident}: {key} must be null or an immutable 40-char commit")
        if item.get("experiment_status") != "planned":
            errors.append(f"{ident}: unverified catalog may only contain planned records")
        if item.get("result") is not None or item.get("run_count") != 0:
            errors.append(f"{ident}: planned model cannot report a result or run count")
        href = 'href="https://huggingface.co/' + ident + '"'
        if href not in website:
            errors.append(f"{ident}: model link absent from website")
        if href not in space:
            errors.append(f"{ident}: model link absent from Space starter")
    if website.count('class="hf-card"') != len(entries):
        errors.append("Website model card count diverges from catalog")
    if space.count('class="card" data-type=') != len(entries):
        errors.append("Space model card count diverges from catalog")
    return errors


def self_test(doc: dict, website: str, space: str) -> list[str]:
    """Cheap mutation tests verifying that corrupt public metadata fails."""
    failures: list[str] = []
    if validate(doc, website, space):
        return ["Positive fixture failed before negative tests"]
    cases: dict[str, dict] = {}
    mutated = deepcopy(doc)
    mutated["models"][1]["repo_id"] = mutated["models"][0]["repo_id"]
    cases["duplicate"] = mutated
    mutated = deepcopy(doc)
    mutated["models"][0]["result"] = 0.98
    cases["fake result"] = mutated
    mutated = deepcopy(doc)
    mutated["models"][0]["revision"] = "main"
    cases["mutable revision"] = mutated
    mutated = deepcopy(doc)
    mutated["models"][0]["family"] = "actuator"
    cases["invalid family"] = mutated
    mutated = deepcopy(doc)
    mutated["models"].pop()
    cases["missing model card"] = mutated
    for name, candidate in cases.items():
        if not validate(candidate, website, space):
            failures.append(f"Negative test incorrectly accepted: {name}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true",
                        help="also run five negative mutation tests")
    args = parser.parse_args()
    try:
        doc = json.loads(MANIFEST.read_text(encoding="utf-8"))
        website = SITE.read_text(encoding="utf-8")
        space = SPACE.read_text(encoding="utf-8")
    except (OSError, ValueError) as error:
        print(f"Catalog read/parse failure: {error}")
        return 1
    errors = validate(doc, website, space)
    if not errors and args.self_test:
        errors.extend(self_test(doc, website, space))
    if errors:
        for error in errors:
            print("ERROR:", error)
        return 1
    print(f"HF catalog validation passed: {len(doc['models'])} linked, planned models.")
    if args.self_test:
        print("Five offline negative mutation tests passed.")
    print("No runtime model, HF access or GPU compatibility validated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
