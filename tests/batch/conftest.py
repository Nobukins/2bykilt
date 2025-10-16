"""
Pytest configuration and fixtures for batch engine tests.

This file makes fixtures available to all test modules in the tests/batch directory.
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

from src.batch.engine import BatchEngine
from src.runtime.run_context import RunContext


@pytest.fixture
def temp_dir():
    """Create temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def run_context(temp_dir):
    """Create mock run context."""
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
    """Create BatchEngine instance."""
    return BatchEngine(run_context)


@pytest.fixture
def log_capture():
    """Capture log output for testing."""
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
