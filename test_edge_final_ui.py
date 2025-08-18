"""Edge related light tests using BrowserConfig only."""

import importlib


def test_set_current_browser_edge(monkeypatch):
	monkeypatch.setenv("DEFAULT_BROWSER", "edge")
	from src.browser import browser_config as bc
	importlib.reload(bc)
	bc.browser_config.set_current_browser("edge")
	assert bc.browser_config.get_current_browser() == "edge"

