#!/usr/bin/env bash
# Fast, CPU-only, network-free checks for this repository. See scripts/ci/README.md.
#
#   bash scripts/ci/run-offline-checks.sh [-x|--fail-fast] [--list] [--only NAME[,NAME...]] [-h]
#
# Runs every step, prints PASS / FAIL / SKIP per step and a summary, and exits
# non-zero if any step failed. A step whose inputs are absent (e.g. a module
# directory that has not landed yet) is skipped with a printed SKIP line, never
# silently. It does not build images, start clusters, or touch the network.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT" || exit 2
PY="${PYTHON:-python3}"
export PYTHONDONTWRITEBYTECODE=1

MODULE_DIRS=(
  examples/ros2-sequence-probe
  examples/lerobot-data-quality
  examples/cloud-robotics/agent-mobility
  experiments/e02-dds-resilience
  experiments/edge-cloud-placement
  experiments/model-serving-fairness
)
# Modules that need a third-party Python package: dir=import-name. The step is SKIPPED (loudly) if it is missing.
declare -A MODULE_REQUIRES=( [experiments/e02-dds-resilience]=yaml )
declare -A MODULE_REQUIRES_HINT=( [yaml]="PyYAML" )
# stdlib-unittest files that live in tests/ (the older pytest files are run separately, if pytest exists)
REPO_TEST_FILES=(test_repo_guard.py test_scan_secrets.py test_offline_checks.py)
PRUNE=(-name .git -o -name '.git-*' -o -name .claude -o -name node_modules -o -name '.venv*' -o -name __pycache__)

fail_fast=0; only=""; list=0
while (( $# )); do
  case "$1" in
    -x|--fail-fast) fail_fast=1 ;;
    --list) list=1 ;;
    --only) shift; only="${1:-}" ;;
    --only=*) only="${1#--only=}" ;;
    -h|--help) sed -n '2,10p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
  shift
done

names=(); results=(); notes=(); n_fail=0
selected() { [[ -z "$only" ]] || [[ ",$only," == *",$1,"* ]]; }
record() { names+=("$1"); results+=("$2"); notes+=("${3:-}"); [[ "$2" == FAIL ]] && n_fail=$((n_fail + 1)); return 0; }
skip() { printf 'SKIP %s: %s\n' "$1" "$2"; record "$1" SKIP "$2"; }

# step NAME CMD... : run CMD (in the current shell's cwd) and record PASS/FAIL
step() {
  local name="$1"; shift
  selected "$name" || return 0
  if (( list )); then echo "$name"; return 0; fi
  if (( fail_fast && n_fail > 0 )); then return 0; fi
  printf '==> %s\n' "$name"
  if "$@"; then printf 'PASS %s\n' "$name"; record "$name" PASS
  else printf 'FAIL %s (exit %s)\n' "$name" "$?" >&2; record "$name" FAIL; fi
}
# maybe_skip NAME REASON : in --list mode print name; return 0 if the step must be skipped
maybe_skip() {
  selected "$1" || return 0
  (( list )) && { echo "$1"; return 0; }
  (( fail_fast && n_fail > 0 )) && return 0
  skip "$1" "$2"
}

# ---- 1. bash syntax (bash -n; never executes the scripts) -------------------
bash_syntax() {
  local f rc=0 n=0
  while IFS= read -r -d '' f; do
    n=$((n + 1))
    bash -n "$f" || { echo "syntax error: $f" >&2; rc=1; }
  done < <(find . \( "${PRUNE[@]}" \) -prune -o -type f -name '*.sh' -print0)
  echo "checked $n shell script(s)"
  (( n > 0 )) || { echo "no shell scripts found" >&2; return 1; }
  return $rc
}
step bash-syntax bash_syntax

# ---- 2. repo-level stdlib unittest files ------------------------------------
repo_tests() {
  local f rc=0 ran=0
  for f in "${REPO_TEST_FILES[@]}"; do
    [[ -f tests/$f ]] || { echo "SKIP tests/$f (absent)"; continue; }
    ran=$((ran + 1))
    "$PY" -I -m unittest discover -s tests -p "$f" || rc=1
  done
  (( ran > 0 )) || { echo "no repo-level unittest files present" >&2; return 1; }
  return $rc
}
if [[ -d tests ]]; then step unittest:tests repo_tests; else maybe_skip unittest:tests "no tests/ directory"; fi

