"""Tests for scripts/check-markdown-links.py (offline; fixtures live in tmp_path)."""

from __future__ import annotations

import importlib.util
import subprocess
from pathlib import Path
from types import ModuleType

import pytest
from conftest import REPO, SCRIPTS, run_python, write

SCRIPT = SCRIPTS / "check-markdown-links.py"


def load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_markdown_links", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


checker = load_module()


def check(
    root: Path, *files: Path, known: Path | None = None
) -> subprocess.CompletedProcess[str]:
    known_path = known or root / "no-known-issues.txt"
    args = ["--root", str(root), "--known-issues", str(known_path)]
    args += [str(f) for f in files]
    return run_python(SCRIPT, *args)


@pytest.fixture()
def docs(tmp_path: Path) -> Path:
    write(tmp_path / "b.md", "# Target\n\n## Section One\n\ntext\n")
    write(
        tmp_path / "a.md",
        "# Source\n\n"
        "[ok file](b.md)\n"
        "[ok anchor](b.md#section-one)\n"
        "[ok same-file](#source)\n"
        "[ok dir](sub/)\n"
        "[external](https://example.invalid/never-fetched)\n"
        "[mail](mailto:nobody@example.invalid)\n",
    )
    (tmp_path / "sub").mkdir()
    write(tmp_path / "sub" / "README.md", "# Sub\n")
    return tmp_path


def test_clean_fixture_passes(docs: Path) -> None:
    result = check(docs, docs / "a.md", docs / "b.md")
    assert result.returncode == 0, result.stderr
    assert "0 broken" in result.stdout
    assert "Markdown link check passed." in result.stdout


def test_broken_file_link_fails(docs: Path) -> None:
    write(docs / "c.md", "[gone](missing.md)\n")
    result = check(docs, docs / "c.md")
    assert result.returncode == 1
    assert "c.md:1: broken link: 'missing.md' does not exist" in result.stderr


def test_broken_anchor_fails_with_line_number(docs: Path) -> None:
    write(docs / "c.md", "intro\n\n[bad](b.md#no-such-heading)\n")
    result = check(docs, docs / "c.md")
    assert result.returncode == 1
    assert "c.md:3: broken anchor: 'b.md#no-such-heading'" in result.stderr


def test_same_file_anchor_checked(docs: Path) -> None:
    write(docs / "c.md", "# Real\n\n[bad](#fake)\n")
    result = check(docs, docs / "c.md")
    assert result.returncode == 1
    assert (
        "broken anchor: '#fake' has no matching heading in this file" in result.stderr
    )


def test_links_in_fences_inline_code_and_comments_are_ignored(docs: Path) -> None:
    write(
        docs / "c.md",
        "```markdown\n[in fence](nope.md)\n```\n\n"
        "~~~\n[tilde fence](nope.md)\n~~~\n\n"
        "Use `[inline](nope.md)` as an example.\n\n"
        "<!-- [comment](nope.md) -->\n\n"
        "<!--\n[multi](nope.md)\n-->\n",
    )
    result = check(docs, docs / "c.md")
    assert result.returncode == 0, result.stderr


def test_reference_definitions_are_checked(docs: Path) -> None:
    write(docs / "c.md", "See [ref][r].\n\n[r]: does-not-exist.md\n")
    result = check(docs, docs / "c.md")
    assert result.returncode == 1
    assert "c.md:3: broken link" in result.stderr


def test_heading_slugs_and_duplicate_headings(tmp_path: Path) -> None:
    target = write(
        tmp_path / "t.md",
        '## Hello, World!\n\n## `Code` Title\n\n## Dup\n\n## Dup\n\n<a name="legacy-anchor"></a>\n',
    )
    assert checker.heading_slug("Hello, World!") == "hello-world"
    assert checker.heading_slug("`Code` Title") == "code-title"
    assert checker.heading_slug("Emoji 🚀 Launch") == "emoji--launch"
    anchors = checker.anchors_for(target)
    assert {"hello-world", "code-title", "dup", "dup-1", "legacy-anchor"} <= anchors


def test_known_issue_is_suppressed_and_counted(docs: Path) -> None:
    write(docs / "c.md", "[gone](missing.md)\n")
    known = write(docs / "known.txt", "# comment\nc.md:missing.md\n")
    result = check(docs, docs / "c.md", known=known)
    assert result.returncode == 0, result.stderr
    assert "1 known issue(s) skipped" in result.stdout


def test_stale_known_issue_warns_but_passes(docs: Path) -> None:
    write(docs / "c.md", "fine\n")
    known = write(docs / "known.txt", "c.md:already-fixed.md\n")
    result = check(docs, docs / "c.md", known=known)
    assert result.returncode == 0
    assert "stale known issue 'c.md:already-fixed.md'" in result.stderr


def test_missing_input_path_is_usage_error(docs: Path) -> None:
    result = check(docs, docs / "does-not-exist.md")
    assert result.returncode == 2
    assert "path not found" in result.stderr


def test_no_markdown_files_is_failure(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()
    result = run_python(
        SCRIPT,
        "--root",
        str(tmp_path),
        "--known-issues",
        str(tmp_path / "x.txt"),
        str(empty),
    )
    assert result.returncode == 1
    assert "No Markdown files found" in result.stderr


def test_repository_markdown_links_are_valid(repo_root: Path) -> None:
    """The real repo must pass its own link check (no network, uses the committed known-issues file)."""
    result = run_python(SCRIPT, "--root", str(REPO))
    assert result.returncode == 0, result.stderr + result.stdout


def test_angle_bracket_space_title_image_and_nested_parens(docs: Path) -> None:
    write(docs / "my file.md", "# My File\n")
    write(docs / "paren(s).md", "# Parens\n")
    write(
        docs / "c.md",
        "[spaced](<my file.md>)\n"
        '[titled](b.md "A title")\n'
        "[parens](paren(s).md)\n"
        "[case](b.md#SECTION-ONE)\n"
        "![missing image](images/nope.png)\n",
    )
    result = check(docs, docs / "c.md")
    assert result.returncode == 1
    assert "c.md:5: broken link: 'images/nope.png' does not exist" in result.stderr
    assert "c.md:1" not in result.stderr  # angle-bracket target with a space resolves
    assert "c.md:2" not in result.stderr  # title is not part of the target
    assert "c.md:3" not in result.stderr  # balanced parentheses in a path
    assert "c.md:4" not in result.stderr  # anchors compare case-insensitively
