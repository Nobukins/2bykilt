"""Smoke test enumerating a few public functions for presence."""

def test_core_symbol_presence():
	# Lazy imports to avoid heavy side effects
	import importlib
	bc = importlib.import_module("src.browser.browser_config")
	dispatcher = importlib.import_module("src.modules.command_dispatcher")
	script_mgr = importlib.import_module("src.script.script_manager")
	assert hasattr(bc, "browser_config")
	assert hasattr(dispatcher, "CommandDispatcher")
	assert hasattr(script_mgr, "run_script")

