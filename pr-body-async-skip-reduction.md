# PR: Async Stabilization & Skip Reduction (106 → 31) + Test Guide & Cleanup Tooling

Related Issues: #263, #101, #81

## Summary
This PR stabilizes the async batch/recording test surface, introduces missing metrics logic, removes obsolete skip decorators, and documents a sustainable test execution process. Net result: skipped tests reduced from 106 to 31 (only environment / LLM / unresolved git-script resolver cases remain), with zero failing tests under `ENABLE_LLM=false`.

## Key Changes
- Added `_record_batch_stop_metrics` to batch engine (previously missing, caused silent metric gaps)
- Converted large block of batch engine tests to proper `async def` with awaited calls
- Removed 70+ blanket skips (three class-level decorators) across `tests/test_batch_engine.py`
- Updated simulation tests to reflect new automation contract (task/command now required)
- Unskipped and validated batch summary tests
- Added `docs/test-execution-guide.md` centralizing commands, flags, skip rationale, roadmap
- Added `scripts/clean_test_logs.sh` (extended cleanup: logs, coverage, caches, stale runs)
- Linked guide from `README.md` with concise environment flag & skip policy summary

## Before vs After
| Metric | Before | After |
|--------|--------|-------|
| Total Tests (collected) | (baseline run) | (unchanged materially) |
| Skipped | 106 | 31 |
| Failing | Multiple async & teardown errors | 0 |
| XFailed | 1 | 1 |
| Event loop warnings | Frequent | Eliminated in target scope |

> Remaining skips are intentional (env-gated integration, local_only heavy UI, git script resolver gap, LLM feature disabled).

## Issues Alignment
- #263 (Event loop teardown instability): Addressed by ensuring all affected tests are fully async + removing manual loop interference via simulation adjustments.
- #101 (Recording stability): Baseline stabilized; recording-related tests now rely on consistent artifact cleanup; future enhancements tracked separately.
- #81 (Test layering & markers): Laid groundwork with guide + environment flag documentation; formal marker taxonomy still pending (follow-up item).

## Follow-Up Actions (Deferred)
| Item | Rationale |
|------|-----------|
| Refactor git script resolver for injection | Unskip 8 git_script_integration tests |
| Introduce formal markers (unit, integration, browser, slow, etc.) | Fulfill #81 acceptance criteria |
| Add nightly full-suite workflow & skip reason dashboard | Visibility into env-gated coverage |
| Enable LLM test lane | Expand functional coverage when tokens available |

## Testing Notes
Performed full run under `ENABLE_LLM=false`; validated metrics, artifact isolation, and absence of lingering coroutine warnings. Regression risk considered low: code changes confined to test async signatures + additive metrics method.

## New Scripts
- `scripts/clean_test_logs.sh`: Dry-run support; removes logs, coverage, htmlcov, pytest cache, stale run directories

## Documentation
- `docs/test-execution-guide.md`: Environment flags, layer strategy, skip snapshot, failure triage, roadmap links
- README updated with quick test section & cleanup commands

## Risk Mitigation
- No production logic modifications beyond additive metrics helper
- Async conversions localized to test suite; engine logic invoked identically
- Cleanup scripts are opt-in; safe (idempotent patterns with glob checks)

## How to Validate Locally
```
# Minimal env
export ENABLE_LLM=false
pytest -q

# View skip inventory
pytest -rs -q | grep -i skipped || true

# Batch engine focus
pytest tests/test_batch_engine.py -v
```

## Screenshots / Logs
(If needed attach CI run summary showing 550 passed / 31 skipped / 1 xfailed.)

## Request
Please review:
1. Test guide clarity & placement
2. Scope of async conversions (no accidental logic change)
3. Metrics helper naming consistency
4. Appropriateness of remaining skip categorization

Feedback on marker taxonomy staging (pre-#81) welcome.

---
Maintainers: after merge, create follow-up issue for git script resolver injection if not already tracked.
