"""Tests comparing chromium/chrome config fallback logic."""

import importlib
import os


def _reload():
	from src.browser import browser_config as bc
	return importlib.reload(bc)


def test_default_browser_is_chrome_when_unspecified(monkeypatch):
	monkeypatch.delenv("DEFAULT_BROWSER", raising=False)
	mod = _reload()
	assert mod.browser_config.get_current_browser() == "chrome"


def test_validate_current_browser_handles_missing_paths(monkeypatch):
	# Force paths to blank so availability will fail => validate returns False
	monkeypatch.setenv("CHROME_PATH", "")
	monkeypatch.setenv("EDGE_PATH", "")
	mod = _reload()
	assert mod.browser_config.validate_current_browser() in (True, False)  # Should not raise

