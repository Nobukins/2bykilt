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
from src.utils.app_logger import logger


_DEF_PREFIX = "screenshot"


def capture_page_screenshot(page, prefix: str = _DEF_PREFIX, image_format: str = "png") -> Tuple[Optional[Path], Optional[str]]:
    """Capture a screenshot of a Playwright page and store through ArtifactManager.

    Returns (file_path, base64_string).
    Fails soft (no raise) to not break primary flows.
    """
    mgr = get_artifact_manager()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"{prefix}_{ts}.{image_format.lower()}"

    logger.info(f"[screenshot_manager] capture_start prefix={prefix} format={image_format.lower()}")

    try:
        raw_bytes = page.screenshot(type=image_format.lower())  # sync API in most contexts
    except Exception as exc:  # Broad for now; follow-up issue will narrow to Playwright specifics
        logger.warning(f"[screenshot_manager] capture_fail prefix={prefix} error={exc}")
        return None, None

    try:
        path = mgr.save_screenshot_bytes(raw_bytes, prefix=f"{prefix}")
        # Optional duplicate (deterministic) filename copy gated by flag (default True for backward compatibility)
        write_dup = True
        try:  # tolerate absent flag config gracefully
            write_dup = FeatureFlags.is_enabled("artifacts.screenshot.user_named_copy_enabled")  # type: ignore
        except Exception:
            write_dup = True
        duplicate_copy = False
        if write_dup:
            user_named = path.parent / fname
            if not user_named.exists():
                try:
                    user_named.write_bytes(raw_bytes)
                    duplicate_copy = True
                except Exception as dup_exc:  # noqa: BLE001
                    logger.warning(f"[screenshot_manager] duplicate_copy_fail target={user_named} error={dup_exc}")
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info(
            f"[screenshot_manager] capture_success prefix={prefix} path={path} duplicate_copy={duplicate_copy}"
        )
        return path, b64
    except Exception as exc:  # noqa: BLE001
        logger.error(f"[screenshot_manager] persist_fail prefix={prefix} error={exc}")
        return None, None

__all__ = ["capture_page_screenshot"]
