"""
Pytest configuration for test path setup.

This file ensures tests can import project modules without hardcoded absolute paths.
It dynamically detects the repository root and adds either the repo root or the
`src` directory to sys.path. An optional environment variable `BYKILT_ROOT`
can override the detection (useful for non-standard layouts).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _detect_project_root(start: Path) -> Path:
    """Detect the repository root by walking up until a marker is found.

    Markers include common project files: pyproject.toml, README.md, .git
    """

    markers = {"pyproject.toml", "README.md", ".git"}
    current = start.resolve()

    for parent in [current] + list(current.parents):
        try:
            entries = {p.name for p in parent.iterdir()}
        except Exception:
            continue
        if markers & entries:
            return parent
    return start


def _ensure_sys_path(path: Path) -> None:
    p = str(path)
    if p not in sys.path:
        sys.path.insert(0, p)


def pytest_configure(config):  # noqa: D401 - pytest hook
    """Pytest configure hook to set up import paths."""

    # 1) Allow explicit override
    root_env = os.environ.get("BYKILT_ROOT")
    if root_env:
        root_path = Path(root_env).expanduser().resolve()
    else:
        # 2) Auto-detect based on this file's location
        this_file = Path(__file__).resolve()
        root_path = _detect_project_root(this_file.parent)

    # Prefer src/ if it exists; else add repo root
    src_path = root_path / "src"
    if src_path.exists():
        _ensure_sys_path(src_path)
    _ensure_sys_path(root_path)

    # Optional: expose for tests that may need it
    os.environ.setdefault("BYKILT_ROOT_EFFECTIVE", str(root_path))
# Ensure project root and src/ are importable when running pytest from tests/
import sys
from pathlib import Path
import asyncio
import pytest

# Mitigate widespread 'event loop is already running' failures in full test runs
# by allowing nested loop usage (some code paths start an event loop internally)
# and by providing a fresh loop per test. (#91 stabilization)
try:
    import nest_asyncio  # type: ignore
    nest_asyncio.apply()
except (ImportError, ModuleNotFoundError):  # narrow scope to import errors only
    pass  # If unavailable, continue; tests that don't nest loops still pass.

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


@pytest.fixture(scope="function")
def event_loop():
    """Provide a fresh asyncio event loop per test.

    The default pytest-asyncio behavior under auto mode occasionally collides
    with nested loop starts inside application code (e.g., utilities launching
    temporary async tasks). Creating an isolated loop here prevents cross-test
    contamination and eliminates re-entrancy errors.
    """
    loop = asyncio.new_event_loop()
    try:
        yield loop
    finally:
        loop.close()
