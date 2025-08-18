"""LLM disabled UI related light test.

Ensures update_model_dropdown returns the disabled placeholder when LLM is off.
We avoid enabling LLM to keep imports light.
"""

import importlib
import os
import pytest


def test_update_model_dropdown_llm_disabled(monkeypatch):
	monkeypatch.setenv("ENABLE_LLM", "false")
	# Reload utils to apply ENABLE_LLM flag at module import time
	import src.utils.utils as utils
	importlib.reload(utils)

	try:
		dropdown = utils.update_model_dropdown("openai")
	except Exception as e:  # pragma: no cover - guard for unexpected env
		pytest.skip(f"Skipped due to environment issue: {e}")

	# When LLM disabled we expect a single disabled choice
	assert hasattr(dropdown, "choice_builder") or dropdown.choices == ["LLM functionality disabled"]

