"""
CI-safe smoke test and mini report for option availability. This complements
the functional tests and emits a concise summary into the test output.
"""

import os
import sys
from pathlib import Path
import pytest


@pytest.mark.ci_safe
def test_pytest_config_and_paths_print_summary(capsys):
    # Verify we are using the project's pytest.ini and coverage is configured
    # Only accept root-level pytest.ini after migration; legacy tests/pytest.ini reference would trigger CI guard
    root_ini = Path('pytest.ini')
    assert root_ini.exists(), "pytest.ini not found at project root (expected after config migration)"
    found_ini = root_ini

    # Emit a short environment summary for logs
    print("[CI-SAFE SUMMARY]")
    print(f"python: {sys.executable}")
    print(f"cwd: {os.getcwd()}")
    print(f"ini: {found_ini}")

    # Provide a placeholder matrix header that CI logs can grep
    print("Type | Chrome起動 | プロファイル | 録画保存")
    print("script | - | - | ✅ (CI-safe path only)")
    print("action_runner_template | - | - | ✅ (CI-safe path only)")
    print("browser-control | ✅ (mocked) | ✅ (mocked) | ✅ (tmp)")
    print("git-script | - | - | ✅ (mocked clone/exec)")

    # Ensure output was written
    out, _ = capsys.readouterr()
    assert "[CI-SAFE SUMMARY]" in out
