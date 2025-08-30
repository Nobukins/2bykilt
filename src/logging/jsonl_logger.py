"""JSON Lines Logger Skeleton (Issue #31)

Design-only skeleton for unified JSONL logging system.
Actual write implementation deferred to Issue #56.

Usage (future):
    from src.logging.jsonl_logger import JsonlLogger
    log = JsonlLogger.get(component="browser")
    log.info("Browser launched", event="browser.launch", kwargs={"headless": True})

Current behavior:
    - Provides interface methods raising NotImplementedError for now.
    - Ensures directory planning logic via RunContext (without creating files yet).

Acceptance Criteria (#31):
    - Adding this module MUST NOT alter existing logging behavior.
    - Methods are safe to import and call (raise explicit NotImplementedError when used).
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, Any, ClassVar, Optional
import threading

from src.runtime.run_context import RunContext

Hook = Callable[[dict], dict]

@dataclass(slots=True)
class _LoggerCore:
    component: str
    file_path: Path
    hooks: list[Hook]
    seq: int = 0
    lock: threading.Lock = threading.Lock()

class JsonlLogger:
    _instances: ClassVar[dict[str, "JsonlLogger"]] = {}
    _instances_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, core: _LoggerCore):
        self._c = core

    # ------------- Factory -------------
    @classmethod
    def get(cls, component: str) -> "JsonlLogger":
        """Return (and create if needed) a component logger.

        Idempotent & thread-safe. Does NOT create the log file yet.
        """
        key = component.strip().lower()
        if key in cls._instances:
            return cls._instances[key]
        with cls._instances_lock:
            if key not in cls._instances:
                rc = RunContext.get()
                # Strategy A: directory `<run_id_base>-log/` containing app.log.jsonl
                base_dir = rc.artifact_dir("log")  # creates directory
                file_path = base_dir / "app.log.jsonl"
                core = _LoggerCore(component=key, file_path=file_path, hooks=[])
                cls._instances[key] = JsonlLogger(core)
            return cls._instances[key]

    # ------------- Public API (skeleton) -------------
    def debug(self, msg: str, **extra: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError("Issue #56 will implement debug logging")

    def info(self, msg: str, **extra: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError("Issue #56 will implement info logging")

    def warning(self, msg: str, **extra: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError("Issue #56 will implement warning logging")

    def error(self, msg: str, **extra: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError("Issue #56 will implement error logging")

    def critical(self, msg: str, **extra: Any) -> None:  # pragma: no cover - placeholder
        raise NotImplementedError("Issue #56 will implement critical logging")

    # ------------- Hook Registration (future) -------------
    def register_hook(self, hook: Hook) -> None:
        """Register a pipeline hook (order preserved)."""
        self._c.hooks.append(hook)

    # ------------- Introspection -------------
    @property
    def file_path(self) -> Path:
        return self._c.file_path

    @property
    def component(self) -> str:
        return self._c.component

__all__ = ["JsonlLogger"]
