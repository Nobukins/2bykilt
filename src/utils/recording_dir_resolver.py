"""Unified recording directory resolver (Issue #28 incremental refactor)

Public helper create_or_get_recording_dir providing centralized precedence:
    1. explicit argument (UI or caller supplied, highest precedence)
    2. environment variable RECORDING_PATH (non-empty)
    3. feature flag artifacts.unified_recording_path (True -> artifacts/runs/<run>-art/videos)
    4. legacy ./tmp/record_videos (flag disabled)

Rationale:
  * Multiple scattered implementations (browser_manager, scripts, utils) caused
    divergence (UI showed ./tmp/record_videos while script mode used env).
  * Centralizing ensures consistent path across script / browser-control.
  * Keeps ArtifactManager.resolve_recording_dir stable for now; future phase
    can delegate internally to this helper then remove duplication.

Environment variable handling:
  - Empty string or whitespace-only RECORDING_PATH is ignored (falls through).
  - Path is created (mkdir -p) lazily on resolution.

Migration flag (future): artifacts.force_recording_migration could remove
legacy fallback entirely (not introduced yet). Placeholder hook left.
"""
from __future__ import annotations

from pathlib import Path
import os
from typing import Optional

from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext

_LEGACY_REL = "./tmp/record_videos"

def _prepare(dir_path: Path) -> Path:
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def create_or_get_recording_dir(explicit: Optional[str] = None) -> Path:
  """Return the canonical recording directory (creates if missing).

  Precedence order (Issue #28):
    explicit > env(RECORDING_PATH non-empty) > unified-flag > legacy
  """
  # 1. explicit argument
  if explicit:
    return _prepare(Path(explicit).expanduser().resolve())

  # 2. environment variable
  env_val = os.getenv("RECORDING_PATH", "").strip()
  if env_val:
    return _prepare(Path(env_val).expanduser().resolve())

  # 3. force migration (strongest among flag paths)
  if FeatureFlags.is_enabled("artifacts.force_recording_migration"):
    p = RunContext.get().artifact_dir("art") / "videos"
    return _prepare(p)

  # 4. unified flag path
  if FeatureFlags.is_enabled("artifacts.unified_recording_path"):
    p = RunContext.get().artifact_dir("art") / "videos"
    return _prepare(p)

  # 5. legacy fallback (one-time warning handled in ArtifactManager today)
  return _prepare(Path(_LEGACY_REL).resolve())

__all__ = ["create_or_get_recording_dir"]
