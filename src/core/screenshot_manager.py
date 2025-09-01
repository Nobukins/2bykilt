"""Screenshot Utility (Issue #33)

Provides a thin wrapper around Playwright page.screenshot() that:
  * Normalizes naming (prefix + timestamp)
  * Persists via ArtifactManager (manifest v2 aware)
  * Returns (path, base64_str)

Design:
  - Avoid importing Playwright types (runtime duck typing) to keep lightweight.
  - If capture fails, returns (None, None) without raising.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from src.core.artifact_manager import get_artifact_manager
from src.config.feature_flags import FeatureFlags


_DEF_PREFIX = "screenshot"


def capture_page_screenshot(page, prefix: str = _DEF_PREFIX, image_format: str = "png") -> Tuple[Optional[Path], Optional[str]]:
    """Capture a screenshot of a Playwright page and store through ArtifactManager.

    Returns (file_path, base64_string).
    Fails soft (no raise) to not break primary flows.
    """
    mgr = get_artifact_manager()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"{prefix}_{ts}.{image_format.lower()}"
    try:
        raw_bytes = page.screenshot(type=image_format.lower())  # sync API in most contexts
    except Exception:  # noqa: BLE001
        return None, None
    # Persist via ArtifactManager (only if manifest v2 enabled OR legacy allowed)
    try:
        # ArtifactManager always writes file to its own screenshots folder (canonical)
        path = mgr.save_screenshot_bytes(raw_bytes, prefix=f"{prefix}")  # it creates its own timestamped name
        # If user wants deterministic name, also write secondary copy under artifacts dir for reference
        user_named = path.parent / fname
        if not user_named.exists():
            user_named.write_bytes(raw_bytes)
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        return path, b64
    except Exception:  # noqa: BLE001
        return None, None

__all__ = ["capture_page_screenshot"]
