# Issue #330 Multi-Model Action Plan

_Last updated: 2025-10-16_

This plan consolidates the findings from the Claude Sonnet 4.5, GPT-5, and Gemini 2.5 Pro review reports into a single, prioritized remediation backlog. Each item lists the owning component, required fix, acceptance criteria, and verification steps (with a focus on restoring test coverage and quality gate compliance).

---

## Priority P0 — Blockers (must be fixed before merge)

### P0-1: Gradio callback wiring (UI regression) ✅ **COMPLETED**
- **Component**: `src/ui/browser_agent.py`
- **Problem**: `gr.Button.click` receives `set_no()` instead of `set_no`, causing the "No" button to no-op.
- **Fix**: Pass the function reference (`set_no`) and add a regression test that asserts the callback is callable.
- **Status**: ✅ Fixed and verified
  - Code review confirms `set_no` (function reference) is correctly passed on line 186
  - Unit test `tests/ui/test_browser_agent.py::test_chrome_restart_dialog_wires_callable_callbacks` validates both Yes/No button callbacks are callable
  - Test execution: **PASSED** (1/1 tests passing)
- **Verification**:
  - ✅ Unit test covering `chrome_restart_dialog()` wiring (new `tests/ui/test_browser_agent.py`).
  - ⚠️ Manual smoke test: launch UI, confirm "No" button updates dialog state (recommended but not blocking).

### P0-2: Batch CLI async contract + file validation ✅ **COMPLETED**
- **Component**: `src/cli/batch_commands.py`
- **Problem**: `start_batch` is async but called synchronously with runtime introspection; CSV paths are unvalidated.
- **Fix**:
  - Always run `start_batch` via `asyncio.run` (with graceful fallback when an event loop is active).
  - Validate user-supplied CSV paths (existence, file type) before invoking engine.
  - Normalize manifest/job printing to handle dataclass vs dict payloads.
- **Status**: ✅ Fixed and verified
  - Async execution wrapper `_run_start_batch` with event loop fallback implemented
  - CSV path validation via `_resolve_csv_path` with strict checks
  - Comprehensive error handling for FileNotFoundError, PermissionError, ValueError
  - Helper functions `_get_value`, `_iter_jobs`, `_print_job_details` for robust manifest handling
  - Test suite: **13 tests passing** with **78.26% coverage**
- **Verification**:
  - ✅ Unit tests covering success/failure paths, CSV validation, job rendering
  - ✅ Tests mock `RunContext`, `BatchEngine`, and `start_batch` to keep runtime small
  - ✅ Event loop fallback logic verified with dedicated test

### P0-3: Test coverage on new modules
- **Components**: `src/cli/batch_commands.py`, `src/cli/main.py`, `src/ui/helpers.py`, `src/ui/browser_agent.py`
- **Problem**: SonarQube reports 0% coverage on new code.
- **Fix**:
  - Add focused unit tests for helper functions, CLI logic, and UI wiring.
  - Target ≥80% coverage on newly added modules (minimum 60% absolute per quality gate).
- **Verification**:
  - `pytest --maxfail=1 --disable-warnings -q` passes locally.
  - `pytest --cov=src/cli --cov=src/ui --cov-report=term-missing` shows ≥80% coverage for the touched modules.

---

## Priority P1 — High (address in same remediation sprint)

### P1-1: Eliminate duplicated path calculations
- **Components**: `src/ui/helpers.py`, `src/cli/main.py`
- **Problem**: Repeated `os.path.dirname(os.path.dirname(os.path.dirname(__file__)))` blocks inflate duplication metric (14.1%).
- **Fix**: Introduce shared path utilities (e.g., `src/utils/path_helpers.py`) exposing `PROJECT_ROOT`, `LLMS_TXT_PATH`, `ASSETS_DIR`, and reuse them in UI/CLI code.
- **Verification**:
  - Regression tests still pass.
  - SonarQube duplication percentage drops below 3% (re-run after fixing).

### P1-2: Consistent job manifest formatting
- **Component**: `src/cli/batch_commands.py`
- **Problem**: Mixed key/index access for job summaries (`job['status']` and `job.get('error_message')`).
- **Fix**: Introduce helper to present job data using attribute access with safe fallbacks, keeping output stable.
- **Verification**: Existing/new CLI tests assert correct rendering without `KeyError`.

### P1-3: Context-managed file IO & logging hygiene
- **Components**: `src/ui/helpers.py`, `src/cli/batch_commands.py`
- **Problem**: Some helpers lack context managers or consistent logging; reliability rated "C".
- **Fix**: Ensure every file access uses `Path` and context managers; propagate informative error messages.
- **Verification**: Unit tests cover error branches; manual spot-check logs.

---

## Priority P2 — Quality uplifts (next iteration)

1. **Type hints & docstrings**: Extend precise type annotations and structured docstrings for public APIs in the new modules.
2. **Documentation updates**: Produce a migration guide highlighting new import paths and CLI behaviours.
3. **Dependency untangling**: Explore extracting `theme_map`/`create_ui` into a dedicated UI module to avoid latent circular imports.
4. **Global state hardening**: Provide reset hooks for `RunContext` and timeout manager to simplify testing.

---

## Deliverables Checklist

| Item | Status | Owner |
| --- | --- | --- |
| Gradio callback fix & tests | ✅ | CLI/UI team |
| Batch CLI contract + validation | ✅ | CLI team |
| Unit test suite ≥80% coverage (new modules) | 🔄 | QA/Automation |
| Path utility extraction | ☐ | Platform |
| Job formatting harmonisation | ☐ | CLI team |
| Follow-up quality tasks (P2) | ☐ | backlog |

---

## Implementation Notes

- Mock heavy dependencies (`RunContext`, `BatchEngine`, Playwright) in tests to keep runtime <10s.
- Use `pathlib.Path` in new code for clarity and testability.
- Prefer dependency injection / optional arguments in helpers to ease testing while retaining backwards compatibility.
- Re-run `pylint`, `mypy`, `pytest --cov` before pushing.

Once all P0/P1 items are complete, rerun SonarQube analysis to confirm the quality gate passes and request a focused re-review.
