# Issue #231: Test Suite Improvement & Coverage Enhancement Plan

**Issue**: [#231](https://github.com/Nobukins/2bykilt/issues/231)  
**Status**: In Progress (partially-done)  
**Priority**: P2  
**Size**: L (4-6 days)  
**Started**: 2025-10-18

## Executive Summary

Test suite improvements for 2bykilt to increase reliability and maintainability. Current overall coverage is ~6%, with significant gaps in LLM functionality, UI components, and error handling.

## Current State Analysis

### Overall Coverage: 6%
- **Total Lines**: 7,350
- **Covered**: ~440
- **Tests Passing**: 456 passed, 65 skipped
- **Test Files**: 100+ test files in tests/ directory

### Coverage by Module (Priority Areas)

#### 🔴 Critical - 0% Coverage
- `src/llm/docker_sandbox.py` - 0% (107 lines)
- `src/ui/admin/artifacts_panel.py` - 0% (135 lines) 
- `src/api/app.py` - 67% (34 lines covered, 70 missing)
- `src/cli/batch_commands.py` - 0% (189 lines)
- `src/cli/main.py` - 0% (108 lines)

#### 🟡 Moderate - 30-70% Coverage
- `src/llm/service_gateway.py` - 35% (71/110 lines missing)
- `src/api/realtime_router.py` - 35% (33/51 lines missing)
- `src/ui/browser_agent.py` - 23% (86/111 lines missing)
- `src/ui/components/settings_panel.py` - 34% (57/86 lines missing)
- `src/ui/main_ui.py` - 36% (43/67 lines missing)
- `src/extraction/extractor.py` - 61% (35/89 lines missing)

#### 🟢 Good - 80%+ Coverage
- `src/ui/services/feature_flag_service.py` - 95%
- `src/ui/components/run_panel.py` - 93%
- `src/extraction/models.py` - 94%
- `src/api/metrics_router.py` - 86%
- `src/ui/helpers.py` - 88%
- `src/extraction/schema.py` - 83%

## Test Improvements Completed

### ✅ Phase 1 (PR #286)
- Many tests stabilized
- Async/Browser test improvements
- Basic batch engine testing

### ✅ Today's Fixes
- Fixed `test_to_portable_relpath_success` - Updated to use utility function
- Fixed `test_to_portable_relpath_fallback` - Updated to use utility function

## Proposed Implementation Plan

### Phase 2A: LLM Module Testing (Priority: High)

#### 1. LLM Service Gateway Tests
**File**: `tests/llm/test_service_gateway.py`
**Target Coverage**: 35% → 80%

Test Cases:
- [ ] LLM provider initialization (OpenAI, Anthropic, etc.)
- [ ] API request formatting and response parsing
- [ ] Error handling for API failures
- [ ] Rate limiting and retry logic
- [ ] Mock external API calls
- [ ] Timeout handling
- [ ] Authentication/API key validation

#### 2. Docker Sandbox Tests
**File**: `tests/llm/test_docker_sandbox.py`
**Target Coverage**: 0% → 70%

Test Cases:
- [ ] Container creation and lifecycle
- [ ] Code execution in sandbox
- [ ] Security restrictions validation
- [ ] Resource limits enforcement
- [ ] Error handling for container failures
- [ ] Cleanup and teardown processes
- [ ] Mock Docker API interactions

### Phase 2B: UI Component Testing (Priority: High)

#### 1. Admin Artifacts Panel Tests
**File**: `tests/ui/admin/test_artifacts_panel.py`
**Target Coverage**: 0% → 60%

Test Cases:
- [ ] Panel initialization and rendering
- [ ] Artifact listing and filtering
- [ ] File operations (view, download, delete)
- [ ] Error state handling
- [ ] Mock Gradio components

#### 2. Browser Agent Tests
**File**: `tests/ui/test_browser_agent.py` (enhance existing)
**Target Coverage**: 23% → 70%

Test Cases:
- [ ] Browser control initialization
- [ ] Command execution flow
- [ ] State management
- [ ] Error recovery
- [ ] Event handling

#### 3. Settings Panel Tests
**File**: `tests/ui/components/test_settings_panel.py`
**Target Coverage**: 34% → 70%

Test Cases:
- [ ] Configuration loading
- [ ] Settings updates and persistence
- [ ] Validation logic
- [ ] UI state synchronization

### Phase 2C: API Testing (Priority: Medium)

#### 1. API Application Tests
**File**: `tests/api/test_app.py` (enhance existing)
**Target Coverage**: 67% → 85%

Test Cases:
- [ ] FastAPI app initialization
- [ ] Endpoint registration
- [ ] Middleware functionality
- [ ] Error handlers
- [ ] CORS configuration

#### 2. Realtime Router Tests
**File**: `tests/api/test_realtime_router.py`
**Target Coverage**: 35% → 75%

Test Cases:
- [ ] WebSocket connection handling
- [ ] Real-time updates
- [ ] Connection management
- [ ] Error recovery

### Phase 2D: CLI Testing (Priority: Medium)

#### 1. Batch Commands Tests
**File**: `tests/cli/test_batch_commands.py` (enhance existing)
**Target Coverage**: 0% → 60%

Test Cases:
- [ ] Command parsing
- [ ] Argument validation
- [ ] Batch execution flow
- [ ] Error handling
- [ ] Output formatting

#### 2. Main CLI Tests
**File**: `tests/cli/test_main.py`
**Target Coverage**: 0% → 60%

Test Cases:
- [ ] CLI initialization
- [ ] Command routing
- [ ] Help text generation
- [ ] Error messages

### Phase 2E: Integration & Error Cases (Priority: Medium)

#### 1. Error Scenario Testing
Create comprehensive error case tests across all modules:
- [ ] Network failures
- [ ] File system errors
- [ ] Invalid input handling
- [ ] Resource exhaustion
- [ ] Timeout scenarios
- [ ] Concurrent access conflicts

#### 2. Integration Tests
- [ ] End-to-end batch processing
- [ ] LLM → Browser automation flow
- [ ] API → Service integration
- [ ] Multi-component workflows

## Testing Best Practices

### Mocking Strategy
- Use `unittest.mock` for external dependencies
- Mock file I/O operations
- Mock network calls (HTTP, WebSocket)
- Mock Docker/subprocess operations
- Use fixtures for common test data

### Async Testing
- Use `pytest-asyncio` for async tests
- Set `asyncio_mode = auto` in pytest.ini
- Ensure proper event loop cleanup

### Test Organization
```
tests/
├── api/              # API endpoint tests
├── llm/              # LLM service tests
├── ui/               # UI component tests
│   ├── admin/        # Admin panel tests
│   ├── components/   # Reusable component tests
│   └── services/     # UI service tests
├── cli/              # CLI command tests
├── integration/      # End-to-end tests
└── unit/             # Pure unit tests
```

### Fixtures
- Reuse common fixtures from `conftest.py`
- Create module-specific fixtures in local `conftest.py`
- Use fixture scope appropriately (`function`, `module`, `session`)

## Success Metrics

### Target Coverage Goals
- **Overall**: 6% → 40% (Phase 2)
- **LLM Module**: 0-35% → 70%
- **UI Module**: 23-54% → 65%
- **API Module**: 35-67% → 75%
- **CLI Module**: 0% → 60%

### Quality Metrics
- All tests pass consistently
- No flaky tests in CI
- Test execution time < 2 minutes
- Clear error messages
- Documented test patterns

## Implementation Timeline

### Week 1 (Days 1-2)
- [x] Fix failing tests
- [x] Analyze coverage gaps
- [ ] Implement LLM Service Gateway tests
- [ ] Implement Docker Sandbox basic tests

### Week 1 (Days 3-4)
- [ ] Implement UI Admin Panel tests
- [ ] Enhance Browser Agent tests
- [ ] Implement Settings Panel tests

### Week 2 (Days 5-6)
- [ ] Implement API tests
- [ ] Implement CLI tests
- [ ] Add integration tests
- [ ] Document testing patterns

## Related Issues & PRs

- PR #286: Many tests stabilized
- Issue #81: Async/Browser test stabilization
- Issue #231: This issue (test suite improvement)

## Notes

- Current test suite is well-organized with clear structure
- pytest configuration is properly set up
- Async testing infrastructure is in place
- Need to focus on mocking external dependencies
- Consider adding test coverage requirements for new PRs

## References

- pytest documentation: https://docs.pytest.org/
- pytest-asyncio: https://pytest-asyncio.readthedocs.io/
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- Coverage.py: https://coverage.readthedocs.io/
