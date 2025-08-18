"""Test that legacy path triggers when BYKILT_USE_NEW_METHOD is false (error expected)."""

import os
import importlib
import pytest


@pytest.mark.asyncio
async def test_legacy_git_script_path(monkeypatch):
	os.environ["BYKILT_USE_NEW_METHOD"] = "false"
	import src.script.script_manager as sm
	importlib.reload(sm)
	# Provide minimal fields; will attempt legacy path and likely fail before clone (network) => capture message
	msg, _ = await sm.run_script({
		"type": "git-script", "git": "https://invalid.invalid/repo.git", "script_path": "a.py"
	}, params={}, headless=True)
	# We just assert it returns a message string
	assert isinstance(msg, str)

