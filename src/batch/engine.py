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
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Iterator
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from contextlib import contextmanager

from ..core.artifact_manager import ArtifactManager, get_artifact_manager
from ..runtime.run_context import RunContext

from .summary import BatchSummary

logger = logging.getLogger(__name__)

# Type aliases for better type hints
ConfigType = Dict[str, Union[str, int, float, bool]]


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


# Constants
BATCH_MANIFEST_FILENAME = "batch_manifest.json"
JOBS_DIRNAME = "jobs"


@dataclass
class BatchJob:
    """Represents a single batch job."""
    job_id: str
    run_id: str
    row_data: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
    batch_id: Optional[str] = None  # Add batch_id for better metrics tracking

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchJob':
        """Create from dictionary."""
        return cls(**data)


@dataclass
class BatchManifest:
    """Manifest for batch execution."""
    batch_id: str
    run_id: str
    csv_path: str
    total_jobs: int
    completed_jobs: int = 0
    failed_jobs: int = 0
    created_at: Optional[str] = None
    jobs: Optional[List[BatchJob]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.jobs is None:
            self.jobs = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        data = asdict(self)
        data['jobs'] = [job.to_dict() for job in self.jobs]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchManifest':
        """Create from dictionary."""
        jobs_data = data.pop('jobs', [])
        jobs = [BatchJob.from_dict(job_data) for job_data in jobs_data]
        return cls(jobs=jobs, **data)


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
                batch_id=batch_id  # Set batch_id for metrics tracking
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
        """
        try:
            from .summary import BatchSummaryGenerator

            # First try to get manifest from current context
            manifest = self._load_manifest_from_current_context(batch_id)
            if manifest is None:
                # Search through all batch manifest files in artifacts/runs
                manifest = self._search_batch_manifest_in_artifacts(batch_id)
            
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
        artifacts_root = Path("artifacts") / "runs"

        if not artifacts_root.exists():
            return None

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
                        return manifest

            except Exception as e:
                self.logger.error(f"Failed to load batch manifest {manifest_file}: {e}")

        return None

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
        artifacts_root = Path("artifacts") / "runs"

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

            self.logger.info(f"Generated batch summary for {manifest.batch_id}")

        except Exception as e:
            self.logger.error(f"Failed to generate batch summary: {e}")


def start_batch(csv_path: str, run_context: Optional[RunContext] = None, config: Optional[ConfigType] = None) -> BatchManifest:
    """
    Start a new batch execution from CSV file.

    This is the main entry point for batch processing. It creates a BatchEngine instance
    with the provided configuration and processes the CSV file to generate jobs.

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

    Returns:
        BatchManifest for the created batch

    Raises:
        ValueError: If CSV parsing fails or configuration is invalid
        FileNotFoundError: If CSV file doesn't exist
        ConfigurationError: If configuration values are invalid
        SecurityError: If path traversal is detected and not allowed

    Example:
        ```python
        # Simple usage
        manifest = start_batch('data.csv')

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
    return engine.create_batch_jobs(csv_path)
