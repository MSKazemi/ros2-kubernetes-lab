# Offline checks and CI helpers

Small, standard-library tools that run on a laptop or a CI runner: CPU only, no
network, no Docker, no Kubernetes cluster. They are **static and unit-level
checks**. A green run does not show that ROS 2 messages cross nodes, that an image
builds, or that a cluster starts.

| File | Purpose |
|---|---|
| `run-offline-checks.sh` | one entry point that runs the fast checks below and prints PASS / FAIL / SKIP per step |
| `scan-secrets.py` | scan tracked files for credentials and for material that must stay private |
| `scan-secrets.config.json` | neutral shipped config for the scanner (ignored paths; empty denylists and allowlist) |
| `repo_guard.py` | add or verify a job-level `github.repository` guard in `.github/workflows/*.yml` |

## Run everything

```sh
bash scripts/ci/run-offline-checks.sh          # all steps, keep going, summary at the end
bash scripts/ci/run-offline-checks.sh -x       # stop at the first failing step
bash scripts/ci/run-offline-checks.sh --list   # print the step names
bash scripts/ci/run-offline-checks.sh --only bash-syntax,yaml-parse
```

Exit status: `0` all executed steps passed, `1` at least one step failed, `2` usage error.

| Step | What it runs |
|---|---|
| `bash-syntax` | `bash -n` on every `*.sh` (nothing is executed) |
| `unittest:tests` | the stdlib `unittest` files in `tests/`: `test_repo_guard.py`, `test_scan_secrets.py`, `test_offline_checks.py` |
| `unittest:<dir>` | `python3 -m unittest discover` inside each of `examples/ros2-sequence-probe`, `examples/lerobot-data-quality`, `examples/cloud-robotics/agent-mobility`, `experiments/e02-dds-resilience`, `experiments/edge-cloud-placement`, `experiments/model-serving-fairness` (uses `<dir>/tests` if present, otherwise `<dir>`). `experiments/e02-dds-resilience` needs PyYAML and prints `SKIP ... NOT tested` if it is not installed; CI should install it explicitly |
| `pytest:tests` | the older pytest suite in `tests/`, only if `pytest` is importable |
| `yaml-parse` | every `*.yml` / `*.yaml` parses with PyYAML (multi-document files are fine) |
| `markdown-links` | `python3 scripts/check-markdown-links.py` |
| `validate-site` | `python3 scripts/validate-site.py` |
| `scan-secrets` | `scripts/ci/scan-secrets.py` over tracked and untracked, non-ignored files |
| `workflow-repo-guard` | opt-in: runs only with `RRL_REQUIRE_REPO_GUARD=1` (see below) |

Rules that matter when reading the output:

- A missing directory or script prints `SKIP <step>: <reason>`. A skipped step was **not run**; the final line says so.
- A module directory that exists but contains **no tests** is a **FAIL** (`Ran 0 tests`), not a pass.
- The `.git`, `.git-*` (other git directories; `.github` is **not** pruned), `.claude`, `node_modules`, `.venv*` and `__pycache__` directories are never searched.
- Set `PYTHON=/path/to/python3` to choose the interpreter. `pytest` and `PyYAML` are optional; without them the matching step is skipped.
- The script sets `PYTHONDONTWRITEBYTECODE=1` and writes nothing into the repository.

## Secret and private-material scan

```sh
python3 scripts/ci/scan-secrets.py                          # git-tracked files, public profile
python3 scripts/ci/scan-secrets.py --include-untracked      # also new, not-yet-added files
python3 scripts/ci/scan-secrets.py docs/ site/              # only these paths
python3 scripts/ci/scan-secrets.py --profile private        # secret rules only (no private-marker checks)
python3 scripts/ci/scan-secrets.py --git-dir <other-gitdir>  # list files from another git directory
```

Exit status: `0` clean, `1` findings (or skipped files with `--fail-on-skipped`), `2` usage or configuration error.

**Findings never contain the matched text.** Each line is
`path:line: rule-id: description [value redacted, N chars]`. Private denylist terms are
also never echoed, because a CI log is often public. `--json` output is redacted the same way.

Detected: private-key headers; AWS access key ids and secret-key assignments; GitHub,
Slack and Hugging Face tokens and Slack webhook URLs; JWT-shaped tokens; kubeconfig
client keys and user tokens (and whole kubeconfig files); `kubeadm join` tokens and CA
hashes; Docker auth blobs; bearer tokens; `*_SECRET` / `*_TOKEN` / `*_PASSWORD`
assignments with a non-placeholder, high-entropy value; tracked `.env`, `*.pem`, `*.key`,
`id_rsa`, `admin.conf`, `join-command.sh` and similar file names (`.env.example` is allowed).

A value counts as a placeholder only when the **whole value** is one: `${{ secrets.X }}`, `<your-token>`,
`${VAR}`, `$(cmd)`, `{{ var }}`, `secrets.X`, `os.environ[...]`, `changeme`, a run of `x`/`*`/`.`, a token
prefix followed by `xxxxxxxx`, the AWS documentation example keys, or words drawn only from a placeholder
vocabulary such as `your-secret-access-key-goes-here-1234`. A real-looking value that merely *contains*
`example`, `todo`, `dummy` and the like is still reported. Low-entropy values and key names that merely
contain the word (`TOKEN_FILE`, `secretFieldSelector`) are not reported either.

