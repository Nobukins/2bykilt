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

try:
    from src.runtime.run_context import RunContext
except Exception:  # noqa: BLE001
    RunContext = None  # type: ignore

logger = logging.getLogger(__name__)

_ENV_ALIASES = {
    "development": "dev",
    "production": "prod",
}
_VALID_ENVS = {"base", "dev", "staging", "prod"}  # Added "base" for default config
_SECRET_KEY_SUBSTRINGS = ["api_key", "token", "secret", "password", "key"]


class MultiEnvConfigError(Exception):
    """Fatal configuration error (new API)."""
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

    def load(self, requested_env: str | None = None) -> Dict[str, Any]:
        self.warnings.clear()
        self.files_loaded.clear()

        # When neither requested_env nor BYKILT_ENV is set, use "base" to load only base config
        # This prevents defaulting to dev environment in CI and tests
        env_var = os.getenv("BYKILT_ENV")
        if requested_env:
            env_raw = requested_env.strip().lower()
        elif env_var:
            env_raw = env_var.strip().lower()
        else:
            env_raw = "base"  # Use base config when no environment specified
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

        # Unified run/job id base (Issue #32)
        if RunContext:
            pseudo_run_id = RunContext.get().artifact_dir("cfg").name  # e.g. <run_id_base>-cfg
        else:  # fallback
            pseudo_run_id = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-legacy-cfg"
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
        return merged  # UNMASKED

    def diff(self, env_a: str, env_b: str) -> Dict[str, Any]:
        cfg_a = self._load_for_diff(env_a)
        cfg_b = self._load_for_diff(env_b)
        flat_a = _flatten(cfg_a)
        flat_b = _flatten(cfg_b)

        keys_a = set(flat_a.keys())
        keys_b = set(flat_b.keys())

        added = sorted(keys_b - keys_a)
        removed = sorted(keys_a - keys_b)
        changed = {
            k: {"from": flat_a[k], "to": flat_b[k]}
            for k in sorted(keys_a & keys_b)
            if flat_a[k] != flat_b[k]
        }

        return {
            "from": self._normalize_env(env_a),
            "to": self._normalize_env(env_b),
            "added": added,
            "removed": removed,
            "changed": changed,
        }

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
                raise MultiEnvConfigError(f"Required directory missing: {directory}")
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
        """
        Return (masked_config, masked_hashes)

        FIX: Do NOT mask entire dict when key itself (e.g. 'secrets') matches pattern.
        Only mask scalar leaves. Recurse into dict/list even if parent key matches.
        """
        masked_hashes: Dict[str, str] = {}

        def recurse(obj: Any, trail: Tuple[str, ...]) -> Any:
            if isinstance(obj, dict):
                new_d = {}
                for key, value in obj.items():
                    lower_key = key.lower()
                    full_path = trail + (key,)
                    # Only mask if scalar (not dict/list) AND key matches
                    if (
                        any(s in lower_key for s in _SECRET_KEY_SUBSTRINGS)
                        and not isinstance(value, (dict, list))
                    ):
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
        # REVIEW FIX: remove duplicated path construction; only mkdir when not created via RunContext
        from src.utils.fs_paths import get_artifacts_run_dir
        out_dir = get_artifacts_run_dir(pseudo_run_id)
        # fs_paths already ensures dir exists; preserve RunContext check for compatibility
        if RunContext and pseudo_run_id.startswith(RunContext.get().run_id_base):
            # ensure parent exists but avoid double-mkdir if run context already created
            out_dir.parent.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / "effective_config.json"
        payload = {
            "env": env,
            "pseudo_run_id": pseudo_run_id,
            "run_id_base": RunContext.get().run_id_base if RunContext else None,
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
        loader = MultiEnvConfigLoader(self.root)
        raw = loader.load(env)
        masked, _ = loader._mask_secrets(raw)  # type: ignore[attr-defined]
        return masked


def load_config(environment: str | None = None) -> Dict[str, Any]:
    loader = MultiEnvConfigLoader()
    return loader.load(environment)


def diff_envs(a: str, b: str) -> Dict[str, Any]:
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

# ---------------------------------------------------------------------------
# Backward compatibility facade (Option B in Issue #65 discussion)
# Provides legacy class & exception names expected by existing tests / scripts.
# NOTE: Marked for deprecation once callers migrate to MultiEnvConfigLoader.
# ---------------------------------------------------------------------------

# Legacy exception alias (tests expect ConfigValidationError)
class ConfigValidationError(MultiEnvConfigError):
    """Backward-compatible validation error alias."""
    pass


class ConfigLoader:
    """Backward-compatible wrapper exposing legacy API surface.

    Legacy methods provided:
      * load_config(environment: str | None)
      * compare_configs(env1, env2)
      * save_effective_config(config, path)
      * _get_current_environment()

    Additional behavior:
      * Injects `_metadata` block (environment / loaded_at / files_loaded / warnings)
      * Maps external env names: development|production ↔ dev|prod
      * Minimal schema-driven environment variable overrides (environment_override field)
    """

    _INVERSE_ENV = {"dev": "development", "staging": "staging", "prod": "production"}
    _FORWARD_ENV = {"development": "dev", "staging": "staging", "production": "prod"}

    def __init__(self, config_dir: str | Path = "config") -> None:
        self._config_dir = Path(config_dir)
        self._loader = MultiEnvConfigLoader(self._config_dir)

    # ---- Public (legacy) API -------------------------------------------------
    def load_config(self, environment: str | None = None) -> Dict[str, Any]:
        try:
            internal_env = None
            original_env_arg = environment
            if environment:
                env_l = environment.lower()
                internal_env = self._FORWARD_ENV.get(env_l, env_l)

            # Legacy flat structure detection:
            #   config_dir/base.yml + per-env *.yml (development.yml / production.yml / staging.yml)
            # New structure would have config_dir/base/ directory.
            base_file = self._config_dir / "base.yml"
            base_dir = self._config_dir / "base"
            use_legacy_flat = base_file.exists() and not base_dir.exists()

            if use_legacy_flat:
                merged = self._legacy_flat_load(internal_env, original_env_arg)
            else:
                merged = self._loader.load(internal_env)
            # Apply schema based env var overrides (minimal implementation)
            self._apply_schema_env_overrides(merged)
            external_env = self._INVERSE_ENV.get(self._loader.logical_env, self._loader.logical_env)
            metadata = {
                "environment": external_env,
                "loaded_at": datetime.now(timezone.utc).isoformat(),
                "files_loaded": [str(p) for p in self._loader.files_loaded],
                "warnings": list(self._loader.warnings),
            }
            if isinstance(merged.get("_metadata"), dict):
                merged["_metadata"].update(metadata)
            else:
                merged["_metadata"] = metadata
            return merged
        except MultiEnvConfigError as e:  # Re-raise under legacy name
            raise ConfigValidationError(str(e)) from e

    def _legacy_flat_load(self, internal_env: str | None, original_env: str | None) -> Dict[str, Any]:
        """Load using legacy single-file-per-env layout expected by older tests.

        Layout:
          config_dir/base.yml
          config_dir/development.yml (or dev.yml)
          config_dir/production.yml (or prod.yml)
          config_dir/staging.yml
        """
        # Determine internal env (dev/staging/prod)
        # When BYKILT_ENV is not set (internal_env is None), use base config only
        env_from_var = os.getenv("BYKILT_ENV", "").lower()
        env_token = internal_env or (env_from_var if env_from_var else None)
        if env_token == "development":
            env_token = "dev"
        if env_token == "production":
            env_token = "prod"
        self._loader.logical_env = env_token or "base"  # keep state consistent for metadata mapping

        def _read_yaml(path: Path) -> Dict[str, Any]:
            if not path.exists():
                return {}
            try:
                text = path.read_text(encoding="utf-8")
                if not text.strip():
                    return {}
                data = yaml.safe_load(text)
                return data if isinstance(data, dict) else {}
            except Exception:  # noqa: BLE001
                return {}

        base_cfg = _read_yaml(self._config_dir / "base.yml")

        # Candidate env file names in preference order
        candidate_names: List[str] = []
        if original_env:
            candidate_names.append(original_env.lower())
        # Add expanded forms
        inverse_map = {"dev": "development", "prod": "production"}
        if env_token in inverse_map:
            candidate_names.append(inverse_map[env_token])
        candidate_names.append(env_token)
        # Deduplicate preserving order
        seen = set()
        unique_candidates = []
        for name in candidate_names:
            if name and name not in seen:
                unique_candidates.append(name)
                seen.add(name)

        env_cfg: Dict[str, Any] = {}
        for cand in unique_candidates:
            for ext in (".yml", ".yaml"):
                p = self._config_dir / f"{cand}{ext}"
                if p.exists():
                    env_cfg = self._loader._deep_merge(env_cfg, _read_yaml(p))  # type: ignore[attr-defined]
                    break

        merged = self._loader._deep_merge(base_cfg, env_cfg)  # type: ignore[attr-defined]
        return merged

    def compare_configs(self, env1: str, env2: str) -> Dict[str, Any]:
        cfg1 = self.load_config(env1)
        cfg2 = self.load_config(env2)
        flat1 = _flatten(cfg1)
        flat2 = _flatten(cfg2)
        keys1 = set(flat1.keys())
        keys2 = set(flat2.keys())
        differences: List[Dict[str, Any]] = []
        # Added (in env2 only)
        for k in sorted(keys2 - keys1):
            differences.append({
                "path": k,
                "type": "added",
                "value_env1": None,
                "value_env2": flat2[k],
            })
        # Removed (in env1 only)
        for k in sorted(keys1 - keys2):
            differences.append({
                "path": k,
                "type": "removed",
                "value_env1": flat1[k],
                "value_env2": None,
            })
        # Changed (present in both, values differ and not both dict/list objects serialized differently)
        for k in sorted(keys1 & keys2):
            if flat1[k] != flat2[k]:
                differences.append({
                    "path": k,
                    "type": "changed",
                    "value_env1": flat1[k],
                    "value_env2": flat2[k],
                })
        summary = {
            "configs_identical": len(differences) == 0,
            "total_differences": len(differences),
        }
        return {
            "environment_1": env1,
            "environment_2": env2,
            "differences": differences,
            "comparison_summary": summary,
        }

    def save_effective_config(self, config: Dict[str, Any], output_path: str) -> str:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8")
        return str(path)

    def _get_current_environment(self) -> str:
        raw = os.getenv("BYKILT_ENV", "dev").lower()
        if raw in ("development", "dev"):
            return "development"
        if raw == "staging":
            return "staging"
        if raw in ("production", "prod"):
            return "production"
        return raw

    # ---- Internal helpers ----------------------------------------------------
    def _apply_schema_env_overrides(self, config: Dict[str, Any]) -> None:
        """Minimal environment variable override applying based on schema files.

        Looks for config_dir/schema/*.yml and applies entries with
        leaf dict containing 'environment_override': ENV_NAME.
        Supported type coercions: float, int, bool, (default: string)
        Silent on errors (non-fatal for backward compatibility focus).
        """
        schema_dir = self._config_dir / "schema"
        if not schema_dir.exists() or not schema_dir.is_dir():
            return
        schema_files = sorted(p for p in schema_dir.glob("*.yml"))
        if not schema_files:
            return
        for sf in schema_files:
            try:
                content = sf.read_text(encoding="utf-8")
                data = yaml.safe_load(content) if content.strip() else None
                if not isinstance(data, dict):
                    continue
                props = data.get("properties")
                if not isinstance(props, dict):
                    continue
                self._walk_schema_properties(props, [], config)
            except Exception:  # noqa: BLE001
                continue

    def _walk_schema_properties(self, props: Dict[str, Any], trail: List[str], config: Dict[str, Any]) -> None:
        for key, node in props.items():
            if not isinstance(node, dict):
                continue
            # Object with nested properties
            if isinstance(node.get("properties"), dict):
                self._walk_schema_properties(node["properties"], trail + [key], config)
                continue
            env_var = node.get("environment_override")
            if not env_var or env_var not in os.environ:
                continue
            raw_val = os.environ[env_var]
            desired_type = node.get("type")
            coerced: Any = raw_val
            try:  # type coercion best-effort
                if desired_type == "float":
                    coerced = float(raw_val)
                elif desired_type == "int":
                    coerced = int(raw_val)
                elif desired_type == "bool":
                    coerced = raw_val.lower() in ("1", "true", "yes", "on")
            except Exception:  # noqa: BLE001
                coerced = raw_val  # fallback to string
            # Navigate/create path
            cursor = config
            for seg in trail:
                cursor = cursor.setdefault(seg, {})  # type: ignore[assignment]
            cursor.setdefault(trail[-1] if trail else key, {})  # ensure object path if nested just created
            cursor = config  # restart to set final value precisely
            # Build parent
            parent = config
            for seg in trail:
                parent = parent.setdefault(seg, {})  # type: ignore[assignment]
            parent[key] = coerced


# Explicit re-export list for type checkers / star imports (legacy + new)
__all__ = [
    "MultiEnvConfigLoader",
    "MultiEnvConfigError",
    "ConfigLoader",
    "ConfigValidationError",
    "load_config",
    "diff_envs",
]
