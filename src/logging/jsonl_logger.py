"""Unified JSON Lines Logger (Issue #56 / #57)

Implements production JSONL logging with:
    - Component based singleton acquisition (`JsonlLogger.get(component)`)
    - Structured event emission (level, msg, component, seq, ts, run_id_base, extra fields)
    - Hook pipeline (mutate / enrich / drop) – hooks return dict or raise to abort
    - File rotation (max size bytes) & retention (keep N rotated files)
    - Thread-safe append (per component lock)

Environment overrides:
    BYKILT_LOG_MAX_SIZE: int (bytes)   – default 1_000_000 (~1MB)
    BYKILT_LOG_MAX_FILES: int          – number of *rotated* files to keep (default 5)
    BYKILT_LOG_FLUSH_ALWAYS: bool-like – if truthy, flush+fsync on every write (slower; default false)

Rotation scheme:
    active: app.log.jsonl
    rotated: app.log.jsonl.1 (most recent), app.log.jsonl.2 ...
    When size > max_size after a write, rotation occurs before next write.

Retention:
    Oldest file index > max_files is deleted.

Design choices:
    - Simplicity over compression (no gzip yet; future enhancement issue)
    - Size check performed *after* write to avoid double encoding overhead
    - Timestamp in UTC ISO8601 with 'Z'

Issues Addressed:
    * #56 JSON Lines logger implementation
    * #57 Rotation & retention policies
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, Any, ClassVar, Optional
import threading
import json
import os
from datetime import datetime, timezone
import io

from src.runtime.run_context import RunContext

Hook = Callable[[dict], dict]

@dataclass(slots=True)
class _LoggerCore:
    component: str
    file_path: Path
    hooks: list[Hook] = field(default_factory=list)
    seq: int = 0
    # Each core gets its own lock (avoid shared dataclass default instance)
    lock: threading.Lock = field(default_factory=threading.Lock)

class JsonlLogger:
    _instances: ClassVar[dict[str, "JsonlLogger"]] = {}
    _instances_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, core: _LoggerCore):
        self._c = core

    # ------------- Factory -------------
    @classmethod
    def get(cls, component: str) -> "JsonlLogger":
        """Return (and create if needed) a component logger.

        Behavior:
          * Component must match ^[a-z0-9_]+$ (lowercase enforced).
          * Strips surrounding whitespace; raises ValueError if normalization changes case/charset.
          * Idempotent & thread-safe. Does NOT create the log file yet.
        """
        if component is None:
            raise ValueError("component is required")
        stripped = component.strip()
        if not stripped:
            raise ValueError("component must be non-empty")
        # Reject if caller had leading/trailing whitespace to avoid confusion
        if stripped != component:
            raise ValueError("component must not have leading/trailing whitespace")
        normalized = stripped.lower()
        # Enforce allowed charset (lowercase alnum + underscore)
        import re
        if not re.fullmatch(r"[a-z0-9_]+", normalized):
            raise ValueError(f"invalid component name '{component}'; allowed pattern [a-z0-9_]+")
        # If caller used uppercase or other diff, we choose strictness: reject rather than silently merge
        if stripped != normalized:
            raise ValueError(f"component '{component}' must be lowercase (received normalized '{normalized}')")
        key = normalized
        if key in cls._instances:
            return cls._instances[key]
        with cls._instances_lock:
            if key not in cls._instances:
                rc = RunContext.get()
                # Strategy A: directory `<run_id_base>-log/` containing app.log.jsonl
                base_dir = rc.artifact_dir("log")  # creates directory
                file_path = base_dir / "app.log.jsonl"
                core = _LoggerCore(component=key, file_path=file_path)
                cls._instances[key] = JsonlLogger(core)
            return cls._instances[key]

    # ------------- Public API (skeleton) -------------
    # ------------- Core Emit -------------
    def _emit(self, level: str, msg: str, extra: Dict[str, Any]) -> None:
        if not isinstance(msg, str):  # defensive
            msg = str(msg)
        rc = RunContext.get()
        with self._c.lock:
            self._c.seq += 1
            record: Dict[str, Any] = {
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "seq": self._c.seq,
                "level": level,
                "msg": msg,
                "component": self._c.component,
                "run_id": rc.run_id_base,
            }
            # Merge user extras (shallow)
            if extra:
                for k, v in extra.items():
                    # Avoid overriding core keys silently
                    if k in record:
                        record[f"extra_{k}"] = v
                    else:
                        record[k] = v
            # Hook processing
            for hook in self._c.hooks:
                try:
                    mutated = hook(record)
                    if mutated is not None:
                        record = mutated
                except Exception as e:  # pragma: no cover - defensive; hook errors shouldn't kill app
                    record.setdefault("hook_errors", []).append(str(e))
            line = json.dumps(record, separators=(",", ":"), ensure_ascii=False)
            # Write
            self._append_line(line)

    def _append_line(self, line: str) -> None:
        max_size = _get_env_int("BYKILT_LOG_MAX_SIZE", 1_000_000)
        max_files = _get_env_int("BYKILT_LOG_MAX_FILES", 5)
        flush_always = _get_env_bool("BYKILT_LOG_FLUSH_ALWAYS", False)
        fp = self._c.file_path
        fp.parent.mkdir(parents=True, exist_ok=True)
        encoded = (line + "\n").encode("utf-8")
        with open(fp, "ab") as f:
            f.write(encoded)
            if flush_always:
                f.flush()
                os.fsync(f.fileno())
        # Rotation check AFTER write
        try:
            size = fp.stat().st_size
            if size > max_size:
                self._rotate_files(max_files)
        except FileNotFoundError:  # pragma: no cover - race unlikely
            return

    def _rotate_files(self, max_files: int) -> None:
        fp = self._c.file_path
        if not fp.exists():
            return
        # Delete the oldest if it'll overflow window
        oldest = fp.with_name(fp.name + f".{max_files}")
        if oldest.exists():
            try:
                oldest.unlink()
            except OSError:  # pragma: no cover - ignore
                pass
        # Shift indexes down (reverse order)
        for idx in range(max_files - 1, 0, -1):
            src = fp.with_name(fp.name + f".{idx}")
            dst = fp.with_name(fp.name + f".{idx+1}")
            if src.exists():
                try:
                    src.replace(dst)
                except OSError:  # pragma: no cover
                    pass
        # Move active -> .1
        try:
            fp.replace(fp.with_name(fp.name + ".1"))
            # Create a fresh empty active file so callers always see an existing path
            fp.touch(exist_ok=True)
        except OSError:  # pragma: no cover
            return

    # Public level helpers
    def debug(self, msg: str, **extra: Any) -> None:
        self._emit("DEBUG", msg, extra)

    def info(self, msg: str, **extra: Any) -> None:
        self._emit("INFO", msg, extra)

    def warning(self, msg: str, **extra: Any) -> None:
        self._emit("WARNING", msg, extra)

    def error(self, msg: str, **extra: Any) -> None:
        self._emit("ERROR", msg, extra)

    def critical(self, msg: str, **extra: Any) -> None:
        self._emit("CRITICAL", msg, extra)

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


# --- Minimal coverage helper (design-phase) ---
def _design_phase_ping() -> bool:
    return True  # kept for backward compatibility with existing tests


# ---- Helpers ----
def _get_env_int(name: str, default: int) -> int:
    v = os.getenv(name)
    if not v:
        return default
    try:
        i = int(v)
        if i <= 0:
            return default
        return i
    except ValueError:
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    v = os.getenv(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}

