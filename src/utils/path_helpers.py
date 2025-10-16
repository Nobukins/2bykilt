"""Common filesystem path helpers used across CLI and UI modules."""
from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ASSETS_DIR = PROJECT_ROOT / "assets"
LLMS_TXT_PATH = PROJECT_ROOT / "llms.txt"


def get_project_root() -> Path:
    """Return the repository root directory."""
    return PROJECT_ROOT


def get_assets_dir() -> Path:
    """Return the shared assets directory."""
    return ASSETS_DIR


def get_llms_txt_path() -> Path:
    """Return the path to the llms.txt configuration file."""
    return LLMS_TXT_PATH
