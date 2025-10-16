"""
Batch processing utility functions.

This module provides helper functions used across the batch processing system.
"""

from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir


def to_portable_relpath(p: Path) -> str:
    """
    Convert a Path to a portable relative path string.
    
    Reuses artifact manager's portable relpath logic pattern (simplified inline) (#175 helper).
    
    Args:
        p: Path to convert
        
    Returns:
        Portable relative path string using forward slashes
        
    Example:
        >>> to_portable_relpath(Path("/path/to/file.txt"))
        'path/to/file.txt'
    """
    try:
        rel = p.relative_to(Path.cwd())
        return rel.as_posix()
    except Exception:  # noqa: BLE001
        try:
            rel = p.relative_to(get_artifacts_base_dir())
            return rel.as_posix()
        except Exception:  # noqa: BLE001
            return p.name
