"""Element Value Capture Helper (Issue #34)

Provides capture_element_value(page, selector: str, label: str, fields: list[str]) -> Path | None
that extracts selected textual properties from a DOM element via Playwright Page API
and persists them as a text artifact using ArtifactManager.

Minimal Scope per Issue #34:
  - Store a single text file per capture under artifacts/runs/<run_id>/elements
  - Update manifest_v2 (ArtifactManager.save_element_capture already does JSON variant)
  - Graceful failure (warn log, no raise)
  - Path traversal safe label -> sanitized filename (<label>.txt)
  - Metrics hook (increment elements count) via ArtifactManager manifest count

Out of Scope (future Issues #35 / #58): structured JSON merging, metrics exporter integration.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional
import re
from datetime import datetime, timezone

from src.core.artifact_manager import get_artifact_manager
from src.utils.app_logger import logger

# Allowed label characters (fallback to underscore for others)
_LABEL_SAFE_RE = re.compile(r"[^A-Za-z0-9_.-]+")

def _sanitize_label(label: str) -> str:
    label = label.strip()[:80] or "element"
    sanitized = _LABEL_SAFE_RE.sub("_", label)
    # Remove leading dots or underscores that could produce hidden or traversal-like names
    sanitized = sanitized.lstrip("./")
    # Collapse long sequences of dots (e.g. 'name..part....ext' -> 'name.part.ext') to reduce ambiguity
    if '..' in sanitized:
        sanitized = re.sub(r'\.{2,}', '.', sanitized)
    if not sanitized:
        sanitized = "element"
    return sanitized

def _persist_capture(collected: List[str], selector: str, safe_label: str) -> Optional[Path]:
    if not collected:
        logger.warning(f"element_capture.empty selector={selector} label={safe_label}")
        return None

    mgr = get_artifact_manager()
    out_dir = mgr.dir / "elements"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"{safe_label}_{ts}.txt"
    fpath = out_dir / fname

    try:
        content = "\n\n".join(collected)
        fpath.write_text(content, encoding="utf-8")
        first_text = next((line[5:].strip() for line in collected if line.startswith("TEXT:")), None)
        first_value = next((line[6:].strip() for line in collected if line.startswith("VALUE:")), None)
        mgr.save_element_capture(selector=selector, text=first_text, value=first_value)
        logger.info(f"element_capture.success file={fpath} selector={selector} label={safe_label}")
        return fpath
    except (OSError, IOError) as e:  # filesystem related
        logger.warning(f"element_capture.fs_fail selector={selector} err={type(e).__name__}:{e}")
        return None
    except Exception as e:  # catch-all safeguard
        logger.warning(f"element_capture.fail selector={selector} err={type(e).__name__}:{e}")
        return None


def _format_tag(base: str, index: int, multi: bool) -> str:
    return base if not multi else f"{base}[{index}]"


def _append_entry(collected: List[str], base: str, index: int, multi: bool, value: str, multiline: bool) -> None:
    tag = _format_tag(base, index, multi)
    entry = f"{tag}:\n{value}" if multiline else f"{tag}: {value}"
    collected.append(entry)


def _log_field_failure(field: str, selector: str, index: int, exc: Exception, async_mode: bool) -> None:
    suffix = "_async_fail" if async_mode else "_fail"
    logger.warning(
        f"element_capture.{field}{suffix} selector={selector} index={index} err={type(exc).__name__}:{exc}"
    )


def _prepare_targets_sync(locator, selector: str) -> tuple[List, bool]:
    try:
        match_count = locator.count()
    except Exception:  # pragma: no cover - Playwright compatibility
        match_count = 1

    if match_count == 0:
        logger.warning(f"element_capture.no_match selector={selector}")
        return [], False

    targets = [locator] if match_count == 1 else [locator.nth(idx) for idx in range(match_count)]
    return targets, len(targets) > 1


def _fetch_text_sync(target) -> Optional[str]:
    txt = target.inner_text(timeout=2000) or ""
    stripped = txt.strip()
    return stripped or None


def _fetch_value_sync(target) -> Optional[str]:
    return target.input_value(timeout=2000)


def _fetch_html_sync(target) -> Optional[str]:
    return target.inner_html(timeout=2000)


_SYNC_FIELD_CONFIG: tuple[tuple[str, Callable, bool, bool], ...] = (
    ("text", _fetch_text_sync, True, False),
    ("value", _fetch_value_sync, False, False),
    ("html", _fetch_html_sync, False, True),
)


def _collect_sync_fields(
    targets: List,
    selector: str,
    normalized_fields: set[str],
    multi: bool,
) -> List[str]:
    collected: List[str] = []
    for index, target in enumerate(targets):
        for field_name, fetcher, skip_blank, multiline in _SYNC_FIELD_CONFIG:
            if field_name not in normalized_fields:
                continue
            try:
                value = fetcher(target)
            except Exception as exc:  # noqa: BLE001
                _log_field_failure(field_name, selector, index, exc, async_mode=False)
                continue
            if value is None:
                continue
            if skip_blank and isinstance(value, str) and not value:
                continue
            _append_entry(collected, field_name.upper(), index, multi, value, multiline)
    return collected


async def _prepare_targets_async(locator, selector: str) -> tuple[List, bool]:
    try:
        match_count = await locator.count()  # noqa: BLE001
    except Exception:  # noqa: BLE001 - Playwright compatibility
        match_count = 1

    if match_count == 0:
        logger.warning(f"element_capture.async_no_match selector={selector}")
        return [], False

    targets = [locator] if match_count == 1 else [locator.nth(idx) for idx in range(match_count)]
    return targets, len(targets) > 1


async def _fetch_text_async(target) -> Optional[str]:
    txt = await target.inner_text(timeout=2000)  # noqa: BLE001
    stripped = (txt or "").strip()
    return stripped or None


async def _fetch_value_async(target) -> Optional[str]:
    return await target.input_value(timeout=2000)  # noqa: BLE001


async def _fetch_html_async(target) -> Optional[str]:
    return await target.inner_html(timeout=2000)  # noqa: BLE001


_ASYNC_FIELD_CONFIG: tuple[tuple[str, Callable, bool, bool], ...] = (
    ("text", _fetch_text_async, True, False),
    ("value", _fetch_value_async, False, False),
    ("html", _fetch_html_async, False, True),
)


async def _collect_async_fields(
    targets: List,
    selector: str,
    normalized_fields: set[str],
    multi: bool,
) -> List[str]:
    collected: List[str] = []
    for index, target in enumerate(targets):
        for field_name, fetcher, skip_blank, multiline in _ASYNC_FIELD_CONFIG:
            if field_name not in normalized_fields:
                continue
            try:
                value = await fetcher(target)  # type: ignore[misc]
            except Exception as exc:  # noqa: BLE001
                _log_field_failure(field_name, selector, index, exc, async_mode=True)
                continue
            if value is None:
                continue
            if skip_blank and isinstance(value, str) and not value:
                continue
            _append_entry(collected, field_name.upper(), index, multi, value, multiline)
    return collected


def capture_element_value(page, selector: str, label: str, fields: Optional[List[str]] = None) -> Optional[Path]:
    """Capture specified element value aspects and persist as a text artifact.

    Args:
        page: Playwright Page-like object (duck typed, must provide locator / query)
        selector: CSS/XPath selector (passed directly to page.locator)
        label: Logical label for file naming (sanitized)
        fields: Subset of ['text', 'value', 'html']; defaults to ['text']

    Returns:
        Path to saved .txt file or None on failure.
    """
    fields = fields or ["text"]
    safe_label = _sanitize_label(label)
    try:
        loc = page.locator(selector)
        targets, multi = _prepare_targets_sync(loc, selector)
        if not targets:
            return None

        normalized_fields = {field.lower() for field in fields}
        collected = _collect_sync_fields(targets, selector, normalized_fields, multi)
        return _persist_capture(collected, selector, safe_label)
    except Exception as e:  # catch-all safeguard
        logger.warning(f"element_capture.fail selector={selector} err={type(e).__name__}:{e}")
        return None


async def async_capture_element_value(page, selector: str, label: str, fields: Optional[List[str]] = None) -> Optional[Path]:
    """Asynchronous variant of :func:`capture_element_value` for Playwright async API."""
    fields = fields or ["text"]
    safe_label = _sanitize_label(label)

    try:
        loc = page.locator(selector)
        targets, multi = await _prepare_targets_async(loc, selector)
        if not targets:
            return None

        normalized_fields = {field.lower() for field in fields}
        collected = await _collect_async_fields(targets, selector, normalized_fields, multi)
        return _persist_capture(collected, selector, safe_label)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"element_capture.async_fail selector={selector} err={type(e).__name__}:{e}")
        return None

__all__ = ["capture_element_value", "async_capture_element_value"]
