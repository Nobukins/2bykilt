"""
Compatibility shim for legacy tmp/myscript path.

Bridges pytest hooks to myscript/conftest.py so that CLI options like --query
continue to work during the transition period. This avoids breakage when users
still run: pytest tmp/myscript/search_script.py --query ...
"""

from __future__ import annotations

from typing import Any


def pytest_addoption(parser):  # type: ignore[override]
    try:
        from myscript.conftest import pytest_addoption as _orig_addoption  # noqa: WPS433
        return _orig_addoption(parser)
    except Exception:  # pragma: no cover - defensive fallback
        # Minimal fallback so --query doesn't crash collection
        parser.addoption("--query", action="store", default="", help="Search query for the test (compat)")


def pytest_configure(config):  # type: ignore[override]
    try:
        from myscript.conftest import pytest_configure as _orig_configure  # noqa: WPS433
        return _orig_configure(config)
    except Exception:  # pragma: no cover - defensive fallback
        # No-op if original is unavailable
        return None
import pytest
import pytest_asyncio

# Register the asyncio plugin
# pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest with asyncio markers"""
    config.addinivalue_line("markers", "asyncio: mark test to run with asyncio")

def pytest_addoption(parser):
    parser.addoption("--query", action="store", default="", help="Search query for the test")
    parser.addoption("--browser-type", action="store", default=None, help="Browser type to use (chrome/edge/firefox/webkit)")
    parser.addoption("--browser-executable", action="store", default=None, help="Path to browser executable")
    parser.addoption("--use-profile", action="store_true", default=False, help="Use user profile for Chrome/Edge")
    parser.addoption("--profile-path", action="store", default=None, help="Custom user profile path")