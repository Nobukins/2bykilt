# pytest-asyncio event-loop teardown failure during CI runs

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

## Update: observed while running PR feature/issue-241-unlock-future-fix

Date: 2025-09-30

While running a local full test pass to validate a small fix (PR: <https://github.com/Nobukins/2bykilt/pull/284>), the same symptom was reproduced:

- Failing test: `tests/final_verification_test.py::test_browser_profile[chromium]` → RuntimeError: "This event loop is already running"
- Teardown error: pytest-asyncio attempted to close the loop and raised `RuntimeError: Cannot close a running event loop`.
- Secondary observation: a `FileNotFoundError` from `tests/config/test_multi_env_loader.py::test_secret_mask_artifact` was seen and fixed by making the test robust to pre-existing artifact runs (this fix is in the PR).

Summary of reproduction steps used locally:

1. Checkout branch `feature/issue-241-unlock-future-fix` and run `pytest -q`.
2. Observe the failures above; the stack traces indicate pytest-asyncio's event-loop fixture clashes with an active event loop started during test execution (or at import time).

Suggested immediate actions (minimal):

- Link and consolidate this report with existing test-stability efforts (see related roadmap issues below). This exact failure appears to be the same class of problem tracked by the project's async/browser stability work.
- Recommended quick mitigation for PRs: skip heavy browser/profile tests on CI for PR checks and run them in nightly/full-suite gating until async fixture stability is resolved.

Related roadmap issues (likely overlap)

- #81 — "Async/Browser テスト安定…" (directly about async/browser test stability)
- #107 — "Cleanup: PytestReturnNotNone..." (pytest-asyncio teardown/fixture cleanup related)
- #108 — "Stabilize Edge head…" (Edge/Chrome profile stability overlap)
- #109 — "[quality][coverage]…" and #218 — "テストカバレッジ率の向上" (test suite / coverage / CI implications)
- #231 — "[testing][enhanceme…" (testing enhancements / layering)

If any of the numbered issues above already exist as GitHub issues, consider linking them together and adding a comment pointing to this file and to PR #284 reproducer. In this repository the canonical discussion artifacts are `docs/issues/ISSUE-NEW-ASYNC-TEST-STABILITY.md` and `docs/issues/ISSUE-ASYNC-TEST-STABILITY-ja.md` which contain extensive remediation proposals; they should be cross-referenced from the matching GitHub issues.

I will also push a short PR note linking PR #284 to this issue file so reviewers see the reproduction context.
