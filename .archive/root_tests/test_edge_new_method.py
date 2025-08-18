"""Test NEW METHOD selection logic for edge via env override."""

import os
import importlib
import pytest


@pytest.mark.asyncio
async def test_new_method_edge(monkeypatch):
	os.environ["BYKILT_USE_NEW_METHOD"] = "true"
	monkeypatch.setenv("DEFAULT_BROWSER", "edge")
	import src.script.script_manager as sm
	importlib.reload(sm)

	async def fake_execute(script_info, params, headless, save_recording_path, browser_type):
		return "OK", "/tmp/x.py"

	monkeypatch.setattr(sm, "execute_git_script_new_method", fake_execute, raising=True)
	msg, path = await sm.run_script({
		"type": "git-script",
		"git": "https://example.com/repo.git",
		"script_path": "edge_test.py"
	}, params={}, headless=True)
	assert "OK" in msg

