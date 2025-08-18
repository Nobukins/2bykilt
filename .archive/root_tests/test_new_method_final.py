"""Sanity test for execute_git_script_new_method monkeypatched path final state."""

import os
import importlib
import pytest


@pytest.mark.asyncio
async def test_execute_git_script_new_method_called(monkeypatch):
	os.environ["BYKILT_USE_NEW_METHOD"] = "true"
	import src.script.script_manager as sm
	importlib.reload(sm)
	called = {}

	async def fake_exec(script_info, params, headless, save_recording_path, browser_type):
		called["ok"] = True
		return "done", "/tmp/z.py"

	monkeypatch.setattr(sm, "execute_git_script_new_method", fake_exec, raising=True)
	await sm.run_script({
		"type": "git-script", "git": "https://example.com/x.git", "script_path": "a.py"
	}, params={}, headless=False)
	assert called.get("ok") is True

