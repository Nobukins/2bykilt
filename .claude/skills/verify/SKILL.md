---
name: verify
description: Verify a 2bykilt change end-to-end before committing — run the right pytest subset under CI-equivalent conditions, check LLM isolation when imports changed, and drive the Gradio UI or an llms.txt action when runtime behavior changed.
---

# Verifying a change in 2bykilt

Pick the verification tier that matches what the diff touches. Always run tier 1; add higher tiers as applicable.

## Tier 1 — targeted tests (always)

```bash
python -m pytest tests/path/to/affected_test.py -xvs --no-cov
```

If no test covers the change, write one and mark it `ci_safe` (or `local_only` if it genuinely needs a local browser profile/UI).

## Tier 2 — CI simulation (config, imports, shared modules, fixtures)

```bash
unset BYKILT_ENV
ENABLE_LLM=true python -m pytest -m ci_safe --cov=src --cov-report=term
```

`BYKILT_ENV` must be unset — CI loads only `config/base`, and a locally-set env activates dev overlays that mask failures.

## Tier 3 — LLM isolation (any change to imports or module-level code)

```bash
ENABLE_LLM=false python scripts/verify_llm_isolation.py
```

This must pass with zero LLM packages imported. If it fails, move the offending import inside a function guarded by `is_llm_enabled()`.

## Tier 4 — runtime smoke (UI, action pipeline, recording/artifact changes)

Launch the app headlessly and exercise the affected flow:

```bash
python bykilt.py --port 7861 &   # or ./dev.sh start; logs in bykilt.log
```

- For action-pipeline changes, run a pre-registered action from `llms.txt` (e.g. `get-title`, a no-param `browser-control` action) and confirm it completes.
- For artifact/recording changes, confirm output appears under `artifacts/runs/<run_id>-art/` (recordings in `videos/`) and the manifest is written.
- Check `bykilt.log` for tracebacks before declaring success. Stop the server afterwards (`./dev.sh stop`).

## Definition of done

Report actual command output, not intentions. A change is verified when the relevant tiers pass under the CI-equivalent environment, not merely when the code "looks right".
