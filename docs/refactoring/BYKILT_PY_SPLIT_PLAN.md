# bykilt.py Split Plan (Issue #326)

## Current State
- File size: 3888 lines
- Multiple duplicate function definitions
- Mixed CLI, UI, and business logic
- No dedicated test file

## Challenges Identified
1. Heavy duplication of `create_batch_parser()`, `handle_batch_command()` functions
2. Multiple `if __name__ == '__main__'` blocks
3. Large `create_ui()` function (1968 lines: 1259-3227)
4. Unclear module boundaries

## Revised Split Strategy

### Phase 1: Cleanup and Deduplicate (Current Priority)
**Goal**: Remove duplicates, create clean baseline
- [x] Remove duplicate `create_batch_parser()` definitions (lines 21, 67, 3570, 3700)
- [x] Remove duplicate `handle_batch_command()` definitions (lines 114, 3617, 3747)
- [x] Remove duplicate `handle_batch_commands()` definitions (lines 224, 3878)
- [x] Remove duplicate `if __name__ == '__main__'` blocks (lines 3418, 3693)
- [x] Commit: "refactor: remove duplicate function definitions in bykilt.py" (11ded1a)

### Phase 2: Extract CLI Module
**Goal**: Move CLI logic to `src/cli/`
- [x] Create `src/cli/__init__.py`
- [x] Create `src/cli/batch_commands.py` with:
  - `create_batch_parser()`
  - `handle_batch_command()`
  - `handle_batch_commands()`
- [x] Update `bykilt.py` to import from `src.cli.batch_commands`
- [x] Test CLI commands: `python bykilt.py batch --help`
- [x] Commit: "refactor: extract CLI logic to src/cli module" (98399d1)

### Phase 3: Extract UI Components
**Goal**: Split large `create_ui()` function
- [x] Create `src/ui/__init__.py`
- [x] Create `src/ui/helpers.py` with utility functions (f911ee7):
  - `load_actions_config()`
  - `load_llms_file()`, `save_llms_file()`
  - `discover_and_preview_llmstxt()`
  - `import_llmstxt_actions()`
  - `preview_merge_llmstxt()`
  - `load_env_browser_settings_file()`
- [ ] Extract largest tabs to separate modules:
  - [ ] `src/ui/batch_processing_tab.py` (765 lines)
  - [ ] `src/ui/recordings_tab.py` (208 lines)
  - [ ] `src/ui/option_availability_tab.py` (205 lines)
  - [ ] `src/ui/playwright_codegen_tab.py` (129 lines)
  - [ ] `src/ui/browser_settings_tab.py` (125 lines)
  - [ ] `src/ui/run_agent_tab.py` (108 lines)
  - [ ] `src/ui/llm_configuration_tab.py` (97 lines)
  - [ ] `src/ui/llmstxt_import_tab.py` (88 lines)
- [ ] Create `src/ui/app.py` with main UI creation logic
- [ ] Update imports in `bykilt.py`
- [ ] Test UI: `python bykilt.py --ui`
- [ ] Commit series: "refactor: extract UI tabs to separate modules"

### Phase 4: Extract Helper Functions (Deprecated - merged into Phase 3)
**Goal**: Move remaining utility functions
- [x] Merged into Phase 3 - already completed
- [x] Helper functions moved to `src/ui/helpers.py`

### Phase 5: Create Minimal Entry Point
**Goal**: Make `bykilt.py` a thin wrapper
- [ ] Reduce `bykilt.py` to ~100 lines:
  ```python
  #!/usr/bin/env python3
  from src.cli.main import main
  
  if __name__ == '__main__':
      main()
  ```
- [ ] Update documentation
- [ ] Run full test suite
- [ ] Commit: "refactor: finalize bykilt.py split - entry point only"

## Success Criteria
- [ ] All tests pass (check with `pytest`)
- [ ] `bykilt.py` < 1500 lines (current: 2988 lines, target: ~1500)
- [ ] Each new module < 500 lines
- [x] No duplicate function definitions
- [x] CLI commands work: `python bykilt.py batch --help`
- [ ] UI launches: `python bykilt.py --ui`
- [ ] Import paths updated across codebase

## Progress Tracking
- **Phase 1 (Cleanup):** ✅ Completed - 515 lines removed (11ded1a)
- **Phase 2 (CLI):** ✅ Completed - 175 lines moved (98399d1)
- **Phase 3.1 (Helpers):** ✅ Completed - 210 lines moved (f911ee7)
- **Phase 3.2+ (Tabs):** 🚧 In Progress
- **Phase 4:** N/A (merged into Phase 3)
- **Phase 5:** ⏳ Pending
- **Phase 6:** ⏳ Pending

## Estimated Effort
- Phase 1 (Cleanup): ✅ 1 hour
- Phase 2 (CLI): ✅ 2 hours
- Phase 3.1 (Helpers): ✅ 1 hour
- Phase 3.2+ (Tab extraction): 🚧 4-6 hours remaining
- Phase 5 (Entry Point): 1 hour
- Phase 6 (Testing): 1 hour
- **Total**: ~11 hours (6-8 hours remaining)
