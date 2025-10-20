"""Unified Configuration Framework (Internal - Issue #355)

Shared foundation for config resolution, env var handling, and artifact persistence.
This module consolidates overlapping logic from feature_flags.py and multi_env_loader.py.

Key Exports:
- ConfigSource: Abstract configuration source
- ChainResolver: Precedence-based configuration resolution
- YamlFileLoader: Shared YAML parsing utilities
- EnvVarResolver: Environment variable resolution
- ArtifactWriter: Unified artifact persistence
- ConfigError: Configuration error base class
"""

from ._loader import (
    ConfigSource,
    ChainResolver,
    YamlFileLoader,
    EnvVarResolver,
    SourcePrecedence,
)
from ._artifacts import ArtifactWriter, MaskedValue
from ._errors import ConfigError, ConfigValidationError

__all__ = [
    "ConfigSource",
    "ChainResolver",
    "YamlFileLoader",
    "EnvVarResolver",
    "SourcePrecedence",
    "ArtifactWriter",
    "MaskedValue",
    "ConfigError",
    "ConfigValidationError",
]
