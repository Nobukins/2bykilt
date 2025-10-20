"""Unified Configuration Loader Framework (Internal - Issue #355)

Shared YAML loading, environment variable resolution, and precedence-based merging.
Replaces overlapping logic from feature_flags.py and multi_env_loader.py.
"""

from __future__ import annotations

import os
import logging
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional, List, Callable
from functools import lru_cache

import yaml

from ._errors import ConfigError, ConfigValidationError

logger = logging.getLogger(__name__)


class SourcePrecedence(Enum):
    """Configuration source precedence (lower value = higher priority)."""
    RUNTIME = 0      # Highest: Runtime overrides
    ENVIRONMENT = 1  # Environment variables
    FILE_ENV = 2     # Environment-specific config file
    FILE_BASE = 3    # Base config file
    DEFAULT = 4      # Lowest: Built-in default


@dataclass
class ConfigSource:
    """Represents a configuration source with metadata."""
    name: str
    data: Dict[str, Any]
    precedence: SourcePrecedence
    origin: Optional[str] = None  # File path or description


class YamlFileLoader:
    """Shared YAML file loading with consistent error handling."""

    @staticmethod
    def load(path: Path, layer: str = "base") -> Dict[str, Any]:
        """Load and parse YAML file with error handling.

        Args:
            path: Path to YAML file
            layer: Layer name for logging

        Returns:
            Parsed YAML as dict

        Raises:
            ConfigError: If file cannot be loaded or parsed
        """
        if not path.exists():
            logger.warning(f"Config file not found: {path} (layer={layer})")
            return {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if content is None:
                    content = {}
                if not isinstance(content, dict):
                    raise ConfigValidationError(
                        f"YAML file must be a dict, got {type(content).__name__}: {path}"
                    )
                logger.debug(f"Loaded config file: {path} (layer={layer})")
                return content
        except yaml.YAMLError as e:
            raise ConfigError(f"Failed to parse YAML {path}: {e}") from e
        except OSError as e:
            raise ConfigError(f"Failed to read config file {path}: {e}") from e

    @staticmethod
    def load_all_in_dir(
        dir_path: Path,
        layer: str = "base",
        file_patterns: Optional[List[str]] = None,
        sort: bool = True,
    ) -> List[Dict[str, Any]]:
        """Load all YAML files in directory.

        Args:
            dir_path: Directory path
            layer: Layer name for logging
            file_patterns: File name patterns (default: ["*.yaml", "*.yml"])
            sort: Sort files before loading

        Returns:
            List of parsed YAML dicts in load order
        """
        if not dir_path.exists() or not dir_path.is_dir():
            logger.debug(f"Config directory not found: {dir_path}")
            return []

        patterns = file_patterns or ["*.yaml", "*.yml"]
        files = []
        for pattern in patterns:
            files.extend(sorted(dir_path.glob(pattern)))

        if sort:
            files = sorted(set(files))

        result = []
        for f in files:
            try:
                data = YamlFileLoader.load(f, layer=layer)
                if data:  # Only add non-empty dicts
                    result.append(data)
            except ConfigError as e:
                logger.warning(f"Skipping config file due to error: {e}")

        return result


class EnvVarResolver:
    """Environment variable resolution with type coercion and aliases."""

    # Boolean string constants
    _TRUE_VALUES = {"true", "1", "yes", "on"}
    _FALSE_VALUES = {"false", "0", "no", "off"}

    def __init__(self, aliases: Optional[Dict[str, str]] = None):
        """Initialize resolver with optional env var name aliases.

        Args:
            aliases: Dict mapping env var names (e.g., "development" -> "dev")
        """
        self.aliases = aliases or {}

    def resolve(
        self,
        name: str,
        expected_type: Optional[type] = None,
        default: Any = None,
    ) -> Optional[Any]:
        """Resolve environment variable with type coercion.

        Args:
            name: Env var name (e.g., "BYKILT_DEBUG")
            expected_type: Expected return type (bool, int, str, float)
            default: Default value if not found

        Returns:
            Resolved value or default
        """
        value = os.getenv(name)
        if value is None:
            return default

        if expected_type is None or expected_type is str:
            return value

        return self._coerce_type(value, expected_type, name)

    def resolve_flag(self, name: str, default: bool = False) -> bool:
        """Convenience method for boolean flags.

        Args:
            name: Env var name
            default: Default value

        Returns:
            Boolean value
        """
        return self.resolve(name, bool, default) or default

    @staticmethod
    def _coerce_type(value: str, target_type: type, var_name: str) -> Any:
        """Coerce string value to target type.

        Args:
            value: String value from environment
            target_type: Target type (bool, int, float)
            var_name: Variable name for error messages

        Returns:
            Coerced value

        Raises:
            ConfigValidationError: If coercion fails
        """
        try:
            if target_type is bool:
                lower_val = value.lower()
                if lower_val in EnvVarResolver._TRUE_VALUES:
                    return True
                elif lower_val in EnvVarResolver._FALSE_VALUES:
                    return False
                else:
                    raise ValueError(f"Cannot parse '{value}' as bool")
            elif target_type is int:
                return int(value)
            elif target_type is float:
                return float(value)
            else:
                return value
        except (ValueError, AttributeError) as e:
            raise ConfigValidationError(
                f"Cannot coerce {var_name}='{value}' to {target_type.__name__}: {e}"
            ) from e


class ChainResolver:
    """Unified configuration resolution with precedence ordering.

    Merges multiple configuration sources in precedence order,
    allowing lower-priority defaults to be overridden by higher-priority sources.
    """

    def __init__(self, sources: List[ConfigSource]):
        """Initialize resolver with ordered sources.

        Args:
            sources: List of ConfigSource objects (will be sorted by precedence)
        """
        # Sort by precedence value (ascending: higher priority first)
        self.sources = sorted(sources, key=lambda s: s.precedence.value)

    def resolve(self, key: str, default: Any = None) -> Any:
        """Resolve key across sources following precedence.

        Args:
            key: Configuration key (dot-separated paths supported)
            default: Default value if key not found

        Returns:
            Resolved value or default
        """
        for source in self.sources:
            value = self._extract_nested(source.data, key)
            if value is not None:
                return value
        return default

    def merge(self, deep: bool = True) -> Dict[str, Any]:
        """Merge all sources into single dict.

        Args:
            deep: If True, perform deep merge; else shallow override

        Returns:
            Merged configuration dict
        """
        result: Dict[str, Any] = {}
        # Iterate in reverse so highest-priority sources win
        for source in reversed(self.sources):
            if deep:
                result = self._deep_merge(result, source.data)
            else:
                result = {**result, **source.data}
        return result

    @staticmethod
    def _extract_nested(data: Dict[str, Any], key: str) -> Any:
        """Extract value from nested dict using dot-separated path.

        Args:
            data: Data dict
            key: Dot-separated key path (e.g., "db.host" or "settings.timeout")

        Returns:
            Value at path or None if not found
        """
        parts = key.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current

    @staticmethod
    def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge override dict into base dict.

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary (base is not modified)
        """
        result = base.copy()
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ChainResolver._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
