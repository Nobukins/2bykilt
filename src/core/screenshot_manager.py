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
import time
import json
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

    start_ts = time.perf_counter()
    # human-readable + structured JSON on following line
    logger.info(f"[screenshot_manager] capture_start event=screenshot.capture_start prefix={prefix} format={image_format.lower()}")
    logger.info(json.dumps({
        "event": "screenshot.capture.start",  # dotted form
        "schema_version": 1,
        "prefix": prefix,
        "format": image_format.lower(),
    }, ensure_ascii=False, separators=(",", ":")))

    try:
        raw_bytes = page.screenshot(type=image_format.lower())  # sync API in most contexts
        capture_latency_ms = int((time.perf_counter() - start_ts) * 1000)
    except Exception as exc:  # noqa: BLE001
        error_type = _classify_exception(exc)
        if error_type == "fatal":
            logger.error(f"[screenshot_manager] capture_fail event=screenshot.capture_fail prefix={prefix} error_type={error_type} error={exc}")
        else:
            logger.warning(f"[screenshot_manager] capture_fail event=screenshot.capture_fail prefix={prefix} error_type={error_type} error={exc}")
        logger.warning(json.dumps({
            "event": "screenshot.capture.fail",
            "schema_version": 1,
            "prefix": prefix,
            "error_type": error_type,
            "error_message": str(exc)[:500],
            "latency_ms": int((time.perf_counter() - start_ts) * 1000),
        }, ensure_ascii=False, separators=(",", ":")))
        return None, None

    try:
        path = mgr.save_screenshot_bytes(raw_bytes, prefix=f"{prefix}")
        size_bytes = len(raw_bytes) if isinstance(raw_bytes, (bytes, bytearray)) else None
        # Evaluate feature flag (default ON to preserve legacy behavior if flag subsystem unavailable)
        try:
            write_dup = FeatureFlags.is_enabled("artifacts.screenshot.user_named_copy_enabled")  # type: ignore
        except Exception:
            write_dup = True

        duplicate_copy = False

        # Gather existing prefixed screenshots (including those from prior test runs sharing RUN_ID)
        try:
            existing = list(path.parent.glob(f"{prefix}_*.{image_format.lower()}"))
        except Exception as scan_exc:  # noqa: BLE001
            existing = []
            logger.debug(f"[screenshot_manager] duplicate_scan_error error={scan_exc}")

        if write_dup:
            user_named = path.parent / fname
            # Prune stale duplicates except current canonical path and new duplicate target
            for old in existing:
                if old.name not in {path.name, user_named.name}:
                    try:
                        old.unlink(missing_ok=True)  # type: ignore[arg-type]
                    except Exception as prune_exc:  # noqa: BLE001
                        logger.debug(f"[screenshot_manager] duplicate_prune_skip target={old} error={prune_exc}")
            if not user_named.exists():
                try:
                    user_named.write_bytes(raw_bytes)
                except Exception as dup_exc:  # noqa: BLE001
                    logger.warning(f"[screenshot_manager] duplicate_copy_fail target={user_named} error={dup_exc}")
            duplicate_copy = user_named.exists()
        else:
            # Flag disabled -> ensure no leftover duplicate artifacts (keep only canonical path)
            for old in existing:
                if old.name != path.name:
                    try:
                        old.unlink(missing_ok=True)  # type: ignore[arg-type]
                    except Exception as prune_exc:  # noqa: BLE001
                        logger.debug(f"[screenshot_manager] duplicate_prune_skip (flag_off) target={old} error={prune_exc}")
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        logger.info(
            f"[screenshot_manager] capture_success event=screenshot.capture_success prefix={prefix} path={path} duplicate_copy={duplicate_copy} latency_ms={capture_latency_ms} size_bytes={size_bytes}"
        )
        logger.info(json.dumps({
            "event": "screenshot.capture.success",
            "schema_version": 1,
            "prefix": prefix,
            "path": str(path),
            "duplicate_copy": duplicate_copy,
            "latency_ms": capture_latency_ms,
            "size_bytes": size_bytes,
        }, ensure_ascii=False, separators=(",", ":")))
        return path, b64
    except Exception as exc:  # noqa: BLE001
        error_type = _classify_exception(exc)
        level_fn = logger.error if error_type == "fatal" else logger.warning
        persist_latency_ms = int((time.perf_counter() - start_ts) * 1000)
        level_fn(f"[screenshot_manager] persist_fail event=screenshot.persist_fail prefix={prefix} error_type={error_type} error={exc} latency_ms={persist_latency_ms}")
        level_fn(json.dumps({
            "event": "screenshot.persist.fail",
            "schema_version": 1,
            "prefix": prefix,
            "error_type": error_type,
            "error_message": str(exc)[:500],
            "latency_ms": persist_latency_ms,
        }, ensure_ascii=False, separators=(",", ":")))
        return None, None

__all__ = ["capture_page_screenshot"]
