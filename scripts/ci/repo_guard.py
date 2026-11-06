#!/usr/bin/env python3
"""Add or verify the job-level repository guard in GitHub Actions workflows.

The private dual-git mirror tracks the same ``.github/workflows`` files as the
public repository but must execute and publish nothing. Every job therefore
carries ``if: github.repository == '<owner>/<repo>' && (<original condition>)``.

Subcommands (stdlib plus PyYAML for ``check``):

  check  [--repo R] [workflow ...]   verify every job's ``if`` starts with the guard
  apply  [--repo R] [--dry-run] [workflow ...]
                                     rewrite workflow text in place, keeping comments

With no workflow arguments, every ``*.yml``/``*.yaml`` under ``.github/workflows``
of the current directory is used. ``apply`` is idempotent. It refuses (exit 2)
to touch a job whose ``if`` is a block scalar, quoted, or has a trailing comment,
because those cannot be wrapped safely by text editing; edit those by hand.

This is a safety measure, not proof that Actions are disabled in a repository.
Exit status: 0 ok, 1 check failed, 2 usage/unsupported input.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

DEFAULT_REPO = "MSKazemi/robo-resilience-lab"
COMMENT = "# Run only in the public repository; the private mirror and forks execute nothing."

JOB_KEY_RE = re.compile(r"^  ([A-Za-z_][A-Za-z0-9_-]*):\s*(#.*)?$")
IF_RE = re.compile(r"^    if:\s*(.*?)\s*$")
NAME_RE = re.compile(r"^    name:")


class Unsupported(Exception):
    """A construct that text-level editing cannot handle safely."""


def guard_expr(repo: str) -> str:
    return f"github.repository == '{repo}'"


def unwrap(expr: str) -> str:
    """Strip an optional ``${{ ... }}`` wrapper (GitHub allows it in ``if:``)."""
    expr = expr.strip()
    if expr.startswith("${{") and expr.endswith("}}"):
        return expr[3:-2].strip()
    return expr


def compose(repo: str, existing: str | None) -> str:
    guard = guard_expr(repo)
    if existing is None:
        return guard
    return f"{guard} && ({unwrap(existing)})"


class ExprError(ValueError):
    """The condition is not in the GitHub expression subset this tool understands."""


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


def _is_guard_node(node, guard_ast) -> bool:
    if node == guard_ast:
        return True
    # the same equality written the other way round: 'owner/name' == github.repository
    return node[0] == "cmp" and node[1] == "==" and guard_ast[1] == "==" and (node[3], node[2]) == (guard_ast[2], guard_ast[3])


def is_guarded(expr: object, repo: str) -> bool:
    """True only if the guard is a top-level AND-conjunct of the whole condition.

    `g`, `g && (a)`, `g && a && b`, `(g) && a`, `g && (a || b)` are guarded. `g && a || b`
    (which is `(g && a) || b`), `a || g`, `g || x`, `!g && a`, `g != 'x'` and a guard text
    inside a string literal are not. Anything that cannot be parsed is treated as unguarded."""
    if not isinstance(expr, str):
        return False
    try:
        tree = parse_condition(expr)
        guard_ast = parse_condition(guard_expr(repo))
    except ExprError:
        return False
    return any(_is_guard_node(c, guard_ast) for c in _conjuncts(tree))


def original_condition(expr: str, repo: str) -> str | None:
    """Inverse of :func:`compose`: the pre-guard condition (None if there was none).

    Only the exact shapes written by ``apply`` are accepted: ``g`` or ``g && (<original>)``."""
    text = unwrap(expr)
    guard = guard_expr(repo)
    try:
        tree, guard_ast = parse_condition(text), parse_condition(guard)
    except ExprError as exc:
        raise ValueError(f"unparseable condition: {exc}") from None
    if tree == guard_ast:
        return None
    prefix = guard + " && ("
    if (tree[0] == "and" and len(tree[1]) == 2 and tree[1][0] == guard_ast and tree[1][1][0] == "paren"
            and text.startswith(prefix) and text.endswith(")")):
        return text[len(prefix) : -1]
    raise ValueError("expression is not of the form written by apply (guard && (original))")


def apply_text(text: str, repo: str) -> tuple[str, int]:
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
            if not is_guarded(raw, repo):
                new_block[if_idx] = f"    if: {compose(repo, raw)}"
                new_block.insert(if_idx, "    " + COMMENT)
                changed += 1
        else:
            name_idx = next((k for k, b in enumerate(block) if NAME_RE.match(b)), None)
            pos = (name_idx + 1) if name_idx is not None else 0
            new_block[pos:pos] = ["    " + COMMENT, f"    if: {guard_expr(repo)}"]
            changed += 1
        out.append(line)
        out.extend(new_block)
        out.extend(tail)
        i = j
    return "\n".join(out), changed


def check_file(path: Path, repo: str) -> list[str]:
    """Return a list of problems for one workflow file (empty = every job guarded)."""
    import yaml  # PyYAML; imported lazily so `apply` needs only the stdlib

    problems: list[str] = []
    try:
        doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return [f"{path}: YAML error: {exc}"]
    jobs = doc.get("jobs") if isinstance(doc, dict) else None
    if not isinstance(jobs, dict) or not jobs:
        return [f"{path}: no jobs mapping found"]
    for job_id, job in jobs.items():
        if not isinstance(job, dict):
            problems.append(f"{path}: job '{job_id}' is not a mapping")
            continue
        if "uses" in job and "steps" not in job:
            # reusable-workflow call: `if` is still honoured at job level
            pass
        if not is_guarded(job.get("if"), repo):
            problems.append(f"{path}: job '{job_id}' has no top-level repository guard (if={job.get('if')!r})")
    # a guarded job may depend on an unguarded one only if that one is also guarded: covered above
    return problems


def default_files() -> list[Path]:
    root = Path(".github/workflows")
    return sorted([*root.glob("*.yml"), *root.glob("*.yaml")]) if root.is_dir() else []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("command", choices=["check", "apply"])
    ap.add_argument("files", nargs="*", type=Path)
    ap.add_argument("--repo", default=DEFAULT_REPO, help="owner/name that may run jobs")
    ap.add_argument("--dry-run", action="store_true", help="apply: report only, write nothing")
    args = ap.parse_args(argv)
    files = args.files or default_files()
    if not files:
        print("ERROR: no workflow files found", file=sys.stderr)
        return 2

    if args.command == "check":
        problems: list[str] = []
        for f in files:
            problems += check_file(f, args.repo)
        for p in problems:
            print(f"FAIL {p}", file=sys.stderr)
        if problems:
            return 1
        print(f"OK: every job in {len(files)} workflow file(s) is guarded by repository == {args.repo}")
        return 0

    status = 0
    for f in files:
        original = f.read_text(encoding="utf-8")
        try:
            new, changed = apply_text(original, args.repo)
        except Unsupported as exc:
            print(f"UNSUPPORTED {f}: {exc}", file=sys.stderr)
            status = 2
            continue
        print(f"{'would change' if args.dry_run else 'changed'} {f}: {changed} job(s)")
        if changed and not args.dry_run:
            f.write_text(new, encoding="utf-8")
    return status


if __name__ == "__main__":
    sys.exit(main())
