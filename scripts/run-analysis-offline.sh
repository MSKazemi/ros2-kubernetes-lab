#!/usr/bin/env bash
# Reproduce the historical offline analysis from the committed samples only.
# No cluster, Prometheus or network is used. Outputs go to DataAnalysis/output/ (not tracked).
#
# Usage:
#   bash scripts/run-analysis-offline.sh            # use ./.venv if present, else current python3
#   PYTHON=/path/to/venv/bin/python bash scripts/run-analysis-offline.sh
#   bash scripts/run-analysis-offline.sh --no-tests # skip the pytest smoke tests
#
# Steps: (1) summary CSV for every committed sample, (2) the existing namespace CPU plot,
# (3) the offline pytest suite. Notebooks are NOT executed: they need a live Prometheus and
# data that is not in the repository (see DataAnalysis/README.md).
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_root"

run_tests=1
for arg in "$@"; do
  case "$arg" in
    --no-tests) run_tests=0 ;;
    -h|--help) sed -n '2,12p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

py="${PYTHON:-}"
if [[ -z "$py" ]]; then
  if [[ -x "$repo_root/.venv/bin/python" ]]; then py="$repo_root/.venv/bin/python"; else py="python3"; fi
fi

if ! "$py" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 12) else 1)'; then
  echo "ERROR: Python >= 3.12 required (the pinned numpy needs it); got: $("$py" --version 2>&1)" >&2
  exit 1
fi
if ! "$py" -c 'import matplotlib' 2>/dev/null; then
  echo "ERROR: matplotlib missing. Create the environment first:" >&2
  echo "  python3 -m venv .venv && .venv/bin/pip install -r DataAnalysis/requirements-offline.txt" >&2
  exit 1
fi

out="$repo_root/DataAnalysis/output"
mkdir -p "$out"

echo "== 1/3 summary CSV for every committed sample =="
while IFS= read -r sample; do
  "$py" DataAnalysis/analyze_sample.py --sample "$sample" --out-dir "$out"
done < <("$py" DataAnalysis/analyze_sample.py --list)

echo "== 2/3 namespace CPU plot (existing script) =="
"$py" DataAnalysis/plot_namespace_cpu.py --out "$out/namespace_cpu.png"

if (( run_tests )); then
  echo "== 3/3 offline tests =="
  "$py" -m pytest DataAnalysis
else
  echo "== 3/3 offline tests skipped (--no-tests) =="
fi

echo "Done. Artifacts in $out:"
ls -1 "$out"
