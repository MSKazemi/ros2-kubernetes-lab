#!/usr/bin/env python3
"""Add or verify the job-level "public repositories only" guard in GitHub Actions workflows.

A private repository (and any private copy of this one) tracks the same ``.github/workflows``
files as the public repository but must execute and publish nothing, while forks of the public
repository keep running CI. Every job therefore carries::

    if: github.event.repository.private == false && (<original condition>)

Subcommands (stdlib; PyYAML is needed for ``check``):

  check  [workflow ...]               every job's ``if`` has the guard as a top-level AND-conjunct;
                                      the retired repository-name guard is reported as LEGACY;
                                      triggers without a repository payload (``schedule``) fail
  apply  [--dry-run] [workflow ...]   add the guard, or migrate a legacy-guarded job
                                      (``legacy && (orig)`` -> ``guard && (orig)``, ``orig`` untouched)

With no workflow arguments, every ``*.yml``/``*.yaml`` under ``.github/workflows`` of the current
directory is used. ``apply`` is idempotent and edits text, so comments are kept. It refuses (exit 2)
to touch a job whose ``if`` is a block scalar, quoted, multi-line, has a trailing comment, mixes text
with ``${{ }}``, or has a legacy guard in a non-standard shape; edit those by hand.

Only the exact guard expression above counts: other spellings of the same idea
(``!github.event.repository.private``, ``private != true``, ``private == 'false'``) are not guarded.
This is a safety measure, not proof that Actions is disabled in a repository.
Exit status: 0 ok, 1 check failed, 2 usage/unsupported input.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

GUARD = "github.event.repository.private == false"
# The retired guard (only recognised so that `apply` can migrate it and `check` can report it).
LEGACY_REPO = "MSKazemi/robo-resilience-lab"
COMMENT = "# Run only in public repositories; a private repository (or private copy) executes nothing."
OLD_COMMENTS = ("# Run only in the public repository; the private mirror and forks execute nothing.",)
# Event payloads WITHOUT a repository object: `github.event.repository` is null there, and GitHub
# coerces null == false to true, so the guard would let the job run in a private repository.
# Every other trigger carries a repository: push, pull_request, pull_request_target, workflow_dispatch,
# repository_dispatch, release, issues, issue_comment, ... include it; workflow_run carries it and
# workflow_call inherits the caller's payload.
NO_REPO_PAYLOAD_EVENTS = frozenset({"schedule"})

JOB_KEY_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*(#.*)?$")
IF_RE = re.compile(r"^    if:\s*(.*?)\s*$")
NAME_RE = re.compile(r"^    name:")


class Unsupported(Exception):
    """A construct that text-level editing cannot handle safely."""


def legacy_guard_expr(repo: str = LEGACY_REPO) -> str:
    return f"github.repository == '{repo}'"


class ExprError(ValueError):
    """The condition is not in the GitHub expression subset this tool understands."""


def _scan_braces(text: str) -> tuple[list[int], list[int]]:
    """Positions of '${{' and '}}' that lie OUTSIDE single-quoted string literals ('' escapes a quote)."""
    opens: list[int] = []
    closes: list[int] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c == "'":
            i += 1
            while i < n:
                if text[i] == "'":
                    if i + 1 < n and text[i + 1] == "'":
                        i += 2
                        continue
                    break
                i += 1
            else:
                raise ExprError("unterminated string literal")
            i += 1
            continue
        if text.startswith("${{", i):
            opens.append(i)
            i += 3
            continue
        if text.startswith("}}", i):
            closes.append(i)
            i += 2
            continue
        i += 1
    return opens, closes


def unwrap(expr: str) -> str:
    """Strip an optional ``${{ ... }}`` wrapper (GitHub allows it in ``if:``).

    The wrapper is removed only when the opening ``${{`` and the final ``}}`` are one matching pair
    around the entire expression. Text outside a single wrapper (``${{ a }} && ${{ b }}``, ``x ${{ a }}``)
    is a different construct (GitHub then treats the whole string as truthy), so it raises
    :class:`ExprError` instead of being rewritten."""
    text = expr.strip()
    opens, closes = _scan_braces(text)
    if not opens and not closes:
        return text
    if opens == [0] and closes == [len(text) - 2] and len(text) >= 5:
        return text[3:-2].strip()
    raise ExprError("'${{ }}' is not a single wrapper around the whole expression")


def compose(existing: str | None) -> str:
    """`GUARD` alone, or `GUARD && (<existing, unwrapped>)`. Raises ExprError for compound ${{ }} shapes."""
    if existing is None:
        return GUARD
    return f"{GUARD} && ({unwrap(existing)})"


_TOKEN_RE = re.compile(
    r"""\s*(?:
        (?P<str>'(?:[^']|'')*')
      | (?P<op>&&|\|\||==|!=|<=|>=|<|>|!|\(|\)|\[|\]|\.|,|\*)
      | (?P<num>-?\d+(?:\.\d+)?)
      | (?P<name>[A-Za-z_][A-Za-z0-9_-]*)
    )""",
    re.VERBOSE,
)


def _tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    pos = 0
    text = text.rstrip()
    while pos < len(text):
        m = _TOKEN_RE.match(text, pos)
        if not m or m.end() == pos:
            raise ExprError(f"cannot tokenize at offset {pos}")
        kind = m.lastgroup or ""
        value = m.group(kind)
        tokens.append((kind, value[1:-1].replace("''", "'") if kind == "str" else value))
        pos = m.end()
    return tokens


class _Parser:
    """Recursive descent over: or > and > comparison > unary(!) > primary. Returns tuple ASTs."""

    def __init__(self, tokens: list[tuple[str, str]]) -> None:
        self.t, self.i = tokens, 0

    def peek(self) -> tuple[str, str] | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def take(self, kind: str | None = None, value: str | None = None) -> tuple[str, str]:
        tok = self.peek()
        if tok is None or (kind and tok[0] != kind) or (value and tok[1] != value):
            raise ExprError("unexpected token")
        self.i += 1
        return tok

    def at_op(self, *ops: str) -> bool:
        tok = self.peek()
        return tok is not None and tok[0] == "op" and tok[1] in ops

    def parse(self):
        node = self.or_()
        if self.peek() is not None:
            raise ExprError("trailing tokens")
        return node

    def or_(self):
        parts = [self.and_()]
        while self.at_op("||"):
            self.take()
            parts.append(self.and_())
        return parts[0] if len(parts) == 1 else ("or", tuple(parts))

    def and_(self):
        parts = [self.cmp_()]
        while self.at_op("&&"):
            self.take()
            parts.append(self.cmp_())
        return parts[0] if len(parts) == 1 else ("and", tuple(parts))

    def cmp_(self):
        node = self.unary()
        while self.at_op("==", "!=", "<", "<=", ">", ">="):
            op = self.take()[1]
            node = ("cmp", op, node, self.unary())
        return node

    def unary(self):
        if self.at_op("!"):
            self.take()
            return ("not", self.unary())
        return self.primary()

    def primary(self):
        tok = self.peek()
        if tok is None:
            raise ExprError("unexpected end")
        kind, value = tok
        if kind == "op" and value == "(":
            self.take()
            inner = self.or_()
            self.take("op", ")")
            return ("paren", inner)
        if kind in ("str", "num"):
            self.take()
            return ("lit", kind, value)
        if kind == "name":
            self.take()
            chain: list = [value]
            while True:
                if self.at_op("."):
                    self.take()
                    nxt = self.peek()
                    if nxt is None or nxt[0] not in ("name", "op") or (nxt[0] == "op" and nxt[1] != "*"):
                        raise ExprError("bad property access")
                    chain.append(self.take()[1])
                elif self.at_op("["):
                    self.take()
                    chain.append(("index", self.or_()))
                    self.take("op", "]")
                elif self.at_op("("):
                    self.take()
                    args = []
                    if not self.at_op(")"):
                        args.append(self.or_())
                        while self.at_op(","):
                            self.take()
                            args.append(self.or_())
                    self.take("op", ")")
                    chain.append(("call", tuple(args)))
                else:
                    break
            return ("ref", tuple(chain))
        raise ExprError("unexpected token")


def parse_condition(expr: str):
    """Parse a job/step `if` expression (optionally wrapped in ${{ }}) into a tuple AST."""
    return _Parser(_tokenize(unwrap(expr))).parse()


def _conjuncts(node) -> list:
    """Flatten the top-level AND structure of the WHOLE expression (looking through redundant parentheses)."""
    if node[0] == "paren":
        return _conjuncts(node[1])
    if node[0] == "and":
        out: list = []
        for child in node[1]:
            out += _conjuncts(child)
        return out
    return [node]


def guard_status(expr: object, legacy_repo: str = LEGACY_REPO) -> str:
    """'guarded', 'legacy' or 'unguarded'.

    'guarded': the exact GUARD is a top-level AND-conjunct of the WHOLE condition (`g`, `g && (a)`,
    `g && a && b`, `(g) && a`, `g && (a || b)`). `g && a || b` is `(g && a) || b`, so `a || g`, `g || x`,
    `!g && a`, other spellings and a guard text inside a string literal are not. Anything that cannot
    be parsed is 'unguarded'. 'legacy': only the retired repository-name guard is present that way."""
    if not isinstance(expr, str):
        return "unguarded"
    try:
        tree = parse_condition(expr)
        guard_ast = parse_condition(GUARD)
        legacy_ast = parse_condition(legacy_guard_expr(legacy_repo))
    except ExprError:
        return "unguarded"
    conjuncts = _conjuncts(tree)
    if guard_ast in conjuncts:
        return "guarded"
    if legacy_ast in conjuncts:
        return "legacy"
    return "unguarded"


def is_guarded(expr: object) -> bool:
    return guard_status(expr) == "guarded"


def original_condition(expr: str, legacy_repo: str = LEGACY_REPO) -> str | None:
    """Inverse of :func:`compose` for either guard: the user's own condition (None if there was none).

    Only the exact shapes written by ``apply`` are accepted: ``g`` or ``g && (<original>)`` where ``g`` is
    the current guard or the legacy repository-name guard."""
    try:
        text = unwrap(expr)
        tree = parse_condition(text)
        for guard in (GUARD, legacy_guard_expr(legacy_repo)):
            guard_ast = parse_condition(guard)
            if tree == guard_ast:
                return None
            prefix = guard + " && ("
            if (tree[0] == "and" and len(tree[1]) == 2 and tree[1][0] == guard_ast and tree[1][1][0] == "paren"
                    and text.startswith(prefix) and text.endswith(")")):
                return text[len(prefix) : -1]
    except ExprError as exc:
        raise ValueError(f"unparseable condition: {exc}") from None
    raise ValueError("expression is not of the form written by apply (guard && (original))")


def apply_text(text: str, legacy_repo: str = LEGACY_REPO) -> tuple[str, int]:
    """Return (new_text, number_of_jobs_changed). Raises Unsupported."""
    lines = text.split("\n")
    out: list[str] = []
    in_jobs = False
    changed = 0
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if re.match(r"^jobs:\s*$", line):
            in_jobs = True
            out.append(line)
            i += 1
            continue
        if in_jobs and re.match(r"^\S", line) and not line.startswith("#"):
            in_jobs = False  # next top-level key ends the jobs mapping
        m = JOB_KEY_RE.match(line) if in_jobs else None
        if not m:
            out.append(line)
            i += 1
            continue
        job_id = m.group(1)
        # collect the job block: until next 2-space key or top-level key
        j = i + 1
        while j < n:
            nxt = lines[j]
            if JOB_KEY_RE.match(nxt) or (re.match(r"^\S", nxt) and not nxt.startswith("#")):
                break
            j += 1
        block = lines[i + 1 : j]
        # trailing blank/comment lines belong to the spacing before the next job
        tail: list[str] = []
        while block and (block[-1].strip() == "" or block[-1].lstrip().startswith("#")) and not block[-1].startswith("    "):
            tail.insert(0, block.pop())
        if_idx = next((k for k, b in enumerate(block) if IF_RE.match(b)), None)
        new_block = list(block)
        if if_idx is not None:
            raw = IF_RE.match(block[if_idx]).group(1)  # type: ignore[union-attr]
            if raw == "" or raw[0] in "|>":
                raise Unsupported(f"job '{job_id}': block-scalar or empty 'if:' is not supported")
            if raw[0] in "'\"":
                raise Unsupported(f"job '{job_id}': quoted 'if:' is not supported")
            if re.search(r"\s#", raw):
                raise Unsupported(f"job '{job_id}': 'if:' with a trailing comment is not supported")
            if if_idx + 1 < len(block) and re.match(r"^      \S", block[if_idx + 1]):
                raise Unsupported(f"job '{job_id}': multi-line 'if:' is not supported")
            status = guard_status(raw, legacy_repo)
            if status != "guarded":
                try:
                    if status == "legacy":
                        try:
                            existing = original_condition(raw, legacy_repo)   # migrate: keep the user's condition verbatim
                        except ValueError:
                            raise Unsupported(f"job '{job_id}': legacy repository guard in a non-standard shape; edit it by hand") from None
                    else:
                        existing = raw
                    new_block[if_idx] = f"    if: {compose(existing)}"
                except ExprError as exc:
                    raise Unsupported(f"job '{job_id}': cannot wrap the existing 'if:' safely ({exc}); edit it by hand") from None
                if if_idx > 0 and new_block[if_idx - 1].strip() in (COMMENT, *OLD_COMMENTS):
                    new_block[if_idx - 1] = "    " + COMMENT
                else:
                    new_block.insert(if_idx, "    " + COMMENT)
                changed += 1
        else:
            name_idx = next((k for k, b in enumerate(block) if NAME_RE.match(b)), None)
            pos = (name_idx + 1) if name_idx is not None else 0
            new_block[pos:pos] = ["    " + COMMENT, f"    if: {GUARD}"]
            changed += 1
        out.append(line)
        out.extend(new_block)
        out.extend(tail)
        i = j
    return "\n".join(out), changed


def trigger_names(doc: dict) -> list[str]:
    """Event names from `on:` given as a string, a list or a mapping (YAML 1.1 parses the key `on` as True)."""
    on = doc.get(True, doc.get("on"))
    if isinstance(on, str):
        return [on]
    if isinstance(on, list):
        return [str(x) for x in on]
    if isinstance(on, dict):
        return [str(k) for k in on]
    return []


def check_file(path: Path, legacy_repo: str = LEGACY_REPO) -> list[str]:
    """Return a list of problems for one workflow file (empty = every job guarded, no unsafe trigger)."""
    import yaml  # PyYAML; imported lazily so `apply` needs only the stdlib

    problems: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{path}: YAML error: {exc}"]
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        return [f"{path}: no jobs mapping found"]
    for event in trigger_names(doc):
        if event in NO_REPO_PAYLOAD_EVENTS:
            problems.append(
                f"{path}: trigger '{event}' has no repository payload (github.event.repository is null, and null == false "
                f"is true), so the guard does not keep it out of a private repository; remove the trigger or guard the job by hand")
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            problems.append(f"{path}: job '{job_id}' is not a mapping")
            continue
        status = guard_status(job.get("if"), legacy_repo)
        if status == "legacy":
            problems.append(f"{path}: job '{job_id}' uses the LEGACY repository-name guard; run "
                            f"`python3 scripts/ci/repo_guard.py apply` to migrate it to `{GUARD}`")
        elif status == "unguarded":
            hint = ""
            if isinstance(job.get("if"), str):
                try:
                    parse_condition(job["if"])
                except ExprError as exc:
                    hint = f" [unsupported 'if' shape: {exc}]"
            problems.append(f"{path}: job '{job_id}' has no top-level `{GUARD}` guard (if={job.get('if')!r}){hint}")
    return problems


def default_files() -> list[Path]:
    root = Path(".github/workflows")
    return sorted([*root.glob("*.yml"), *root.glob("*.yaml")]) if root.is_dir() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=["check", "apply"])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--legacy-repo", default=LEGACY_REPO,
                    help="owner/name in the retired repository-name guard that apply migrates and check reports (default %(default)s)")
    ap.add_argument("--dry-run", action="store_true", help="apply: report only, write nothing")
    args = ap.parse_args(argv)
    files = args.files or default_files()
    if not files:
        print("ERROR: no workflow files found", file=sys.stderr)
        return 2

    if args.command == "check":
        problems: list[str] = []
        for f in files:
            problems += check_file(f, args.legacy_repo)
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        if problems:
            return 1
        print(f"OK: every job in {len(files)} workflow file(s) has the guard `{GUARD}`; no trigger without a repository payload")
        return 0

    status = 0
    for f in files:
        original = f.read_text(encoding="utf-8")
        try:
            new, changed = apply_text(original, args.legacy_repo)
        except Unsupported as exc:
            print(f"UNSUPPORTED {f}: {exc}", file=sys.stderr)
            status = 2
            continue
        try:
            import yaml
            for event in trigger_names(yaml.safe_load(original) or {}):
                if event in NO_REPO_PAYLOAD_EVENTS:
                    print(f"WARNING {f}: trigger '{event}' has no repository payload; the guard cannot protect it "
                          f"(`check` will fail)", file=sys.stderr)
        except Exception:  # noqa: BLE001 - the warning is best effort
            pass
        print(f"{'would change' if args.dry_run else 'changed'} {f}: {changed} job(s)")
        if changed and not args.dry_run:
            f.write_text(new, encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
