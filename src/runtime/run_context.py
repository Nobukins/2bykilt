"""Run / Job ID Context (Issue #32)

Provides a singleton RunContext that generates and exposes a stable `run_id_base`
for the lifetime of the process. This ID is used to unify artifact directory
prefixes across subsystems (config loader, feature flags, future logging, etc.).

Directory naming convention (transitional, backward compatible):
    artifacts/runs/<run_id_base>-<component>

Where `<component>` is a short token such as `cfg`, `flags`, `log`.

Backward compatibility considerations:
 - Existing tests expect directories ending in `-cfg` and `-flags` directly under
   `artifacts/runs/`. This convention is preserved.
 - Future consolidation (Issue #31) may introduce nested component folders;
   design allows extension via `component_dir_strategy` if needed.

Environment overrides:
  BYKILT_RUN_ID    : Exact run id base (must be filesystem safe). If provided we
                     trust the caller (no regeneration). Useful for integration
                     tests or orchestrators.

Format (default generation):
  <UTC YYYYMMDDHHMMSS>-<shortrandom>
  Example: 20250830T104512-7f3c2a  (stored as 20250830104512-7f3c2a internally
  without the 'T' to keep lexicographic ordering by timestamp)

Public API:
  RunContext.get() -> RunContext               (singleton accessor)
  rc.run_id_base -> str                        (stable for process)
  rc.artifact_dir(component: str) -> Path      (ensures directory exists)

Thread-safety: Creation guarded by a lock; read operations are lock-free.
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

    _instance: ClassVar[RunContext | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    # ---------------- Singleton Accessor -----------------
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

    # ---------------- Artifact Helpers -------------------
    def artifact_dir(self, component: str, ensure: bool = True) -> Path:
        """Return the artifact directory for a component.

        Current strategy keeps backward compatible `<run_id_base>-<component>` top-level
        directories (no nesting). e.g. `20250830104512-7f3c2a-cfg`.
        """
        safe_component = component.strip().replace(os.sep, "_")
        path = _ARTIFACT_ROOT / f"{self.run_id_base}-{safe_component}"
        if ensure:
            path.mkdir(parents=True, exist_ok=True)
        return path

    # Alias for future extension if nested strategy adopted
    get_component_dir = artifact_dir


__all__ = ["RunContext"]
