"""Basic placeholder ensuring module import for patch function works."""

import importlib


def test_patch_function_importable():
	import src.script.script_manager as sm
	importlib.reload(sm)
	assert hasattr(sm, "patch_search_script_for_chrome")

