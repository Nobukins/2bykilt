# Copilot instructions for 2bykilt

Project-specific rules only. For general workflow (1 Issue = 1 PR, dependency checks, STOP & ASK) see
[`docs/engineering/AGENT_PROMPT_GUIDE.md`](../docs/engineering/AGENT_PROMPT_GUIDE.md).

## Before pushing: reproduce CI locally

CI (`.github/workflows/security-ci.yml`) runs only `ci_safe` tests, with `ENABLE_LLM=true` and no `BYKILT_ENV`.
Reproduce that, or at least run the test files you touched:

```bash
unset BYKILT_ENV
export ENABLE_LLM=true
python -m pytest -m ci_safe --cov=src --cov-report=term -v   # full CI-equivalent run
python -m pytest path/to/modified_test.py -xvs               # minimum before any push
```

- Never push without running at least the modified test files.
- New tests need a marker: `ci_safe` (mocked or headless Chromium), `local_only` (interactive UI, user profiles, Edge, macOS paths) or `integration`. See `pytest.ini`.

## Test pitfalls already hit in this repo (Issue #340)

- **Patch scope**: every assertion that depends on a patch must be inside the `with patch(...)` block.
  ```python
  with patch("module.VARIABLE", False):
      result = function_call()
      assert result == expected   # inside the block, patch still active
  ```
- **Module-level variables** are evaluated at import time. Patch them with `with patch(...)` rather than `@patch` decorators when ordering matters.
- **Multi-env config**: files under `config/` (`base/`, `dev/`, `staging/`, `prod/`) can activate unexpectedly. When touching config code, also test with `BYKILT_ENV` unset, as CI does.

## Roadmap files

`docs/roadmap/ISSUE_DEPENDENCIES.yml` is the only hand-edited file. `TASK_QUEUE.yml`, `TASK_DASHBOARD.md` and
`DEPENDENCY_GRAPH.md` are generated; follow ROADMAP.md Section K to regenerate and validate them.
