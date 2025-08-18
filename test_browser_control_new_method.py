"""Tests that git-script execution selects NEW METHOD when env flag is true.

We monkeypatch the execute_git_script_new_method coroutine so no external
network or Playwright setup is required.
"""

import asyncio
import os
import importlib

import pytest


@pytest.mark.asyncio
async def test_git_script_uses_new_method(monkeypatch):
	os.environ["BYKILT_USE_NEW_METHOD"] = "true"

	# Import & reload to ensure fresh environment logic
	import src.script.script_manager as sm
	importlib.reload(sm)

	called = {}

	async def fake_execute(script_info, params, headless, save_recording_path, browser_type):  # noqa: D401
		called["args"] = (script_info, params, headless, save_recording_path, browser_type)
		return "SUCCESS: new method path", "/tmp/dummy/path.py"

	monkeypatch.setattr(sm, "execute_git_script_new_method", fake_execute, raising=True)

	script_info = {
		"type": "git-script",
		"git": "https://example.com/dummy.git",
		"script_path": "dummy.py",
		"name": "dummy"
	}

	msg, path = await sm.run_script(script_info, params={}, headless=True)

	assert "SUCCESS" in msg
	assert path.endswith("dummy.py") or path == "/tmp/dummy/path.py"
	assert "args" in called, "execute_git_script_new_method was not invoked"

