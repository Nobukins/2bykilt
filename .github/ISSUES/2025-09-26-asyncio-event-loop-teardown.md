Title: pytest-asyncio event-loop teardown failure during CI runs

Summary

While running the full test suite locally, `tests/final_verification_test.py::test_browser_profile[chromium]` fails with a RuntimeError indicating "This event loop is already running" during the test run and teardown. This appears unrelated to the CSV preview work in PR feature/173-csv-preview but blocks green test runs.

Reproduction

1. Use the project's virtualenv: `venv312/bin/python -m pytest -q`
2. Observe the failure in `tests/final_verification_test.py::test_browser_profile[chromium]` with traceback indicating event loop already running and teardown failing to close the loop.

Observed behavior

- The test launches Playwright, copies browser profile data, and opens contexts. During teardown pytest-asyncio attempts to close the event loop but raises `RuntimeError: Cannot close a running event loop`.
- The test run also shows `RuntimeError: This event loop is already running` when pytest tries to run coroutine tasks.

Likely cause

- Some module or top-level code starts or runs an asyncio event loop at import-time (possibly `bykilt.py` or other UI/Gradio initialization) which interferes with pytest-asyncio's management of the event loop.
- Running `bykilt.py` at import-time should be avoided; move UI startup / asyncio.run calls under `if __name__ == "__main__":` or use an environment guard to skip on test runners.

Suggested fixes

- Make `bykilt.py` import-safe: avoid creating the Gradio UI or calling `asyncio.run(...)` during module import. Wrap app startup in `if __name__ == "__main__":`.
- Alternatively, use an env var guard, e.g., `BYKILT_SKIP_UI_ON_IMPORT` or detect pytest via `PYTEST_CURRENT_TEST` or `sys.argv` to skip UI initialization.
- Add CI job that runs the full test suite and surfaces this issue on PRs.

Notes

- I will separate this into its own issue and proceed to commit and push the CSV preview changes for PR review.
- Tag: testing, pytest-asyncio, ci
