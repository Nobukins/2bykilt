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
import json
import time
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


def _emit_event(level: str, payload: dict) -> None:
    """Emit a structured JSON line for screenshot events (Issue #89 schema v1).

    Payload MUST already contain 'event' key. Adds schema_version if missing.
    """
    if "schema_version" not in payload:
        payload["schema_version"] = 1
    line = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    if level == "error":
        logger.error(line)
    elif level == "warning":
        logger.warning(line)
    else:
        logger.info(line)


def capture_page_screenshot(page, prefix: str = _DEF_PREFIX, image_format: str = "png") -> Tuple[Optional[Path], Optional[str]]:
    """Capture a screenshot of a Playwright page and store through ArtifactManager.

    Returns (file_path, base64_string). Soft-fail design: returns (None,None) on error.
    Structured logging (Issue #89) events:
      - screenshot.capture.start
      - screenshot.capture.success
      - screenshot.capture.fail
      - screenshot.persist.fail
    Common fields: event, prefix, latency_ms (when applicable), size_bytes (success), error_type/error_message (fail), duplicate_copy.
    """
    mgr = get_artifact_manager()
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"{prefix}_{ts}.{image_format.lower()}"
    start_ts = time.perf_counter()

    _emit_event("info", {
        "event": "screenshot.capture.start",
        "prefix": prefix,
        "format": image_format.lower(),
    })

    try:
        raw_bytes = page.screenshot(type=image_format.lower())  # sync API
        capture_latency_ms = int((time.perf_counter() - start_ts) * 1000)
    except Exception as exc:  # noqa: BLE001
        capture_latency_ms = int((time.perf_counter() - start_ts) * 1000)
        error_type = _classify_exception(exc)
        level = "error" if error_type == "fatal" else "warning"
        _emit_event(level, {
            "event": "screenshot.capture.fail",
            "prefix": prefix,
            "error_type": error_type,
            "error_message": str(exc),
            "latency_ms": capture_latency_ms,
        })
        return None, None

    # Success path: attempt persistence and optional duplicate
    try:
        path = mgr.save_screenshot_bytes(raw_bytes, prefix=f"{prefix}")
        size_bytes = len(raw_bytes) if isinstance(raw_bytes, (bytes, bytearray)) else None
        # Optional duplicate (deterministic) filename copy gated by flag (default True for backward compatibility)
        write_dup = True
        try:
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
                    _emit_event("warning", {
                        "event": "screenshot.duplicate.fail",
                        "prefix": prefix,
                        "target": str(user_named),
                        "error_message": str(dup_exc),
                    })
            duplicate_copy = user_named.exists()
        b64 = base64.b64encode(raw_bytes).decode("utf-8")
        _emit_event("info", {
            "event": "screenshot.capture.success",
            "prefix": prefix,
            "path": str(path),
            "duplicate_copy": duplicate_copy,
            "latency_ms": capture_latency_ms,
            "size_bytes": size_bytes,
        })
        return path, b64
    except Exception as exc:  # noqa: BLE001
        persist_latency_ms = int((time.perf_counter() - start_ts) * 1000)
        error_type = _classify_exception(exc)
        level = "error" if error_type == "fatal" else "warning"
        _emit_event(level, {
            "event": "screenshot.persist.fail",
            "prefix": prefix,
            "error_type": error_type,
            "error_message": str(exc),
            "latency_ms": persist_latency_ms,
        })
        return None, None

__all__ = ["capture_page_screenshot"]
