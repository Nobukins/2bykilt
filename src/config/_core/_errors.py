"""Configuration Error Handling (Internal - Issue #355)"""


class ConfigError(Exception):
    """Base exception for configuration errors."""
    pass


class ConfigValidationError(ConfigError):
    """Configuration validation error."""
    pass


class ConfigResolutionError(ConfigError):
    """Configuration resolution error."""
    pass
