# Test Execution Guide

This guide documents how to run, filter, and maintain the 2bykilt test suite after the async stabilization & skip reduction work (106 → 31 skips).

## Quick Start

```bash
# Run full suite (fastest typical path) – skips env-gated tests automatically
pytest -q

# Focus on batch engine (recently refactored async logic)
pytest tests/test_batch_engine.py -v

# Run only non-LLM unit-ish layers (safe in minimal env)
pytest -m "not integration and not local_only" -q
```

## Environment Flags & Their Effects

| Variable | Values | Effect |
|----------|--------|--------|
| ENABLE_LLM | true/false | Enables LLM-dependent tests (currently 1 test skipped when false) |
| RUN_LOCAL_FINAL_VERIFICATION | 1 unset | Enables heavy local verification tests (UI/browser + recording) |
| RUN_LOCAL_INTEGRATION | 1 unset | Enables broader integration tests (network/browser/profile) |

Unset values are treated as disabled.

## Remaining Skip Categories (Snapshot)

| Category | Approx Count | Reason | Re-enable Path |
|----------|--------------|--------|----------------|
| LLM-dependent | 1 | Requires model + tokens | Set ENABLE_LLM=true |
| local_only (final verification) | ~10 | Long-running / interactive | Export RUN_LOCAL_FINAL_VERIFICATION=1 |
| integration | ~12 | Browser/env dependent & slower | Export RUN_LOCAL_INTEGRATION=1 |
| git_script_integration (mocking gap) | 8 | Resolver injection not mockable yet | Refactor get_git_script_resolver (planned) |

Exact counts may shift slightly as tests evolve.

## Typical Test Layers / Markers (Current State)

Project already uses pragmatic environment gating; a future issue (#81) proposes formal marker taxonomy (unit, integration, browser, slow, etc.). Until then:

- local_only: Explicitly opt-in heavy / environment sensitive tests
- integration: Broader multi-component flows
- (future) browser, unit, slow: To be added per #81 acceptance criteria

## Running Specific Layers

```bash
# Opt into integration tests
RUN_LOCAL_INTEGRATION=1 pytest -m integration -v

# Opt into final verification
RUN_LOCAL_FINAL_VERIFICATION=1 pytest -m local_only -v

# Include LLM tests
ENABLE_LLM=true pytest -m "not local_only" -v
```

### Artifact capture integration checks

The browser automation pipeline now has a focused regression around artifact generation. It exercises both the script-based demo runner and the direct browser-control flow, asserting that screenshots, element captures, and recordings are persisted in the run directory. Run it locally with integration tests enabled:

```bash
RUN_LOCAL_INTEGRATION=1 pytest tests/integration/test_artifact_capture.py -vv
```

The suite writes to a temp `ARTIFACTS_BASE_DIR`, so existing local artifacts are untouched. On success you should see one `*-art` run folder per test containing `screenshots/`, `elements/`, and `videos/` entries plus the standard `manifest_v2.json`.

## Async Test Conventions

All new async tests should:

1. Be declared with `async def test_*` when awaiting async code directly.
2. Avoid manual event loop creation/closing – rely on pytest-asyncio auto mode.
3. Ensure any background tasks (e.g., spawned via `asyncio.create_task`) are awaited or canceled explicitly in the test body or fixture finalizer.
4. Use temporary directories (`tmp_path`) and avoid persisting state in `artifacts/` unless the test asserts on artifact outputs.

## Artifact & Log Cleanup

Two cleanup scripts (existing + new) help ensure hermetic test runs:

```bash
# Remove run-specific artifact directories & pytest cache
./scripts/clean_test_artifacts.sh

# Remove logs, coverage, htmlcov, and residual run dirs (dry run first)
./scripts/clean_test_logs.sh --dry-run
./scripts/clean_test_logs.sh
```

Recommended before large refactors or when investigating flakiness.

## Common Commands

```bash
# Verbose skip reasons (inventory)
pytest -rs -q

# Single test debug
pytest tests/test_batch_engine.py::TestStartBatch::test_creates_new_batch -vv

# Fail fast & show locals
pytest -x --showlocals

# Only modified tests since main
pytest $(git diff --name-only origin/main | grep '^tests/' | tr '\n' ' ')
```

## Adding New Tests – Checklist

- [ ] Use deterministic data (no real network unless integration-marked)
- [ ] Prefer factories/fixtures for complex objects
- [ ] Clean up artifacts or write to tmp_path
- [ ] Avoid real sleeps > 0.1s (use async timeouts / monkeypatch) unless integration
- [ ] If test requires environment asset (browser/profile) – gate with env flag

## Metrics Related Testing

Batch engine metrics now include `batch_jobs_stopped`. When expanding metrics:

- Provide a `_record_*` helper mirroring `_record_batch_stop_metrics` pattern
- Patch/spy metric collector in tests for assertion isolation

## Dealing With git_script_integration Skips

Current blockers: Mocking `get_git_script_resolver` and side effects of cloning/copying. Planned approach (post-PR):

- Introduce resolver injection via fixture or parameter
- Provide lightweight in-memory or tempdir fake repo
- Remove class-level skips incrementally

## Failure Triage Flow

1. Re-run with `-vv -k failing_test_name` to isolate
2. If async warning appears: ensure the test function is async & awaited
3. If artifacts mismatch: run cleanup scripts and retry
4. If event loop RuntimeError: check for manual loop manipulation or lingering tasks
5. If path errors inside simulation: ensure job manifest includes required task/command structure

## Roadmap Links

- Issue #263: Event loop teardown/runtime stabilization (addressed by async refactors & ordering rules)
- Issue #101: Recording stability & generation – baseline stabilized, further refinements future scope
- Issue #81: Test layering & marker formalization – next structural enhancement

## Known Gaps (Post-Work)

| Gap | Impact | Planned Remedy |
|-----|--------|----------------|
| Missing formal marker schema | Harder selective CI matrix | Implement per #81 |
| git_script resolver not injectable | 8 tests skipped | Refactor factory + fixture |
| Single remaining LLM skip | Minor coverage gap | Enable in LLM-capable CI lane |

## Suggested CI Profiles (Future)

| Profile | Command | Purpose |
|---------|---------|---------|
| fast | `pytest -m "not integration and not local_only"` | PR gating |
| extended | `RUN_LOCAL_INTEGRATION=1 pytest -m "integration and not local_only"` | Nightly/integration |
| full | `ENABLE_LLM=true RUN_LOCAL_*=1 pytest` | Exhaustive / manual release gate |

## Appendix – Legacy Cleanup Note

Simulation tests previously assumed lightweight automation stubs; the engine now executes real automation flow requiring valid task/command fields. Old assumptions were updated; future changes should keep simulation test semantics aligned with engine contract evolution.

---
Maintainers: Update this document whenever skip policy, markers, or environment flags change.
