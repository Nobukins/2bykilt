"""Test that run_script gracefully handles missing required fields for git-script."""

import pytest

from src.script import script_manager as sm


@pytest.mark.asyncio
async def test_git_script_missing_fields():
	msg, path = await sm.run_script({"type": "git-script"}, params={})
	assert "Missing" in msg or "requires" in msg or path is None

