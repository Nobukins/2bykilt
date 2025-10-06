"""Realtime (WebSocket) endpoints for UI updates."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.ui.services import get_feature_flag_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["realtime"])

_RUN_HISTORY_FILE = Path("logs/run_history.json")
_POLL_INTERVAL = float(os.getenv("RUN_HISTORY_WS_POLL_INTERVAL", "1.0"))


@router.websocket("/run-history")
async def run_history_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    flag_service = get_feature_flag_service()
    last_payload = None

    try:
        while True:
            state = flag_service.get_current_state(force_refresh=True)
            if not state.ui_realtime_updates:
                await asyncio.sleep(_POLL_INTERVAL)
                continue

            payload = _build_run_history_payload()
            if payload and payload != last_payload:
                await websocket.send_text(payload)
                last_payload = payload

            await asyncio.sleep(_POLL_INTERVAL)
    except WebSocketDisconnect:  # pragma: no cover - expected on client close
        logger.debug("Run history websocket disconnected")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Run history websocket encountered error",
            extra={"event": "ui.realtime.error", "error": repr(exc)},
        )


def _build_run_history_payload() -> str:
    data = _load_history_entries()
    stats = _compute_stats(data)
    payload = {
        "type": "run_history",
        "entries": data,
        "stats": stats,
    }
    return json.dumps(payload, ensure_ascii=False)


def _load_history_entries() -> list[Dict[str, Any]]:
    if not _RUN_HISTORY_FILE.exists():
        return []

    try:
        content = _RUN_HISTORY_FILE.read_text(encoding="utf-8")
        return json.loads(content)
    except json.JSONDecodeError:
        logger.warning("Invalid run history JSON payload", exc_info=False)
        return []
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning(
            "Failed to read run history file",
            extra={"event": "ui.realtime.load_error", "error": repr(exc)},
        )
        return []


def _compute_stats(entries: list[Dict[str, Any]]) -> Dict[str, Any]:
    if not entries:
        return {
            "total": 0,
            "success": 0,
            "success_rate": 0.0,
            "avg_duration": 0.0,
        }

    total = len(entries)
    success = len([e for e in entries if e.get("status") == "success"])
    durations = [float(e.get("duration_sec", 0.0)) for e in entries]
    avg_duration = sum(durations) / len(durations) if durations else 0.0

    return {
        "total": total,
        "success": success,
        "success_rate": (success / total * 100.0) if total else 0.0,
        "avg_duration": avg_duration,
    }
