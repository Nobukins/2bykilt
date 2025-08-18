"""Chrome specific small test using BrowserConfig path retrieval."""

import importlib


def test_get_current_browser_path(monkeypatch):
	monkeypatch.setenv("DEFAULT_BROWSER", "chrome")
	from src.browser import browser_config as bc
	mod = importlib.reload(bc)
	path = mod.browser_config.get_current_browser_path()
	# Path may be empty on CI, just ensure it's a string
	assert isinstance(path, str)

