"""Verifies is_browser_available returns a bool for both browsers."""

import importlib


def test_is_browser_available_types(monkeypatch):
	from src.browser import browser_config as bc
	importlib.reload(bc)
	for browser in ["chrome", "edge"]:
		available = bc.browser_config.is_browser_available(browser)
		assert isinstance(available, bool)

