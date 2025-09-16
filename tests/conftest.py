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
        except (PermissionError, OSError):
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
