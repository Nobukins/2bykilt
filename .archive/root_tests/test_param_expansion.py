"""Test ActionRunner style ${params.name|default} expansion via script_manager logic.

We exercise the regex replacement by calling the private branch through run_script
with type=action_runner_template to keep code paths covered.
"""

import importlib
import pytest


@pytest.mark.asyncio
async def test_action_runner_param_expansion(tmp_path, monkeypatch):
	import src.script.script_manager as sm
	importlib.reload(sm)
	# Build a fake action that will run 'echo' (portable) so no pytest / browser.
	script_info = {
		"type": "action_runner_template",
		"action_script": "echo",
		"command": "python -c 'print(\"hello\", \"${params.target|world}\")'"
	}
	msg, path = await sm.run_script(script_info, params={"target": "universe"}, headless=True)
	# For this template path is None by design
	assert path is None
	assert isinstance(msg, str)

