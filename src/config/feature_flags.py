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
_ARTIFACT_ROOT = Path("artifacts") / "runs"


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

    # ----------------------- Public API ---------------------------------- #
    @classmethod
    def reload(cls) -> None:
        """Reload defaults from file, clearing caches (runtime overrides kept)."""
        with cls._lock:
            cls._defaults = {}
            cls._resolved_cache = {}
            cls._artifact_written = False
            cls._flags_file = cls._determine_flags_file()
            if cls._flags_file and cls._flags_file.exists():
                try:
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
                        logger.warning(
                            "Undefined feature flag accessed",
                            extra={"event": "flag.undefined", "flag": name},
                        )

            coerced = cls._coerce(resolved, expected_type, name)
            cls._resolved_cache[name] = coerced
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

    # -------------------- Internal helpers -------------------------------- #
    @classmethod
    def _ensure_loaded(cls) -> None:
        if not cls._defaults and cls._flags_file is None:
            cls.reload()

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
        now = datetime.now(timezone.utc)
        expired = [k for k, (_v, exp) in cls._overrides.items() if exp and exp <= now]
        for k in expired:
            cls._overrides.pop(k, None)
            cls._resolved_cache.pop(k, None)
            logger.info("Expired feature flag override removed", extra={"event": "flag.override.expired", "flag": k})

    @classmethod
    def _maybe_write_artifact(cls, force_refresh: bool = False) -> None:
        if not force_refresh and cls._artifact_written:
            return
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
            # Compose artifact directory
            if not _ARTIFACT_ROOT.exists():
                _ARTIFACT_ROOT.mkdir(parents=True, exist_ok=True)
            run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-flags"
            out_dir = _ARTIFACT_ROOT / run_id
            out_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "flags_file": str(cls._flags_file) if cls._flags_file else None,
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
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "Failed to write feature flags artifact",
                extra={"event": "flag.artifact.error", "error": repr(e)},
            )


# Initialize on import (safe, file missing handled gracefully)
FeatureFlags.reload()

__all__ = [
    "FeatureFlags",
]
