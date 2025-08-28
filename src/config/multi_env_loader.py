"""
Multi-environment configuration loader (hierarchical) for 2bykilt (Issue #65)

Features:
- Directory based layering:
    config/base/*.yml|*.yaml  (base layer, merged in name order)
    config/<env>/*.yml|*.yaml (env overrides; env in {dev, staging, prod})
- Environment selection via BYKILT_ENV (default: dev); aliases:
    development -> dev, production -> prod
- Merge strategy:
    dict  : deep recursive
    list  : full replace by env layer
    scalar: override
- Type conflict warnings (recorded, not fatal)
- Secret masking (artifact only; returned config is UNMASKED for backward compatibility):
    key name (lower) contains any of: api_key, token, secret, password, key
    -> value masked as "***", SHA256(value) first 8 hex stored under masked_hashes
- Effective config artifact:
    artifacts/runs/<YYYYMMDDHHMMSS-cfg>/effective_config.json
- Diff helper: diff_envs(a,b) → added / removed / changed
- Logging:
    info  event=config.env.loaded
    warn  event=config.env.load.warning
- Returned value: raw (unmasked) merged config (per Q1 policy)

Out of scope for Issue #65 (handled by future issues):
- Schema validation (#63)
- Feature flags resolution (#64)
- Env var validation (#48)
"""

from __future__ import annotations
import os
import json
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

logger = logging.getLogger(__name__)

# ---- Constants / Config ----
_ENV_ALIASES = {
    "development": "dev",
    "production": "prod",
}
_VALID_ENVS = {"dev", "staging", "prod"}
_SECRET_KEY_SUBSTRINGS = ["api_key", "token", "secret", "password", "key"]


class MultiEnvConfigError(Exception):
    """Fatal configuration error (used sparingly)."""
    pass


