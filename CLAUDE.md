# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

2bykilt is a Gradio-based browser automation tool built on Playwright. It has a **dual-mode architecture** that is the single most important thing to understand before changing code:

- **Minimal mode (`ENABLE_LLM=false`, the default)**: deterministic browser automation driven by pre-registered actions in `llms.txt`. Zero LLM dependencies — this mode exists so enterprises can deploy without AI-governance review (see `README-MINIMAL.md`).
- **Full mode (`ENABLE_LLM=true`)**: adds an LLM agent (browser-use / langchain) that handles free-form prompts which don't match a pre-registered action.

The default git branch is `2bykilt` (not `main`).

## Commands

```bash
# Setup (full)                          # Setup (minimal / LLM-free)
pip install -r requirements.txt         pip install -r requirements-minimal.txt
playwright install chromium

# Run the UI (Gradio, default http://127.0.0.1:7788)
python bykilt.py                        # --port, --theme, --dark-mode available
./dev.sh start|stop|restart|status|logs # background dev server on port 7861

# Tests — CI-equivalent run (this is what security-ci.yml executes on PRs)
ENABLE_LLM=true python -m pytest -m ci_safe --cov=src --cov-report=term -v

# Unified test entrypoint
./scripts/ci_pytest.sh                  # ci_safe subset (default)
./scripts/ci_pytest.sh full             # full suite
./scripts/ci_pytest.sh marker <name>    # custom marker subset

# Single test (preferred while iterating)
python -m pytest tests/path/to/test_file.py::test_name -xvs --no-cov

# Verify LLM isolation after touching imports (required for minimal-mode safety)
ENABLE_LLM=false python scripts/verify_llm_isolation.py

# Lint / type-check
pylint src/          # .pylintrc
mypy src/            # mypy.ini (Python 3.12)

# llms.txt remote import CLI
python bykilt.py --preview-llms <url>
python bykilt.py --import-llms <url> [--strategy skip|overwrite|rename]
```

### pytest configuration facts

- `pytest.ini` enforces `--maxfail=1`, a **30-second per-test timeout**, coverage on `src/`, `asyncio_mode = auto`, and discovery only under `tests/`.
- Every new test must carry a marker; CI only runs `-m ci_safe`. Markers: `ci_safe` (mocked or headless-Chromium, no user profiles), `local_only` (interactive UI / Edge / macOS paths), `integration`, `playwright_required`, `unit`.
- CI runs with `BYKILT_ENV` **unset** and `ENABLE_LLM=true`. Reproduce locally with `unset BYKILT_ENV` before running the ci_safe subset — a locally-set `BYKILT_ENV` activates dev config overlays that mask CI failures.

## Architecture

### Prompt → execution pipeline (the core flow)

1. `bykilt.py` builds the Gradio UI and delegates to `src/cli/main.py:main()`. Batch CLI commands are intercepted before UI init by `src/cli/batch_commands.py`.
2. A user prompt is first evaluated **without any LLM** by `src/config/standalone_prompt_evaluator.py` / `src/modules/command_dispatcher.py`, which match it against pre-registered actions parsed from `llms.txt` (`src/config/llms_parser.py`, schema-validated by `llms_schema_validator.py`).
3. A matched action is executed by `src/script/script_manager.py` or one of the execution engines in `src/modules/` (`execution_engine.py`, `execution_debug_engine.py`).
4. Only an unmatched prompt falls through to the LLM agent (`src/agent/agent_manager.py` → browser-use), and only when LLM is enabled.

### Action types in `llms.txt`

| Type | Executor | Behavior |
|------|----------|----------|
| `script` | script_manager | Runs a pytest script with `${params.name}` substitution |
| `browser-control` | script_manager | Generates/executes Playwright flows from YAML `flow:` steps |
| `git-script` | script_manager | Clones a repo and runs a script from it |
| `unlock-future` | execution_debug_engine | JSON-based command execution (tab strategies: `active_tab`/`new_tab`) |
| `action_runner_template` | templates/ | Parameterized template runner |

