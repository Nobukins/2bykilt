"""Browser args / config validation tests.

Fast, side‑effect free tests covering BrowserConfig logic:
  - default / env override
  - invalid browser fallback
  - idempotent set_current_browser
  - switching browsers
  - validate_current_browser fallback
  - debugging port override

These tests intentionally avoid launching Playwright browsers.
"""

import os
import sys
import importlib
from types import SimpleNamespace
from pathlib import Path

import pytest

# Ensure project root and src/ are on path when running from tests/
ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))


def _reset_singleton():
    from src.browser.browser_config import BrowserConfig
    BrowserConfig._instance = None  # type: ignore


def fresh_browser_config(env: dict):
    """Return a fresh BrowserConfig instance with controlled environment.

    Resets the singleton and reloads the module so environment variables are re-read.
    """
    backup = os.environ.copy()
    os.environ.update(env)
    try:
        _reset_singleton()
        import src.browser.browser_config as cfg_mod
        importlib.reload(cfg_mod)
        return cfg_mod.BrowserConfig(), SimpleNamespace(module=cfg_mod, backup=backup)
    finally:
        os.environ.clear()
        os.environ.update(backup)


def test_default_browser_fallback():
    cfg, _ = fresh_browser_config({})
    assert cfg.get_current_browser() == "chrome"
    assert cfg.get_browser_settings()["browser_type"] == "chrome"


def test_env_overrides_default_browser():
    cfg, _ = fresh_browser_config({"DEFAULT_BROWSER": "edge"})
    assert cfg.get_current_browser() == "edge"
    assert cfg.get_browser_settings()["browser_type"] == "edge"


def test_invalid_browser_type_graceful_fallback(caplog):
    cfg, _ = fresh_browser_config({"DEFAULT_BROWSER": "safari"})
    settings = cfg.get_browser_settings("safari")
    assert settings["browser_type"] == "chrome"
    assert any("Unknown browser type" in r.getMessage() for r in caplog.records)


def test_set_current_browser_idempotent():
    cfg, _ = fresh_browser_config({"DEFAULT_BROWSER": "chrome"})
    before = cfg.get_current_browser()
    cfg.set_current_browser("chrome")  # no exception & state unchanged
    assert cfg.get_current_browser() == before == "chrome"


def test_set_current_browser_switch():
    cfg, _ = fresh_browser_config({"DEFAULT_BROWSER": "chrome"})
    cfg.set_current_browser("edge")
    assert cfg.get_current_browser() == "edge"


def test_validate_current_browser_auto_fallback(monkeypatch):
    cfg, _ = fresh_browser_config({"DEFAULT_BROWSER": "chrome"})
    availability = {"chrome": False, "edge": True}

    # Force path existence to True (path value doesn't matter here)
    monkeypatch.setattr("os.path.exists", lambda p: True)
    monkeypatch.setattr(cfg, "is_browser_available", lambda b: availability[b])
    monkeypatch.setattr(cfg, "get_available_browsers", lambda: [b for b, ok in availability.items() if ok])

    assert cfg.validate_current_browser() is True
    assert cfg.get_current_browser() == "edge"


def test_debugging_port_env_override(monkeypatch):
    monkeypatch.setenv("CHROME_DEBUGGING_PORT", "9333")
    cfg, _ = fresh_browser_config({"CHROME_DEBUGGING_PORT": "9333"})
    chrome_settings = cfg.get_browser_settings("chrome")
    assert chrome_settings["debugging_port"] == 9333
