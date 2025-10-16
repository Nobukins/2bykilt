# Large Files Report - Issue #264

**Generated:** 2025-10-15  
**Purpose:** Identify Python files exceeding 1500 lines for refactoring

## Summary

| File | Lines | Status | Priority |
|------|-------|--------|----------|
| `bykilt.py` | 3887 | 🔴 Critical | P0 |
| `tests/test_batch_engine.py` | 2303 | 🔴 Critical | P1 |
| `src/batch/engine.py` | 2111 | 🔴 Critical | P1 |
| `src/script/script_manager.py` | 1884 | 🔴 Critical | P1 |

**Total files over 1500 lines:** 4  
**Total lines in large files:** 10,185

## Detailed Analysis

### 1. `bykilt.py` (3887 lines) - Priority: P0

**Current Responsibilities:**
- CLI argument parsing (batch commands)
- Gradio UI creation and event handlers
- LLM integration and agent execution
- Browser automation orchestration
- Feature flag management
- FastAPI integration

**Proposed Split:**
```
bykilt.py (3887 lines) → Split into:
├── src/cli/main.py              (~300 lines) - Entry point, arg parsing
├── src/cli/batch_commands.py    (~400 lines) - Batch CLI handlers
├── src/ui/app.py                (~800 lines) - Gradio UI creation
├── src/ui/event_handlers.py     (~600 lines) - UI event handlers
├── src/ui/recordings_tab.py     (~400 lines) - Recording playback UI
├── src/ui/artifacts_tab.py      (~300 lines) - Artifacts UI
└── src/ui/llm_tabs.py           (~800 lines) - LLM-related tabs
```

**Benefits:**
- Easier to maintain individual UI components
- Better for Copilot Agent prompts (1 file = 1 responsibility)
- Clearer test isolation

**Risks:**
- High coupling with existing imports
- Need careful backward compatibility for API users

**Estimated Effort:** Size L (4-6 days)

---

### 2. `tests/test_batch_engine.py` (2303 lines) - Priority: P1

**Current Responsibilities:**
- Batch engine integration tests
- Job lifecycle tests
- Error handling tests
- Manifest tests

**Proposed Split:**
```
tests/test_batch_engine.py (2303 lines) → Split into:
├── tests/batch/test_batch_creation.py    (~400 lines)
├── tests/batch/test_job_execution.py     (~500 lines)
├── tests/batch/test_job_lifecycle.py     (~400 lines)
├── tests/batch/test_error_handling.py    (~400 lines)
└── tests/batch/test_manifest.py          (~400 lines)
```

**Benefits:**
- Faster test execution (parallel test runs)
- Easier to identify failing test categories
- Better test organization

**Estimated Effort:** Size M (2-3 days)

---

### 3. `src/batch/engine.py` (2111 lines) - Priority: P1

**Current Responsibilities:**
- Batch job creation and execution
- Job state management
- Manifest generation
- Error recovery

**Proposed Split:**
```
src/batch/engine.py (2111 lines) → Split into:
├── src/batch/core.py             (~400 lines) - BatchEngine base
├── src/batch/job_executor.py     (~500 lines) - Job execution logic
├── src/batch/manifest.py         (~400 lines) - Manifest operations
├── src/batch/state_manager.py    (~400 lines) - Job state tracking
└── src/batch/error_handler.py    (~300 lines) - Error recovery
```

**Benefits:**
- Single Responsibility Principle
- Easier to add new batch features
- Better testability

**Estimated Effort:** Size M (2-3 days)

---

### 4. `src/script/script_manager.py` (1884 lines) - Priority: P1

**Current Responsibilities:**
- Script execution orchestration
- Action resolution
- Parameter extraction
- Browser automation
- Recording management

**Proposed Split:**
```
src/script/script_manager.py (1884 lines) → Split into:
├── src/script/executor.py        (~400 lines) - Main execution
├── src/script/action_resolver.py (~300 lines) - Action lookup
├── src/script/param_parser.py    (~300 lines) - Parameter extraction
├── src/script/recording.py       (~300 lines) - Recording logic
└── src/script/browser_adapter.py (~400 lines) - Browser integration
```

**Benefits:**
- Clear separation of concerns
- Easier to extend with new action types
- Better for unit testing

**Estimated Effort:** Size M (2-3 days)

---

## Other Notable Files (Under 1500 but worth monitoring)

| File | Lines | Notes |
|------|-------|-------|
| `myscript/search_script.py` | 1217 | Approaching threshold |
| `src/agent/custom_agent.py` | 843 | Could benefit from split |
| `src/browser/engine/cdp_engine.py` | 804 | Monitor growth |

## Dependencies Analysis

### High-Impact Files (many imports from other modules)
1. `bykilt.py` - Imported by: FastAPI app, CLI tools
2. `src/batch/engine.py` - Imported by: CLI batch commands, tests
3. `src/script/script_manager.py` - Imported by: bykilt.py, agents, tests

### Recommended Split Order
1. **Phase 1 (Week 1-2):** `bykilt.py` split - Highest impact, most complex
2. **Phase 2 (Week 3):** `tests/test_batch_engine.py` - Low risk, immediate benefit
3. **Phase 3 (Week 4):** `src/batch/engine.py` - Medium complexity
4. **Phase 4 (Week 5):** `src/script/script_manager.py` - Moderate risk

## Test Coverage (Current State)

```bash
# Run coverage analysis
pytest --cov=. --cov-report=term-missing

# Current coverage for large files:
# bykilt.py: Not directly tested (integration via UI)
# src/batch/engine.py: 87% coverage
# src/script/script_manager.py: 72% coverage
# tests/*: N/A (these are tests themselves)
```

## Next Steps

1. Create sub-issues for each file split:
   - Issue: "Split bykilt.py into CLI and UI modules" (Size: L, Priority: P0)
   - Issue: "Split test_batch_engine.py into focused test modules" (Size: M, Priority: P1)
   - Issue: "Split batch/engine.py into core components" (Size: M, Priority: P1)
   - Issue: "Split script/script_manager.py into executor modules" (Size: M, Priority: P1)

2. Update ROADMAP.md with refactoring wave

3. Create feature branch: `refactor/issue-264-file-splits`

4. Implement splits one PR at a time, ensuring:
   - All tests pass
   - No breaking changes to public APIs
   - Documentation updated

## Success Metrics

- [ ] All files under 1500 lines
- [ ] Test execution time reduced by 20%
- [ ] CI pipeline remains green
- [ ] No breaking changes to existing integrations
- [ ] Documentation updated for new module structure

---

**Report Status:** ✅ Complete  
**Next Action:** Create sub-issues and assign priorities
