# Batch processing module
"""
CSV-driven batch execution engine for 2bykilt.

This module provides functionality to execute multiple browser automation
tasks based on CSV input files, with job tracking and manifest management.
"""

__version__ = "0.1.0"

from .engine import BatchEngine, start_batch
from .summary import BatchSummary, BatchSummaryGenerator, generate_batch_summary
from .exceptions import (
    BatchEngineError,
    ConfigurationError,
    FileProcessingError,
    SecurityError,
)
from .models import (
    BatchJob,
    BatchManifest,
    BATCH_MANIFEST_FILENAME,
    JOBS_DIRNAME,
)

__all__ = [
    "BatchEngine",
    "BatchManifest", 
    "BatchJob",
    "BatchSummary",
    "BatchSummaryGenerator",
    "start_batch",
    "generate_batch_summary",
    "BatchEngineError",
    "ConfigurationError",
    "FileProcessingError",
    "SecurityError",
    "BATCH_MANIFEST_FILENAME",
    "JOBS_DIRNAME",
]
