"""FastAPI routes for Playwright trace viewer sessions."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from src.ui.services import get_playwright_trace_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/trace-viewer", tags=["trace-viewer"])


@router.get("/playwright/sessions/{session_id}/trace.zip")
def serve_playwright_trace(session_id: str) -> FileResponse:
    session = get_playwright_trace_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Trace session not found or expired")

    trace_path: Path = session.trace_path
    if not trace_path.exists():
        raise HTTPException(status_code=404, detail="Trace artifact missing")

    return FileResponse(
        trace_path,
        media_type="application/zip",
        filename="trace.zip",
    )
