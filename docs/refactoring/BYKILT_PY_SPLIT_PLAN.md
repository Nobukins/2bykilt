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
- [ ] Remove duplicate `create_batch_parser()` definitions (lines 21, 67, 3570, 3700)
- [ ] Remove duplicate `handle_batch_command()` definitions (lines 114, 3617, 3747)
- [ ] Remove duplicate `handle_batch_commands()` definitions (lines 224, 3878)
- [ ] Remove duplicate `if __name__ == '__main__'` blocks (lines 3418, 3693)
- [ ] Commit: "refactor: remove duplicate function definitions in bykilt.py"

### Phase 2: Extract CLI Module
**Goal**: Move CLI logic to `src/cli/`
- [ ] Create `src/cli/__init__.py`
- [ ] Create `src/cli/batch_commands.py` with:
  - `create_batch_parser()`
  - `handle_batch_command()`
  - `handle_batch_commands()`
- [ ] Create `src/cli/main.py` with:
  - `main()` function
  - Argument parsing
  - llms.txt import CLI logic
- [ ] Update `bykilt.py` to import from `src.cli.main`
- [ ] Test CLI commands: `python bykilt.py batch --help`
- [ ] Commit: "refactor: extract CLI logic to src/cli module"

### Phase 3: Extract UI Components
**Goal**: Split large `create_ui()` function
- [ ] Create `src/ui/__init__.py`
- [ ] Analyze `create_ui()` function (1968 lines)
- [ ] Create `src/ui/app.py` with main UI creation logic
- [ ] Extract UI tabs to separate modules:
  - `src/ui/status_tab.py`
  - `src/ui/log_tab.py`
  - `src/ui/browser_panel.py`
  - `src/ui/recordings.py`
  - `src/ui/artifacts.py`
  - `src/ui/feature_flags.py`
  - `src/ui/settings.py`
- [ ] Update imports in `bykilt.py`
- [ ] Test UI: `python bykilt.py --ui`
- [ ] Commit: "refactor: extract UI components to src/ui module"

### Phase 4: Extract Helper Functions
**Goal**: Move utility functions
- [ ] Create `src/ui/helpers.py` with:
  - `load_actions_config()`
  - `load_llms_file()`
  - `save_llms_file()`
  - `discover_and_preview_llmstxt()`
  - `import_llmstxt_actions()`
  - `preview_merge_llmstxt()`
  - `chrome_restart_dialog()`
  - `show_restart_dialog()`
  - `load_env_browser_settings_file()`
- [ ] Update imports
- [ ] Run all tests
- [ ] Commit: "refactor: extract helper functions to src/ui/helpers.py"

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
- [ ] `bykilt.py` < 200 lines
- [ ] Each new module < 500 lines
- [ ] No duplicate function definitions
- [ ] CLI commands work: `python bykilt.py batch --help`
- [ ] UI launches: `python bykilt.py --ui`
- [ ] Import paths updated across codebase

## Estimated Effort
- Phase 1 (Cleanup): 1 hour
- Phase 2 (CLI): 2 hours
- Phase 3 (UI): 4 hours
- Phase 4 (Helpers): 1 hour
- Phase 5 (Entry Point): 1 hour
- **Total**: ~9 hours (1.5 days)
