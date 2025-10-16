"""
CSV-driven batch execution engine core.

This module provides the core functionality for processing CSV files
and generating batch jobs for browser automation tasks.
"""

import csv
import json
import logging
import uuid
import os
import mimetypes
import time
import random
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Iterator, Callable, Awaitable
from typing import TYPE_CHECKING
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager

from ..core.artifact_manager import ArtifactManager, get_artifact_manager
from ..runtime.run_context import RunContext
from src.utils.fs_paths import get_artifacts_base_dir

from .summary import BatchSummary
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
from .utils import to_portable_relpath

if TYPE_CHECKING:
    from ..extraction.models import ExtractionResult

logger = logging.getLogger(__name__)

# Type aliases for better type hints
ConfigType = Dict[str, Union[str, int, float, bool]]

# Constants for job execution simulation
DEFAULT_SUCCESS_RATE = 0.7  # 70% success rate for simulation
MAX_RANDOM_DELAY = 0.1  # Maximum random delay in seconds for simulation

# Constants for retry mechanism
DEFAULT_MAX_RETRIES = 3  # Default maximum number of retry attempts
DEFAULT_RETRY_DELAY = 1.0  # Default initial delay between retries in seconds
DEFAULT_BACKOFF_FACTOR = 2.0  # Default exponential backoff multiplier
MAX_RETRY_DELAY = 60.0  # Maximum retry delay in seconds (cap for exponential backoff)


