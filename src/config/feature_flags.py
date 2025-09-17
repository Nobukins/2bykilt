"""Feature Flag Framework (Issue #64)

Provides unified feature flag resolution with precedence:
    runtime_override > environment variable > file default

File defaults are loaded from `config/feature_flags.yaml` by default or a path
specified via env var `BYKILT_FLAGS_FILE`.

Environment variable resolution:
  For a flag name like "engine.cdp_use" we derive candidate env var names:
    1. BYKILT_FLAG_ENGINE_CDP_USE
    2. ENGINE_CDP_USE
  First present one wins. Values are parsed to the declared type.

Supported types: bool, int, str.

Runtime overrides:
  FeatureFlags.set_override(name, value, ttl_seconds=None)
  Expiring overrides are removed lazily upon access.

Artifacts:
  A single artifact of resolved (current) flag values is written lazily on
  first access to: artifacts/runs/<timestamp>-flags/feature_flags_resolved.json
  (A real run/job id will replace this once Issue #32 lands.)

Undefined flags:
  Logged at WARNING (event=flag.undefined) and returns False for bool / None
  for other types unless a default is explicitly provided at call site.

Public API (stable for initial version):
  FeatureFlags.get(name: str, expected_type: type | None = None, default: Any | None = None) -> Any
  FeatureFlags.is_enabled(name: str) -> bool
  FeatureFlags.set_override(name: str, value: Any, ttl_seconds: int | None = None) -> None
  FeatureFlags.clear_override(name: str) -> None
  FeatureFlags.clear_all_overrides() -> None
  FeatureFlags.dump_snapshot() -> Path
  FeatureFlags.set_lazy_artifact_enabled(enabled: bool) -> None
  FeatureFlags.is_lazy_artifact_enabled() -> bool
  FeatureFlags.get_override_source(name: str) -> str | None
  FeatureFlags.reload() -> None  (reload defaults file)

Non-goals (future issues):
  * Multi-variant / percentage rollout
  * Persistent override storage
  * Targeting rules
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

logger = logging.getLogger(__name__)


_DEFAULT_FLAGS_FILE = "config/feature_flags.yaml"
_ARTIFACT_ROOT = Path("artifacts") / "runs"  # retained for backward compatibility

try:
    from src.runtime.run_context import RunContext  # local import to avoid cycle
except Exception:  # noqa: BLE001
    RunContext = None  # type: ignore


@dataclass
class _FlagDef:
    name: str
    type: str  # "bool" | "int" | "str"
    default: Any
    description: str | None = None


class FeatureFlags:
    """Static facade for feature flag resolution.

    All state is stored on the class to keep a minimal integration surface.
    Thread-safety: runtime override operations are guarded by a lock.
    """

    _lock = threading.RLock()
    _defaults: Dict[str, _FlagDef] = {}
    _overrides: Dict[str, Tuple[Any, Optional[datetime]]] = {}
    _artifact_written = False
    _resolved_cache: Dict[str, Any] = {}
    _flags_file: Path | None = None
    _flags_mtime: float | None = None  # track mtime to auto-reload if file updated during runtime

    # Lazy artifact creation control
    _lazy_artifact_enabled = True  # default: enabled for backward compatibility

    # ----------------------- Public API ---------------------------------- #
    @classmethod
    def reload(cls) -> None:
        """Reload defaults from file, clearing caches (runtime overrides kept)."""
        with cls._lock:
            cls._defaults = {}
            cls._resolved_cache = {}
            cls._artifact_written = False
            cls._flags_file = cls._determine_flags_file()
            cls._flags_mtime = None
            if cls._flags_file and cls._flags_file.exists():
                try:
                    try:
                        cls._flags_mtime = cls._flags_file.stat().st_mtime
                    except Exception:  # noqa: BLE001
                        cls._flags_mtime = None
                    data = yaml.safe_load(cls._flags_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and isinstance(data.get("flags"), dict):
                        for name, meta in data["flags"].items():  # type: ignore[index]
                            if not isinstance(meta, dict):  # skip invalid entries
                                continue
                            flag_type = str(meta.get("type", "bool")).lower()
                            if flag_type not in {"bool", "int", "str"}:
                                flag_type = "str"  # fallback
                            cls._defaults[name] = _FlagDef(
                                name=name,
                                type=flag_type,
                                default=meta.get("default"),
                                description=meta.get("description"),
                            )
                except Exception as e:  # noqa: BLE001
                    logger.warning(
                        "Failed to load feature flags file", extra={"event": "flag.file.load.error", "error": repr(e)}
                    )
            else:
                logger.info(
                    "Feature flags defaults file missing (proceeding with empty defaults)",
                    extra={"event": "flag.file.missing", "path": str(cls._flags_file) if cls._flags_file else None},
                )

            # Reset lazy artifact setting based on environment variable
            env_lazy = os.getenv("BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED", "true").lower()
            cls._lazy_artifact_enabled = env_lazy in ("true", "1", "yes", "on")

    @classmethod
    def get(cls, name: str, expected_type: type | None = None, default: Any | None = None) -> Any:
        """Return resolved flag value (may be cached).

        Resolution precedence: runtime_override > environment > file default.
        If `expected_type` provided, attempt safe coercion.
        Undefined flags: log warning (once) and use provided default, else derive fallback:
          * bool -> False, int -> 0, str -> "" (if expected_type specified)
        """
        cls._ensure_loaded()
        with cls._lock:
            cls._prune_expired()
            if name in cls._resolved_cache:
                return cls._coerce(cls._resolved_cache[name], expected_type, name)

            # 1. Runtime override
            if name in cls._overrides:
                value, _exp = cls._overrides[name]
                resolved = value
            else:
                # 2. Environment variable
                env_value = cls._get_env_override(name)
                if env_value is not None:
                    resolved = env_value
                else:
                    # 3. File default
                    if name in cls._defaults:
                        resolved = cls._defaults[name].default
                    else:
                        # Undefined
                        if default is not None:
                            resolved = default
                        else:
                            if expected_type is bool:
                                resolved = False
                            elif expected_type is int:
                                resolved = 0
                            elif expected_type is str:
                                resolved = ""
                            else:
                                resolved = False  # generic fallback

                        # Check if lazy artifact creation is enabled for undefined flags
                        if cls._lazy_artifact_enabled and not cls._artifact_written:
                            logger.info(
                                "Undefined feature flag accessed, creating lazy artifact",
                                extra={"event": "flag.undefined.lazy_artifact", "flag": name},
                            )
                            # Force artifact creation for undefined flag access
                            cls._maybe_write_artifact(force_refresh=True)
                        else:
                            logger.warning(
                                "Undefined feature flag accessed",
                                extra={"event": "flag.undefined", "flag": name},
                            )

            coerced = cls._coerce(resolved, expected_type, name)
            cls._resolved_cache[name] = coerced

            # Only write artifact for defined flags or when lazy creation is enabled
            if name in cls._defaults or cls._lazy_artifact_enabled:
                cls._maybe_write_artifact()

            return coerced

    @classmethod
    def is_enabled(cls, name: str) -> bool:
        """Boolean helper (expected_type=bool)."""
        return bool(cls.get(name, expected_type=bool))

    @classmethod
    def set_override(cls, name: str, value: Any, ttl_seconds: int | None = None) -> None:
        """Set a runtime override (highest precedence).

        ttl_seconds: expire after given seconds (lazy removal on next access)."""
        cls._ensure_loaded()
        with cls._lock:
            expiry = None
            if ttl_seconds is not None and ttl_seconds > 0:
                expiry = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)
            cls._overrides[name] = (value, expiry)
            # override should refresh cache
            cls._resolved_cache.pop(name, None)
            logger.info(
                "Runtime feature flag override set",
                extra={"event": "flag.override.set", "flag": name, "ttl": ttl_seconds},
            )
            cls._maybe_write_artifact(force_refresh=True)

    @classmethod
    def clear_override(cls, name: str) -> None:
        with cls._lock:
            if cls._overrides.pop(name, None) is not None:
                cls._resolved_cache.pop(name, None)
                logger.info(
                    "Runtime feature flag override cleared",
                    extra={"event": "flag.override.cleared", "flag": name},
                )
                cls._maybe_write_artifact(force_refresh=True)

    @classmethod
    def clear_all_overrides(cls) -> None:
        with cls._lock:
            if cls._overrides:
                cls._overrides.clear()
                cls._resolved_cache.clear()
                logger.info("All runtime feature flag overrides cleared", extra={"event": "flag.override.cleared_all"})
                cls._maybe_write_artifact(force_refresh=True)

    @classmethod
    def dump_snapshot(cls) -> Path:
        """Write a snapshot artifact of current resolved flags and return path.

        Useful in tests and tooling that need to ensure a flags artifact exists
        without relying on lazy writes. Returns the directory path containing
        the JSON file.
        """
        cls._ensure_loaded()
        # Force refresh to ensure latest cache/overrides are reflected
        out_dir = cls._maybe_write_artifact(force_refresh=True)
        if out_dir is None:
            # Fallback if writing failed: ensure artifact directory and file exist
            out_dir = None
            try:
                out_dir = cls._create_fallback_artifact_dir("fallback-flags")

                # Write current resolved flags to JSON
                payload = {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "flags_file": str(cls._flags_file) if cls._flags_file else None,
                    "run_id_base": None,
                    "resolved": cls._resolved_cache.copy(),
                    "overrides_active": list(cls._overrides.keys()),
                }
                (out_dir / "feature_flags_resolved.json").write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
                )
                logger.info(
                    "Fallback feature flags artifact written",
                    extra={"event": "flag.artifact.fallback.written", "path": str(out_dir)},
                )
            except Exception as e:  # noqa: BLE001
                logger.error(
                    "Failed to write fallback feature flags snapshot artifact",
                    extra={"event": "flag.artifact.fallback.error", "error": repr(e)},
                )
                # Last resort: raise an exception to indicate failure
                # This ensures callers are aware the artifact was not created
                fallback_dir = str(out_dir) if out_dir is not None else "fallback directory"
                raise RuntimeError(
                    f"Failed to write feature flags snapshot artifact to {fallback_dir}. Error: {e}"
                )
        return out_dir

    @classmethod
    def set_lazy_artifact_enabled(cls, enabled: bool) -> None:
        """Enable or disable lazy artifact creation for undefined flag access.

        When enabled (default), accessing an undefined flag will automatically
        create a flags artifact if one doesn't already exist. When disabled,
        undefined flag access will only log a warning without creating artifacts.

        Args:
            enabled: Whether to enable lazy artifact creation
        """
        with cls._lock:
            cls._lazy_artifact_enabled = enabled
            logger.info(
                "Lazy artifact creation setting changed",
                extra={"event": "flag.lazy_artifact.setting", "enabled": enabled},
            )

    @classmethod
    def is_lazy_artifact_enabled(cls) -> bool:
        """Return whether lazy artifact creation is enabled."""
        return cls._lazy_artifact_enabled

    # -------------------- Internal helpers -------------------------------- #
    @classmethod
    def _ensure_loaded(cls) -> None:
        # Initial load
        if (not cls._defaults and cls._flags_file is None) or cls._flags_file is None:
            cls.reload()
            return
        # Hot-reload if file mtime changed (Issue #91: tests modify defaults between runs)
        try:
            if cls._flags_file.exists():
                current_mtime = cls._flags_file.stat().st_mtime
                if cls._flags_mtime is not None and current_mtime > cls._flags_mtime:
                    logger.info(
                        "Feature flags file modified on disk; reloading",
                        extra={"event": "flag.file.modified.reload", "path": str(cls._flags_file)},
                    )
                    cls.reload()
            else:
                # If file disappeared, keep existing defaults (avoid churn)
                pass
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed during feature flag mtime check",
                extra={"event": "flag.file.mtime.error", "error": repr(e)},
            )

    @staticmethod
    def _determine_flags_file() -> Path:
        env_path = os.getenv("BYKILT_FLAGS_FILE")
        if env_path:
            return Path(env_path).resolve()
        return Path(_DEFAULT_FLAGS_FILE).resolve()

    @classmethod
    def _get_env_override(cls, name: str) -> Any | None:
        candidates = []
        normalized = name.upper().replace(".", "_")
        candidates.append(f"BYKILT_FLAG_{normalized}")
        candidates.append(normalized)
        for var in candidates:
            if var in os.environ:
                raw = os.environ[var]
                # Attempt primitive parsing
                if raw.lower() in ("true", "false"):
                    return raw.lower() == "true"
                # int parse
                try:
                    if raw.isdigit() or (raw.startswith("-") and raw[1:].isdigit()):
                        return int(raw)
                except Exception:  # noqa: BLE001
                    pass
                return raw
        return None

    @classmethod
    def _coerce(cls, value: Any, expected_type: type | None, name: str) -> Any:
        if expected_type is None:
            return value
        try:
            if expected_type is bool:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    return value.lower() in ("1", "true", "yes", "on")
                return bool(value)
            if expected_type is int:
                if isinstance(value, int):
                    return value
                return int(value)  # may raise
            if expected_type is str:
                if isinstance(value, str):
                    return value
                return str(value)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed to coerce feature flag value",
                extra={"event": "flag.coerce.error", "flag": name, "error": repr(e), "value": value},
            )
        return value

    @classmethod
    def _prune_expired(cls) -> None:
        """Remove expired runtime overrides.

        This method may be called from multiple places to ensure expired overrides are cleaned up.
        """
        now = datetime.now(timezone.utc)
        expired = [k for k, (_v, exp) in cls._overrides.items() if exp and exp <= now]
        for k in expired:
            cls._overrides.pop(k, None)
            cls._resolved_cache.pop(k, None)
            logger.info("Expired feature flag override removed", extra={"event": "flag.override.expired", "flag": k})

    @classmethod
    def _create_fallback_artifact_dir(cls, suffix: str) -> Path:
        """Create a fallback artifact directory with timestamp-based naming.

        Args:
            suffix: Suffix for the directory name (e.g., 'legacy-flags', 'fallback-flags')

        Returns:
            Path to the created directory
        """
        _ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + f"-{suffix}"
        out_dir = _ARTIFACT_ROOT / run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    @classmethod
    def _maybe_write_artifact(cls, force_refresh: bool = False) -> Path | None:
        if not force_refresh and cls._artifact_written:
            # If working directory changed after first write (tests use tmp_path + chdir),
            # the previously written artifact may no longer exist relative to the new CWD.
            # Allow a second write in that case so tests see a -flags directory (Issue #91 side-effect).
            try:  # defensive; never block flag resolution
                expected_dir = RunContext.get().artifact_dir("flags", ensure=False)
                if not expected_dir.exists():
                    cls._artifact_written = False  # reset and proceed to write below
                else:
                    return expected_dir
            except Exception as e:  # noqa: BLE001
                # Log once for observability while still suppressing to avoid cascading failures
                logger.warning(
                    "Error while probing existing flags artifact directory",
                    extra={"event": "flag.artifact.dir.error", "error": repr(e)},
                )
                return None
        try:
            # Gather current resolved values (resolve defaults without side effects)
            resolved: Dict[str, Any] = {}
            for name in sorted(cls._defaults.keys()):
                # Use cache or simple resolution without logging undefined
                if name in cls._resolved_cache:
                    resolved[name] = cls._resolved_cache[name]
                else:
                    # quick resolution (simulate precedence except undefined won't occur here)
                    if name in cls._overrides:
                        resolved[name] = cls._overrides[name][0]
                    else:
                        env_val = cls._get_env_override(name)
                        if env_val is not None:
                            resolved[name] = env_val
                        else:
                            resolved[name] = cls._defaults[name].default
            # Also add any override-only flags
            for name in cls._overrides.keys():
                if name not in resolved:
                    resolved[name] = cls._overrides[name][0]
            # Unified RunContext directory (Issue #32)
            try:
                out_dir = RunContext.get().artifact_dir("flags")
                run_id_base = RunContext.get().run_id_base
            except Exception:  # noqa: BLE001
                # Fallback to legacy behavior
                out_dir = cls._create_fallback_artifact_dir("legacy-flags")
                run_id_base = None

            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "flags_file": str(cls._flags_file) if cls._flags_file else None,
                "run_id_base": run_id_base,
                "resolved": resolved,
                "overrides_active": list(cls._overrides.keys()),
            }
            (out_dir / "feature_flags_resolved.json").write_text(
                json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            cls._artifact_written = True
            logger.info(
                "Feature flags artifact written",
                extra={"event": "flag.artifact.written", "path": str(out_dir)},
            )
            return out_dir
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed to write feature flags artifact",
                extra={"event": "flag.artifact.error", "error": repr(e)},
            )
            return None


# Initialize on import (safe, file missing handled gracefully)
FeatureFlags.reload()

__all__ = [
    "FeatureFlags",
]

# ---------------------------------------------------------------------------
# Backward compatibility helpers (legacy env variable migration)
# ---------------------------------------------------------------------------
def is_llm_enabled() -> bool:
        """Temporary helper bridging legacy ENABLE_LLM env and new feature flag.

        Resolution order:
            1. Explicit feature flag 'enable_llm' (runtime/env/file) via FeatureFlags
            2. Legacy environment variable ENABLE_LLM (already handled inside flag via env)

        This wrapper exists so call sites can migrate from direct os.getenv checks
        to a stable function. Eventually legacy ENABLE_LLM usages will be removed
        (Issue: follow-up to #64) and callers should import FeatureFlags directly.
        """
        try:
                return FeatureFlags.is_enabled("enable_llm")
        except Exception:
                # Safe fallback mimicking original behavior
                return os.getenv("ENABLE_LLM", "false").lower() == "true"

__all__.append("is_llm_enabled")

# ------------------------- Test Helpers (non-public) ------------------------------
def _reset_feature_flags_for_tests() -> None:  # pragma: no cover - test utility
    """Internal helper to clear caches & reload defaults (used by tests)."""
    try:
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()
    except Exception:  # noqa: BLE001
        pass

__all__.append("_reset_feature_flags_for_tests")