class MultiEnvConfigLoader:
    """
    Loader encapsulating hierarchical environment configuration logic.
    Returns UNMASKED config (artifact is masked).
    """

    def __init__(self, root: str | Path = "config") -> None:
        self.root = Path(root).resolve()
        self.warnings: List[Dict[str, Any]] = []
        self.files_loaded: List[Path] = []
        self.logical_env: str = "dev"

    # ---------- Public API ----------

    def load(self, requested_env: str | None = None) -> Dict[str, Any]:
        """
        Load & merge configuration for environment.
        Args:
            requested_env: Optional environment name/alias.
        Returns:
            UNMASKED merged configuration dict.
        Raises:
            MultiEnvConfigError only for truly fatal base layer absence.
        """
        self.warnings.clear()
        self.files_loaded.clear()

        env_raw = (requested_env or os.getenv("BYKILT_ENV") or "dev").strip().lower()
        self.logical_env = self._normalize_env(env_raw)

        base_dir = self.root / "base"
        env_dir = self.root / self.logical_env

        base_files = self._gather_yaml_files(base_dir, layer="base", fatal=True)
        env_files = self._gather_yaml_files(env_dir, layer=self.logical_env, fatal=False)

        base_cfg: Dict[str, Any] = {}
        env_cfg: Dict[str, Any] = {}

        for f in base_files:
            base_cfg = self._deep_merge(base_cfg, self._load_yaml(f, "base"))
        for f in env_files:
            env_cfg = self._deep_merge(env_cfg, self._load_yaml(f, self.logical_env))

        merged = self._deep_merge(base_cfg, env_cfg)

        masked_cfg, masked_hashes = self._mask_secrets(merged)

        pseudo_run_id = datetime.utcnow().strftime("%Y%m%d%H%M%S") + "-cfg"
        artifact_path = self._write_effective_artifact(
            env=self.logical_env,
            pseudo_run_id=pseudo_run_id,
            masked_config=masked_cfg,
            masked_hashes=masked_hashes,
            files=self.files_loaded,
            warnings=self.warnings,
        )

        logger.info(
            "Environment configuration loaded",
            extra={
                "event": "config.env.loaded",
                "env": self.logical_env,
                "base_file_count": len(base_files),
                "env_file_count": len(env_files),
                "warnings": len(self.warnings),
                "artifact": str(artifact_path),
            },
        )
        return merged  # UNMASKED (per Q1)

    # ---------- Diff Helper (module-level wrapper exposes) ----------

    def diff(self, env_a: str, env_b: str) -> Dict[str, Any]:
        """Compute structural diff (masked secrets in diff via fresh loads)."""
        cfg_a = self._load_for_diff(env_a)
        cfg_b = self._load_for_diff(env_b)
        flat_a = _flatten(cfg_a)
        flat_b = _flatten(cfg_b)

        keys_a = set(flat_a.keys())
        keys_b = set(flat_b.keys())

        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = {}
        for k in sorted(keys_a & keys_b):
            if flat_a[k] != flat_b[k]:
                changed[k] = {"from": flat_a[k], "to": flat_b[k]}

        return {
            "from": self._normalize_env(env_a),
            "to": self._normalize_env(env_b),
            "added": added,
            "removed": removed,
            "changed": changed,
        }

    # ---------- Internal Helpers ----------

    def _normalize_env(self, env: str) -> str:
        logical = _ENV_ALIASES.get(env, env)
        if logical not in _VALID_ENVS:
            self._warn(
                code="unknown_env",
                message=f"Unknown environment '{env}', falling back to 'dev'",
                data={"requested": env},
            )
            logical = "dev"
        return logical

    def _gather_yaml_files(
        self, directory: Path, layer: str, fatal: bool
    ) -> List[Path]:
        if not directory.exists():
            if fatal:
                raise MultiEnvConfigError(
                    f"Required directory missing: {directory}"
                )
            self._warn(
                code="missing_dir",
                message=f"Config directory missing: {directory}",
                data={"layer": layer, "path": str(directory)},
            )
            return []
        files = sorted(
            p
            for p in directory.glob("*")
            if p.is_file() and p.suffix.lower() in (".yml", ".yaml")
        )
        if not files and fatal:
            raise MultiEnvConfigError(
                f"No YAML files in required base directory: {directory}"
            )
        if not files and not fatal:
            self._warn(
                code="empty_dir",
                message=f"No YAML files in {directory}",
                data={"layer": layer},
            )
        self.files_loaded.extend(files)
        return files

    def _load_yaml(self, path: Path, layer: str) -> Dict[str, Any]:
        try:
            text = path.read_text(encoding="utf-8")
            if not text.strip():
                self._warn(
                    code="empty_file",
                    message=f"Empty file: {path}",
                    data={"layer": layer, "file": str(path)},
                )
                return {}
            data = yaml.safe_load(text)
            if data is None:
                return {}
            if not isinstance(data, dict):
                self._warn(
                    code="non_mapping_root",
                    message="Top-level YAML not a mapping",
                    data={"layer": layer, "file": str(path), "type": type(data).__name__},
                )
                return {}
            return data
        except Exception as e:  # noqa: BLE001
            self._warn(
                code="parse_error",
                message=f"Failed to parse YAML: {path.name}",
                data={"layer": layer, "file": str(path), "error": repr(e)},
            )
            return {}

    def _deep_merge(
        self, base: Dict[str, Any], override: Dict[str, Any], path: Tuple[str, ...] = ()
    ) -> Dict[str, Any]:
        result = dict(base)
        for k, v in override.items():
            if k in result:
                existing = result[k]
                if isinstance(existing, dict) and isinstance(v, dict):
                    result[k] = self._deep_merge(existing, v, path + (k,))
                elif isinstance(existing, list) and isinstance(v, list):
                    # list replace
                    result[k] = list(v)
                else:
                    if type(existing) is not type(v):  # noqa: E721
                        self._warn(
                            code="type_conflict",
                            message="Type conflict during merge",
                            data={
                                "path": ".".join(path + (k,)),
                                "base_type": type(existing).__name__,
                                "override_type": type(v).__name__,
                            },
                        )
                    result[k] = v
            else:
                result[k] = v
        return result

    def _mask_secrets(
        self, cfg: Dict[str, Any]
    ) -> Tuple[Dict[str, Any], Dict[str, str]]:
        masked_hashes: Dict[str, str] = {}

        def recurse(obj: Any, trail: Tuple[str, ...]) -> Any:
            if isinstance(obj, dict):
                new_d = {}
                for key, value in obj.items():
                    lower_key = key.lower()
                    full_path = trail + (key,)
                    if any(s in lower_key for s in _SECRET_KEY_SUBSTRINGS):
                        raw = "" if value is None else str(value)
                        digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]
                        masked_hashes[".".join(full_path)] = digest
                        new_d[key] = "***"
                    else:
                        new_d[key] = recurse(value, full_path)
                return new_d
            if isinstance(obj, list):
                return [recurse(v, trail + (str(i),)) for i, v in enumerate(obj)]
            return obj

        return recurse(cfg, ()), masked_hashes

    def _write_effective_artifact(
        self,
        env: str,
        pseudo_run_id: str,
        masked_config: Dict[str, Any],
        masked_hashes: Dict[str, str],
        files: List[Path],
        warnings: List[Dict[str, Any]],
    ) -> Path:
        out_dir = Path("artifacts") / "runs" / pseudo_run_id
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "effective_config.json"
        payload = {
            "env": env,
            "pseudo_run_id": pseudo_run_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "files_loaded": [
                str(p.relative_to(Path.cwd())) if p.is_absolute() else str(p)
                for p in files
            ],
            "config": masked_config,
            "masked_hashes": masked_hashes,
            "warnings": warnings,
        }
        out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return out_file

    def _warn(self, code: str, message: str, data: Dict[str, Any]) -> None:
        entry = {"code": code, "message": message, **data}
        self.warnings.append(entry)
        logger.warning(
            message,
            extra={"event": "config.env.load.warning", "code": code, **data},
        )

    def _load_for_diff(self, env: str) -> Dict[str, Any]:
        # Fresh loader instance to isolate warnings; we need masked for diff secrecy -> mask after load
        loader = MultiEnvConfigLoader(self.root)
        raw = loader.load(env)
        masked, _ = loader._mask_secrets(raw)
        return masked


# -------- Module-level convenience --------

def load_config(environment: str | None = None) -> Dict[str, Any]:
    """
    Load UNMASKED configuration (artifact contains masked).
    """
    loader = MultiEnvConfigLoader()
    return loader.load(environment)


def diff_envs(a: str, b: str) -> Dict[str, Any]:
    """
    Return diff structure between environments a and b.
    """
    loader = MultiEnvConfigLoader()
    return loader.diff(a, b)


def _flatten(obj: Any, prefix: Tuple[str, ...] = ()) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(_flatten(v, prefix + (k,)))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_flatten(v, prefix + (str(i),)))
    else:
        out[".".join(prefix)] = obj
    return out
