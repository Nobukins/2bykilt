# Issue: Async / Browser Integration Test Stability & Scope Separation

Identifier: (proposed) #NEW (follow-up after Issue #31 design PR)

Status: Open

Priority: Medium (blocks reliable full-suite CI but not design-phase logging work)

Wave: A2 (post-#31)

## Summary

Full test suite execution revealed multiple async event loop teardown errors and environment-dependent browser/profile test failures (Edge/Chrome profile paths). These are unrelated to logging design (Issue #31) and should be isolated into a dedicated stabilization effort.

## Observed Failures (from local full run on 2025-08-30)

- 14 test failures & 12 teardown errors centered on:
  - RuntimeError: This event loop is already running / Cannot close a running event loop / Runner is closed
  - Browser launcher / GitScriptAutomator / real Edge integration tests requiring local browser environment
  - Profile path FileNotFoundError / SeleniumProfile path validation
- Warnings: PytestUnhandledCoroutineWarning, loop cleanup RuntimeWarnings, indicates mismatch between async tests & pytest-asyncio configuration.

## Root Cause Hypotheses

1. pytest-asyncio mode set to strict causing conflicts with anyio & custom async fixtures.
2. Environment assumptions (installed Edge, existing profile directories) not guarded by conditional skips.
3. Async tests mixing manual event loop management with framework-managed loops leading to double-run/close.
4. Lack of segregation between fast contract/unit tests and heavy integration/browser tests in CI gating.

## Impact

- Full suite instability hinders confidence and slows iteration.
- Sonar/coverage jobs may be noisy if full suite required in future pipelines.
- Risk of masking genuine regressions in unrelated domains.

## Proposed Scope of This Issue

Establish a stable, layered test strategy and remediate async fixture usage.

### Deliverables

1. Test Layering:
   - Define markers: unit, logging_spec, integration, browser, slow.
   - Update CI to run: unit + logging_spec (+ optional integration smoke) by default.
2. Async Infrastructure:
   - Adopt `asyncio_mode = auto` (already provisional) or explicitly decorate async tests with @pytest.mark.asyncio.
   - Audit fixtures to avoid manual loop close during active tasks.
3. Conditional Skips:
   - Introduce helper `tests/helpers/env_checks.py` with functions (has_edge(), has_chrome(), profile_available()).
   - Skip browser/profile tests when prerequisites not met (emit informative reason).
4. Fixture Refactor:
   - Centralize browser launch logic; ensure awaited tasks are canceled before loop teardown.
5. Profile Path Handling:
   - Provide temporary directory factory in tests ensuring ProfileManager receives existing paths.
6. Documentation:
   - Update `docs/testing/TEST_STRATEGY.md` with layering & marker matrix.
7. CI Enhancement:
   - Optional nightly workflow runs full suite (with allow-fail first iteration) for visibility.

### Non-Goals

- Implementing browser automation features beyond stabilizing tests.
- Logging feature expansion (covered by Issues #56+).

## Acceptance Criteria

- Running `pytest -m "unit or logging_spec"` passes on clean checkout (no browsers required).
- Running full suite on a dev machine with browsers installed yields zero loop teardown RuntimeError occurrences.
- Browser/profile tests gracefully skip (not fail) when environment prerequisites missing.
- Documented test layer matrix present and referenced from README or CONTRIBUTING.

## Phased Plan

1. Markers & skip guards (fast PR).
2. Async fixture normalization (eliminate manual loop closes; rely on pytest-asyncio auto mode).
3. Profile path test scaffolding (temp dirs + dummy structure).
4. Nightly full-suite workflow addition.
5. Documentation updates & final stabilization report comment.

## Risks & Mitigation

| Risk | Mitigation |
|------|------------|
| Over-skipping hides regressions | Add nightly full run & periodic dashboard summary |
| Marker misuse | Provide guidelines & pre-commit check (optional) |
| Residual loop warnings | Add finalizer asserting no pending tasks in key fixtures |

## References

- PR #80 (logging design) scope isolation decision.
- tests/pytest.ini (asyncio_mode provisional change).

---

(End of Issue Draft – create as GitHub issue and link from roadmap after review)
