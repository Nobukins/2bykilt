"""Minimal sanity test for edge browser settings retrieval."""

import importlib


def test_edge_settings_dict(monkeypatch):
	monkeypatch.setenv("DEFAULT_BROWSER", "edge")
	from src.browser import browser_config as bc
	mod = importlib.reload(bc)
	settings = mod.browser_config.get_browser_settings("edge")
	assert settings["browser_type"] == "edge"
	assert {"path", "user_data", "debugging_port"}.issubset(settings.keys())

