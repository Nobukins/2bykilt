#!/usr/bin/env bash
set -euo pipefail
# Unified entrypoint for CI and local selective test runs.
# Usage:
#   ./scripts/ci_pytest.sh            # run ci_safe subset with coverage (default)
#   ./scripts/ci_pytest.sh full       # run full test suite with coverage
#   ./scripts/ci_pytest.sh marker <m> # run custom marker subset <m>
# Environment:
#   EXTRA_PYTEST_ARGS  Additional args to append (optional)

MODE="ci"
CUSTOM_MARKER=""
if [[ "${1:-}" == "full" ]]; then
  MODE="full"
elif [[ "${1:-}" == "marker" ]]; then
  MODE="marker"
  shift || true
  CUSTOM_MARKER="${1:-}" || true
fi

CFG_FILE="pytest.ini"  # rely on root config
if [[ ! -f "${CFG_FILE}" ]]; then
  echo "[FATAL] Root pytest.ini not found. Abort." >&2
  exit 2
fi

COVERAGE_CMD=(python -m pytest -c "${CFG_FILE}")
BASE_ARGS=()

case "$MODE" in
  ci)
    BASE_ARGS+=( -m ci_safe )
    ;;
  full)
    # no marker restriction
    ;;
  marker)
    if [[ -z "${CUSTOM_MARKER:-}" ]]; then
      echo "[FATAL] marker mode selected but no marker provided" >&2
      exit 3
    fi
    BASE_ARGS+=( -m "${CUSTOM_MARKER}" )
    ;;
esac

# Always show first error fast in CI subset to keep feedback short; allow override for full.
if [[ "$MODE" == "ci" ]]; then
  BASE_ARGS+=( --maxfail=1 )
fi

# Append user-provided extra args
if [[ -n "${EXTRA_PYTEST_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  EXTRA_ARR=(${EXTRA_PYTEST_ARGS})
  BASE_ARGS+=( "${EXTRA_ARR[@]}" )
fi

echo "[INFO] Running mode=$MODE marker=${CUSTOM_MARKER:-} config=${CFG_FILE}" >&2
set -x
if ((${#BASE_ARGS[@]})); then
  "${COVERAGE_CMD[@]}" "${BASE_ARGS[@]}"
else
  "${COVERAGE_CMD[@]}"
fi
set +x

# Generate/refresh coverage xml if coverage data exists
if command -v coverage >/dev/null 2>&1 && [ -f .coverage ]; then
    coverage xml -i -o coverage.xml
else
    echo "[INFO] Coverage data not found, skipping XML generation"
fi

echo "[INFO] Done." >&2
