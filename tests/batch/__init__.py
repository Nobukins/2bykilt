"""
Common fixtures and utilities for batch engine tests.

This module provides shared test fixtures and helper functions used across
all batch engine test modules.
"""

import asyncio
import logging
import tempfile
import threading
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest
from _pytest.outcomes import OutcomeException

from src.batch.engine import (
    BatchEngine,
    BatchJob,
    BatchManifest,
    start_batch,
    ConfigurationError,
    FileProcessingError,
    SecurityError,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_DELAY,
    DEFAULT_BACKOFF_FACTOR,
    MAX_RETRY_DELAY,
)
from src.runtime.run_context import RunContext


def _run_async(coro_fn):
    """
    Run async coroutine in a separate thread for testing.
    
    This helper function executes an async coroutine function in a new thread
    to avoid event loop conflicts in pytest.
    
    Args:
        coro_fn: Async coroutine function to execute
        
    Returns:
        The return value of the coroutine
        
    Raises:
        Any exception raised by the coroutine
    """
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:
            result["error"] = exc

    thread = threading.Thread(target=worker, name="test-batch-engine", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


# ============================================================================
# Common Fixtures
# ============================================================================

@pytest.fixture
def temp_dir():
    """
    Create temporary directory for tests.
    
    Yields:
        Path: Temporary directory path that is automatically cleaned up
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def run_context(temp_dir):
    """
    Create mock run context for batch engine tests.
    
    Args:
        temp_dir: Temporary directory fixture
        
    Returns:
        Mock: Mocked RunContext with artifact_dir method
    """
    context = Mock(spec=RunContext)
    context.run_id_base = "test_run_123"
    
    def artifact_dir_mock(component):
        """Create artifact directory for given component."""
        path = temp_dir / f"{context.run_id_base}-{component}"
        path.mkdir(parents=True, exist_ok=True)
        return path
    
    context.artifact_dir = artifact_dir_mock
    return context


@pytest.fixture
def engine(run_context):
    """
    Create BatchEngine instance with mocked run context.
    
    Args:
        run_context: Mocked RunContext fixture
        
    Returns:
        BatchEngine: Configured batch engine instance
    """
    return BatchEngine(run_context)


@pytest.fixture
def log_capture():
    """
    Capture log output for testing.
    
    This fixture captures log messages from the batch engine for assertion
    in tests. Automatically cleans up after the test.
    
    Yields:
        StringIO: Stream containing captured log messages
    """
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    # Get the logger used by BatchEngine
    logger = logging.getLogger('src.batch.engine')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield log_stream
    
    # Clean up
    logger.removeHandler(handler)


# ============================================================================
# Re-exports for convenience
# ============================================================================

__all__ = [
    # Helper functions
    "_run_async",
    
    # Fixtures
    "temp_dir",
    "run_context",
    "engine",
    "log_capture",
    
    # Re-exported classes from batch.engine
    "BatchEngine",
    "BatchJob",
    "BatchManifest",
    "start_batch",
    "ConfigurationError",
    "FileProcessingError",
    "SecurityError",
    "DEFAULT_MAX_RETRIES",
    "DEFAULT_RETRY_DELAY",
    "DEFAULT_BACKOFF_FACTOR",
    "MAX_RETRY_DELAY",
    "RunContext",
]
