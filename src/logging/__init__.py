"""Logging module for bykilt.

Provides unified logging interface with category-based logger acquisition.
"""

from .jsonl_logger import JsonlLogger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .jsonl_logger import JsonlLogger as LoggerType


def get_logger(category: str) -> "LoggerType":
    """Get a logger for the specified category.

    Args:
        category: Logger category (runner, artifacts, browser, config, metrics, security, system)

    Returns:
        JsonlLogger instance for the category

    Example:
        >>> logger = get_logger("runner")
        >>> logger.info("Application started", run_id="12345")
    """
    return JsonlLogger.get(category)


__all__ = ["get_logger"]