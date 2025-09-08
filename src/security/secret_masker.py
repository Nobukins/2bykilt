"""Secret Masking Extension (Issue #60)

Implements secret pattern detection and masking functionality to prevent
sensitive information from being logged.

Core Functionality:
- Detect common secret patterns (API keys, passwords, tokens)
- Automatically mask secrets in log output
- Feature flag control for enable/disable
- Minimal performance impact (<5ms overhead)

Security Patterns Supported:
- API Keys: sk-, pk-, xoxp-, xoxb- prefixes
- Passwords: password=, passwd=, pwd= fields  
- Tokens: Bearer, Authorization headers
- Generic: 32+ character alphanumeric strings
"""
from __future__ import annotations

import re
import time
from typing import Any, Dict, Pattern
from dataclasses import dataclass, field

from src.config.feature_flags import FeatureFlags


@dataclass
class SecretPattern:
    """Represents a secret pattern to detect and mask."""
    name: str
    pattern: Pattern[str]
    replacement: str = "***MASKED***"


class SecretMasker:
    """Core secret masking functionality.
    
    Detects and masks sensitive information in text and data structures
    while maintaining minimal performance impact.
    """
    
    # Pre-compiled patterns for performance
    PATTERNS = [
        SecretPattern(
            name="api_key_prefix",
            pattern=re.compile(r'\b(sk-|pk-|xoxp-|xoxb-)[A-Za-z0-9]{16,}', re.IGNORECASE),
            replacement="***MASKED_API_KEY***"
        ),
        SecretPattern(
            name="password_field",
            pattern=re.compile(r'(password|passwd|pwd)\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?', re.IGNORECASE),
            replacement=r'\1=***MASKED_PASSWORD***'
        ),
        SecretPattern(
            name="bearer_token",
            pattern=re.compile(r'Bearer\s+[A-Za-z0-9+/=]{16,}', re.IGNORECASE),
            replacement="Bearer ***MASKED_TOKEN***"
        ),
        SecretPattern(
            name="authorization_header",
            pattern=re.compile(r'Authorization:\s*[A-Za-z0-9+/=]{16,}', re.IGNORECASE),
            replacement="Authorization: ***MASKED_AUTH***"
        ),
        SecretPattern(
            name="generic_secret",
            pattern=re.compile(r'\b[A-Za-z0-9]{32,}\b'),
            replacement="***MASKED_GENERIC***"
        ),
    ]
    
    # Sensitive field names that should be masked regardless of value
    SENSITIVE_KEYS = {
        'password', 'secret', 'token', 'key', 'credential',
        'auth', 'session', 'cookie', 'private', 'api_key',
        'access_token', 'refresh_token', 'client_secret'
    }
    
    def __init__(self, enabled: bool = True):
        """Initialize the secret masker.
        
        Args:
            enabled: Whether masking is enabled. If False, no masking is performed.
        """
        self.enabled = enabled
        
    @classmethod
    def from_feature_flags(cls) -> 'SecretMasker':
        """Create a SecretMasker instance configured from feature flags.
        
        Returns:
            SecretMasker instance with enabled state from feature flags
        """
        try:
            enabled = FeatureFlags.is_enabled("security.secret_masking_enabled")
        except Exception:
            # Default to enabled if feature flags are not available
            enabled = True
        return cls(enabled=enabled)
    
    def mask_text(self, text: str) -> str:
        """Mask sensitive patterns in text.
        
        Args:
            text: Text to scan and mask
            
        Returns:
            Text with sensitive patterns masked
        """
        if not self.enabled or not isinstance(text, str):
            return text
            
        masked_text = text
        for pattern in self.PATTERNS:
            masked_text = pattern.pattern.sub(pattern.replacement, masked_text)
        
        return masked_text
    
    def _is_sensitive_key(self, key: str) -> bool:
        """Check if a key name indicates sensitive data.
        
        Args:
            key: Key name to check
            
        Returns:
            True if key is considered sensitive
        """
        key_lower = key.lower()
        return any(sensitive in key_lower for sensitive in self.SENSITIVE_KEYS)
    
    def mask_data(self, data: Any) -> Any:
        """Recursively mask sensitive data in data structures.
        
        Args:
            data: Data to scan and mask (dict, list, str, or other)
            
        Returns:
            Data with sensitive information masked
        """
        if not self.enabled:
            return data
            
        if isinstance(data, dict):
            return {
                k: "***MASKED***" if self._is_sensitive_key(k) else self.mask_data(v)
                for k, v in data.items()
            }
        elif isinstance(data, list):
            return [self.mask_data(item) for item in data]
        elif isinstance(data, str):
            return self.mask_text(data)
        else:
            return data
    
    def mask_log_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive information in a log record.
        
        This is the main entry point for log record masking.
        Designed to be used as a logging pipeline hook.
        
        Args:
            record: Log record dictionary to mask
            
        Returns:
            Log record with sensitive information masked
        """
        if not self.enabled:
            return record
            
        start_time = time.time()
        
        # Create a copy to avoid mutating the original
        masked_record = record.copy()
        
        # Mask the main message
        if 'msg' in masked_record:
            masked_record['msg'] = self.mask_text(masked_record['msg'])
        
        # Mask any extra fields
        for key, value in list(masked_record.items()):
            if key not in {'ts', 'seq', 'level', 'component', 'run_id'}:
                if self._is_sensitive_key(key):
                    masked_record[key] = "***MASKED***"
                else:
                    masked_record[key] = self.mask_data(value)
        
        # Track performance (should be <5ms)
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        if processing_time > 5.0:  # Performance requirement: <5ms
            # Log warning about performance but don't break the logging
            masked_record.setdefault('warnings', []).append(
                f"secret_masking_slow: {processing_time:.2f}ms"
            )
        
        return masked_record


def create_masking_hook() -> callable:
    """Create a logging hook for secret masking.
    
    Returns:
        Callable hook function suitable for JsonlLogger.register_hook()
    """
    masker = SecretMasker.from_feature_flags()
    
    def masking_hook(record: Dict[str, Any]) -> Dict[str, Any]:
        """Hook function that masks sensitive information in log records."""
        return masker.mask_log_record(record)
    
    return masking_hook


__all__ = ['SecretMasker', 'SecretPattern', 'create_masking_hook']