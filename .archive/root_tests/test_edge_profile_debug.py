"""Profile debug style test using BrowserConfig.log_all_browser_states."""

import importlib


def test_log_all_browser_states(monkeypatch):
	monkeypatch.setenv("DEFAULT_BROWSER", "chrome")
	from src.browser import browser_config as bc
	mod = importlib.reload(bc)
	state = mod.browser_config.log_all_browser_states()
	assert set(state.keys()) == {"global", "new", "matching"}

