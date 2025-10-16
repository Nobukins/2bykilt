"""
Batch engine exception classes.

This module defines all custom exceptions used by the batch processing system.
These exceptions provide specific error handling for different failure scenarios.
"""


class BatchEngineError(Exception):
    """Base exception for BatchEngine errors."""
    pass


class ConfigurationError(BatchEngineError):
    """Raised when configuration is invalid."""
    pass


class FileProcessingError(BatchEngineError):
    """
    Raised when file processing fails.

    This exception covers errors such as:
    - CSV parsing errors (malformed rows, missing headers, etc.)
    - File encoding issues (unsupported or invalid encoding)
    - File size limits exceeded
    - File not found or inaccessible
    - Unsupported file format or MIME type
    - Permission errors when reading files
    - Any other errors encountered during file reading or processing

    Catch this exception when handling file input/output operations in the batch engine.
    """
    pass


class SecurityError(BatchEngineError):
    """Raised when security violations are detected."""
    pass
