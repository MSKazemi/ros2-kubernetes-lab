#!/usr/bin/env python3
"""Check LOCAL links in tracked Markdown files (no network access, stdlib only).

For every inline link/image `[text](target)` and reference definition
`[label]: target` outside fenced code blocks and inline code spans, verify that:

  * a relative file or directory target exists (directory links are valid);
  * a `#fragment` matches a GitHub-style heading slug (or an explicit
    `<a name=...>` / `id=...` anchor) in the target Markdown file.

http(s), mailto, tel and other URL schemes are ignored on purpose; external
URLs are not fetched. Failures are printed as `path:line: message` and the
exit status is 1 if any are found.

Documented in-flight problems can be listed in
scripts/markdown-links-known-issues.txt (one `path:target` per line, `#`
comments). A known issue that is no longer broken is reported as a warning.
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

SKIP_DIRS = {".git", ".claude", "node_modules"}
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})")
REF_DEF_RE = re.compile(r"^ {0,3}\[(?!\^)((?:[^\]\\]|\\.)+)\]:\s*(<[^>]*>|\S+)")
CODE_SPAN_RE = re.compile(r"(?<!`)(`+)(?!`)(.+?)(?<!`)\1(?!`)")
ATX_RE = re.compile(r"^ {0,3}#{1,6}[ \t]+(.*?)(?:[ \t]+#+)?[ \t]*$")
SETEXT_RE = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
HTML_ANCHOR_RE = re.compile(r"""<[a-zA-Z][^>]*\s(?:id|name)\s*=\s*["']([^"']+)["']""")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Check local Markdown links (relative paths and #anchors). "
            "External URLs are not fetched. Exit status 1 if any link is broken."
        )
    )
    parser.add_argument(
        "paths",
        nargs="*",
        help="Markdown files or directories to scan "
        "(default: all tracked *.md files in the repository)",
    )
    parser.add_argument(
        "--root",
        help="Directory that '/'-rooted links, known-issue paths and reported "
        "paths are relative to (default: the git top-level directory)",
    )
    parser.add_argument(
        "--known-issues",
        help="Known-issues file (default: scripts/markdown-links-known-issues.txt "
        "next to this script)",
    )
    return parser.parse_args()


def find_root(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit).resolve()
    script_dir = Path(__file__).resolve().parent
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=script_dir, capture_output=True, text=True, check=True,
        ).stdout.strip()
        return Path(out).resolve()
    except (OSError, subprocess.CalledProcessError):
        return script_dir.parent


def walk_markdown(base: Path) -> list[Path]:
    found: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
        found.extend(Path(dirpath, f) for f in sorted(filenames) if f.endswith(".md"))
    return found


def tracked_markdown(root: Path) -> list[Path]:
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z", "--", "*.md"],
            cwd=root, capture_output=True, check=True,
        ).stdout.decode("utf-8", "surrogateescape")
        files = [root / p for p in out.split("\0") if p]
    except (OSError, subprocess.CalledProcessError):
        files = walk_markdown(root)
    return [f for f in files if f.is_file() and not SKIP_DIRS & set(f.relative_to(root).parts)]


def collect_files(paths: list[str], root: Path) -> list[Path]:
    if not paths:
        return sorted(tracked_markdown(root))
    files: list[Path] = []
    for raw in paths:
        p = Path(raw).resolve()
        if p.is_dir():
            files.extend(walk_markdown(p))
        elif p.is_file():
            files.append(p)
        else:
            print(f"ERROR: path not found: {raw}", file=sys.stderr)
            sys.exit(2)
    return sorted(set(files))


def display(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def strip_inline_code(line: str) -> str:
    return CODE_SPAN_RE.sub(lambda m: " " * len(m.group(0)), line)


def markdown_lines(text: str):
    """Yield (line_number, line) for lines outside fenced code and HTML comments."""
    fence: tuple[str, int] | None = None
    in_comment = False
    for number, line in enumerate(text.splitlines(), 1):
        match = FENCE_RE.match(line)
        if fence is not None:
            if match and match.group(1)[0] == fence[0] and len(match.group(1)) >= fence[1] \
                    and not line.strip().strip(fence[0]):
                fence = None
            continue
        if match:
            fence = (match.group(1)[0], len(match.group(1)))
            continue
        if in_comment:
            if "-->" not in line:
                continue
            line = line.split("-->", 1)[1]
            in_comment = False
        line = re.sub(r"<!--.*?-->", "", line)
        if "<!--" in line:
            line = line.split("<!--", 1)[0]
            in_comment = True
        yield number, line


def parse_destination(line: str, start: int) -> str | None:
    """Parse a link destination beginning at line[start] (just after '(')."""
    i = start
    while i < len(line) and line[i] in " \t":
        i += 1
    if i >= len(line):
        return None
    if line[i] == "<":
        end = line.find(">", i + 1)
        return line[i + 1:end] if end != -1 else None
    depth = 0
    begin = i
    while i < len(line):
        ch = line[i]
        if ch == "\\":
            i += 2
            continue
        if ch.isspace():
            break
        if ch == "(":
            depth += 1
        elif ch == ")":
            if depth == 0:
                break
            depth -= 1
        i += 1
    return line[begin:i]


def extract_links(text: str):
    """Yield (line_number, raw_target) for inline links/images and reference definitions."""
    for number, raw_line in markdown_lines(text):
        line = strip_inline_code(raw_line)
        ref = REF_DEF_RE.match(line)
        if ref:
            target = ref.group(2)
            yield number, target[1:-1] if target.startswith("<") else target
        pos = 0
        while True:
            idx = line.find("](", pos)
            if idx == -1:
                break
            pos = idx + 2
            if idx > 0 and line[idx - 1] == "\\":
                continue
            target = parse_destination(line, idx + 2)
            if target:
                yield number, target


def heading_slug(heading: str) -> str:
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", heading)  # links/images -> text
    text = re.sub(r"!?\[([^\]]*)\]\[[^\]]*\]", r"\1", text)
    text = re.sub(r"<[^>]+>", "", text)  # inline HTML
    text = text.replace("`", "").replace("*", "")
    text = re.sub(r"(?<!\w)_+|_+(?!\w)", "", text)  # emphasis underscores only
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)  # drop punctuation, emoji; keep _ - space
    return text.replace(" ", "-")


_anchor_cache: dict[Path, set[str]] = {}


def anchors_for(path: Path) -> set[str]:
    if path in _anchor_cache:
        return _anchor_cache[path]
    anchors: set[str] = set()
    counts: dict[str, int] = {}
    previous = ""

    def add_heading(heading: str) -> None:
        slug = heading_slug(heading)
        n = counts.get(slug, 0)
        counts[slug] = n + 1
        anchors.add(slug if n == 0 else f"{slug}-{n}")

    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        text = ""
    for _, line in markdown_lines(text):
        anchors.update(m.lower() for m in HTML_ANCHOR_RE.findall(line))
        atx = ATX_RE.match(line)
        if atx:
            add_heading(atx.group(1))
            previous = ""
            continue
        if SETEXT_RE.match(line) and previous.strip():
            add_heading(previous.strip())
            previous = ""
            continue
        previous = line
    _anchor_cache[path] = anchors
    return anchors


def check_target(source: Path, raw: str, root: Path) -> str | None:
    """Return an error message for a broken local target, or None if fine."""
    target = raw.strip()
    if not target or SCHEME_RE.match(target) or target.startswith("//"):
        return None
    path_part, _, fragment = target.partition("#")
    path_part = unquote(path_part.split("?", 1)[0])
    fragment = unquote(fragment)

    if not path_part:
        resolved = source
    elif path_part.startswith("/"):
        resolved = root / path_part.lstrip("/")
    else:
        resolved = source.parent / path_part
    resolved = Path(os.path.normpath(resolved))

    if path_part and not resolved.exists():
        return f"broken link: '{raw}' does not exist"
    if fragment and resolved.is_file() and resolved.suffix == ".md":
        wanted = fragment.lower()
        if wanted.startswith("user-content-"):
            wanted = wanted[len("user-content-"):]
        if wanted not in anchors_for(resolved):
            where = "this file" if resolved == source else display(resolved, root)
            return f"broken anchor: '{raw}' has no matching heading in {where}"
    return None


def load_known_issues(path: Path) -> dict[tuple[str, str], int]:
    entries: dict[tuple[str, str], int] = {}
    if not path.is_file():
        return entries
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        file_part, sep, target = line.partition(":")
        if not sep or not target.strip():
            print(f"WARNING: {display(path, path.parent)}:{number}: "
                  "malformed known-issue entry (expected 'path:target')", file=sys.stderr)
            continue
        entries[(file_part.strip(), target.strip())] = number
    return entries


def main() -> int:
    args = parse_args()
    root = find_root(args.root)
    known_path = Path(args.known_issues) if args.known_issues else \
        Path(__file__).resolve().parent / "markdown-links-known-issues.txt"
    known = load_known_issues(known_path)
    files = collect_files(args.paths, root)

    if not files:
        print("ERROR: No Markdown files found; check the repository and file selection.",
              file=sys.stderr)
        return 1

    failures = 0
    link_count = 0
    suppressed: set[tuple[str, str]] = set()
    scanned = {display(f, root) for f in files}

    for md in files:
        rel = display(md, root)
        text = md.read_text(encoding="utf-8", errors="replace")
        for line_number, raw in extract_links(text):
            link_count += 1
            message = check_target(md, raw, root)
            if message is None:
                continue
            if (rel, raw) in known:
                suppressed.add((rel, raw))
                continue
            failures += 1
            print(f"{rel}:{line_number}: {message}", file=sys.stderr)

    known_label = display(known_path.resolve(), root)
    for (file_part, target), number in known.items():
        if (file_part, target) in suppressed:
            continue
        if file_part in scanned or not (root / file_part).exists():
            print(f"WARNING: {known_label}:{number}: stale known issue "
                  f"'{file_part}:{target}' is no longer broken; remove it.", file=sys.stderr)

    summary = (f"Checked {link_count} link(s) in {len(files)} Markdown file(s): "
               f"{failures} broken, {len(suppressed)} known issue(s) skipped.")
    if failures:
        print(summary)
        print("Markdown link check failed.", file=sys.stderr)
        return 1
    print(summary)
    print("Markdown link check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
