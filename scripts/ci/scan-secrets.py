#!/usr/bin/env python3
"""Scan tracked (or explicitly given) files for secrets and private-only material.

Standard library only, offline, fast. Findings never include the matched text:
the report shows ``path:line: rule-id`` plus the length of the match, so CI logs
cannot leak what the scanner found (this also protects private denylist terms).

What it looks for
  * private key blocks; AWS access key ids and secret keys; GitHub, Slack and
    Hugging Face tokens; JWT-shaped service-account tokens;
  * kubeconfig material (client keys, tokens, whole kubeconfig files) and
    ``kubeadm join`` tokens / CA hashes;
  * tracked ``.env`` / key files, and ``NAME_TOKEN=value``-style assignments
    with a non-placeholder, high-entropy value;
  * (profile ``public``) paths matching a private-pattern file, and private
    marker words, both loaded at run time from untracked local files. Each
    location comes from, in order: a command-line flag, an environment variable
    (``RRL_PRIVATE_DENY``, ``RRL_PRIVATE_CARVEOUT``, ``RRL_PRIVATE_MARKERS``,
    ``RRL_SCAN_LOCAL_CONFIG``), then the repository-local git config key
    (``rrl.privateDeny``, ``rrl.privateCarveout``, ``rrl.privateMarkers``,
    ``rrl.scanLocalConfig``; a path relative to the repository root). There is
    no default path. If nothing is configured (public CI, forks) one line says
    the private-marker checks were SKIPPED; no private name lives in a tracked file.

Selection: without path arguments the files tracked by git (``git ls-files``,
optionally with ``--git-dir``) are scanned; with arguments only those files or
directories. Nothing else on disk is read.

Suppress a single line with the comment ``scan-secrets: ignore`` on that line,
or add an ``allow`` entry to the config (path glob + rule id or ``*``).

Exit status: 0 clean, 1 findings, 2 usage or configuration error.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).with_name("scan-secrets.config.json")
MAX_BYTES = 1_000_000
IGNORE_MARK = "scan-secrets: ignore"

PLACEHOLDER_RE = re.compile(
    r"(\$\{|\$\(|\{\{|<[^>]*>|%[A-Za-z_(]|your[-_ ]|change[-_ ]?me|example|placeholder|dummy|"
    r"redacted|xxxx|\*{3,}|\.{3,}|todo|fixme|^\$[A-Za-z_]|secrets\.|env\.|os\.environ|getenv)",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Rule:
    id: str
    description: str
    regex: re.Pattern[str]
    group: int = 0  # which group is the secret value (for length/placeholder checks)
    entropy: float = 0.0  # minimum Shannon entropy (bits/char) of the value; 0 = off
    skip_placeholders: bool = True


def _r(pattern: str, flags: int = 0) -> re.Pattern[str]:
    return re.compile(pattern, flags)


# Patterns avoid matching their own source text (no literal key header on one line).
RULES: tuple[Rule, ...] = (
    Rule("private-key-block", "private key block header",
         _r(r"-{5}BEGIN (?:RSA |EC |DSA |OPENSSH |PGP |ENCRYPTED )?PRIVATE KEY(?: BLOCK)?-{5}"),
         skip_placeholders=False),
    Rule("aws-access-key-id", "AWS access key id",
         _r(r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA|ANPA|ANVA)[0-9A-Z]{16}\b")),
    Rule("aws-secret-access-key", "AWS secret access key assignment",
         _r(r"(?i)aws_?secret_?access_?key[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9/+=]{40})\b"), group=1),
    Rule("github-token", "GitHub token",
         _r(r"\b(?:gh[pousr]_[A-Za-z0-9]{36,}|github_pat_[A-Za-z0-9_]{22,})\b")),
    Rule("slack-token", "Slack token",
         _r(r"\bxox[abprso]-[A-Za-z0-9-]{10,}")),
    Rule("slack-webhook", "Slack incoming webhook URL",
         _r(r"https://hooks\.slack\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[A-Za-z0-9]{16,}")),
    Rule("huggingface-token", "Hugging Face access token",
         _r(r"\bhf_[A-Za-z0-9]{30,}\b")),
    Rule("jwt", "JWT / service-account token",
         _r(r"\beyJ[A-Za-z0-9_-]{10,}\.eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    Rule("kubeadm-join-token", "kubeadm join / bootstrap token",
         _r(r"(?i)(?:--token|kubeadm\s+join[^\n]*?)\s*[= ]\s*([a-z0-9]{6}\.[a-z0-9]{16})\b"), group=1),
    Rule("kubeadm-ca-hash", "kubeadm discovery CA cert hash",
         _r(r"--discovery-token-ca-cert-hash\s+sha256:([0-9a-f]{64})"), group=1),
    Rule("kubeconfig-client-key", "kubeconfig client key or token data",
         _r(r"^\s*(?:client-key-data|client-key)\s*:\s*([A-Za-z0-9+/=]{40,})"), group=1),
    Rule("kubeconfig-user-token", "kubeconfig user token",
         _r(r"^\s*token\s*:\s*([A-Za-z0-9._~+/=-]{24,})\s*$"), group=1, entropy=3.5),
    Rule("docker-auth", "Docker registry auth blob",
         _r(r"\"auth\"\s*:\s*\"([A-Za-z0-9+/=]{20,})\""), group=1),
    Rule("bearer-token", "Authorization bearer token",
         _r(r"(?i)authorization\s*[:=]\s*[\"']?bearer\s+([A-Za-z0-9._~+/=-]{20,})"), group=1, entropy=3.2),
    Rule("secret-assignment", "secret-like assignment with a non-placeholder value",
         # the key must END in a secret-ish word (so TOKEN_FILE or secretFieldSelector do not match)
         _r(r"(?i)^\s*(?:export\s+)?[\"']?[A-Za-z0-9_.-]*(?:secret|secret[_-]?key|token|passw(?:or)?d|api[_-]?key|private[_-]?key|access[_-]?key)"
            r"[\"']?\s*[:=]\s*[\"']?([^\s\"'#,;/.][^\s\"'#,;]{15,})"), group=1, entropy=3.5),
)

KUBECONFIG_FILE_RE = (re.compile(r"^kind:\s*Config\s*$", re.M), re.compile(r"^clusters:", re.M), re.compile(r"^users:", re.M))

# Basename patterns that must not be tracked at all (fnmatch-style, matched on the basename).
FORBIDDEN_NAMES = (
    (".env", "environment file"),
    (".env.*", "environment file"),
    ("*.pem", "PEM file (review: may be a public certificate)"),
    ("*.key", "key file"),
    ("*.p12", "PKCS#12 keystore"),
    ("*.pfx", "PKCS#12 keystore"),
    ("*.kubeconfig", "kubeconfig"),
    ("kubeconfig", "kubeconfig"),
    ("admin.conf", "kubeadm admin kubeconfig"),
    ("id_rsa", "SSH private key"),
    ("id_ed25519", "SSH private key"),
    ("id_ecdsa", "SSH private key"),
    ("join-command.sh", "kubeadm join script"),
    (".htpasswd", "password file"),
)
ALLOWED_ENV_NAMES = {".env.example", ".env.sample", ".env.template", ".env.dist"}


# --------------------------------------------------------------------- helpers
def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """gitignore-lite: ``**`` crosses directories, ``*``/``?`` stay in one segment;
    a pattern without ``/`` matches the basename at any depth."""
    anchored = "/" in pattern.rstrip("/")
    pat = pattern.lstrip("/")
    out = []
    i = 0
    while i < len(pat):
        c = pat[i]
        if pat.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif pat.startswith("**", i):
            out.append(".*")
            i += 2
        elif c == "*":
            out.append("[^/]*")
            i += 1
        elif c == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(c))
            i += 1
    body = "".join(out)
    prefix = "" if anchored else "(?:.*/)?"
    return re.compile(f"^{prefix}{body}$")


def entropy(value: str) -> float:
    if not value:
        return 0.0
    counts: dict[str, int] = {}
    for ch in value:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(value)
    return -sum(c / n * math.log2(c / n) for c in counts.values())


@dataclass(frozen=True)
class Finding:
    path: str
    line: int  # 0 = whole file / path
    rule: str
    description: str
    length: int = 0

    def text(self) -> str:
        loc = f"{self.path}:{self.line}" if self.line else self.path
        extra = f" [value redacted, {self.length} chars]" if self.length else ""
        return f"{loc}: {self.rule}: {self.description}{extra}"

    def as_dict(self) -> dict[str, object]:
        return {"path": self.path, "line": self.line, "rule": self.rule,
                "description": self.description, "length": self.length}


PATH_RULE = "private-marker-denylist"
_CONFIG_KEYS = {"_comment", "ignore_paths", "denylist_paths", "denylist_terms", "allow"}


def _ancestors(rel: str) -> list[str]:
    """'a/b/c.md' -> ['a', 'a/b', 'a/b/c.md'] (every path prefix, shortest first)."""
    parts = rel.split("/")
    return ["/".join(parts[: i + 1]) for i in range(len(parts))]


class Config:
    def __init__(self, data: dict) -> None:
        self.ignore: list[re.Pattern[str]] = []
        self.deny_paths: list[re.Pattern[str]] = []
        self.terms: list[tuple[str, re.Pattern[str], list[re.Pattern[str]]]] = []
        self.allow: list[tuple[re.Pattern[str], str]] = []
        self.carveouts: list[str] = []
        self.private_deny_loaded = False
        self.merge(data)

    def merge(self, data: dict) -> None:
        """Add rules from a config mapping (shipped config or an untracked local one)."""
        for key in data:
            if key not in _CONFIG_KEYS:
                raise ValueError(f"unknown config key: {key!r}")
        self.ignore += [glob_to_regex(p) for p in data.get("ignore_paths", [])]
        self.deny_paths += [glob_to_regex(d["glob"] if isinstance(d, dict) else d) for d in data.get("denylist_paths", [])]
        for t in data.get("denylist_terms", []):
            if not t.get("enabled", True):
                continue
            flags = re.IGNORECASE if t.get("ignore_case", True) else 0
            body = t["term"] if t.get("regex") else re.escape(t["term"])
            if t.get("whole_word", True):
                body = rf"\b(?:{body})\b"
            self.terms.append((t.get("id", "private-term"), re.compile(body, flags),
                               [glob_to_regex(p) for p in t.get("paths", ["**"])]))
        self.allow += [(glob_to_regex(a["path"]), a.get("rule", "*")) for a in data.get("allow", [])]

    def load_private_deny(self, deny_file: Path, carveout_file: Path | None = None) -> bool:
        """Load gitignore-style private patterns at run time.

        Returns False (and loads nothing) when the file is absent, which is the normal
        situation in public CI. A pattern matches a path if it matches the path or any
        of its parent directories; a carve-out re-includes a directory only against
        denies that match at or above it, so nested denies below a carve-out still apply.
        """
        try:
            lines = deny_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith(("#", "!")):
                continue
            self.deny_paths.append(glob_to_regex(line.rstrip("/")))
        if carveout_file is not None:
            try:
                for raw in carveout_file.read_text(encoding="utf-8").splitlines():
                    line = raw.strip().strip("/")
                    if line and not line.startswith("#"):
                        self.carveouts.append(line)
            except OSError:
                pass
        self.private_deny_loaded = True
        return True

    def load_markers(self, marker_file: Path) -> bool:
        """Load private marker words (one literal per line, '#' comments) from an untracked file.

        Each word matches case-insensitively as a whole word in any scanned file. Returns
        False when the file is absent."""
        try:
            lines = marker_file.read_text(encoding="utf-8").splitlines()
        except OSError:
            return False
        for raw in lines:
            word = raw.strip()
            if word and not word.startswith("#"):
                self.terms.append(("private-marker-term", re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE),
                                   [glob_to_regex("**")]))
        return True

    def path_denied(self, rel: str) -> bool:
        for prefix in _ancestors(rel):
            if any(rx.match(prefix) for rx in self.deny_paths):
                if any(c == prefix or c.startswith(prefix + "/") for c in self.carveouts):
                    continue  # deny matched at/above a carved-out public directory
                return True
        return False

    @classmethod
    def load(cls, path: Path | None) -> "Config":
        if path is None:
            return cls({})
        try:
            return cls(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"scan-secrets: bad config {path}: {exc}") from None

    def merge_file(self, path: Path) -> None:
        try:
            self.merge(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"scan-secrets: bad config {path}: {exc}") from None

    def allowed(self, rel: str, rule: str) -> bool:
        return any(rx.match(rel) and r in ("*", rule) for rx, r in self.allow)

    def ignored(self, rel: str) -> bool:
        return any(rx.match(rel) for rx in self.ignore)


# --------------------------------------------------------------------- scanning
def scan_text(rel: str, text: str, cfg: Config, profile: str = "public") -> list[Finding]:
    findings: list[Finding] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if IGNORE_MARK in line:
            continue
        for rule in RULES:
            for m in rule.regex.finditer(line):
                value = m.group(rule.group) if rule.group else m.group(0)
                if rule.skip_placeholders and PLACEHOLDER_RE.search(value):
                    continue
                if rule.entropy and entropy(value) < rule.entropy:
                    continue
                if cfg.allowed(rel, rule.id):
                    continue
                findings.append(Finding(rel, lineno, rule.id, rule.description, len(value)))
        if profile == "public":
            for tid, rx, scopes in cfg.terms:
                if any(sc.match(rel) for sc in scopes) and rx.search(line) and not cfg.allowed(rel, tid):
                    findings.append(Finding(rel, lineno, tid, "configured private-marker term (not shown)"))
    if all(rx.search(text) for rx in KUBECONFIG_FILE_RE) and re.search(r"(?m)^\s*(client-key-data|token|client-key)\s*:", text):
        if not cfg.allowed(rel, "kubeconfig-file"):
            findings.append(Finding(rel, 0, "kubeconfig-file", "file looks like a kubeconfig with credentials"))
    return findings


def scan_path_name(rel: str, cfg: Config, profile: str) -> list[Finding]:
    findings: list[Finding] = []
    base = rel.rsplit("/", 1)[-1]
    if profile == "public" and cfg.path_denied(rel) and not cfg.allowed(rel, PATH_RULE):
        findings.append(Finding(rel, 0, PATH_RULE, "path matches the private-marker denylist"))
    from fnmatch import fnmatchcase
    for pattern, reason in FORBIDDEN_NAMES:
        if fnmatchcase(base, pattern) and base not in ALLOWED_ENV_NAMES and not cfg.allowed(rel, "forbidden-filename"):
            findings.append(Finding(rel, 0, "forbidden-filename", reason))
            break
    return findings


def scan_file(root: Path, rel: str, cfg: Config, profile: str) -> list[Finding]:
    findings = scan_path_name(rel, cfg, profile)
    path = root / rel
    try:
        if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_BYTES:
            return findings
        data = path.read_bytes()
    except OSError:
        return findings
    if b"\0" in data[:8192]:
        return findings
    findings += scan_text(rel, data.decode("utf-8", errors="replace"), cfg, profile)
    return findings


def git_tracked(root: Path, git_dir: str | None, untracked: bool = False) -> list[str]:
    cmd = ["git"]
    if git_dir:
        cmd += [f"--git-dir={git_dir}", f"--work-tree={root}"]
    cmd += ["-C", str(root), "ls-files", "-z"]
    if untracked:
        cmd += ["--cached", "--others", "--exclude-standard"]
    try:
        proc = subprocess.run(cmd, capture_output=True, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SystemExit(f"scan-secrets: cannot list tracked files ({exc}); pass paths explicitly") from None
    return [p for p in proc.stdout.decode("utf-8", "replace").split("\0") if p]


def collect(root: Path, args_paths: list[str], cfg: Config, git_dir: str | None, untracked: bool = False) -> list[str]:
    if not args_paths:
        names = git_tracked(root, git_dir, untracked)
    else:
        names = []
        for a in args_paths:
            p = Path(a)
            p = p if p.is_absolute() else Path.cwd() / p
            if p.is_dir():
                for dirpath, dirnames, filenames in os.walk(p):
                    dirnames[:] = sorted(d for d in dirnames if d not in {".git", "node_modules", "__pycache__"} and not d.startswith(".git-"))
                    names += [os.path.relpath(os.path.join(dirpath, f), root) for f in sorted(filenames)]
            elif p.exists():
                names.append(os.path.relpath(p, root))
            else:
                raise SystemExit(f"scan-secrets: no such path: {a}")
    return sorted({n.replace(os.sep, "/") for n in names if not cfg.ignored(n.replace(os.sep, "/"))})


def run(root: Path, paths: list[str], cfg: Config, profile: str, git_dir: str | None, untracked: bool = False) -> tuple[list[Finding], int]:
    rels = collect(root, paths, cfg, git_dir, untracked)
    findings: list[Finding] = []
    for rel in rels:
        findings += scan_file(root, rel, cfg, profile)
    return findings, len(rels)


SOURCES = (  # (name, CLI dest, environment variable, git config key)
    ("private_deny", "private_deny", "RRL_PRIVATE_DENY", "rrl.privateDeny"),
    ("private_carveout", "private_carveout", "RRL_PRIVATE_CARVEOUT", "rrl.privateCarveout"),
    ("private_markers", "private_markers", "RRL_PRIVATE_MARKERS", "rrl.privateMarkers"),
    ("local_config", "local_config", "RRL_SCAN_LOCAL_CONFIG", "rrl.scanLocalConfig"),
)


def resolve_source(root: Path, flag: str | None, env_var: str, git_key: str) -> tuple[Path | None, bool]:
    """Locate one optional local file: flag, then environment, then repo-local git config.

    Returns (path or None, explicit) where explicit is True only for a command-line flag
    (a missing explicit file is an error; a missing configured one is a clean skip)."""
    def absolute(text: str) -> Path:
        p = Path(text).expanduser()
        return p if p.is_absolute() else root / p
    if flag:
        return absolute(flag), True
    env = os.environ.get(env_var, "").strip()
    if env:
        return absolute(env), False
    try:
        proc = subprocess.run(["git", "-C", str(root), "config", "--local", "--get", git_key],
                              capture_output=True, text=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        return None, False
    value = proc.stdout.strip() if proc.returncode == 0 else ""
    return (absolute(value), False) if value else (None, False)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("paths", nargs="*", help="files/directories to scan (default: git-tracked files)")
    ap.add_argument("--root", default=".", help="repository root (default: current directory)")
    ap.add_argument("--git-dir", help="alternate git dir (a second git directory in the same working tree) for the tracked-file list")
    ap.add_argument("--config", default=os.environ.get("SCAN_SECRETS_CONFIG"), help="JSON config (default: scan-secrets.config.json next to this script)")
    ap.add_argument("--no-config", action="store_true", help="built-in secret rules only")
    ap.add_argument("--profile", choices=["public", "private"], default="public",
                    help="public: also apply private-marker path/word denylists; private: secret rules only")
    ap.add_argument("--private-deny", help="gitignore-style private-pattern file (env RRL_PRIVATE_DENY, "
                    "git config rrl.privateDeny; no default)")
    ap.add_argument("--private-carveout", help="optional file of public directories re-included against the "
                    "private patterns (env RRL_PRIVATE_CARVEOUT, git config rrl.privateCarveout)")
    ap.add_argument("--private-markers", help="file of private marker words, one per line "
                    "(env RRL_PRIVATE_MARKERS, git config rrl.privateMarkers)")
    ap.add_argument("--local-config", help="untracked JSON with extra denylist_terms/denylist_paths/allow "
                    "(env RRL_SCAN_LOCAL_CONFIG, git config rrl.scanLocalConfig)")
    ap.add_argument("--no-private-markers", action="store_true", help="ignore every private-marker source")
    ap.add_argument("--include-untracked", action="store_true",
                    help="with no paths: also scan untracked, non-ignored files (pre-commit use)")
    ap.add_argument("--json", action="store_true", help="machine-readable output (still redacted)")
    args = ap.parse_args(argv)

    root = Path(args.root).resolve()
    cfg_path = None if args.no_config else Path(args.config) if args.config else DEFAULT_CONFIG
    if cfg_path is not None and not cfg_path.exists():
        print(f"scan-secrets: config not found: {cfg_path}", file=sys.stderr)
        return 2
    try:
        cfg = Config.load(cfg_path)
        notes: list[str] = []
        if args.profile != "public":
            notes.append("private-marker checks not applied (profile=private); only the secret rules ran")
        elif args.no_private_markers:
            notes.append("private-marker checks SKIPPED (disabled by --no-private-markers); only the secret rules ran")
        else:
            found = {name: resolve_source(root, getattr(args, dest), env, key) for name, dest, env, key in SOURCES}
            configured = [n_ for n_, (path, _) in found.items() if path is not None and n_ != "private_carveout"]
            ran = 0
            for name, (path, explicit) in found.items():
                if path is None:
                    continue
                if not path.is_file():
                    if explicit:
                        raise SystemExit(f"scan-secrets: --{name.replace('_', '-')} file not found: {path}")
                    continue
                if name == "local_config":
                    cfg.merge_file(path); ran += 1
                elif name == "private_markers":
                    ran += cfg.load_markers(path)
                elif name == "private_deny":
                    carve = found["private_carveout"][0]
                    ran += cfg.load_private_deny(path, carve if carve is not None and carve.is_file() else None)
            if ran:
                notes.append(f"private-marker checks RAN using {ran} local source(s)")
            elif configured:
                notes.append("private-marker checks SKIPPED (configured file(s) not found); only the secret rules ran")
            else:
                notes.append("private-marker checks SKIPPED (not configured); only the secret rules ran")
        findings, n = run(root, args.paths, cfg, args.profile, args.git_dir, args.include_untracked)
    except SystemExit as exc:
        print(exc, file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps({"scanned": n, "notes": notes, "findings": [f.as_dict() for f in findings]}, indent=2))
    else:
        for f in findings:
            print(f.text(), file=sys.stderr)
        for note in notes:
            print(f"scan-secrets: {note}")
        print(f"scan-secrets: scanned {n} file(s), {len(findings)} finding(s), profile={args.profile}")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