class BatchEngine:
    """
    Core engine for CSV-driven batch execution.

    This engine processes CSV files and generates individual jobs for browser automation tasks.
    It provides configurable parsing options, security features, and comprehensive error handling.

    Features:
    - Configurable CSV parsing with automatic delimiter detection
    - Security controls including path traversal prevention
    - Memory-efficient processing for large files
    - Comprehensive error handling and logging
    - Flexible configuration options

    Example:
        ```python
        from src.batch.engine import BatchEngine, start_batch
        from src.runtime.run_context import RunContext

        # Create engine with custom config
        config = {
            'max_file_size_mb': 100,
            'encoding': 'utf-8',
            'allow_path_traversal': False
        }

        # Start batch processing
        manifest = start_batch('data.csv', config=config)
        ```
    """

    def __init__(self, run_context: RunContext, config: Optional[ConfigType] = None):
        self.run_context = run_context
        self.logger = logging.getLogger(f"{__name__}.BatchEngine")

        # Default configuration with validation
        self.config = {
            'max_file_size_mb': 500,  # Maximum file size to process (MB)
            'chunk_size': 1000,      # Rows to process at once for memory efficiency
            'encoding': 'utf-8',     # Default file encoding
            'delimiter_fallback': ',', # Fallback delimiter if detection fails
            'allow_path_traversal': True, # Security setting (default: allow for compatibility)
            'validate_headers': True, # Validate CSV headers exist
            'skip_empty_rows': True, # Skip empty rows automatically
            'log_level': 'INFO',     # Logging level (DEBUG, INFO, WARNING, ERROR)
        }

        # Load configuration from environment variables first
        env_config = self._load_config_from_env()
        self.config.update(env_config)

        # Update with user configuration (overrides environment variables)
        if config:
            self.config.update(config)

        # Validate configuration values
        self._validate_config()

        # Configure logging level
        self._configure_logging()

    def _validate_file_type(self, csv_path: str):
        """
        Validate that the file is a CSV file based on extension and MIME type.

        Args:
            csv_path: Path to the file to validate

        Raises:
            FileProcessingError: If file type validation fails
        """
        csv_path_obj = Path(csv_path)

        # Check file extension
        if csv_path_obj.suffix.lower() not in ['.csv', '.txt']:
            self.logger.warning(f"File '{csv_path}' does not have a typical CSV extension (.csv, .txt). "
                              f"Extension: {csv_path_obj.suffix}")

        # Check MIME type if possible
        try:
            mime_type, _ = mimetypes.guess_type(str(csv_path_obj))
            if mime_type and not (mime_type.startswith('text/') or mime_type in ['application/csv', 'application/vnd.ms-excel']):
                self.logger.warning(f"File '{csv_path}' has unexpected MIME type: {mime_type}. "
                                  f"Expected text/* or CSV-related MIME types.")
        except Exception as e:
            # MIME type detection might fail, log but don't fail
            self.logger.debug(f"Could not determine MIME type for {csv_path}: {e}")

    def _configure_logging(self):
        """Configure logging level based on configuration."""
        log_level = getattr(logging, self.config['log_level'], logging.INFO)
        self.logger.setLevel(log_level)

        # Also configure the module-level logger if needed
        module_logger = logging.getLogger(__name__)
        module_logger.setLevel(log_level)

    def _load_config_from_env(self) -> Dict[str, Any]:
        """
        Load configuration values from environment variables.

        Returns:
            Dictionary of configuration values from environment variables
        """
        env_config = {}

        # Mapping of environment variables to config keys
        env_mapping = {
            'BATCH_MAX_FILE_SIZE_MB': ('max_file_size_mb', float),
            'BATCH_CHUNK_SIZE': ('chunk_size', int),
            'BATCH_ENCODING': ('encoding', str),
            'BATCH_DELIMITER_FALLBACK': ('delimiter_fallback', str),
            'BATCH_ALLOW_PATH_TRAVERSAL': ('allow_path_traversal', lambda x: x.lower() in ('true', '1', 'yes')),
            'BATCH_VALIDATE_HEADERS': ('validate_headers', lambda x: x.lower() in ('true', '1', 'yes')),
            'BATCH_SKIP_EMPTY_ROWS': ('skip_empty_rows', lambda x: x.lower() in ('true', '1', 'yes')),
            'BATCH_LOG_LEVEL': ('log_level', str),
        }

        for env_var, (config_key, converter) in env_mapping.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                try:
                    env_config[config_key] = converter(env_value)
                    self.logger.debug(f"Loaded {config_key} from environment: {env_config[config_key]}")
                except (ValueError, TypeError) as e:
                    self.logger.warning(f"Invalid value for {env_var}: {env_value}. Using default value. Error: {e}")

        return env_config

    def _validate_config(self):
        """
        Validate configuration values to ensure they are within acceptable ranges.

        Raises:
            ConfigurationError: If any configuration value is invalid
        """
        try:
            # Validate max_file_size_mb
            max_size = self.config['max_file_size_mb']
            if not isinstance(max_size, (int, float)) or max_size <= 0:
                raise ConfigurationError(f"max_file_size_mb must be a positive number, got: {max_size}")
            if max_size > 10000:  # Reasonable upper limit
                raise ConfigurationError(f"max_file_size_mb too large: {max_size}MB. Maximum allowed: 10000MB")

            # Validate chunk_size
            chunk_size = self.config['chunk_size']
            if not isinstance(chunk_size, int) or chunk_size <= 0:
                raise ConfigurationError(f"chunk_size must be a positive integer, got: {chunk_size}")
            if chunk_size > 100000:  # Reasonable upper limit
                raise ConfigurationError(f"chunk_size too large: {chunk_size}. Maximum allowed: 100000")

            # Validate encoding
            encoding = self.config['encoding']
            if not isinstance(encoding, str) or not encoding.strip():
                raise ConfigurationError(f"encoding must be a non-empty string, got: {encoding}")

            # Validate delimiter_fallback
            delimiter = self.config['delimiter_fallback']
            if not isinstance(delimiter, str) or len(delimiter) != 1:
                raise ConfigurationError(f"delimiter_fallback must be a single character, got: {delimiter}")

            # Validate boolean settings
            for bool_key in ['allow_path_traversal', 'validate_headers', 'skip_empty_rows']:
                value = self.config[bool_key]
                if not isinstance(value, bool):
                    raise ConfigurationError(f"{bool_key} must be a boolean, got: {value} ({type(value).__name__})")

            # Validate log_level
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
            log_level = self.config['log_level'].upper()
            if log_level not in valid_log_levels:
                raise ConfigurationError(f"log_level must be one of {valid_log_levels}, got: {self.config['log_level']}")
            self.config['log_level'] = log_level  # Normalize to uppercase

        except KeyError as e:
            raise ConfigurationError(f"Missing required configuration key: {e}")
        except Exception as e:
            raise ConfigurationError(f"Configuration validation failed: {e}")

    def _check_security_for_path(self, csv_path_obj: Path, csv_path: str):
        """
        Perform security checks on file path to prevent unauthorized access.
        
        Args:
            csv_path_obj: Resolved Path object
            csv_path: Original path string for error messages
            
        Raises:
            SecurityError: If security check fails
        """
        # Security check: prevent path traversal (configurable)
        if self.config.get('allow_path_traversal', True) is False:
            if not csv_path_obj.is_relative_to(Path.cwd()):
                # Allow access to current working directory and subdirectories only
                cwd = Path.cwd().resolve()
                try:
                    csv_path_obj.relative_to(cwd)
                except ValueError:
                    self.logger.error(f"Access denied: '{csv_path}' is outside allowed directory. "
                                      f"Path traversal detected. To allow access to files outside the current "
                                      f"working directory, set 'allow_path_traversal' to True in configuration.")
                    raise SecurityError(f"Access denied: '{csv_path}' is outside allowed directory. "
                                      f"Path traversal detected. To allow access to files outside the current "
                                      f"working directory, set 'allow_path_traversal' to True in configuration.")

            # Additional security check: prevent access to sensitive system directories
            resolved_path = csv_path_obj.resolve()
            sensitive_paths = [
                Path('/etc'),
                Path('/usr'),
                Path('/bin'),
                Path('/sbin'),
                Path('/System'),  # macOS system directory
                Path('/Library/Preferences'),  # macOS preferences
                Path('/private/var'),  # macOS private directory
                Path('C:\\Windows'),  # Windows system directory
                Path('C:\\Program Files'),  # Windows program files
                Path('C:\\Users'),  # Windows user directories (if running as system)
            ]

            for sensitive_path in sensitive_paths:
                try:
                    if sensitive_path.exists() and resolved_path.is_relative_to(sensitive_path):
                        self.logger.error(
                            f"Access denied: '{csv_path}' points to a sensitive system directory. "
                            f"Resolved path: '{resolved_path}'. "
                            f"Sensitive directory: '{sensitive_path}'. "
                            f"This access is blocked for security reasons."
                        )
                        raise SecurityError(
                            f"Access denied: '{csv_path}' points to a sensitive system directory. "
                            f"Resolved path: '{resolved_path}'. "
                            f"Sensitive directory: '{sensitive_path}'. "
                            f"This access is blocked for security reasons."
                        )
                except (OSError, ValueError):
                    # Path might not exist on this system, continue checking
                    continue

    def _validate_csv_file_exists_and_size(self, csv_path_obj: Path, csv_path: str):
        """
        Validate CSV file existence and size.
        
        Args:
            csv_path_obj: Resolved Path object
            csv_path: Original path string for error messages
            
        Raises:
            FileNotFoundError: If file doesn't exist
            FileProcessingError: If file is empty or too large
        """
        if not csv_path_obj.exists():
            raise FileNotFoundError(f"CSV file not found: '{csv_path}'. Please verify the file path and ensure the file exists.")

        if csv_path_obj.stat().st_size == 0:
            raise FileProcessingError(f"CSV file is empty: '{csv_path}'. The file contains no data to process.")

        # Validate file type (extension and MIME type)
        self._validate_file_type(csv_path)

        # Check file size for memory considerations
        file_size_mb = csv_path_obj.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config['max_file_size_mb']:
            raise FileProcessingError(f"CSV file too large ({file_size_mb:.1f}MB). Maximum allowed: {self.config['max_file_size_mb']}MB. "
                                    f"Consider splitting the file or increasing 'max_file_size_mb' in configuration.")

        if file_size_mb > 100:  # Warn for files larger than 100MB
            self.logger.warning(f"Large CSV file detected ({file_size_mb:.1f}MB). Consider using streaming processing.")

    def _read_and_parse_csv_content(self, csv_path_obj: Path, csv_path: str, chunk_size: int) -> List[Dict[str, Any]]:
        """
        Read and parse CSV file content.
        
        Args:
            csv_path_obj: Resolved Path object
            csv_path: Original path string for error messages
            chunk_size: Number of rows to process at once
            
        Returns:
            List of dictionaries representing CSV rows
            
        Raises:
            FileProcessingError: If parsing fails
            UnicodeDecodeError: If encoding is invalid
        """
        try:
            with open(csv_path_obj, 'r', encoding=self.config['encoding']) as f:
                # Check if file has content
                content = f.read()
                if not content.strip():
                    raise FileProcessingError(f"CSV file contains no data: '{csv_path}'. The file is empty or contains only whitespace.")

                f.seek(0)

                # Detect delimiter and handle various CSV formats
                try:
                    sample = content[:1024] if len(content) > 1024 else content
                    sniffer = csv.Sniffer()
                    delimiter = sniffer.sniff(sample).delimiter
                except csv.Error:
                    # Fallback to configured delimiter if detection fails
                    delimiter = self.config['delimiter_fallback']
                    self.logger.warning(f"Could not detect delimiter for {csv_path}, using '{delimiter}'")

                reader = csv.DictReader(f, delimiter=delimiter)
                rows = []
                processed_rows = 0

                for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
                    # Skip empty rows if configured
                    if self.config['skip_empty_rows'] and not any(row.values()):
                        self.logger.debug(f"Skipping empty row {row_num} in {csv_path}")
                        continue

                    # Validate row has required fields (customize based on needs)
                    if not row:
                        self.logger.debug(f"Skipping invalid row {row_num} in {csv_path}")
                        continue

                    rows.append(row)
                    processed_rows += 1

                    # Process in chunks to avoid memory issues with very large files
                    # Use the provided chunk_size parameter, fallback to config if not provided
                    effective_chunk_size = chunk_size if chunk_size != 1000 else self.config['chunk_size']
                    if processed_rows % effective_chunk_size == 0:
                        self.logger.debug(f"Processed {processed_rows} rows from {csv_path}")

                if not rows:
                    raise FileProcessingError(f"No valid data rows found in CSV file: '{csv_path}'. "
                                            f"The file may contain only headers or all rows were filtered out.")

                self.logger.info(f"Successfully parsed {len(rows)} valid rows from {csv_path}")
                return rows

        except UnicodeDecodeError as e:
            raise FileProcessingError(f"Invalid file encoding in '{csv_path}'. Expected '{self.config['encoding']}' encoding. "
                                    f"Try saving the file with UTF-8 encoding or specify a different encoding in config. "
                                    f"Original error: {e}")
        except csv.Error as e:
            raise FileProcessingError(f"Invalid CSV format in '{csv_path}': {e}. "
                                    f"Please ensure the file is a valid CSV with proper formatting and consistent delimiters.")
        except Exception as e:
            raise FileProcessingError(f"Failed to parse CSV file '{csv_path}': {e}. "
                                    f"Please check the file format, encoding, and contents.")

    def parse_csv(self, csv_path: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Parse CSV file and return list of row dictionaries.

        This method handles various CSV formats, encoding issues, and provides
        memory-efficient processing for large files through chunked reading.

        Args:
            csv_path: Path to CSV file (absolute or relative)
            chunk_size: Number of rows to process at once (for memory efficiency). 
                       If not provided, uses the configured chunk_size value.

        Returns:
            List of dictionaries representing CSV rows, where keys are column headers

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            ValueError: If CSV parsing fails or file is invalid
            UnicodeDecodeError: If file encoding is invalid
            SecurityError: If path traversal is detected (when enabled)

        Example:
            ```python
            rows = engine.parse_csv('data.csv')
            for row in rows:
                print(f"Name: {row['name']}, Value: {row['value']}")
            ```
        """
        csv_path_obj = Path(csv_path).resolve()

        # Security check: prevent path traversal (configurable)
        self._check_security_for_path(csv_path_obj, csv_path)

        # Validate file existence and size
        self._validate_csv_file_exists_and_size(csv_path_obj, csv_path)

        # Read and parse CSV content
        return self._read_and_parse_csv_content(csv_path_obj, csv_path, chunk_size)

    def create_batch_jobs(self, csv_path: str) -> BatchManifest:
        """
        Create batch jobs from CSV file.

        Parses the CSV file and creates individual job files for each row.
        Generates a unique batch ID and creates a manifest file tracking all jobs.

        Args:
            csv_path: Path to CSV file to process

        Returns:
            BatchManifest containing all generated jobs and batch metadata

        Raises:
            ValueError: If CSV file has no valid rows or parsing fails
            FileNotFoundError: If CSV file doesn't exist

        Example:
            ```python
            manifest = engine.create_batch_jobs('customers.csv')
            print(f"Created batch {manifest.batch_id} with {manifest.total_jobs} jobs")
            ```
        """
        # Generate unique IDs
        batch_id = str(uuid.uuid4())
        run_id = self.run_context.run_id_base

        # Parse CSV
        rows = self.parse_csv(csv_path)

        if not rows:
            raise FileProcessingError(f"No valid rows found in CSV file: '{csv_path}'. "
                                    f"The file may be empty or contain only invalid data.")

        # Create jobs directory
        jobs_dir = self.run_context.artifact_dir("jobs")
        jobs_dir.mkdir(exist_ok=True)

        # Create individual job files
        jobs = []
        for i, row_data in enumerate(rows):
            job_id = f"{run_id}_{i+1:04d}"
            job = BatchJob(
                job_id=job_id,
                run_id=run_id,
                row_data=row_data,
                batch_id=batch_id,  # Set batch_id for metrics tracking
                row_index=i  # Set row index for robust field extraction
            )

            # Save individual job file
            job_file = jobs_dir / f"{job_id}.json"
            with open(job_file, 'w', encoding='utf-8') as f:
                json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)

            jobs.append(job)
            self.logger.info(f"Created job {job_id} for row {i+1}")

        # Create batch manifest
        manifest = BatchManifest(
            batch_id=batch_id,
            run_id=run_id,
            csv_path=csv_path,
            total_jobs=len(jobs),
            jobs=jobs
        )

        # Save manifest
        manifest_file = self.run_context.artifact_dir("batch") / BATCH_MANIFEST_FILENAME
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"Created batch with {len(jobs)} jobs (batch_id: {batch_id})")

        # Record batch creation metrics
        self._record_batch_creation_metrics(manifest)

        return manifest

    def _record_batch_creation_metrics(self, manifest: BatchManifest):
        """Record metrics for batch creation."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            # Record batch creation metric
            collector.record_metric(
                name="batch_created",
                value=1,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": manifest.batch_id,
                    "run_id": manifest.run_id,
                    "total_jobs": str(manifest.total_jobs)
                }
            )

            # Record batch size metric
            collector.record_metric(
                name="batch_size",
                value=manifest.total_jobs,
                metric_type=MetricType.GAUGE,
                tags={
                    "batch_id": manifest.batch_id,
                    "run_id": manifest.run_id
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record batch creation metrics: {e}")

    def get_batch_summary(self, batch_id: str) -> Optional['BatchSummary']:
        """
        Get batch summary for a batch execution.

        Args:
            batch_id: Batch identifier

        Returns:
            BatchSummary if found, None otherwise

        Note:
            The returned BatchSummary uses a hybrid data access pattern:
            - Summary statistics: Use attribute access (e.g., summary.completed_jobs)
            - Individual job details: Use dictionary access (e.g., summary.jobs[0]['status'])

        Example:
            ```python
            summary = engine.get_batch_summary("batch-123")
            if summary:
                print(f"Completed: {summary.completed_jobs}/{summary.total_jobs}")
                if summary.jobs:
                    print(f"First job status: {summary.jobs[0]['status']}")
            ```
        """
        try:
            from .summary import BatchSummaryGenerator

            manifest = self._load_manifest_by_batch_id(batch_id)
            
            if manifest is None:
                return None

            # Generate summary from manifest
            generator = BatchSummaryGenerator()
            return generator.generate_summary(manifest)

        except Exception as e:
            error_msg = f"Failed to get batch summary for {batch_id} - {type(e).__name__}: {e}"
            self.logger.error(error_msg)
            return None

    def _load_manifest_from_current_context(self, batch_id: str) -> Optional[BatchManifest]:
        """Load batch manifest from current run context."""
        manifest_file = self.run_context.artifact_dir("batch") / BATCH_MANIFEST_FILENAME
        if not manifest_file.exists():
            return None

        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                manifest = BatchManifest.from_dict(data)

                if manifest.batch_id == batch_id:
                    return manifest
        except Exception as e:
            self.logger.error(f"Failed to load batch manifest: {e}")

        return None

    def _search_batch_manifest_in_artifacts(self, batch_id: str) -> Optional[BatchManifest]:
        """Search for batch manifest in artifacts/runs directory."""
        artifacts_root = get_artifacts_base_dir() / "runs"

        if not artifacts_root.exists():
            return None

        candidates = []
        # Look for batch manifest files in all run directories
        for batch_dir in artifacts_root.glob("*-batch"):
            manifest_file = batch_dir / BATCH_MANIFEST_FILENAME
            if not manifest_file.exists():
                continue

            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    manifest = BatchManifest.from_dict(data)

                    if manifest.batch_id == batch_id:
                        candidates.append((manifest_file, manifest))

            except Exception as e:
                self.logger.error(f"Failed to load batch manifest {manifest_file}: {e}")

        if candidates:
            # Return the manifest with the most recent mtime
            candidates.sort(key=lambda x: x[0].stat().st_mtime, reverse=True)
            return candidates[0][1]

        return None

    def _load_manifest_by_batch_id(self, batch_id: str) -> Optional[BatchManifest]:
        """Load batch manifest by batch ID from current context or artifacts."""
        # First try to get manifest from current context
        manifest = self._load_manifest_from_current_context(batch_id)
        if manifest is None:
            # Search through all batch manifest files in artifacts/runs
            manifest = self._search_batch_manifest_in_artifacts(batch_id)
        
        return manifest

    def update_job_status(self, job_id: str, status: str, error_message: Optional[str] = None):
        """
        Update the status of a specific job.

        Args:
            job_id: Job identifier
            status: New status (completed, failed)
            error_message: Optional error message for failed jobs
        """
        # Find the manifest file containing this job
        manifest_file = self._find_manifest_file_for_job(job_id)

        if manifest_file is None:
            self.logger.warning(f"Batch manifest not found for job {job_id}")
            return

        try:
            # Load and update manifest
            manifest = self._load_manifest(manifest_file)
            if manifest is None:
                return

            job = self._find_job_by_id(manifest, job_id)
            if job is None:
                return

            self._update_single_job_status(job, status, error_message, manifest)
            self._save_manifest(manifest_file, manifest)

            # Generate summary if batch is complete
            if self._is_batch_complete(manifest):
                self._generate_batch_summary(manifest)

            # Record metrics for job completion
            self._record_job_metrics(job, status, error_message)

            self.logger.info(f"Updated job {job_id} status to {status}")

        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")

    # ------------------------------------------------------------------
    # Row-level Artifact Registration (Issue #175 PoC)
    # ------------------------------------------------------------------
    def add_row_artifact(self, job_id: str, artifact_type: str, content: Any,
                          extension: Optional[str] = None, meta: Optional[Dict[str, Any]] = None) -> Path:
        """Persist a row-level artifact and attach reference to the job entry in the batch manifest.

        Minimal PoC Goals (#175):
          * Provide per-row directory under artifacts/runs/<run_id>-batch/rows/<job_id>/
          * Allow arbitrary content types: bytes -> raw file, str -> text file, dict/list -> JSON file
          * Append manifest.jobs[*].artifacts list with portable relative path + metadata

        Args:
            job_id: Target job identifier
            artifact_type: Logical type label (e.g. 'screenshot', 'element_capture', 'log')
            content: bytes | str | dict | list content payload
            extension: Optional file extension override (e.g. 'png'); if None inferred
            meta: Optional metadata dict stored alongside reference

        Returns:
            Path to written artifact file

        Raises:
            ValueError: if job / manifest not found or invalid params
        """
        if not job_id or not isinstance(job_id, str):
            raise ValueError("job_id must be a non-empty string")
        if not artifact_type or not isinstance(artifact_type, str):
            raise ValueError("artifact_type must be a non-empty string")

        manifest_file = self._find_manifest_file_for_job(job_id)
        if manifest_file is None:
            raise ValueError(f"Batch manifest not found for job {job_id}")

        manifest = self._load_manifest(manifest_file)
        if manifest is None:
            raise ValueError("Failed to load batch manifest")

        job = self._find_job_by_id(manifest, job_id)
        if job is None:
            raise ValueError(f"Job not found: {job_id}")

        # Prepare row directory
        rows_root = self.run_context.artifact_dir("batch") / "rows" / job_id
        rows_root.mkdir(parents=True, exist_ok=True)

        # Determine file name & write content
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S%f")
        # Basic inference of extension
        if extension:
            ext = extension.lstrip('.')
        else:
            if isinstance(content, (dict, list)):
                ext = 'json'
            elif isinstance(content, (bytes, bytearray)):
                # Let caller specify for binary; default to bin
                ext = 'bin'
            else:
                ext = 'txt'

        fname = f"{artifact_type}_{ts}.{ext}"
        fpath = rows_root / fname

        try:
            if isinstance(content, (dict, list)):
                fpath.write_text(json.dumps(content, ensure_ascii=False, indent=2), encoding='utf-8')
            elif isinstance(content, (bytes, bytearray)):
                fpath.write_bytes(content)  # assume already encoded/binary
            else:  # treat as text
                fpath.write_text(str(content), encoding='utf-8')
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed writing artifact for job {job_id}: {e}") from e

        # Append artifact ref to job (in-memory) & persist manifest
        try:
            rel_path = to_portable_relpath(fpath)
        except Exception:
            rel_path = fpath.name

        artifact_entry = {
            "type": artifact_type,
            "path": rel_path,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        if meta:
            artifact_entry["meta"] = meta

        if job.artifacts is None:
            job.artifacts = []
        job.artifacts.append(artifact_entry)

        # Persist entire manifest update
        try:
            self._save_manifest(manifest_file, manifest)
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"Failed to persist manifest after adding row artifact: {e}") from e

        self.logger.info(
            f"Added row artifact for job {job_id}",
            extra={
                "event": "batch.row.artifact.added",
                "job_id": job_id,
                "artifact_type": artifact_type,
                "file": str(fpath),
            },
        )
        return fpath

    def _record_job_metrics(self, job: BatchJob, status: str, error_message: Optional[str] = None):
        """Record metrics for job execution."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            # Record job status metric
            collector.record_metric(
                name="job_status",
                value=1,
                metric_type=MetricType.COUNTER,
                tags={
                    "job_id": job.job_id,
                    "run_id": job.run_id,
                    "status": status,
                    "batch_id": job.batch_id or "unknown"
                }
            )

            # Record job duration if completed_at is available
            if job.completed_at and job.created_at:
                try:
                    from datetime import datetime, timezone
                    created_time = datetime.fromisoformat(job.created_at.replace('Z', '+00:00'))
                    completed_time = datetime.fromisoformat(job.completed_at.replace('Z', '+00:00'))
                    duration_seconds = (completed_time - created_time).total_seconds()

                    collector.record_metric(
                        name="job_duration_seconds",
                        value=duration_seconds,
                        metric_type=MetricType.HISTOGRAM,
                        tags={
                            "job_id": job.job_id,
                            "run_id": job.run_id,
                            "status": status,
                            "batch_id": job.batch_id or "unknown"
                        }
                    )
                except Exception as e:
                    self.logger.debug(f"Failed to calculate job duration: {e}")

            # Record error metrics if job failed
            if status == "failed" and error_message:
                collector.record_metric(
                    name="job_errors",
                    value=1,
                    metric_type=MetricType.COUNTER,
                    tags={
                        "job_id": job.job_id,
                        "run_id": job.run_id,
                        "error_type": "execution_error",
                        "batch_id": job.batch_id or "unknown"
                    }
                )

        except Exception as e:
            self.logger.debug(f"Failed to record job metrics: {e}")

    def _load_and_check_manifest(self, manifest_file: Path, job_id: str) -> bool:
        """Load manifest and check if it contains the specified job."""
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                manifest = BatchManifest.from_dict(data)
                return any(job.job_id == job_id for job in manifest.jobs)
        except Exception as e:
            self.logger.error(f"Failed to load batch manifest {manifest_file}: {e}")
            return False

    def _find_manifest_file_for_job(self, job_id: str) -> Optional[Path]:
        """Find the manifest file that contains the specified job."""
        # First try the current run context
        manifest_file = self.run_context.artifact_dir("batch") / BATCH_MANIFEST_FILENAME
        if manifest_file.exists() and self._load_and_check_manifest(manifest_file, job_id):
            return manifest_file

        # Search through all batch manifest files in artifacts/runs
        artifacts_root = get_artifacts_base_dir() / "runs"

        if not artifacts_root.exists():
            return None

        # Look for batch manifest files in all run directories
        for batch_dir in artifacts_root.glob("*-batch"):
            manifest_file = batch_dir / BATCH_MANIFEST_FILENAME
            if manifest_file.exists() and self._load_and_check_manifest(manifest_file, job_id):
                return manifest_file

        return None

    def _update_single_job_status(self, job: BatchJob, status: str, error_message: Optional[str], manifest: BatchManifest):
        """Update a single job's status and related counters."""
        job.status = status
        if error_message:
            job.error_message = error_message

        if status in ['completed', 'failed']:
            job.completed_at = datetime.now(timezone.utc).isoformat()

            if status == 'completed':
                manifest.completed_jobs += 1
            elif status == 'failed':
                manifest.failed_jobs += 1

    def _load_manifest(self, manifest_file: Path) -> Optional[BatchManifest]:
        """Load batch manifest from file."""
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BatchManifest.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load batch manifest: {e}")
            return None

    def _save_manifest(self, manifest_file: Path, manifest: BatchManifest):
        """Save batch manifest to file."""
        try:
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.debug(f"Saved batch manifest to {manifest_file}")
        except Exception as e:
            self.logger.error(f"Failed to save batch manifest: {e}")
            raise

    def _find_job_by_id(self, manifest: BatchManifest, job_id: str) -> Optional[BatchJob]:
        """Find job by ID in manifest."""
        for job in manifest.jobs:
            if job.job_id == job_id:
                return job
        self.logger.warning(f"Job {job_id} not found in manifest")
        return None

    def _is_batch_complete(self, manifest: BatchManifest) -> bool:
        """Check if all jobs in the batch are complete."""
        return manifest.completed_jobs + manifest.failed_jobs == manifest.total_jobs

    def _generate_batch_summary(self, manifest: BatchManifest):
        """Generate and save batch summary when batch is complete."""
        try:
            from .summary import BatchSummaryGenerator

            generator = BatchSummaryGenerator()
            summary = generator.generate_summary(manifest)

            # Save summary to artifacts/runs/<run_id>/batch_summary.json
            summary_path = self.run_context.artifact_dir("batch") / "batch_summary.json"
            generator.save_summary(summary, summary_path)

            # Export failed rows to CSV if there are any failures
            if manifest.failed_jobs > 0:
                self._export_failed_rows(manifest)

            self.logger.info(f"Generated batch summary for {manifest.batch_id}")

        except Exception as e:
            self.logger.error(f"Failed to generate batch summary: {e}")

    def _export_failed_rows(self, manifest: BatchManifest):
        """Export failed job rows to CSV file."""
        try:
            failed_jobs = [job for job in manifest.jobs if job.status == 'failed']
            if not failed_jobs:
                return

            # Prepare CSV data
            csv_rows = []
            headers = None

            for job in failed_jobs:
                if headers is None:
                    # Use the first job's row_data keys as headers
                    headers = list(job.row_data.keys()) + ['error_message', 'job_id', 'failed_at']
                    csv_rows.append(headers)

                # Create row data
                row = list(job.row_data.values()) + [
                    job.error_message or '',
                    job.job_id,
                    job.completed_at or ''
                ]
                csv_rows.append(row)

            # Save to CSV
            failed_csv_path = self.run_context.artifact_dir("batch") / "failed_rows.csv"
            with open(failed_csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for row in csv_rows:
                    writer.writerow(row)

            self.logger.info(f"Exported {len(failed_jobs)} failed rows to {failed_csv_path}")

            # Record export metric
            self._record_failed_rows_export_metric(len(failed_jobs))

        except Exception as e:
            self.logger.error(f"Failed to export failed rows: {e}")

    def _record_failed_rows_export_metric(self, failed_count: int):
        """Record metrics for failed rows export."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            collector.record_metric(
                name="failed_rows_exported",
                value=failed_count,
                metric_type=MetricType.COUNTER,
                tags={
                    "run_id": self.run_context.run_id_base
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record failed rows export metrics: {e}")

    def _validate_retry_parameters(self, max_retries: int, retry_delay: float,
                                  backoff_factor: float, max_retry_delay: Optional[float]) -> float:
        """
        Validate retry-related parameters and return the effective max_retry_delay.

        Args:
            max_retries: Maximum number of retry attempts
            retry_delay: Initial delay between retries in seconds
            backoff_factor: Exponential backoff multiplier
            max_retry_delay: Maximum retry delay in seconds (optional)

        Returns:
            Effective max_retry_delay value

        Raises:
            ValueError: If any parameter is invalid
        """
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")

        if retry_delay <= 0:
            raise ValueError("retry_delay must be > 0")

        if backoff_factor <= 1.0:
            raise ValueError("backoff_factor must be > 1.0")

        if max_retry_delay is not None and max_retry_delay <= 0:
            raise ValueError("max_retry_delay must be > 0")

        # Use default if not specified
        return max_retry_delay if max_retry_delay is not None else MAX_RETRY_DELAY

    def retry_batch_jobs(self, batch_id: str, job_ids: List[str], max_retries: int = DEFAULT_MAX_RETRIES,
                        retry_delay: float = DEFAULT_RETRY_DELAY, backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                        max_retry_delay: Optional[float] = None) -> Dict[str, Any]:
        """
        Prepare specific jobs in a batch for retry by resetting their status.

        This method resets failed jobs to 'pending' status, allowing them to be
        executed again. It does not execute the jobs immediately - it only prepares
        them for subsequent execution.

        Args:
            batch_id: Batch identifier (must be non-empty string)
            job_ids: List of job IDs to retry (must contain valid job IDs)
            max_retries: Maximum number of retry attempts per job (must be >= 0, default: DEFAULT_MAX_RETRIES)
            retry_delay: Initial delay between retries in seconds (must be > 0, default: DEFAULT_RETRY_DELAY)
            backoff_factor: Exponential backoff multiplier (must be > 1.0, default: DEFAULT_BACKOFF_FACTOR)
            max_retry_delay: Maximum retry delay in seconds (optional, defaults to MAX_RETRY_DELAY)

        Returns:
            Dictionary with retry results and statistics

        Raises:
            ValueError: If batch or jobs are not found, or input validation fails
        """
        # Input validation
        if not batch_id or not isinstance(batch_id, str):
            raise ValueError("batch_id must be a non-empty string")

        if not job_ids or not isinstance(job_ids, list):
            raise ValueError("job_ids must be a non-empty list")

        if not all(isinstance(job_id, str) and job_id for job_id in job_ids):
            raise ValueError("All job_ids must be non-empty strings")

        if len(job_ids) != len(set(job_ids)):
            raise ValueError("job_ids must not contain duplicates")

        # Validate retry parameters using common function
        max_retry_delay = self._validate_retry_parameters(
            max_retries, retry_delay, backoff_factor, max_retry_delay
        )

        try:
            # Load batch manifest
            manifest = self._load_manifest_by_batch_id(batch_id)

            if manifest is None:
                raise ValueError(f"Batch not found: {batch_id}")

            # Validate job IDs exist in the batch
            batch_job_ids = {job.job_id for job in manifest.jobs}
            invalid_job_ids = [job_id for job_id in job_ids if job_id not in batch_job_ids]
            if invalid_job_ids:
                raise ValueError(f"Jobs not found in batch {batch_id}: {invalid_job_ids}")

            # Filter jobs to retry (only failed jobs)
            jobs_to_retry = [
                job for job in manifest.jobs
                if job.job_id in job_ids and job.status == 'failed'
            ]

            if not jobs_to_retry:
                self.logger.info(f"No failed jobs to retry in batch {batch_id}")
                return {
                    'batch_id': batch_id,
                    'total_requested': len(job_ids),
                    'retried': 0,
                    'skipped': len(job_ids),
                    'reason': 'No failed jobs found'
                }

            # Reset job statuses for retry
            retry_results = []
            for job in jobs_to_retry:
                original_status = job.status
                original_error = job.error_message
                original_completed_at = job.completed_at

                # Reset job for retry
                job.status = 'pending'
                job.error_message = None
                job.completed_at = None

                # Update manifest counters
                if original_status == 'failed':
                    manifest.failed_jobs -= 1

                retry_results.append({
                    'job_id': job.job_id,
                    'original_status': original_status,
                    'original_error': original_error,
                    'reset_at': datetime.now(timezone.utc).isoformat()
                })

                self.logger.info(f"Reset job {job.job_id} for retry")

            # Save updated manifest
            manifest_file = self._find_manifest_file_for_batch(batch_id)
            if manifest_file:
                self._save_manifest(manifest_file, manifest)

            # Record retry metrics
            self._record_retry_metrics(batch_id, len(jobs_to_retry))

            result = {
                'batch_id': batch_id,
                'total_requested': len(job_ids),
                'retried': len(jobs_to_retry),
                'skipped': len(job_ids) - len(jobs_to_retry),
                'retry_details': retry_results,
                'max_retries': max_retries,
                'retry_delay': retry_delay,
                'backoff_factor': backoff_factor,
                'max_retry_delay': max_retry_delay
            }

            self.logger.info(f"Prepared {len(jobs_to_retry)} jobs for retry in batch {batch_id}")
            return result

        except Exception as e:
            error_msg = f"Failed to retry batch jobs for batch '{batch_id}': {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e

    def _find_manifest_file_for_batch(self, batch_id: str) -> Optional[Path]:
        """Find manifest file for a specific batch."""
        # First try current run context
        manifest_file = self.run_context.artifact_dir("batch") / BATCH_MANIFEST_FILENAME
        if manifest_file.exists():
            try:
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    manifest = BatchManifest.from_dict(data)
                    if manifest.batch_id == batch_id:
                        return manifest_file
            except Exception:
                pass

        # Search in artifacts/runs
        artifacts_root = get_artifacts_base_dir() / "runs"
        if not artifacts_root.exists():
            return None

        for batch_dir in artifacts_root.glob("*-batch"):
            manifest_file = batch_dir / BATCH_MANIFEST_FILENAME
            if manifest_file.exists():
                try:
                    with open(manifest_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        manifest = BatchManifest.from_dict(data)
                        if manifest.batch_id == batch_id:
                            return manifest_file
                except Exception:
                    continue

        return None

    def _record_retry_metrics(self, batch_id: str, retry_count: int) -> None:
        """Record metrics for batch retry operations."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            collector.record_metric(
                name="batch_retry_initiated",
                value=retry_count,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": batch_id,
                    "run_id": self.run_context.run_id_base
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record retry metrics: {e}")

    def _record_batch_stop_metrics(self, batch_id: str, stopped_count: int) -> None:
        """Record metrics for batch stop operations."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            collector.record_metric(
                name="batch_jobs_stopped",
                value=stopped_count,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": batch_id,
                    "run_id": self.run_context.run_id_base
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record batch stop metrics: {e}")

    # ------------------------------------------------------------------
    # Batch Stop (graceful) Support
    # ------------------------------------------------------------------
    def stop_batch(self, batch_id: str) -> Dict[str, Any]:
        """Gracefully stop a batch by marking pending / running jobs as 'stopped'.

        This does not delete artifacts; it only updates job statuses and manifest
        counters. Already completed / failed jobs remain unchanged.

        Args:
            batch_id: Target batch identifier.

        Returns:
            Dict with summary: {batch_id, stopped_jobs, unaffected_jobs, total_jobs}

        Raises:
            ValueError: If batch manifest cannot be found.
        """
        if not batch_id or not isinstance(batch_id, str):
            raise ValueError("batch_id must be a non-empty string")

        manifest = self._load_manifest_by_batch_id(batch_id)
        if manifest is None:
            raise ValueError(f"Batch not found: {batch_id}")

        stopped_count = 0
        unaffected = 0

        for job in manifest.jobs:
            if job.status in ("pending", "running"):
                job.status = "stopped"
                job.completed_at = datetime.now(timezone.utc).isoformat()
                stopped_count += 1
            else:
                unaffected += 1

        # Persist manifest update
        manifest_file = self._find_manifest_file_for_batch(batch_id)
        if manifest_file:
            try:
                self._save_manifest(manifest_file, manifest)
            except Exception as e:
                self.logger.error(f"Failed saving manifest while stopping batch {batch_id}: {e}")
                raise

        # Record metric
        self._record_batch_stop_metrics(batch_id, stopped_count)

        result = {
            "batch_id": batch_id,
            "stopped_jobs": stopped_count,
            "unaffected_jobs": unaffected,
            "total_jobs": len(manifest.jobs),
        }
        self.logger.info(
            f"Stopped batch {batch_id}: stopped={stopped_count} unaffected={unaffected} total={len(manifest.jobs)}"
        )
        return result

    def _record_batch_execution_metrics(self, batch_id: str, executed: int, completed: int, failed: int) -> None:
        """Record metrics for batch execution."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            # Record batch execution metrics
            collector.record_metric(
                name="batch_jobs_executed",
                value=executed,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": batch_id,
                    "run_id": self.run_context.run_id_base
                }
            )

            collector.record_metric(
                name="batch_jobs_completed",
                value=completed,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": batch_id,
                    "run_id": self.run_context.run_id_base
                }
            )

            collector.record_metric(
                name="batch_jobs_failed",
                value=failed,
                metric_type=MetricType.COUNTER,
                tags={
                    "batch_id": batch_id,
                    "run_id": self.run_context.run_id_base
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record batch execution metrics: {e}")

    async def execute_batch_jobs(self, batch_id: str, max_retries: int = DEFAULT_MAX_RETRIES,
                           retry_delay: float = DEFAULT_RETRY_DELAY, backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                           max_retry_delay: Optional[float] = None, progress_callback: Optional[Callable[[int, int], None]] = None) -> Dict[str, Any]:
        """
        Execute all pending jobs in a batch.

        This method finds all pending jobs in the specified batch and executes them
        using the browser automation system. Jobs are executed sequentially to avoid
        resource conflicts.

        Args:
            batch_id: Batch identifier to execute
            max_retries: Maximum number of retry attempts per job (default: DEFAULT_MAX_RETRIES)
            retry_delay: Initial delay between retries in seconds (default: DEFAULT_RETRY_DELAY)
            backoff_factor: Exponential backoff multiplier (default: DEFAULT_BACKOFF_FACTOR)
            max_retry_delay: Maximum retry delay in seconds (optional, defaults to MAX_RETRY_DELAY)
            progress_callback: Optional callback function called after each job completion.
                              Receives (completed_jobs: int, total_jobs: int) as arguments.
                              Useful for UI progress updates.

        Returns:
            Dictionary with execution results and statistics

        Raises:
            ValueError: If batch is not found or invalid parameters
        """
        # Input validation
        if not batch_id or not isinstance(batch_id, str):
            raise ValueError("batch_id must be a non-empty string")

        # Validate retry parameters
        max_retry_delay = self._validate_retry_parameters(
            max_retries, retry_delay, backoff_factor, max_retry_delay
        )

        try:
            # Load batch manifest
            manifest = self._load_manifest_by_batch_id(batch_id)
            if manifest is None:
                raise ValueError(f"Batch not found: {batch_id}")

            # Find pending jobs
            pending_jobs = [job for job in manifest.jobs if job.status == 'pending']
            if not pending_jobs:
                self.logger.info(f"No pending jobs found in batch {batch_id}")
                return {
                    'batch_id': batch_id,
                    'executed': 0,
                    'completed': 0,
                    'failed': 0,
                    'skipped': len(manifest.jobs),
                    'reason': 'No pending jobs found'
                }

            self.logger.info(f"Starting execution of {len(pending_jobs)} pending jobs in batch {batch_id}")

            # Execute jobs sequentially
            executed = 0
            completed = 0
            failed = 0
            job_results = []

            for job in pending_jobs:
                try:
                    # Update job status to running
                    job.status = 'running'
                    self._save_manifest(self._find_manifest_file_for_batch(batch_id), manifest)

                    # Execute job with retry
                    status = await self.execute_job_with_retry(
                        job, max_retries, retry_delay, backoff_factor, max_retry_delay
                    )

                    # Update job status
                    job.status = status
                    if status == 'completed':
                        completed += 1
                        manifest.completed_jobs += 1
                    elif status == 'failed':
                        failed += 1
                        manifest.failed_jobs += 1

                    executed += 1

                    job_results.append({
                        'job_id': job.job_id,
                        'status': status,
                        'error_message': job.error_message
                    })

                    self.logger.info(f"Job {job.job_id} finished with status: {status}")

                except Exception as e:
                    # Mark job as failed
                    job.status = 'failed'
                    job.error_message = str(e)
                    failed += 1
                    manifest.failed_jobs += 1
                    executed += 1

                    job_results.append({
                        'job_id': job.job_id,
                        'status': 'failed',
                        'error_message': str(e)
                    })

                    self.logger.error(f"Job {job.job_id} failed: {e}")

                # Save manifest after each job
                manifest_file_for_save = self._find_manifest_file_for_batch(batch_id)
                self._save_manifest(manifest_file_for_save, manifest)

                # Call progress callback if provided
                if progress_callback:
                    try:
                        progress_callback(manifest.completed_jobs, manifest.total_jobs)
                    except Exception as e:
                        # Best-effort; never fail job execution because of callback
                        self.logger.debug(f"Progress callback failed: {e}")

                # Emit a concise progress message after each job so CLI/UI can reflect
                # incremental progress (e.g., "Jobs: 1/4 completed"). This addresses
                # the issue where status stayed at 0/4 until the end of execution.
                try:
                    self.logger.info(f"Jobs: {manifest.completed_jobs}/{manifest.total_jobs} completed")
                except Exception:
                    # Best-effort; never fail job execution because of logging
                    self.logger.debug("Failed to emit progress message")

            # Generate batch summary if complete
            if self._is_batch_complete(manifest):
                self._generate_batch_summary(manifest)

            # Record batch execution metrics
            self._record_batch_execution_metrics(batch_id, executed, completed, failed)

            result = {
                'batch_id': batch_id,
                'executed': executed,
                'completed': completed,
                'failed': failed,
                'skipped': len(manifest.jobs) - executed,
                'total_jobs': len(manifest.jobs),
                'job_results': job_results,
                'max_retries': max_retries,
                'retry_delay': retry_delay,
                'backoff_factor': backoff_factor,
                'max_retry_delay': max_retry_delay
            }

            self.logger.info(f"Batch {batch_id} execution completed: {completed} completed, {failed} failed")
            return result

        except Exception as e:
            error_msg = f"Failed to execute batch jobs for batch '{batch_id}': {e}"
            self.logger.error(error_msg)
            raise ValueError(error_msg) from e

    async def execute_job_with_retry(self, job: BatchJob, max_retries: int = DEFAULT_MAX_RETRIES,
                              retry_delay: float = DEFAULT_RETRY_DELAY,
                              backoff_factor: float = DEFAULT_BACKOFF_FACTOR,
                              max_retry_delay: Optional[float] = None) -> str:
        """
        Execute a job with automatic retry on failure.

        Args:
            job: Job to execute (must be valid BatchJob instance)
            max_retries: Maximum number of retry attempts (must be >= 0, default: DEFAULT_MAX_RETRIES)
            retry_delay: Initial delay between retries in seconds (must be > 0, default: DEFAULT_RETRY_DELAY)
            backoff_factor: Exponential backoff multiplier (must be > 1.0, default: DEFAULT_BACKOFF_FACTOR)
            max_retry_delay: Maximum retry delay in seconds (optional, defaults to MAX_RETRY_DELAY)

        Returns:
            Final status of the job ('completed' or 'failed')
        """
        # Input validation
        if not isinstance(job, BatchJob):
            raise ValueError("job must be a BatchJob instance")

        if not job.job_id or not isinstance(job.job_id, str):
            raise ValueError("job.job_id must be a non-empty string")

        # Validate retry parameters using common function
        max_retry_delay = self._validate_retry_parameters(
            max_retries, retry_delay, backoff_factor, max_retry_delay
        )

        last_error: Optional[str] = None
        last_exception: Optional[Exception] = None
        current_delay = retry_delay

        for attempt in range(max_retries + 1):  # +1 for initial attempt
            try:
                self.logger.info(f"Executing job {job.job_id} (attempt {attempt + 1}/{max_retries + 1})")

                # Execute the job using the actual implementation
                status = await self._execute_single_job(job)

                if status == 'completed':
                    self.logger.info(f"Job {job.job_id} completed successfully on attempt {attempt + 1}")
                    return 'completed'
                else:
                    error_msg = f"Job execution returned unexpected status: {status}"
                    self.logger.warning(f"Job {job.job_id} returned status '{status}' on attempt {attempt + 1}")
                    raise ValueError(error_msg)

            except Exception as e:
                last_error = str(e)
                last_exception = e
                self.logger.warning(f"Job {job.job_id} failed on attempt {attempt + 1}: {type(e).__name__}")

                # Don't retry on the last attempt
                if attempt < max_retries:
                    self.logger.info(f"Retrying job {job.job_id} in {current_delay:.1f}s...")
                    time.sleep(current_delay)
                    # Exponential backoff with configurable parameters
                    current_delay = min(current_delay * backoff_factor, max_retry_delay)
                else:
                    self.logger.error(f"Job {job.job_id} failed after {max_retries + 1} attempts")

        # All attempts failed
        error_summary = f"Failed after {max_retries + 1} attempts"
        job.error_message = f"{error_summary}. Last error: {type(last_exception).__name__ if last_exception else 'Unknown'}"
        self.logger.error(f"Job {job.job_id} permanently failed: {error_summary}")

        # Re-raise the last exception to preserve the original error context
        if last_exception:
            raise last_exception
        else:
            raise RuntimeError(f"Job {job.job_id}: {error_summary}")

    async def _execute_single_job(self, job: BatchJob) -> str:
        """
        Execute a single job.

        This method integrates with the actual job execution logic.
        In the current implementation, it processes the job data and
        simulates job execution based on the data content.

        TODO: Replace simulation with actual job execution logic (e.g., browser automation)

        Args:
            job: Job to execute (must be valid BatchJob instance)

        Returns:
            Job status ('completed' or 'failed')

        Raises:
            ValueError: If job data is invalid
            RuntimeError: If job execution fails
        """
        # Input validation
        if not isinstance(job, BatchJob):
            raise ValueError("job must be a BatchJob instance")

        if not job.job_id or not isinstance(job.job_id, str):
            raise ValueError("job.job_id must be a non-empty string")

        try:
            # Validate job data
            if not job.row_data:
                raise ValueError(f"Job {job.job_id} has no row data")

            self.logger.debug(f"Processing job {job.job_id} with data keys: {list(job.row_data.keys()) if job.row_data else 'None'}")

            # Basic validation of required fields
            # In a real implementation, this would validate against your schema
            if not isinstance(job.row_data, dict):
                raise ValueError(f"Job {job.job_id} row_data must be a dictionary")

            # Simulate job execution based on data content
            # In real implementation, replace with actual browser automation or processing logic
            status = await self._simulate_job_execution(job)

            # Execute field extraction if schema is available and job succeeded
            if status == 'completed':
                self._execute_field_extraction(job)

            return status

        except Exception as e:
            error_msg = f"Job execution failed for {job.job_id}: {type(e).__name__}"
            self.logger.error(error_msg)
            raise RuntimeError(f"Job {job.job_id}: {type(e).__name__}") from e

    async def _simulate_job_execution(self, job: BatchJob, success_rate: Optional[float] = None,
                               max_random_delay: Optional[float] = None) -> str:
        """
        Execute actual browser automation for a job.

        This method replaces the simulation with real browser automation
        by executing commands from the job's row data.

        Args:
            job: Job to execute (must be valid BatchJob instance)
            success_rate: Ignored (kept for backward compatibility)
            max_random_delay: Ignored (kept for backward compatibility)

        Returns:
            Job status ('completed' or 'failed')
        """
        # Input validation
        if not isinstance(job, BatchJob):
            raise ValueError("job must be a BatchJob instance")

        if not job.row_data:
            raise ValueError(f"Job {job.job_id} has no row data")

        try:
            # Get task from row data
            task = job.row_data.get('task') or job.row_data.get('command')
            if not task:
                raise ValueError(f"Job {job.job_id} has no 'task' or 'command' field in row data")

            self.logger.info(f"Executing browser automation for job {job.job_id} with task: {task}")

            # Import required modules
            from src.config.standalone_prompt_evaluator import pre_evaluate_prompt_standalone

            # Evaluate the task as a command
            evaluation_result = pre_evaluate_prompt_standalone(task)
            if not evaluation_result or not evaluation_result.get('is_command'):
                raise ValueError(f"Task '{task}' is not a valid pre-registered command")

            # Get command details
            action_name = evaluation_result.get('command_name', '').lstrip('@')
            action_def = evaluation_result.get('action_def', {})
            action_params = evaluation_result.get('params', {})
            action_type = action_def.get('type', '')

            if not action_def:
                raise ValueError(f"Pre-registered command '{action_name}' not found")

            # Map CSV row data to action parameters based on param names
            for param_def in action_def.get('params', []):
                param_name = param_def.get('name')
                if param_name:
                    # Check for params.param_name first (new naming convention)
                    csv_param_key = f"params.{param_name}"
                    if csv_param_key in job.row_data:
                        action_params[param_name] = job.row_data[csv_param_key]
                    # Fallback to direct param_name for backward compatibility
                    elif param_name in job.row_data:
                        action_params[param_name] = job.row_data[param_name]

            print(f"🔍 Final extracted params: {action_params}")

            # Execute based on action type
            if action_type == 'browser-control':
                from src.modules.direct_browser_control import execute_direct_browser_control

                # Determine headless mode from job or config, default to False
                user_headless = job.row_data.get('headless')
                if user_headless is not None:
                    # Accept bool or string
                    if isinstance(user_headless, str):
                        headless = user_headless.lower() == 'true'
                    else:
                        headless = bool(user_headless)
                else:
                    headless = self.config.get('headless', False)

                execution_params = {
                    'use_own_browser': False,  # Use shared browser for batch jobs
                    'headless': headless,      # Default to False unless set
                    **action_params
                }

                result = await execute_direct_browser_control(action_def, **execution_params)

                if result:
                    self.logger.info(f"Browser control command '{action_name}' executed successfully for job {job.job_id}")
                    return 'completed'
                else:
                    raise Exception(f"Browser control command '{action_name}' execution failed")

            elif action_type == 'script':
                # Handle script execution
                command_template = action_def.get('command', '')
                if not command_template:
                    raise ValueError(f"Script command '{action_name}' has no command template")

                # Replace parameters in command template
                command = command_template
                for param_name, param_value in action_params.items():
                    placeholder = f"${{params.{param_name}}}"
                    command = command.replace(placeholder, str(param_value))

                # Execute the script command
                import subprocess
                import os

                # Change to the project directory
                project_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

                # Set environment
                env = os.environ.copy()
                env['PYTHONPATH'] = project_dir

                # Execute the command
                if command.startswith('python '):
                    command = command.replace('python ', f'"{sys.executable}" ', 1)

                shell_value = True

                process = subprocess.run(
                    command,
                    cwd=project_dir,
                    env=env,
                    shell=shell_value,
                    capture_output=True,
                    text=True,
                    timeout=300  # 5 minute timeout
                )

                if process.returncode == 0:
                    self.logger.info(f"Script command '{action_name}' executed successfully for job {job.job_id}")
                    return 'completed'
                else:
                    error_msg = f"Script command failed with exit code {process.returncode}"
                    if process.stderr:
                        error_msg += f": {process.stderr}"
                    raise Exception(error_msg)



            elif action_type in ['action_runner_template', 'git-script']:
                # Use the script_manager for these types
                from src.script.script_manager import run_script

                # Determine headless mode from job or config, default to False
                user_headless = job.row_data.get('headless')
                if user_headless is not None:
                    if isinstance(user_headless, str):
                        headless = user_headless.lower() == 'true'
                    else:
                        headless = bool(user_headless)
                else:
                    headless = self.config.get('headless', False)

                script_output, script_path = await run_script(action_def, action_params, headless=headless)

                if script_output and "successfully" in script_output.lower():
                    self.logger.info(f"{action_type} command '{action_name}' executed successfully for job {job.job_id}")
                    return 'completed'
                else:
                    raise Exception(f"{action_type} command execution failed: {script_output}")

            else:
                raise ValueError(f"Action type '{action_type}' is not supported for batch execution")

        except Exception as e:
            self.logger.error(f"Job {job.job_id} execution failed: {type(e).__name__}: {e}")
            raise

    def _execute_field_extraction(self, job: BatchJob):
        """
        Execute field extraction for a completed job.

        This method attempts to extract fields based on the extraction schema
        if one is configured for the batch.

        Args:
            job: The completed job to extract fields from
        """
        try:
            # Check if extraction schema is configured
            schema_path = self.config.get('extraction_schema_path')
            if not schema_path:
                # No schema configured, skip extraction
                return

            schema_path = Path(schema_path)
            if not schema_path.exists():
                self.logger.warning(f"Extraction schema not found: {schema_path}")
                return

            # Import extraction modules
            from ..extraction.schema import ExtractionSchema
            from ..extraction.extractor import FieldExtractor

            # Load schema
            schema = ExtractionSchema(schema_path)
            extractor = FieldExtractor(schema)

            # Extract fields (using mock data for now)
            # TODO: Integrate with actual browser context
            result = extractor.extract_fields(
                job_id=job.job_id,
                row_index=job.row_index if job.row_index is not None else self._parse_row_index_from_job_id(job.job_id),
                page_content=self._get_mock_page_content(job)
            )

            # Save extraction result
            rows_dir = self.run_context.artifact_dir("batch") / "rows" / job.job_id
            result_file = extractor.save_result(result, rows_dir)

            # Add extraction result as artifact
            self.add_row_artifact(
                job_id=job.job_id,
                artifact_type="extracted_fields",
                content=result.to_dict(),
                meta={
                    "schema_version": schema.version,
                    "field_count": len(schema.fields),
                    "extraction_success_count": result.success_count,
                    "extraction_failure_count": result.failure_count
                }
            )

            # Record extraction metrics
            self._record_extraction_metrics(job.job_id, result)

            self.logger.info(f"Completed field extraction for job {job.job_id}")

        except Exception as e:
            self.logger.warning(f"Field extraction failed for job {job.job_id}: {e}")
            # Don't fail the job if extraction fails, just log the warning

    def _get_mock_page_content(self, job: BatchJob) -> str:
        """
        Generate mock HTML content for testing.

        In production, this would be replaced with actual page content
        from the browser automation system.
        """
        # Mock HTML content based on job data
        mock_html = f"""
        <html>
        <body>
            <div id="status">success</div>
            <div class="profile">
                <span class="uid" data-user="{job.job_id}">user123</span>
            </div>
            <div class="data">{job.row_data.get('name', 'test_data')}</div>
        </body>
        </html>
        """
        return mock_html

    def _parse_row_index_from_job_id(self, job_id: str) -> int:
        """
        Parse row index from job ID.

        Supports various job ID formats:
        - run_id_001, run_id_002, etc.
        - UUID-based IDs
        - Custom formats

        Returns:
            Parsed row index or 0 if parsing fails
        """
        try:
            # Try to extract numeric part from the end
            parts = job_id.split('_')
            if len(parts) >= 2:
                last_part = parts[-1]
                if last_part.isdigit():
                    return int(last_part)

            # Try to find any numeric sequence at the end
            match = re.search(r'(\d+)$', job_id)
            if match:
                return int(match.group(1))

            # Fallback to 0 for UUIDs or other formats
            return 0

        except (ValueError, AttributeError):
            self.logger.debug(f"Could not parse row index from job_id: {job_id}")
            return 0

    def _record_extraction_metrics(self, job_id: str, result: 'ExtractionResult'):
        """Record metrics for field extraction."""
        try:
            from ..metrics import get_metrics_collector, MetricType

            collector = get_metrics_collector()
            if collector is None:
                return

            collector.record_metric(
                name="extraction_fields_success_total",
                value=result.success_count,
                metric_type=MetricType.COUNTER,
                tags={
                    "job_id": job_id,
                    "run_id": self.run_context.run_id_base
                }
            )

            collector.record_metric(
                name="extraction_fields_failure_total",
                value=result.failure_count,
                metric_type=MetricType.COUNTER,
                tags={
                    "job_id": job_id,
                    "run_id": self.run_context.run_id_base
                }
            )

            collector.record_metric(
                name="extraction_last_schema_field_count",
                value=result.total_fields,
                metric_type=MetricType.GAUGE,
                tags={
                    "run_id": self.run_context.run_id_base
                }
            )

        except Exception as e:
            self.logger.debug(f"Failed to record extraction metrics: {e}")


async def start_batch(csv_path: str, run_context: Optional[RunContext] = None, config: Optional[ConfigType] = None, execute_immediately: bool = True, progress_callback: Optional[Callable[[int, int], Awaitable[None]]] = None) -> BatchManifest:
    """
    Start a new batch execution from CSV file.

    This is the main entry point for batch processing. It creates a BatchEngine instance
    with the provided configuration and processes the CSV file to generate jobs.
    By default, it also executes the jobs immediately after creation.

    Args:
        csv_path: Path to CSV file to process
        run_context: Optional run context (creates new if not provided)
        config: Optional configuration dictionary for BatchEngine. Available options:
            - max_file_size_mb (float): Maximum file size in MB (default: 100)
            - chunk_size (int): Number of rows to process at once (default: 1000)
            - encoding (str): File encoding (default: 'utf-8')
            - delimiter_fallback (str): Fallback delimiter if auto-detection fails (default: ',')
            - allow_path_traversal (bool): Allow access to files outside current directory (default: True)
            - validate_headers (bool): Validate CSV headers (default: True)
            - skip_empty_rows (bool): Skip empty rows during processing (default: True)
            - log_level (str): Logging level ('DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL')
        execute_immediately: Whether to execute jobs immediately after creation (default: True)
        progress_callback: Optional callback function called after each job completion with (completed_jobs, total_jobs)

    Returns:
        BatchManifest for the created batch

    Raises:
        ValueError: If CSV parsing fails or configuration is invalid
        FileNotFoundError: If CSV file doesn't exist
        ConfigurationError: If configuration values are invalid
        SecurityError: If path traversal is detected and not allowed

    Example:
        ```python
        # Simple usage (creates and executes jobs)
        manifest = start_batch('data.csv')

        # Create jobs only (no execution)
        manifest = start_batch('data.csv', execute_immediately=False)

        # With custom configuration
        config = {
            'max_file_size_mb': 200,
            'encoding': 'utf-8',
            'allow_path_traversal': False
        }
        manifest = start_batch('data.csv', config=config)
        ```
    """
    if run_context is None:
        run_context = RunContext.get()

    engine = BatchEngine(run_context, config)
    manifest = engine.create_batch_jobs(csv_path)

    # Execute jobs immediately if requested
    if execute_immediately:
        try:
            execution_result = await engine.execute_batch_jobs(manifest.batch_id, progress_callback=progress_callback)
            logger.info(f"Batch {manifest.batch_id} execution completed: {execution_result.get('completed', 0)} completed, {execution_result.get('failed', 0)} failed")
        except Exception as e:
            logger.error(f"Failed to execute batch {manifest.batch_id} immediately: {e}")
            # Don't fail the batch creation if execution fails
            # The jobs can still be executed later manually

        # After execution, reload manifest from artifacts so the returned
        # manifest reflects any status updates performed during execution.
        try:
            updated = engine._load_manifest_by_batch_id(manifest.batch_id)
            if updated is not None:
                manifest = updated
        except Exception as e:
            logger.debug(f"Could not reload updated manifest for {manifest.batch_id}: {e}")

    return manifest
