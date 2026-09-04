# Copilot Instructions for 2bykilt

> **Single source of truth: [`/CLAUDE.md`](../CLAUDE.md).**
> Project architecture, commands, invariants, and testing rules are maintained there
> (shared by Claude Code, Copilot, and other coding agents). This file only pins the
> rules that must never be violated. If this file and CLAUDE.md disagree, CLAUDE.md wins.

## Non-negotiable rules

1. **Dual-mode integrity**: code reachable with `ENABLE_LLM=false` must not import LLM
   packages (`langchain*`, `openai`, `anthropic`, `browser_use`, …) at module top level.
   Guard with `is_llm_enabled()` and lazy imports. Verify:
   `ENABLE_LLM=false python scripts/verify_llm_isolation.py`
2. **Test markers**: every test needs a pytest marker; CI only runs `-m ci_safe`.
   An unmarked test silently never runs in CI.
3. **CI-equivalent testing before push**: run at minimum the modified test files
   (`python -m pytest tests/... -xvs`). For config/import/shared-module changes:
   `unset BYKILT_ENV; ENABLE_LLM=true python -m pytest -m ci_safe`
4. **Patch scope**: keep assertions inside `with patch(...)` blocks; use context
   managers (not decorators) when patching module-level variables (Issue #340).
5. **Artifacts**: all run outputs go under `artifacts/runs/<run_id>-art/`; do not
   reintroduce legacy recording paths (Issue #353).
6. The default branch is `2bykilt`.
