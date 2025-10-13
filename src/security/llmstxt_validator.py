"""llms.txt Security Validator (Issue #320 Phase 2)

Security validation layer for llms.txt auto-import feature.

Design goals:
  * HTTPS enforcement with optional HTTP fallback (aligned with LlmsTxtSource)
  * Domain whitelist support (optional, configurable)
  * Command injection pattern detection
  * Path traversal prevention
  * YAML content safety validation
  * Fail-fast security validation with detailed error messages

Security checks:
  1. URL Security: HTTPS enforcement, domain whitelist
  2. Content Security: Command injection patterns, path traversal
  3. Action Safety: Validates action commands and parameters for malicious patterns

Public API:
  SecurityValidator(https_only=True, allowed_domains=None)
    .validate_source_url(url: str) -> ValidationResult
    .validate_action_safety(action: dict) -> ValidationResult
    .validate_yaml_content(yaml_text: str) -> ValidationResult

Integration with Phase 1:
  - Works with LlmsTxtSource discovery results
  - Pre-merge validation before LlmsTxtMerger operations
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from src.utils.app_logger import logger


class SecurityValidationError(Exception):
    """Raised when security validation fails."""


@dataclass(slots=True)
class ValidationResult:
    """Result of security validation."""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add an error message."""
        self.valid = False
        self.errors.append(message)
        logger.error(f"Security validation error: {message}")

    def add_warning(self, message: str) -> None:
        """Add a warning message."""
        self.warnings.append(message)
        logger.warning(f"Security validation warning: {message}")


class SecurityValidator:
    """Security validator for llms.txt import operations."""

    # Command injection patterns (common shell metacharacters and command chains)
    INJECTION_PATTERNS = [
        r'[;&|`$]',  # Shell metacharacters
        r'\$\(',  # Command substitution
        r'\.\.',  # Path traversal
        r'~/',  # Home directory expansion
        r'>\s*/',  # Redirect to absolute path
        r'<\s*/',  # Read from absolute path
    ]

    # Dangerous command patterns
    DANGEROUS_COMMANDS = [
        r'\brm\s+-rf\b',
        r'\bsudo\b',
        r'\bsu\b',
        r'\bchmod\b',
        r'\bchown\b',
        r'\bcurl\s+.*\|\s*bash\b',
        r'\bwget\s+.*\|\s*bash\b',
        r'\beval\b',
        r'\bexec\b',
    ]

    def __init__(
        self,
        https_only: bool = True,
        allowed_domains: Optional[List[str]] = None,
    ):
        """Initialize security validator.

        Args:
            https_only: If True, only HTTPS URLs are allowed (default: True)
            allowed_domains: Optional list of allowed domain names (e.g., ["example.com", "github.com"])
                           If None, all domains are allowed (after HTTPS check)
        """
        self.https_only = https_only
        self.allowed_domains = allowed_domains or []
        self._compiled_injection_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.INJECTION_PATTERNS
        ]
        self._compiled_dangerous_commands = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.DANGEROUS_COMMANDS
        ]
        logger.info(
            f"SecurityValidator initialized: https_only={https_only}, "
            f"allowed_domains={allowed_domains or 'all'}"
        )

    def validate_source_url(self, url: str) -> ValidationResult:
        """Validate source URL for security.

        Args:
            url: URL to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(valid=True)

        if not url or not isinstance(url, str):
            result.add_error("URL must be a non-empty string")
            return result

        try:
            parsed = urlparse(url)
        except Exception as e:
            result.add_error(f"Invalid URL format: {e}")
            return result

        # Check scheme
        if not parsed.scheme:
            result.add_error("URL must include a scheme (http:// or https://)")
            return result

        if self.https_only and parsed.scheme != 'https':
            result.add_error(f"Only HTTPS URLs are allowed, got: {parsed.scheme}://")
            return result

        if parsed.scheme not in ('http', 'https'):
            result.add_error(f"Unsupported URL scheme: {parsed.scheme}")
            return result

        # Check domain whitelist
        if self.allowed_domains:
            domain = parsed.netloc.lower()
            # Remove port if present
            domain = domain.split(':')[0]
            
            if not any(domain == allowed or domain.endswith(f'.{allowed}') 
                      for allowed in self.allowed_domains):
                result.add_error(
                    f"Domain '{domain}' is not in allowed domains list: {self.allowed_domains}"
                )
                return result

        # Check for suspicious patterns in URL
        if '..' in url:
            result.add_error("Path traversal detected in URL")
            return result

        logger.debug(f"URL validation passed: {url}")
        return result

    def validate_action_safety(self, action: Dict[str, Any]) -> ValidationResult:
        """Validate action for security issues.

        Args:
            action: Action dictionary to validate

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(valid=True)

        if not isinstance(action, dict):
            result.add_error("Action must be a dictionary")
            return result

        action_name = action.get('name', '<unnamed>')
        action_type = action.get('type', '<unknown>')

        # Validate script commands
        if action_type == 'script':
            command = action.get('command', '')
            script_content = action.get('script', '')
            
            if command:
                self._check_command_safety(command, f"action '{action_name}' command", result)
            if script_content:
                self._check_command_safety(script_content, f"action '{action_name}' script", result)

        # Validate git-script paths
        if action_type == 'git-script':
            script_path = action.get('script_path', '')
            if script_path:
                self._check_path_safety(script_path, f"action '{action_name}' script_path", result)

        # Validate flow steps
        flow = action.get('flow', [])
        if isinstance(flow, list):
            for idx, step in enumerate(flow):
                if isinstance(step, dict):
                    # Check for command injection in step parameters
                    # Flow steps should be treated more strictly as they can affect browser behavior
                    for key, value in step.items():
                        if isinstance(value, str):
                            # Check for injection patterns with ERROR (not warning) for flow steps
                            for pattern in self._compiled_injection_patterns:
                                if pattern.search(value):
                                    result.add_error(
                                        f"Injection pattern detected in action '{action_name}' "
                                        f"flow[{idx}].{key}: {pattern.pattern}"
                                    )

        # Validate params
        params = action.get('params', [])
        if isinstance(params, list):
            for idx, param in enumerate(params):
                if isinstance(param, dict):
                    default = param.get('default', '')
                    if isinstance(default, str):
                        self._check_string_safety(
                            default,
                            f"action '{action_name}' params[{idx}].default",
                            result
                        )

        if result.valid:
            logger.debug(f"Action safety validation passed: {action_name}")

        return result

    def validate_yaml_content(self, yaml_text: str) -> ValidationResult:
        """Validate YAML content for security issues.

        Args:
            yaml_text: YAML content as string

        Returns:
            ValidationResult with validation status and any errors/warnings
        """
        result = ValidationResult(valid=True)

        if not isinstance(yaml_text, str):
            result.add_error("YAML content must be a string")
            return result

        # Check for YAML bombs (excessive nesting or anchors)
        if yaml_text.count('&') > 10 or yaml_text.count('*') > 10:
            result.add_warning("Excessive YAML anchors/aliases detected (possible YAML bomb)")

        # Check for suspicious patterns in raw YAML
        suspicious_patterns = [
            (r'!!python/', "Python object deserialization detected (unsafe)"),
            (r'!!map', "Explicit YAML map type hint (potentially unsafe)"),
        ]

        for pattern, message in suspicious_patterns:
            if re.search(pattern, yaml_text, re.IGNORECASE):
                result.add_error(message)

        if result.valid:
            logger.debug("YAML content safety validation passed")

        return result

    def _check_command_safety(self, command: str, context: str, result: ValidationResult) -> None:
        """Check command string for injection patterns.

        Args:
            command: Command string to check
            context: Context description for error messages
            result: ValidationResult to update with errors
        """
        # Check for dangerous commands
        for pattern in self._compiled_dangerous_commands:
            if pattern.search(command):
                result.add_error(
                    f"Dangerous command detected in {context}: {pattern.pattern}"
                )

        # Check for injection patterns
        for pattern in self._compiled_injection_patterns:
            if pattern.search(command):
                result.add_error(
                    f"Command injection pattern detected in {context}: {pattern.pattern}"
                )

    def _check_path_safety(self, path: str, context: str, result: ValidationResult) -> None:
        """Check path string for traversal attempts.

        Args:
            path: Path string to check
            context: Context description for error messages
            result: ValidationResult to update with errors
        """
        if '..' in path:
            result.add_error(f"Path traversal detected in {context}")

        if path.startswith('/'):
            result.add_warning(f"Absolute path detected in {context}: {path}")

        if path.startswith('~'):
            result.add_warning(f"Home directory expansion in {context}: {path}")

    def _check_string_safety(self, value: str, context: str, result: ValidationResult) -> None:
        """Check arbitrary string value for security issues.

        Args:
            value: String value to check
            context: Context description for error messages
            result: ValidationResult to update with errors
        """
        # Check for basic injection patterns
        for pattern in self._compiled_injection_patterns:
            if pattern.search(value):
                result.add_warning(
                    f"Potential injection pattern in {context}: {pattern.pattern}"
                )


