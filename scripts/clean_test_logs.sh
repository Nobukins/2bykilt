#!/bin/bash
#
# clean_test_logs.sh - Extended cleanup for logs, coverage, caches, and stale run artifacts.
#
# Usage:
#   ./scripts/clean_test_logs.sh          # perform cleanup
#   ./scripts/clean_test_logs.sh --dry-run # show what would be removed
#
# Safe Idempotent: script skips absent paths. Exits non-zero only on internal errors.
#
set -euo pipefail

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
  echo "[DRY-RUN] Listing targets (no deletions performed)"
fi

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$PROJECT_ROOT"

# Collect targets
TARGETS=(
  "logs/*"
  "artifacts/runs/*/logs"
  "artifacts/runs/*/videos/*.log"
  "htmlcov"
  ".coverage"
  "coverage.xml"
  "reports/coverage*"
  ".pytest_cache"
  "pip-audit-raw.json"
  "pip-audit-normalized.json"
  "tmp/*"
)

# Dynamic stale run dirs pattern (older test run prefixes)
TARGETS+=(
  "artifacts/runs/TEST*-art"
  "artifacts/runs/*-art/tmp"
)

remove_path() {
  local path="$1"
  if compgen -G "$path" > /dev/null; then
    if $DRY_RUN; then
      echo "Would remove: $path"
    else
      rm -rf $path
      echo "Removed: $path"
    fi
  fi
}

echo "Cleaning extended test logs & coverage artifacts..."
for t in "${TARGETS[@]}"; do
  remove_path "$t"
done

echo "✅ Cleanup complete ($([[ $DRY_RUN == true ]] && echo DRY-RUN || echo EXECUTED))"