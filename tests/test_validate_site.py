"""Tests for scripts/validate-site.py against a temporary copy of site/.

The real site/ tree is copied, so every mutation below stays inside tmp_path.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from conftest import REPO, run_python, write

VALIDATOR = REPO / "scripts" / "validate-site.py"


@pytest.fixture()
def site_copy(tmp_path: Path) -> Path:
    root = tmp_path / "copy"
    (root / "scripts").mkdir(parents=True)
    shutil.copy2(VALIDATOR, root / "scripts" / "validate-site.py")
    shutil.copytree(REPO / "site", root / "site")
    return root


def validate(root: Path) -> subprocess.CompletedProcess[str]:
    return run_python(root / "scripts" / "validate-site.py", cwd=root)


def test_unmodified_copy_passes(site_copy: Path) -> None:
    result = validate(site_copy)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Static website validation passed" in result.stdout


def test_deliberately_broken_page_is_reported(site_copy: Path) -> None:
    write(
        site_copy / "site" / "docs" / "broken-test.html",
        "<!doctype html><html><head><title>Broken</title></head><body>"
        '<main id="main"><h2>No H1</h2>'
        '<a href="does-not-exist.html">dead link</a>'
        '<a href="index.html#no-such-fragment">dead fragment</a>'
        '<img src="assets/logo-mark.svg">'
        '<script type="application/ld+json">{not json</script>'
        "</main></body></html>\n",
    )
    result = validate(site_copy)
    assert result.returncode == 1
    out = result.stdout
    assert "Static website validation failed" in out
    assert "docs/broken-test.html: missing linked target: does-not-exist.html" in out
    assert "expected exactly one H1, got 0" in out
    assert "images without alt" in out
    assert "invalid JSON-LD block 1" in out
    assert "inner page needs BreadcrumbList JSON-LD" in out


@pytest.mark.parametrize(
    ("relative", "old", "new", "expected"),
    [
        (
            "index.html",
            "</body>",
            '<a href="missing-asset.css">x</a></body>',
            "missing linked target: missing-asset.css",
        ),
        (
            "index.html",
            "</body>",
            '<a href="index.html#nope-nope">x</a></body>',
            "broken fragment index.html#nope-nope",
        ),
        (
            "index.html",
            "</body>",
            '<div id="dup-x"></div><div id="dup-x"></div></body>',
            "duplicate ids",
        ),
        (
            "index.html",
            "</body>",
            '<a href="https://example.com/">ok</a></body>',
            None,
        ),  # external links are not fetched: must still pass
        (
            "index.html",
            "</body>",
            '<a href="../../outside.html">x</a></body>',
            "link exits published site",
        ),
    ],
)
def test_link_and_id_mutations(
    site_copy: Path, relative: str, old: str, new: str, expected: str | None
) -> None:
    path = site_copy / "site" / relative
    text = path.read_text(encoding="utf-8")
    assert text.count(old) == 1, "fixture anchor must be unique"
    path.write_text(text.replace(old, new), encoding="utf-8")
    result = validate(site_copy)
    if expected is None:
        assert result.returncode == 0, result.stdout
    else:
        assert result.returncode == 1
        assert expected in result.stdout


def test_sitemap_mismatch_is_reported(site_copy: Path) -> None:
    sitemap = site_copy / "site" / "sitemap.xml"
    text = sitemap.read_text(encoding="utf-8")
    sitemap.write_text(
        text.replace(
            "</urlset>", "<url><loc>https://example.invalid/extra/</loc></url></urlset>"
        ),
        encoding="utf-8",
    )
    result = validate(site_copy)
    assert result.returncode == 1
    assert "Sitemap mismatch" in result.stdout


def test_verified_scenario_without_evidence_is_rejected(site_copy: Path) -> None:
    registry = site_copy / "site" / "scenarios" / "data" / "experiments.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["experiments"][0]["status"] = "verified"
    registry.write_text(json.dumps(data), encoding="utf-8")
    result = validate(site_copy)
    assert result.returncode == 1
    assert "verified result must be a finite number" in result.stdout
    assert "missing immutable run_manifest_sha256" in result.stdout


def test_unverified_scenario_with_result_is_rejected(site_copy: Path) -> None:
    registry = site_copy / "site" / "scenarios" / "data" / "experiments.json"
    data = json.loads(registry.read_text(encoding="utf-8"))
    data["experiments"][0]["result"] = 0.9
    registry.write_text(json.dumps(data), encoding="utf-8")
    result = validate(site_copy)
    assert result.returncode == 1
    assert "unverified status must keep result null" in result.stdout