def validate_remote_llmstxt(
    url: str,
    actions: List[Dict[str, Any]],
    yaml_content: str,
    *,
    https_only: bool = True,
    allowed_domains: Optional[List[str]] = None,
) -> ValidationResult:
    """Convenience function to validate all aspects of remote llms.txt import.

    Args:
        url: Source URL
        actions: List of parsed actions
        yaml_content: Raw YAML content
        https_only: If True, only HTTPS URLs are allowed
        allowed_domains: Optional list of allowed domains

    Returns:
        Combined ValidationResult with all validation checks
    """
    validator = SecurityValidator(https_only=https_only, allowed_domains=allowed_domains)
    
    # Validate URL
    url_result = validator.validate_source_url(url)
    if not url_result.valid:
        return url_result

    # Validate YAML content
    yaml_result = validator.validate_yaml_content(yaml_content)
    if not yaml_result.valid:
        return yaml_result

    # Validate each action
    combined_result = ValidationResult(valid=True)
    combined_result.warnings.extend(url_result.warnings)
    combined_result.warnings.extend(yaml_result.warnings)

    for action in actions:
        action_result = validator.validate_action_safety(action)
        if not action_result.valid:
            combined_result.valid = False
            combined_result.errors.extend(action_result.errors)
        combined_result.warnings.extend(action_result.warnings)

    if combined_result.valid:
        logger.info(f"Remote llms.txt validation passed: {url} ({len(actions)} actions)")
    else:
        logger.error(
            f"Remote llms.txt validation failed: {url} "
            f"({len(combined_result.errors)} errors, {len(combined_result.warnings)} warnings)"
        )

    return combined_result


__all__ = [
    "SecurityValidator",
    "SecurityValidationError",
    "ValidationResult",
    "validate_remote_llmstxt",
]