With the `public` profile (default) the scanner can also flag **private-marker** paths and
words. Nothing private is stored in any tracked file and there is **no default path**. Each
input is an optional local file whose location is looked up in this order: command-line flag,
environment variable, then the repository-local git config key (a path relative to the
repository root, set with `git config --local <key> <path>`).

| Input | Flag | Environment variable | Git config key | Content |
|---|---|---|---|---|
| private path patterns | `--private-deny` | `RRL_PRIVATE_DENY` | `rrl.privateDeny` | gitignore-style lines; a pattern matches a path or any parent directory |
| carve-outs (optional) | `--private-carveout` | `RRL_PRIVATE_CARVEOUT` | `rrl.privateCarveout` | one public directory per line, re-included against patterns that match at or above it; nested denies below it still apply |
| marker words | `--private-markers` | `RRL_PRIVATE_MARKERS` | `rrl.privateMarkers` | one literal word per line (`#` comments), matched case-insensitively as whole words in any scanned file |
| local config | `--local-config` | `RRL_SCAN_LOCAL_CONFIG` | `rrl.scanLocalConfig` | same JSON schema as the shipped config: extra `denylist_terms`, `denylist_paths`, `allow` |

Path hits are reported under the neutral rule id `private-marker-denylist`; word hits use
`private-marker-term` (or the `id` given in the local config). Neither the patterns nor the
words are ever printed. A flag that names a missing file is an error (exit 2); a missing file
named by the environment or git config is a clean skip.

The scanner prints exactly one line about these checks: `private-marker checks RAN using N
local source(s)`, or `private-marker checks SKIPPED (not configured); only the secret rules
ran` (also used in CI and on forks, where nothing is configured), or `SKIPPED (configured
file(s) not found)`. A skipped run never claims the checks ran. `--no-private-markers` and
`--profile private` switch the checks off.

Suppress one line with the comment `scan-secrets: ignore` on that line, or add an
`allow` entry (`{"path": "glob", "rule": "rule-id or *", "reason": "..."}`) to the config.
### Coverage: what was and was not scanned

Text files up to a hard cap (25 MiB, change with `--max-mb`) are scanned in windows of about
1 MiB that overlap by 8 KiB, so a token that straddles a window cut is still found (a token
longer than the overlap could be missed; real credentials are far shorter). Windows end at a
newline when possible, so normal lines are never split. Line numbers stay exact.

Content that is **not** scanned is never dropped silently. The status line counts it by category:

    scan-secrets: scanned 376 file(s), skipped 27 (binary: 27), 0 finding(s), profile=public

Categories: `binary` (a NUL byte in the first 8 KiB), `over-cap`, `unreadable`, `symlink`,
`missing` (listed by git but absent on disk). File-name rules still apply to skipped files.
`--list-skipped` prints their paths. `--fail-on-skipped` (default off) exits 1 when anything was
skipped; give a comma list (`--fail-on-skipped=over-cap,unreadable`) to fail only for those
categories, which is the useful form here because tracked images and PDFs are legitimately binary.

This is a pattern scanner. It finds common, recognisable credential shapes; it does not
prove a repository is free of secrets, and it does not replace rotating a credential that
was ever committed.

## Workflow repository guard

The private mirror of this repository tracks the same workflow files as the public one
but must execute and publish nothing. `repo_guard.py` makes every job start with
`if: github.repository == 'MSKazemi/robo-resilience-lab' && (<original condition>)`.

```sh
python3 scripts/ci/repo_guard.py check                       # verify (needs PyYAML); exit 1 if a job is unguarded
python3 scripts/ci/repo_guard.py apply --dry-run             # show what would change
python3 scripts/ci/repo_guard.py apply                       # rewrite .github/workflows/* in place (idempotent)
python3 scripts/ci/repo_guard.py apply --repo OWNER/NAME     # a different canonical repository
```

`check` and `apply` parse each condition (`&&`, `||`, `!`, comparisons, parentheses, string
literals, optional `${{ }}`) and accept a job only if the guard is a top-level AND-conjunct of the
**whole** condition. `g`, `g && (a)`, `g && a && b`, `(g) && a` and `g && (a || b)` pass.
`g && a || b` does not, because `&&` binds tighter than `||` and that means `(g && a) || b`,
which runs in any repository; `a || g`, `!g && a`, `g != 'x'` and a guard text inside a string
literal fail too, and so does anything the parser cannot read.

`${{ }}` is removed only when it is one wrapper around the whole condition. Text outside it
(`${{ a }} && ${{ b }}`) makes `apply` stop with an error naming the file and job (exit 2, file untouched)
and `check` report the job as unguarded; fix those by hand.

`apply` edits text, so comments, SHA pins and ordering are kept. It refuses (exit 2) to
touch a job whose `if:` is a block scalar, quoted, multi-line or carries a trailing
comment; edit those by hand. Step-level `if:` lines are left alone.

A job guard is a **safety measure**. It does not prove GitHub Actions is disabled in the
private repository: the workflows still start and report skipped jobs. Disabling Actions
there is a repository setting that needs the owner's explicit approval.

## Tests

```sh
python3 -m unittest discover -s tests -p 'test_repo_guard.py'
python3 -m unittest discover -s tests -p 'test_scan_secrets.py'
python3 -m unittest discover -s tests -p 'test_offline_checks.py'
```

All three use only the standard library (`test_repo_guard.py` also needs PyYAML and skips
without it), take a few seconds in total, and write only to temporary directories. The
test files build their synthetic "secrets" from fragments at run time so they pass their
own scan.
