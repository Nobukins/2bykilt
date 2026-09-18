---
name: add-llms-action
description: Add or modify a pre-registered automation action in llms.txt — choosing the right action type (script, browser-control, git-script, unlock-future, action_runner_template), parameter syntax, schema validation, and how to test it without an LLM.
---

# Adding an action to llms.txt

Actions in `llms.txt` are the LLM-free automation vocabulary of 2bykilt. They are matched against user prompts by `src/modules/command_dispatcher.py` before any LLM is consulted.

## 1. Choose the action type

| You want to… | Use type | Key fields |
|---|---|---|
| Run an existing pytest script with params | `script` | `script`, `command` |
| Describe a click/fill/extract flow declaratively | `browser-control` | `flow:` list of steps |
| Run a script that lives in another git repo | `git-script` | `git`, `script_path`, `version`, `command` |
| JSON-based execution with tab control | `unlock-future` | `flow:`, `tab_selection_strategy`, `keep_tab_open` |
| Reuse a parameterized template under `templates/` | `action_runner_template` | `template`, `command` |

Flow steps available in `browser-control`/`unlock-future`: `command` (navigate; `url`, `wait_until`/`wait_for`), `click`, `fill_form`, `keyboard_press`, `scroll_to_bottom`, `screenshot` (`prefix`, `full_page`), `extract_content` (`selectors` with optional `label`/`fields`).

## 2. Declare parameters

```yaml
params:
  - name: query
    required: true
    type: string
    description: "Search query to execute"
```

Reference them as `${params.query}`; defaults use pipe syntax: `${params.browser|chromium}`. In `command:` strings, `${script_path}` and `${template}` are also substituted.

## 3. Validate and test

- Schema validation lives in `src/config/llms_schema_validator.py`; parsing in `src/config/llms_parser.py`. Run their tests after editing:
  ```bash
  python -m pytest tests/test_llms_schema_validation.py tests/test_pre_registered_commands.py -xvs --no-cov
  ```
- Smoke-test the action for real: launch `python bykilt.py --port 7861`, enter the action name (plus params) as the prompt, and confirm execution artifacts under `artifacts/runs/<run_id>-art/`.
- `slowmo` (ms) and `timeout` (s) tune execution pace; keep `slowmo` around 1000 for sites with dynamic content.

## Cautions

- Action names must be unique — the remote-import feature resolves collisions with skip/overwrite/rename strategies, but hand-edited duplicates break matching silently.
- Never embed secrets in `llms.txt`; sensitive values are resolved from env vars at runtime (`resolve_sensitive_env_variables_standalone`).
- Site selectors rot. Prefer stable IDs, add a `screenshot` step for debuggability, and note the target site in `description`.
