"""Unified Artifact Persistence Framework (Internal - Issue #355)

Shared artifact writing, masking, and metadata generation for config and artifacts.
Consolidates overlapping logic from feature_flags.py, multi_env_loader.py, and artifact_manager.py.
"""

from __future__ import annotations

import json
import hashlib
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timezone

from ._errors import ConfigError

logger = logging.getLogger(__name__)


@dataclass
class MaskedValue:
    """Tracking for masked sensitive values."""
    original: str
    masked: str = "***"
    hash_digest: str = ""  # SHA256 first 8 hex chars

    def to_dict(self) -> Dict[str, str]:
        """Convert to dict representation."""
        return {"masked": self.masked, "hash": self.hash_digest}


class ArtifactWriter:
    """Unified artifact persistence for configs, flags, and recordings."""

    # Default secret key substrings
    SECRET_KEY_SUBSTRINGS = ["api_key", "token", "secret", "password", "key"]

    def __init__(
        self,
        artifact_base_dir: Optional[Path] = None,
        secret_substrings: Optional[List[str]] = None,
    ):
        """Initialize artifact writer.

        Args:
            artifact_base_dir: Base directory for artifacts (auto-detected if None)
            secret_substrings: List of substrings to identify secret values
        """
        self.artifact_base_dir = artifact_base_dir
        self.secret_substrings = secret_substrings or self.SECRET_KEY_SUBSTRINGS

    def write_config_artifact(
        self,
        config: Dict[str, Any],
        artifact_id: str,
        artifact_type: str = "config",
        env: Optional[str] = None,
        mask_secrets: bool = True,
    ) -> Path:
        """Write configuration artifact with optional secret masking.

        Args:
            config: Configuration dict to persist
            artifact_id: Unique artifact ID (e.g., "20251021120000-cfg")
            artifact_type: Artifact type ("config", "flags", etc.)
            env: Environment name (optional)
            mask_secrets: Whether to mask sensitive values

        Returns:
            Path to written artifact file

        Raises:
            ConfigError: If write fails
        """
        artifact_dir = self._get_artifact_dir(artifact_id, artifact_type)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        artifact_file = artifact_dir / "artifact.json"

        # Prepare artifact payload
        payload = {
            "artifact_type": artifact_type,
            "artifact_id": artifact_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "env": env,
            "config": config,
        }

        masked_values = {}
        if mask_secrets:
            payload["config"], masked_values = self._mask_secrets(config)
            if masked_values:
                payload["masked_values"] = masked_values

        try:
            with open(artifact_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, default=str)
            logger.info(
                f"Wrote {artifact_type} artifact",
                extra={
                    "event": f"artifact.{artifact_type}.written",
                    "path": str(artifact_file),
                    "id": artifact_id,
                },
            )
            return artifact_file
        except OSError as e:
            raise ConfigError(f"Failed to write artifact {artifact_file}: {e}") from e

    def write_metadata(
        self,
        metadata: Dict[str, Any],
        artifact_id: str,
        artifact_type: str = "metadata",
    ) -> Path:
        """Write artifact metadata file.

        Args:
            metadata: Metadata dict
            artifact_id: Unique artifact ID
            artifact_type: Artifact type

        Returns:
            Path to written metadata file

        Raises:
            ConfigError: If write fails
        """
        artifact_dir = self._get_artifact_dir(artifact_id, artifact_type)
        artifact_dir.mkdir(parents=True, exist_ok=True)

        metadata_file = artifact_dir / "metadata.json"

        try:
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, default=str)
            logger.debug(f"Wrote metadata artifact: {metadata_file}")
            return metadata_file
        except OSError as e:
            raise ConfigError(f"Failed to write metadata {metadata_file}: {e}") from e

    def _mask_secrets(
        self,
        data: Dict[str, Any],
    ) -> tuple[Dict[str, Any], Dict[str, Dict[str, str]]]:
        """Recursively mask sensitive values in config.

        Args:
            data: Configuration dict

        Returns:
            Tuple of (masked_config, masked_values_map)
        """
        masked_config = {}
        masked_map = {}

        for key, value in data.items():
            masked_value, key_map = self._process_config_value(key, value)
            masked_config[key] = masked_value
            masked_map.update(key_map)

        return masked_config, masked_map

    def _process_config_value(
        self, key: str, value: Any
    ) -> tuple[Any, Dict[str, Dict[str, str]]]:
        """Process single config value for masking.

        Args:
            key: Configuration key
            value: Configuration value

        Returns:
            Tuple of (masked_value, mask_map)
        """
        if self._is_secret_key(key) and isinstance(value, str):
            hash_val = hashlib.sha256(value.encode()).hexdigest()[:8]
            return "***", {key: {"masked": "***", "hash": hash_val}}

        if isinstance(value, dict):
            masked_val, nested_map = self._mask_secrets(value)
            prefixed_map = {f"{key}.{k}": v for k, v in nested_map.items()}
            return masked_val, prefixed_map

        if isinstance(value, list):
            masked_list = [self._mask_item(item) if isinstance(item, dict) else item
                          for item in value]
            return masked_list, {}

        return value, {}

    def _mask_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Mask item in list."""
        masked_item = {}
        for key, value in item.items():
            if self._is_secret_key(key) and isinstance(value, str):
                masked_item[key] = "***"
            elif isinstance(value, dict):
                masked_item[key] = self._mask_item(value)
            else:
                masked_item[key] = value
        return masked_item

    def _is_secret_key(self, key: str) -> bool:
        """Check if key looks like a secret."""
        key_lower = key.lower()
        return any(substr in key_lower for substr in self.secret_substrings)

    def _get_artifact_dir(self, artifact_id: str, artifact_type: str) -> Path:
        """Get or create artifact directory.

        Args:
            artifact_id: Unique artifact ID
            artifact_type: Artifact type

        Returns:
            Path to artifact directory
        """
        if self.artifact_base_dir is None:
            # Auto-detect from project structure
            from src.utils.fs_paths import get_artifacts_base_dir
            base = get_artifacts_base_dir()
        else:
            base = self.artifact_base_dir

        return base / "runs" / f"{artifact_id}-{artifact_type}"
