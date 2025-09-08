"""Secret Masking Module (Issue #60)

Provides automatic detection and masking of sensitive information in log output.
Supports common secret patterns like API keys, passwords, and tokens.

Features:
    - Pattern-based secret detection using regex
    - Configurable masking rules
    - Feature flag control
    - Performance optimized for logging pipeline
    - Thread-safe operations

Security Patterns Supported:
    - API Keys: sk-, pk-, xoxp-, xoxb- prefixes
    - Passwords: password=, passwd=, pwd= fields
    - Tokens: Bearer, Authorization headers
    - Generic: Long alphanumeric strings (32+ chars)

Configuration:
    - BYKILT_SECRET_MASKING_ENABLED: Enable/disable masking (default: true)
    - Custom patterns can be added via SecretMasker.add_pattern()

Performance:
    - Regex compilation cached
    - Early exit on disabled state
    - Minimal overhead (<5ms per log entry)
"""
from __future__ import annotations

import re
import os
from typing import List, Dict, Any, Pattern, Optional
from dataclasses import dataclass
from threading import Lock


@dataclass
class MaskingRule:
    """Represents a single masking rule with pattern and replacement."""
    name: str
    pattern: Pattern[str]
    replacement: str
    description: str = ""


class SecretMasker:
    """Thread-safe secret masking utility for log sanitization."""

    _instance: Optional["SecretMasker"] = None
    _instance_lock: Lock = Lock()

    def __init__(self):
        self._rules: List[MaskingRule] = []
        self._rules_lock: Lock = Lock()
        self._enabled: bool = self._get_env_enabled()
        self._compiled_patterns: Dict[str, Pattern[str]] = {}

        # Initialize default patterns
        self._initialize_default_patterns()

    @classmethod
    def get_instance(cls) -> "SecretMasker":
        """Get singleton instance of SecretMasker."""
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _get_env_enabled(self) -> bool:
        """Check if secret masking is enabled via environment variable."""
        env_value = os.getenv("BYKILT_SECRET_MASKING_ENABLED", "true")
        return env_value.lower() in {"1", "true", "yes", "on"}

    def _initialize_default_patterns(self) -> None:
        """Initialize default secret detection patterns."""
        default_patterns = [
            # API Keys (OpenAI, Stripe, etc.)
            MaskingRule(
                name="openai_api_key",
                pattern=re.compile(r'\b(sk-[a-zA-Z0-9]{32,})\b'),
                replacement="sk-****",
                description="OpenAI API keys"
            ),
            MaskingRule(
                name="stripe_secret_key",
                pattern=re.compile(r'\b(sk_(?:live_|test_)?[a-zA-Z0-9]{24,})\b'),
                replacement="sk_****",
                description="Stripe secret keys"
            ),
            MaskingRule(
                name="generic_api_key",
                pattern=re.compile(r'\b(pk_[a-zA-Z0-9]{24,})\b'),
                replacement="pk_****",
                description="Generic private keys"
            ),

            # Slack tokens
            MaskingRule(
                name="slack_token",
                pattern=re.compile(r'\b(xox[p|b|a]-[0-9]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24,})\b'),
                replacement="xox*-****-****-****-****",
                description="Slack bot/user tokens"
            ),

            # Password fields (both JSON and direct values)
            MaskingRule(
                name="password_field",
                pattern=re.compile(r'("password"|"passwd"|"pwd")\s*:\s*"([^"]{3,})"'),
                replacement=r'\1: "****"',
                description="JSON password fields"
            ),
            MaskingRule(
                name="password_param",
                pattern=re.compile(r'\b(password|passwd|pwd)=([^&\s]{3,})'),
                replacement=r'\1=****',
                description="URL/form password parameters"
            ),

            # Bearer tokens
            MaskingRule(
                name="bearer_token",
                pattern=re.compile(r'\b(Bearer\s+)([a-zA-Z0-9_\-\.]{20,})\b'),
                replacement=r'\1****',
                description="Bearer token authentication"
            ),

            # Authorization headers
            MaskingRule(
                name="auth_header",
                pattern=re.compile(r'\b(Authorization)\s*:\s*([^\s]{10,})\b'),
                replacement=r'\1: ****',
                description="Authorization header values"
            ),

            # Generic long alphanumeric strings (potential secrets)
            MaskingRule(
                name="generic_secret",
                pattern=re.compile(r'\b([a-zA-Z0-9]{32,})\b'),
                replacement="****",
                description="Generic long alphanumeric strings"
            ),
        ]

        with self._rules_lock:
            self._rules.extend(default_patterns)

    def add_pattern(self, name: str, pattern: str, replacement: str, description: str = "") -> None:
        """Add a custom masking pattern.

        Args:
            name: Unique identifier for the pattern
            pattern: Regex pattern string
            replacement: Replacement string (can use \1, \2 for groups)
            description: Optional description
        """
        try:
            compiled_pattern = re.compile(pattern)
            rule = MaskingRule(name, compiled_pattern, replacement, description)

            with self._rules_lock:
                # Remove existing rule with same name if present
                self._rules = [r for r in self._rules if r.name != name]
                self._rules.append(rule)

        except re.error as e:
            raise ValueError(f"Invalid regex pattern for '{name}': {e}")

    def remove_pattern(self, name: str) -> bool:
        """Remove a masking pattern by name.

        Returns:
            True if pattern was removed, False if not found
        """
        with self._rules_lock:
            original_length = len(self._rules)
            self._rules = [r for r in self._rules if r.name != name]
            return len(self._rules) < original_length

    def mask_text(self, text: str) -> str:
        """Mask sensitive information in the given text.

        Args:
            text: Input text to sanitize

        Returns:
            Text with secrets masked
        """
        if not (self._get_env_enabled() and self._enabled) or not text:
            return text

        masked_text = text

        with self._rules_lock:
            for rule in self._rules:
                try:
                    masked_text = rule.pattern.sub(rule.replacement, masked_text)
                except Exception:
                    # Skip problematic patterns to avoid breaking the masking pipeline
                    continue

        return masked_text

    def mask_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively mask sensitive information in a dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            Dictionary with secrets masked
        """
        if not (self._get_env_enabled() and self._enabled) or not data:
            return data

        def _mask_value(value: Any) -> Any:
            if isinstance(value, str):
                return self.mask_text(value)
            elif isinstance(value, dict):
                return {k: _mask_value(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [_mask_value(item) for item in value]
            else:
                return value

        return _mask_value(data)

    def is_enabled(self) -> bool:
        """Check if secret masking is currently enabled."""
        return self._get_env_enabled() and self._enabled

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable secret masking."""
        self._enabled = enabled

    def get_patterns(self) -> List[Dict[str, str]]:
        """Get list of all masking patterns."""
        with self._rules_lock:
            return [
                {
                    "name": rule.name,
                    "pattern": rule.pattern.pattern,
                    "replacement": rule.replacement,
                    "description": rule.description
                }
                for rule in self._rules
            ]

    def clear_patterns(self) -> None:
        """Clear all masking patterns (including defaults)."""
        with self._rules_lock:
            self._rules.clear()


# Convenience functions for easy access
def mask_text(text: str) -> str:
    """Convenience function to mask text using the singleton instance."""
    return SecretMasker.get_instance().mask_text(text)


def mask_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to mask dictionary using the singleton instance."""
    return SecretMasker.get_instance().mask_dict(data)


def is_masking_enabled() -> bool:
    """Check if secret masking is enabled."""
    return SecretMasker.get_instance().is_enabled()


__all__ = [
    "SecretMasker",
    "mask_text",
    "mask_dict",
    "is_masking_enabled"
]
