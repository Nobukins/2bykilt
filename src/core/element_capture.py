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
from typing import List, Optional
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
    if not sanitized:
        sanitized = "element"
    return sanitized

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
    mgr = get_artifact_manager()
    out_dir = mgr.dir / "elements"
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
    fname = f"{safe_label}_{ts}.txt"
    fpath = out_dir / fname

    try:
        loc = page.locator(selector)
        collected: list[str] = []

        if "text" in fields:
            try:
                txt = loc.inner_text(timeout=2000)
                collected.append(f"TEXT: {txt.strip()}")
            except (AttributeError, RuntimeError, TimeoutError) as e:  # narrow expected failures
                logger.warning(f"element_capture.text_fail selector={selector} err={type(e).__name__}:{e}")
            except Exception as e:  # unexpected
                logger.warning(f"element_capture.text_unexpected selector={selector} err={type(e).__name__}:{e}")

        if "value" in fields:
            try:
                val = loc.input_value(timeout=2000)
                collected.append(f"VALUE: {val}")
            except (AttributeError, RuntimeError, TimeoutError) as e:
                logger.warning(f"element_capture.value_fail selector={selector} err={type(e).__name__}:{e}")
            except Exception as e:
                logger.warning(f"element_capture.value_unexpected selector={selector} err={type(e).__name__}:{e}")

        if "html" in fields:
            try:
                html = loc.inner_html(timeout=2000)
                collected.append("HTML:\n" + html)
            except (AttributeError, RuntimeError, TimeoutError) as e:
                logger.warning(f"element_capture.html_fail selector={selector} err={type(e).__name__}:{e}")
            except Exception as e:
                logger.warning(f"element_capture.html_unexpected selector={selector} err={type(e).__name__}:{e}")

        if not collected:
            logger.warning(f"element_capture.empty selector={selector} label={safe_label}")
            return None

        content = "\n\n".join(collected)
        fpath.write_text(content, encoding="utf-8")
        first_text = next((line[5:].strip() for line in collected if line.startswith("TEXT:")), None)
        mgr.save_element_capture(selector=selector, text=first_text, value=None)
        logger.info(f"element_capture.success file={fpath} selector={selector} label={safe_label}")
        return fpath
    except (OSError, IOError) as e:  # file system related
        logger.warning(f"element_capture.fs_fail selector={selector} err={type(e).__name__}:{e}")
        return None
    except Exception as e:
        logger.warning(f"element_capture.fail selector={selector} err={type(e).__name__}:{e}")
        return None

__all__ = ["capture_element_value"]