# ---- 3. unittest discovery per module directory ------------------------------
module_tests() {
  local dir="$1" start="." top=()
  if [[ -d "$dir/tests" ]]; then
    start="tests"
    [[ -f "$dir/tests/__init__.py" ]] && top=(-t .)
  fi
  ( cd "$dir" && "$PY" -m unittest discover -s "$start" -p 'test*.py' "${top[@]}" )
}
for d in "${MODULE_DIRS[@]}"; do
  req="${MODULE_REQUIRES[$d]:-}"
  if [[ ! -d "$d" ]]; then maybe_skip "unittest:$d" "directory absent"
  elif [[ -n "$req" ]] && ! "$PY" -c "import $req" 2>/dev/null; then
    maybe_skip "unittest:$d" "needs ${MODULE_REQUIRES_HINT[$req]:-$req}, not installed; this module was NOT tested"
  else step "unittest:$d" module_tests "$d"; fi
done

# ---- 4. the older pytest suite, only if pytest is installed -------------------
if [[ -d tests ]] && "$PY" -c 'import pytest' 2>/dev/null; then
  step pytest:tests "$PY" -m pytest -q -p no:cacheprovider tests
else
  maybe_skip pytest:tests "pytest not installed or no tests/ (the older pytest files were not run)"
fi

# ---- 5. every YAML file parses -------------------------------------------------
yaml_parse() {
  find . \( "${PRUNE[@]}" \) -prune -o -type f \( -name '*.yml' -o -name '*.yaml' \) -print0 \
    | "$PY" -I -c '
import sys, yaml
bad = 0; n = 0
for p in sys.stdin.buffer.read().split(b"\0"):
    if not p: continue
    path = p.decode()
    n += 1
    try:
        with open(path, encoding="utf-8") as fh:
            list(yaml.safe_load_all(fh))
    except Exception as exc:  # noqa: BLE001
        bad += 1
        print("YAML error in %s: %s" % (path, str(exc).splitlines()[0]), file=sys.stderr)
print("parsed %d YAML file(s), %d failed" % (n, bad))
sys.exit(1 if bad else 0)'
}
if "$PY" -c 'import yaml' 2>/dev/null; then step yaml-parse yaml_parse
else maybe_skip yaml-parse "PyYAML not installed"; fi

# ---- 6-8. repository scripts (skipped if absent) -------------------------------
script_step() { # NAME SCRIPT [args...]
  local name="$1" script="$2"; shift 2
  if [[ -f "$script" ]]; then step "$name" "$PY" -I "$script" "$@"
  else maybe_skip "$name" "$script absent"; fi
}
script_step markdown-links scripts/check-markdown-links.py
script_step validate-site scripts/validate-site.py
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  script_step scan-secrets scripts/ci/scan-secrets.py --include-untracked
else
  script_step scan-secrets scripts/ci/scan-secrets.py .
fi

# ---- 9. workflow guard (opt-in until the guard patch has landed) -------------------
if [[ "${RRL_REQUIRE_REPO_GUARD:-0}" == 1 ]]; then
  step workflow-repo-guard "$PY" -I scripts/ci/repo_guard.py check
else
  maybe_skip workflow-repo-guard "opt-in: set RRL_REQUIRE_REPO_GUARD=1 once the private-CI guard patch is applied"
fi

(( list )) && exit 0

# ---- summary -------------------------------------------------------------------
echo
echo "=== offline checks summary ==="
n_pass=0; n_skip=0
for i in "${!names[@]}"; do
  if [[ -n "${notes[$i]}" ]]; then printf '%-4s %s  (%s)\n' "${results[$i]}" "${names[$i]}" "${notes[$i]}"
  else printf '%-4s %s\n' "${results[$i]}" "${names[$i]}"; fi
  [[ "${results[$i]}" == PASS ]] && n_pass=$((n_pass + 1))
  [[ "${results[$i]}" == SKIP ]] && n_skip=$((n_skip + 1))
done
printf 'passed=%d failed=%d skipped=%d\n' "$n_pass" "$n_fail" "$n_skip"
if (( n_fail > 0 )); then echo "RESULT: FAIL" >&2; exit 1; fi
if (( ${#names[@]} == 0 )); then echo "RESULT: no step selected" >&2; exit 2; fi
echo "RESULT: OK (skipped steps were NOT run)"
exit 0
