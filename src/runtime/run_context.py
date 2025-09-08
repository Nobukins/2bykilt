"""Run / Job ID Context (Issue #32)

Singleton providing a stable ``run_id_base`` throughout the process lifetime.
Used to unify artifact directory prefixes across subsystems.

Public API:
  RunContext.get()   -> RunContext (singleton accessor)
  RunContext.reset() -> None       (testing/support helper)
  rc.run_id_base     -> str
  rc.artifact_dir(component: str) -> Path
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import os
import secrets
import threading
from pathlib import Path
from typing import ClassVar


_ARTIFACT_ROOT = Path("artifacts") / "runs"


def _generate_run_id_base() -> str:
    now = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = secrets.token_hex(3)  # 6 hex chars
    return f"{now}-{rand}"  # lexicographically sortable


@dataclass(frozen=True, slots=True)
class RunContext:
  run_id_base: str

  _instance: ClassVar["RunContext" | None] = None
  _lock: ClassVar[threading.Lock] = threading.Lock()

  # -------------- Singleton Accessors --------------
  @classmethod
  def get(cls) -> "RunContext":
    if cls._instance is not None:
      return cls._instance
    with cls._lock:
      if cls._instance is None:
        overridden = os.getenv("BYKILT_RUN_ID")
        base = overridden if overridden else _generate_run_id_base()
        cls._instance = RunContext(run_id_base=base)
      return cls._instance

  @classmethod
  def reset(cls) -> None:  # pragma: no cover - trivial helper
    with cls._lock:
      cls._instance = None

  # -------------- Artifact Helpers --------------
  def artifact_dir(self, component: str, ensure: bool = True) -> Path:
    """Return artifact directory for a component.

    ensure=False returns the expected path without creating it (used by tests to
    detect whether a previous working directory write occurred)."""
    safe_component = component.strip().replace(os.sep, "_")
    path = _ARTIFACT_ROOT / f"{self.run_id_base}-{safe_component}"
    if ensure:
      path.mkdir(parents=True, exist_ok=True)
    return path

  get_component_dir = artifact_dir


__all__ = ["RunContext"]
