#!/usr/bin/env bash
# Regenerate roadmap derived artifacts & validate (Issue #76 helper)
# Ensure this file has execute permission: chmod +x scripts/regen_dependencies.sh
set -euo pipefail

INPUT=${1:-docs/roadmap/ISSUE_DEPENDENCIES.yml}

python scripts/validate_dependencies.py "$INPUT"
python scripts/gen_mermaid.py "$INPUT" > docs/roadmap/DEPENDENCY_GRAPH.md
python scripts/generate_task_dashboard.py --input "$INPUT" --output docs/roadmap/TASK_DASHBOARD.md
python scripts/generate_task_queue.py --input "$INPUT" --output docs/roadmap/TASK_QUEUE.yml --no-api

# Idempotency check (Mermaid generation) - second run into temp file
TMP=$(mktemp)
python scripts/gen_mermaid.py "$INPUT" > "$TMP"
if ! diff -q "$TMP" docs/roadmap/DEPENDENCY_GRAPH.md >/dev/null; then
  echo "[ERROR] Mermaid graph non-idempotent" >&2
  diff -u "$TMP" docs/roadmap/DEPENDENCY_GRAPH.md || true
  exit 1
fi
rm -f "$TMP"

echo "[OK] Regeneration complete & idempotent"