Parameter syntax: `${params.name}` with optional default `${params.name|default}`.

### Configuration system (three layers)

- **Multi-env config**: `config/{base,dev,staging,prod}` selected by `BYKILT_ENV` via `src/config/multi_env_loader.py`. **When `BYKILT_ENV` is unset, only `base` is loaded** (this is the CI condition). CLI: `bykilt-config` (`src/config/config_cli.py`).
- **Feature flags**: `config/feature_flags.yaml` accessed through `src/config/feature_flags.py` (`FeatureFlags.get(...)`, test override via `FeatureFlags.set_override(name, value)`). New user-visible behavior should ship behind a flag. `is_llm_enabled()` bridges the legacy `ENABLE_LLM` env var.
- **Env vars**: `.env` (see `.env.example`). Recording path precedence: UI Browser Settings > `RECORDING_PATH` env > default.

### Run artifacts

`src/runtime/run_context.py` provides the `RunContext` singleton generating a sortable `run_id_base` (override with `BYKILT_RUN_ID` in tests). All artifacts live under `artifacts/runs/<run_id>-art/` — recordings go to its `videos/` subdirectory (legacy `./tmp/record_videos` was removed in Issue #353; don't reintroduce it). Logging follows the JSON Lines spec in `docs/engineering/LOGGING_SPEC.md`. Note: `src/logging/` shadows the stdlib `logging` module — in scripts, `import logging` **before** inserting `src` into `sys.path`.

### Directory map (non-obvious parts only)

- `src/modules/` — command dispatcher, execution engines, llms.txt discovery/merger, handlers
- `src/batch/` — CSV-driven batch execution engine; `src/runner/queue_manager.py` schedules jobs
- `src/llm/` — LLM service gateway + docker sandbox (only loaded in full mode)
- `myscript/` — standalone runnable automation scripts (own CI: `ci-local-selector.yml`)
- `tests/` mirrors `src/`; root-level `tests/test_*.py` are mostly feature/integration tests

### Security CI (see `docs/security/continuous-security.md`)

PRs run `security-ci.yml`: ci_safe tests + SonarCloud, pip-audit gated by `security/security_policy.yaml` (critical/high = 0), gitleaks, dependency-review, and zizmor. CodeQL, OpenSSF Scorecard, Trivy, and SBOM generation (`supply-chain.yml`) run on push/schedule. Vulnerability suppressions in `security/suppressions.yaml` are **time-boxed** — `expires_at` is enforced, so an expired entry resurfaces the vulnerability and can turn CI red.

## Critical invariants

1. **LLM import isolation**: never import `langchain*`, `openai`, `anthropic`, `browser_use`, etc. at module top level in any code reachable in minimal mode. Guard with `is_llm_enabled()` and import lazily inside functions. After touching imports, run `ENABLE_LLM=false python scripts/verify_llm_isolation.py` — CI enforces this.
2. **Marker discipline**: an unmarked test silently never runs in CI. Mark it `ci_safe` unless it genuinely needs a local environment.
3. **Feature-flag deprecations**: several flags in `feature_flags.yaml` are `deprecated: true` kept for compatibility — check before removing or repurposing a flag.

## Testing pitfalls (learned from Issue #340)

- Keep assertions **inside** `with patch(...)` blocks — the patch is gone after the block exits. One indentation level = a different scope.
- Module-level variables (e.g. `ENABLE_LLM` in `bykilt.py`) are evaluated at import time; decorator `@patch` often misses them. Use `with patch(...)` context managers so patch timing is explicit.
- Config-related tests must pass with `BYKILT_ENV` unset (CI condition) and with it set.

## Pre-push checklist

Never push without at least running the modified test files locally (`python -m pytest tests/... -xvs`). For anything touching config, imports, or shared modules, run the full CI simulation: `unset BYKILT_ENV; ENABLE_LLM=true python -m pytest -m ci_safe`. Budget ~2–5 min locally; CI takes ~5–8 min.
