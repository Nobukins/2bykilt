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
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Type

from src.core.artifact_manager import get_artifact_manager
from src.config.feature_flags import FeatureFlags
from src.utils.app_logger import logger

# --- Exception Classification (Issue #88) ---
# We avoid importing playwright.sync_api directly to keep optional dependency loose.
# Instead we classify by exception name substrings to prevent hard coupling.
_TRANSIENT_KEYWORDS = [
    "TimeoutError",  # operation timeouts
    "TargetClosedError",  # browser/page closed mid-operation
    "WebSocketError",  # transport hiccups
]

_FATAL_KEYWORDS = [
    "NotConnectedError",  # underlying browser driver dead
    "ProtocolError",  # low-level protocol corruption
]

def _classify_exception(exc: Exception) -> str:
    name = type(exc).__name__
    full = f"{name}:{exc}"[:300]
    for kw in _TRANSIENT_KEYWORDS:
        if kw in name:
            return "transient"
    for kw in _FATAL_KEYWORDS:
        if kw in name:
            return "fatal"
    # Generic fallback: treat common OSError as transient (IOError is alias in Py3)
    if isinstance(exc, OSError):
        return "transient"
    return "unknown"


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
    except Exception as exc:  # noqa: BLE001
        error_type = _classify_exception(exc)
        # Log level selection: transient -> warning, fatal -> error, unknown -> warning
        if error_type == "fatal":
            logger.error(f"[screenshot_manager] capture_fail prefix={prefix} error_type={error_type} error={exc}")
        else:
            logger.warning(f"[screenshot_manager] capture_fail prefix={prefix} error_type={error_type} error={exc}")
        # For transient we may consider retry in future (#89 / metrics instrumentation) – no retry yet.
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
                except Exception as dup_exc:  # noqa: BLE001
                    # Failure to create the optional duplicate should not fail overall capture.
                    logger.warning(f"[screenshot_manager] duplicate_copy_fail target={user_named} error={dup_exc}")
            # PR #96 review: treat duplicate_copy as "present after operation" (either pre-existing or just written)
            duplicate_copy = user_named.exists()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info(
            f"[screenshot_manager] capture_success prefix={prefix} path={path} duplicate_copy={duplicate_copy}"
        )
        return path, b64
    except Exception as exc:  # noqa: BLE001
        error_type = _classify_exception(exc)
        # Consistent with capture_fail: only fatal escalates to error level; unknown stays warning.
        level_fn = logger.error if error_type == "fatal" else logger.warning
        level_fn(f"[screenshot_manager] persist_fail prefix={prefix} error_type={error_type} error={exc}")
        return None, None

__all__ = ["capture_page_screenshot"]
