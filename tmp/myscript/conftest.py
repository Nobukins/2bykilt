"""
Compatibility shim for legacy tmp/myscript path.

Bridges pytest hooks to myscript/conftest.py so that CLI options like --query
continue to work during the transition period. This avoids breakage when users
still run: pytest tmp/myscript/search_script.py --query ...
"""

from __future__ import annotations

import pytest
from typing import Any


def pytest_addoption(parser: pytest.Parser) -> None:
    try:
        from myscript.conftest import pytest_addoption as _orig_addoption  # noqa: WPS433
        return _orig_addoption(parser)
    except ImportError:  # pragma: no cover - defensive fallback
        # Minimal fallback so --query doesn't crash collection
        parser.addoption("--query", action="store", default="", help="Search query for the test (compat)")


def pytest_configure(config: pytest.Config) -> None:
    try:
        from myscript.conftest import pytest_configure as _orig_configure  # noqa: WPS433
        return _orig_configure(config)
    except ImportError:  # pragma: no cover - defensive fallback
        # No-op if original is unavailable
        return None