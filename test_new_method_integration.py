"""Integration-lite combining dispatcher + new method flag (no real network)."""

import os
import importlib
import pytest

from src.modules.command_dispatcher import CommandDispatcher


@pytest.mark.asyncio
async def test_dispatch_git_script_new_method(monkeypatch):
	# Create temporary llms.txt action referencing git-script
	monkeypatch.setenv("BYKILT_USE_NEW_METHOD", "true")
	content = "actions:\n  - name: run-repo\n    type: git-script\n    git: https://example.com/repo.git\n    script_path: main.py\n"
	with open("llms.txt", "w", encoding="utf-8") as f:
		f.write(content)

	# Patch execute function
	import src.script.script_manager as sm
	importlib.reload(sm)
	async def fake_exec(script_info, params, headless, save_recording_path, browser_type):
		return "ok", "/tmp/y.py"
	monkeypatch.setattr(sm, "execute_git_script_new_method", fake_exec, raising=True)

	d = CommandDispatcher()
	result = await d.dispatch("run-repo")
	assert result["action_type"] == "git-script"

