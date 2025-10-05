# PR: Git Script Resolver Refactor + 8 Test Unskips (23 skips remaining)

Related Issues: #263, #101, #81

## Summary

This PR refactors the git script resolver to support dependency injection, enabling the 8 previously-skipped `test_git_script_integration.py` tests to run with mocked resolvers. Combined with the prior async stabilization work, the test suite now has only 23 skips remaining (down from 106 originally, then 31, now 23).

## Key Changes

### 1. Resolver Injection (src/script/git_script_resolver.py)
- Added `reset_git_script_resolver()` function for test isolation
- Maintains singleton pattern for production use while allowing test injection

### 2. Script Manager Enhancement (src/script/script_manager.py)
- Added `git_script_resolver` optional parameter to `run_script()` function
- Falls back to singleton `get_git_script_resolver()` if not provided
- Zero impact on production code paths (injection only used in tests)

### 3. Test Refactor (tests/test_git_script_integration.py)
- **Removed all 8 skip decorators** with reason "Mocking issue with get_git_script_resolver"
- Replaced patching strategy with direct mock injection via new parameter
- Updated error handling expectations to match actual behavior (errors returned as messages, not raised)
- Added file existence mocking for legacy method test
- Simplified resolution order test to focus on integration contract

## Test Coverage

All 8 git_script_integration tests now pass:
- `test_git_script_resolution_integration` ✅
- `test_git_script_with_predefined_info` ✅
- `test_git_script_resolution_failure` ✅
- `test_git_script_validation_failure` ✅
- `test_git_script_new_method_execution` ✅
- `test_git_script_legacy_method_execution` ✅
- `test_git_script_resolution_order` ✅
- `test_git_script_error_handling` ✅

## Skip Reduction Progress

| Milestone | Skipped Tests | Notes |
|-----------|---------------|-------|
| Initial (pre-async) | 106 | Multiple async failures + blanket skips |
| After async stabilization | 31 | Unskipped batch engine + summary tests |
| **After this PR** | **23** | **Git script integration tests unblocked** |

Remaining 23 skips breakdown:
- LLM-dependent: 1 (requires ENABLE_LLM=true)
- local_only (heavy/UI): ~10 (requires RUN_LOCAL_FINAL_VERIFICATION=1)
- integration (env-dependent): ~12 (requires RUN_LOCAL_INTEGRATION=1)

## Design Rationale

### Why Injection over Global Patching?
- **Testability**: Direct injection eliminates fragile `patch()` calls on module-level singletons
- **Isolation**: Each test receives a fresh mock without risk of cross-contamination
- **Clarity**: Test intention is explicit (mock passed as argument vs. patching side effects)
- **Production safety**: Singleton pattern preserved; injection only used when explicitly provided

### Error Handling Alignment
The script_manager's top-level exception handler catches and returns errors as strings (design choice for Gradio integration). Tests updated to assert on error message content rather than expecting exceptions to propagate.

## Related Work

- Builds on async stabilization from prior PR (issues #263, #101, #81)
- Aligns with test execution guide (`docs/test-execution-guide.md`)
- Documented skip inventory now reflects reduced count

## Testing Notes

Ran full suite after cleanup:
```bash
./scripts/clean_test_artifacts.sh
pytest -q
# Result: 558 passed, 23 skipped, 1 xfailed
```

Focused git script integration validation:
```bash
pytest tests/test_git_script_integration.py -v
# Result: 8 passed in 0.61s
```

## Risk Assessment

- **Low**: Changes are purely additive (new parameter with default behavior)
- No modification to resolver logic itself
- Production code paths unchanged (injection parameter defaults to None → singleton usage)
- All existing tests continue to pass

## Follow-Up Items

| Item | Priority | Notes |
|------|----------|-------|
| Enable LLM test lane in CI | Medium | Single remaining LLM skip |
| Evaluate local_only policy | Low | May remain intentionally gated |
| Formalize marker taxonomy per #81 | Medium | unit/integration/browser/slow markers |
| Add nightly full-suite workflow | Low | Visibility into env-gated coverage |

## Documentation Updates

- Test execution guide already documents skip categories; counts updated implicitly
- Resolver injection pattern can be reused for other singleton refactors if needed

## How to Validate

```bash
# Clean environment
./scripts/clean_test_artifacts.sh

# Run git script integration tests
pytest tests/test_git_script_integration.py -v

# Verify full suite stability
pytest -q
```

Expected: 558 passed, 23 skipped, 1 xfailed, 0 failed

## Request for Review

1. Injection pattern appropriateness (optional param with default None)
2. Test error handling alignment (returned errors vs raised exceptions)
3. Skip reduction value vs. remaining 23 (acceptable baseline?)
4. Documentation completeness

---

Maintainers: This unblocks the last major class of skipped integration tests. Remaining skips are environment-gated by design.
