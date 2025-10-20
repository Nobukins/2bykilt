"""Unified recording directory resolver (Issue #353 - legacy path removal)

Public helper create_or_get_recording_dir providing centralized precedence:
    1. explicit argument (UI or caller supplied, highest precedence)
    2. environment variable RECORDING_PATH (non-empty)
    3. artifacts/runs/<run>-art/videos (unified path)

Rationale (Issue #353):
  * Removed legacy ./tmp/record_videos fallback path
  * All recordings now stored within unified artifact hierarchy
  * Simplifies path resolution and eliminates scattered implementations
  * Centralizes logic across script mode, UI, and browser control

Environment variable handling:
  - Empty string or whitespace-only RECORDING_PATH is ignored (falls through).
  - Path is created (mkdir -p) lazily on resolution.
  - RECORDING_PATH takes precedence for migration flexibility
"""
from __future__ import annotations

from pathlib import Path
import os
from typing import Optional

from src.runtime.run_context import RunContext

def _prepare(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def create_or_get_recording_dir(explicit: Optional[str] = None) -> Path:
  """Return the canonical recording directory (creates if missing).

  Precedence order (Issue #353):
    explicit > env(RECORDING_PATH non-empty) > artifacts/runs/<run>-art/videos
  """
  # 1. explicit argument
  if explicit:
    return _prepare(Path(explicit).expanduser().resolve())

  # 2. environment variable (for migration flexibility)
  env_val = os.getenv("RECORDING_PATH", "").strip()
  if env_val:
    return _prepare(Path(env_val).expanduser().resolve())

  # 3. unified artifacts path (no legacy fallback)
  p = RunContext.get().artifact_dir("art") / "videos"
  return _prepare(p)

__all__ = ["create_or_get_recording_dir"]
