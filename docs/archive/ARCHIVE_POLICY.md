# Archive and Cleanup Policy

This repository consolidates active tests under `tests/` and moves root-level tests and scripts to `.archive/` to avoid duplicate discovery and reduce clutter.

- `.archive/root_tests/` — Historical or ad-hoc root-level tests moved from the repo root.
- `.archive/root_py/` — Root-level helper/debug scripts moved from the repo root.

Guidelines:
- Do not run pytest at the repo root without `-c tests/pytest.ini`. Use `python -m pytest -c tests/pytest.ini`.
- New tests should live only under `tests/` and use markers (`ci_safe`, `local_only`).
- Prefer `sys.executable` in subprocesses to ensure interpreter stability in venv/CI.
- If an archived test is still valuable, rehome it into an appropriate subfolder in `tests/` and adapt it to the current test policy.
