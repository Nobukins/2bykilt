import os
import re
import asyncio
import importlib
import sys
from pathlib import Path

import pytest


def _read_generated_script(path: Path) -> str:
    assert path.exists(), f"Generated script not found: {path}"
    return path.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_generate_browser_control_script_session_scope(tmp_path, monkeypatch):
    """Regression test for Issue #220 / PR #235.

    Ensures that the generated browser_control.py uses session-scoped fixtures
    (browser_context_args, browser_type_launch_args) to avoid pytest ScopeMismatch
    with pytest-playwright's session-scoped `browser` fixture.
    """
    # Import here to ensure patched generator code is loaded
    from src.script.script_manager import run_script

    script_info = {
        "type": "browser-control",
        "slowmo": 0,  # faster test
        "flow": [
            {"action": "navigate", "url": "https://example.com", "wait_until": "domcontentloaded"},
        ],
    }

    params = {"query": "dummy"}

    # Use a temp recordings directory
    recording_dir = tmp_path / "videos"

    # Run generation only (we don't actually want to launch browser in CI). To prevent
    # real browser launch, set an env var making PLAYWRIGHT skip? Instead run the generator
    # but immediately stop before subprocess by monkeypatching asyncio.create_subprocess_exec.
    created_commands = {}

    async def fake_subprocess_exec(*cmd, **kwargs):  # noqa: D401
        class DummyProc:
            returncode = 0

            async def communicate(self):
                # Simulate minimal pytest output
                return (
                    b"============================= test session starts ==============================\n1 passed in 0.01s\n",
                    b"",
                )

        created_commands["cmd"] = cmd
        created_commands["cwd"] = kwargs.get("cwd")
        created_commands["env"] = kwargs.get("env")
        return DummyProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_subprocess_exec)

    msg, script_path = await run_script(
        script_info=script_info,
        params=params,
        headless=True,
        save_recording_path=str(recording_dir),
        browser_type="chromium",
    )

    assert script_path, f"Script path not returned: {msg}"
    script_text = _read_generated_script(Path(script_path))

    # Validate session scope for fixtures
    assert re.search(r"@pytest.fixture\(scope=\"session\"\)\ndef browser_context_args", script_text), "browser_context_args must be session scoped"
    assert re.search(r"@pytest.fixture\(scope=\"session\"\)\ndef browser_type_launch_args", script_text), "browser_type_launch_args must be session scoped"

    # Confirm our fake subprocess ran (generation attempted to execute pytest)
    assert created_commands.get("cmd"), "Pytest subprocess wasn't invoked (monkeypatch may have failed)"
    # Ensure environment carries BYKILT_BROWSER_TYPE
    env = created_commands["env"]
    assert env.get("BYKILT_BROWSER_TYPE") == "chromium"

    # Confirm success message path
    assert "Script executed successfully" in msg or "script execution failed" not in msg

    # Safety: ensure no module-scope decorators remain (legacy regression)
    assert "@pytest.fixture(scope=\"module\")" not in script_text, "Found legacy module-scoped fixture decorator"
