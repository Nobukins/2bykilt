"""Simple test for get_available_browsers list type."""

import importlib


def test_get_available_browsers():
	from src.browser import browser_config as bc
	importlib.reload(bc)
	browsers = bc.browser_config.get_available_browsers()
	assert isinstance(browsers, list)

