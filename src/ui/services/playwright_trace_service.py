"""Utilities for embedding the Playwright trace viewer.

This module is responsible for copying the Playwright trace viewer static
assets into our `/assets` tree and managing short-lived trace viewer
sessions.  A session wraps a trace archive (`.zip`) so that the viewer can
fetch it through a well-defined FastAPI route.
"""
from __future__ import annotations

import shutil
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Optional

import logging

from src.utils.fs_paths import get_artifacts_base_dir

logger = logging.getLogger(__name__)

_TRACE_VIEWER_RELATIVE_DIR = Path("assets") / "playwright-trace-viewer"
_TRACE_SESSION_DIRNAME = "trace_viewer_sessions"


def _default_asset_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    asset_dir = repo_root / _TRACE_VIEWER_RELATIVE_DIR
    asset_dir.mkdir(parents=True, exist_ok=True)
    return asset_dir


def _default_asset_source() -> Path:
    try:
        import playwright  # type: ignore
    except ImportError as exc:  # pragma: no cover - depends on runtime env
        raise RuntimeError(
            "Playwright is required to embed the trace viewer. Install playwright to "
            "enable embedded trace playback."
        ) from exc

    viewer_dir = (
        Path(playwright.__file__).resolve().parent
        / "driver"
        / "package"
        / "lib"
        / "vite"
        / "traceViewer"
    )
    if not viewer_dir.exists():  # pragma: no cover - defensive
        raise RuntimeError(
            "Playwright trace viewer assets were not found."
        )
    return viewer_dir


@dataclass(slots=True)
class TraceViewerSession:
    session_id: str
    trace_path: Path
    created_at: float

    def viewer_url(self) -> str:
        cache_bust = int(self.created_at)
        trace_param = (
            f"/trace-viewer/playwright/sessions/{self.session_id}/trace.zip"
        )
        return (
            "/static/playwright-trace-viewer/index.html"
            f"?trace={trace_param}&_cb={cache_bust}"
        )


class PlaywrightTraceService:
    def __init__(
        self,
        asset_dir: Optional[Path] = None,
        session_root: Optional[Path] = None,
        asset_source_resolver: Callable[[], Path] | None = None,
        session_ttl_seconds: int = 1800,
    ) -> None:
        self._asset_dir = (asset_dir or _default_asset_dir()).resolve()
        self._session_root = (
            session_root
            or (get_artifacts_base_dir() / _TRACE_SESSION_DIRNAME)
        ).resolve()
        self._session_root.mkdir(parents=True, exist_ok=True)
        self._asset_source_resolver = asset_source_resolver or _default_asset_source
        self._session_ttl_seconds = session_ttl_seconds
        self._sessions: Dict[str, TraceViewerSession] = {}
        self._lock = threading.Lock()
        self._assets_ready = False

    @property
    def asset_dir(self) -> Path:
        return self._asset_dir

    @property
    def session_root(self) -> Path:
        return self._session_root

    def ensure_assets(self, force: bool = False) -> Path:
        with self._lock:
            if self._assets_ready and not force:
                return self._asset_dir
            source_dir = self._asset_source_resolver()
            if not source_dir.exists():
                raise RuntimeError(
                    f"Playwright trace viewer source directory not found: {source_dir}"
                )
            logger.debug(
                "Copying Playwright trace viewer assets",
                extra={
                    "event": "trace_viewer.assets.copy",
                    "source": str(source_dir),
                    "destination": str(self._asset_dir),
                },
            )
            shutil.copytree(source_dir, self._asset_dir, dirs_exist_ok=True)
            self._assets_ready = True
            return self._asset_dir

    def prepare_session(self, trace_zip: Path) -> TraceViewerSession:
        if not trace_zip.exists():
            raise FileNotFoundError(trace_zip)
        self.ensure_assets()
        session_id = uuid.uuid4().hex
        target = self._session_root / f"{session_id}.zip"
        shutil.copy2(trace_zip, target)
        session = TraceViewerSession(
            session_id=session_id,
            trace_path=target,
            created_at=time.time(),
        )
        with self._lock:
            self._sessions[session_id] = session
            self._prune_sessions_locked()
        logger.debug(
            "Prepared Playwright trace viewer session",
            extra={
                "event": "trace_viewer.session.created",
                "session_id": session_id,
                "trace_path": str(target),
            },
        )
        return session

    def get_session(self, session_id: str) -> Optional[TraceViewerSession]:
        with self._lock:
            session = self._sessions.get(session_id)
            if session and (time.time() - session.created_at) > self._session_ttl_seconds:
                del self._sessions[session_id]
                return None
            return session

    def _prune_sessions_locked(self) -> None:
        now = time.time()
        expired = [
            key
            for key, session in self._sessions.items()
            if now - session.created_at > self._session_ttl_seconds
        ]
        for key in expired:
            trace_path = self._sessions[key].trace_path
            try:
                trace_path.unlink(missing_ok=True)
            except Exception:  # pragma: no cover - best effort cleanup
                logger.debug(
                    "Failed to delete expired trace session file",
                    extra={
                        "event": "trace_viewer.session.cleanup.fail",
                        "session_id": key,
                        "trace_path": str(trace_path),
                    },
                )
            finally:
                self._sessions.pop(key, None)

    def prune_sessions(self) -> None:
        with self._lock:
            self._prune_sessions_locked()


_default_service = PlaywrightTraceService()


def ensure_playwright_trace_assets(force: bool = False) -> Path:
    return _default_service.ensure_assets(force=force)


def prepare_playwright_trace_session(trace_zip: Path) -> TraceViewerSession:
    return _default_service.prepare_session(trace_zip)


def get_playwright_trace_session(session_id: str) -> Optional[TraceViewerSession]:
    return _default_service.get_session(session_id)


def prune_playwright_trace_sessions() -> None:
    _default_service.prune_sessions()


__all__ = [
    "TraceViewerSession",
    "PlaywrightTraceService",
    "ensure_playwright_trace_assets",
    "prepare_playwright_trace_session",
    "get_playwright_trace_session",
    "prune_playwright_trace_sessions",
]
