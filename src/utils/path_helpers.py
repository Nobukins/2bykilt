"""Common filesystem path helpers used across CLI and UI modules."""
from __future__ import annotations

from pathlib import Path

def find_project_root(start_path: Path = Path(__file__).resolve(), markers=("pyproject.toml", "setup.py")) -> Path:
    """Search upwards from start_path for a directory containing a marker file."""
    for parent in [start_path] + list(start_path.parents):
        for marker in markers:
            if (parent / marker).is_file():
                return parent
    raise FileNotFoundError(f"Could not find project root containing one of {markers}")

PROJECT_ROOT = find_project_root()
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
