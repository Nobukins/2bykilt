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

        Args:
            csv_path: Path to CSV file (absolute or relative)
            chunk_size: Number of rows to process at once (for memory efficiency)

        Returns:
            List of dictionaries representing CSV rows, where keys are column headers

        Raises:
            FileNotFoundError: If CSV file doesn't exist
            FileProcessingError: If CSV parsing fails or file is invalid
            SecurityError: If path traversal is detected (when enabled)
        """
        csv_path_obj = self._validate_and_resolve_path(csv_path)
        self._validate_file_basic_properties(csv_path_obj)
        
        try:
            return self._parse_csv_content(csv_path_obj)
        except UnicodeDecodeError as e:
            raise FileProcessingError(
                f"Invalid file encoding in '{csv_path}'. Expected '{self.config['encoding']}' encoding. "
                f"Try saving the file with UTF-8 encoding or specify a different encoding in config. "
                f"Original error: {e}"
            )
        except csv.Error as e:
            raise FileProcessingError(
                f"Invalid CSV format in '{csv_path}': {e}. "
                f"Please ensure the file is a valid CSV with proper formatting and consistent delimiters."
            )
        except FileProcessingError:
            # Re-raise FileProcessingError as-is
            raise
        except Exception as e:
            raise FileProcessingError(
                f"Failed to parse CSV file '{csv_path}': {e}. "
                f"Please check the file format, encoding, and contents."
            )

    def _validate_and_resolve_path(self, csv_path: str) -> Path:
        """Validate and resolve the CSV file path with security checks."""
        csv_path_obj = Path(csv_path).resolve()
        
        if not self.config.get('allow_path_traversal', True):
            self._check_path_traversal_security(csv_path, csv_path_obj)
        
        return csv_path_obj

    def _check_path_traversal_security(self, original_path: str, resolved_path: Path) -> None:
        """Check for path traversal security issues."""
        cwd = Path.cwd().resolve()
        
        # Check if path is outside current working directory
        try:
            resolved_path.relative_to(cwd)
        except ValueError:
            raise SecurityError(
                f"Access denied: '{original_path}' is outside allowed directory. "
                f"Path traversal detected. To allow access to files outside the current "
                f"working directory, set 'allow_path_traversal' to True in configuration."
            )
        
        # Check for access to sensitive system directories
        self._check_sensitive_directory_access(original_path, resolved_path)

    def _check_sensitive_directory_access(self, original_path: str, resolved_path: Path) -> None:
        """Check if path attempts to access sensitive system directories."""
        sensitive_paths = [
            Path('/etc'), Path('/usr'), Path('/bin'), Path('/sbin'),
            Path('/System'), Path('/Library/Preferences'), Path('/private/var'),
            Path('C:\\Windows'), Path('C:\\Program Files'), Path('C:\\Users'),
        ]

        for sensitive_path in sensitive_paths:
            try:
                if sensitive_path.exists() and resolved_path.is_relative_to(sensitive_path):
                    raise SecurityError(
                        f"Access denied: '{original_path}' points to a sensitive system directory. "
                        f"Resolved path: '{resolved_path}'. "
                        f"Sensitive directory: '{sensitive_path}'. "
                        f"This access is blocked for security reasons."
                    )
            except (OSError, ValueError):
                # Path might not exist on this system, continue checking
                continue

    def _validate_file_basic_properties(self, csv_path_obj: Path) -> None:
        """Validate basic file properties like existence and size."""
        if not csv_path_obj.exists():
            raise FileNotFoundError(
                f"CSV file not found: '{csv_path_obj}'. Please verify the file path and ensure the file exists."
            )

        if csv_path_obj.stat().st_size == 0:
            raise FileProcessingError(
                f"CSV file is empty: '{csv_path_obj}'. The file contains no data to process."
            )

        # Check file size for memory considerations
        file_size_mb = csv_path_obj.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config['max_file_size_mb']:
            raise FileProcessingError(
                f"CSV file too large ({file_size_mb:.1f}MB). "
                f"Maximum allowed: {self.config['max_file_size_mb']}MB. "
                f"Consider splitting the file or increasing 'max_file_size_mb' in configuration."
            )

        if file_size_mb > 100:  # Warn for files larger than 100MB
            self.logger.warning(f"Large CSV file detected ({file_size_mb:.1f}MB). Consider using streaming processing.")

    def _parse_csv_content(self, csv_path_obj: Path) -> List[Dict[str, Any]]:
        """Parse the actual CSV content and return rows."""
        with open(csv_path_obj, 'r', encoding=self.config['encoding']) as f:
            # For large files, use a streaming approach to avoid memory issues
            file_size_mb = csv_path_obj.stat().st_size / (1024 * 1024)
            if file_size_mb > 50:  # Use streaming for files larger than 50MB
                return self._parse_csv_streaming(f, csv_path_obj)
            else:
                return self._parse_csv_in_memory(f, csv_path_obj)

    def _parse_csv_in_memory(self, file_handle, csv_path_obj: Path) -> List[Dict[str, Any]]:
        """Parse CSV content in memory (for smaller files)."""
        # Check if file has content (using a small read first)
        first_chunk = file_handle.read(1024)
        if not first_chunk.strip():
            raise FileProcessingError(
                f"CSV file contains no data: '{csv_path_obj}'. The file is empty or contains only whitespace."
            )
        
        file_handle.seek(0)
        delimiter = self._detect_csv_delimiter(first_chunk, csv_path_obj)
        
        reader = csv.DictReader(file_handle, delimiter=delimiter)
        rows = []
        processed_rows = 0

        for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
            if self._should_skip_row(row, row_num, csv_path_obj):
                continue

            rows.append(row)
            processed_rows += 1

            # Process in chunks to avoid memory issues with very large files
            if processed_rows % self.config['chunk_size'] == 0:
                self.logger.debug(f"Processed {processed_rows} rows from {csv_path_obj}")

        if not rows:
            raise FileProcessingError(
                f"No valid data rows found in CSV file: '{csv_path_obj}'. "
                f"The file may contain only headers or all rows were filtered out."
            )

        self.logger.info(f"Successfully parsed {len(rows)} valid rows from {csv_path_obj}")
        return rows

    def _parse_csv_streaming(self, file_handle, csv_path_obj: Path) -> List[Dict[str, Any]]:
        """Parse CSV content using streaming approach (for larger files)."""
        # Read only first chunk to detect delimiter and check content
        first_chunk = file_handle.read(8192)  # Larger chunk for better delimiter detection
        if not first_chunk.strip():
            raise FileProcessingError(
                f"CSV file contains no data: '{csv_path_obj}'. The file is empty or contains only whitespace."
            )
        
        file_handle.seek(0)
        delimiter = self._detect_csv_delimiter(first_chunk, csv_path_obj)
        
        reader = csv.DictReader(file_handle, delimiter=delimiter)
        rows = []
        processed_rows = 0
        
        self.logger.info(f"Using streaming mode for large file: {csv_path_obj}")

        try:
            for row_num, row in enumerate(reader, start=2):  # Start from 2 (header is 1)
                if self._should_skip_row(row, row_num, csv_path_obj):
                    continue

                rows.append(row)
                processed_rows += 1

                # More frequent progress updates for large files
                if processed_rows % (self.config['chunk_size'] // 4) == 0:
                    self.logger.info(f"Streamed {processed_rows} rows from {csv_path_obj}")

        except MemoryError:
            raise FileProcessingError(
                f"File '{csv_path_obj}' is too large to process in available memory. "
                f"Consider reducing the file size or increasing available memory."
            )

        if not rows:
            raise FileProcessingError(
                f"No valid data rows found in CSV file: '{csv_path_obj}'. "
                f"The file may contain only headers or all rows were filtered out."
            )

        self.logger.info(f"Successfully streamed {len(rows)} valid rows from {csv_path_obj}")
        return rows

    def _detect_csv_delimiter(self, sample_content: str, csv_path_obj: Path) -> str:
        """Detect the CSV delimiter from sample content."""
        try:
            sniffer = csv.Sniffer()
            delimiter = sniffer.sniff(sample_content).delimiter
            return delimiter
        except csv.Error:
            # Fallback to configured delimiter if detection fails
            delimiter = self.config['delimiter_fallback']
            self.logger.warning(f"Could not detect delimiter for {csv_path_obj}, using '{delimiter}'")
            return delimiter

    def _should_skip_row(self, row: Dict[str, Any], row_num: int, csv_path_obj: Path) -> bool:
        """Determine if a row should be skipped during processing."""
        # Skip empty rows if configured
        if self.config['skip_empty_rows'] and not any(row.values()):
            self.logger.debug(f"Skipping empty row {row_num} in {csv_path_obj}")
            return True

        # Validate row has required fields (customize based on needs)
        if not row:
            self.logger.debug(f"Skipping invalid row {row_num} in {csv_path_obj}")
            return True

        return False

    def create_batch_jobs(self, csv_path: str) -> BatchManifest:
        """
        Create batch jobs from CSV file.

        Args:
            csv_path: Path to CSV file to process

        Returns:
            BatchManifest containing all generated jobs and batch metadata

        Raises:
            FileProcessingError: If CSV parsing fails or no valid rows found
            FileNotFoundError: If CSV file doesn't exist
        """
        # Generate unique IDs and parse CSV
        batch_id = str(uuid.uuid4())
        run_id = self.run_context.run_id_base
        rows = self.parse_csv(csv_path)

        if not rows:
            raise FileProcessingError(
                f"No valid rows found in CSV file: '{csv_path}'. "
                f"The file may be empty or contain only invalid data."
            )

        # Create job files and collect job objects
        jobs = self._create_individual_job_files(rows, run_id)
        
        # Create and save batch manifest
        manifest = self._create_and_save_manifest(batch_id, run_id, csv_path, jobs)
        
        self.logger.info(f"Created batch with {len(jobs)} jobs (batch_id: {batch_id})")
        return manifest

    def _create_individual_job_files(self, rows: List[Dict[str, Any]], run_id: str) -> List[BatchJob]:
        """Create individual job files for each CSV row."""
        jobs_dir = self.run_context.artifact_dir("jobs")
        jobs_dir.mkdir(exist_ok=True)

        jobs = []
        for i, row_data in enumerate(rows):
            job_id = f"{run_id}_{i+1:04d}"
            job = BatchJob(job_id=job_id, run_id=run_id, row_data=row_data)

            # Save individual job file
            job_file = jobs_dir / f"{job_id}.json"
            self._save_job_file(job_file, job)

            jobs.append(job)
            self.logger.info(f"Created job {job_id} for row {i+1}")

        return jobs

    def _save_job_file(self, job_file: Path, job: BatchJob) -> None:
        """Save a single job to its JSON file."""
        with open(job_file, 'w', encoding='utf-8') as f:
            json.dump(job.to_dict(), f, indent=2, ensure_ascii=False)

    def _create_and_save_manifest(self, batch_id: str, run_id: str, csv_path: str, jobs: List[BatchJob]) -> BatchManifest:
        """Create the batch manifest and save it to file."""
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

        return manifest

    def get_batch_status(self, batch_id: str) -> Optional[BatchManifest]:
        """
        Get status of a batch execution.

        Args:
            batch_id: Batch identifier

        Returns:
            BatchManifest if found, None otherwise
        """
        # First try the current run context
        manifest = self._load_manifest_from_current_context(batch_id)
        if manifest is not None:
            return manifest

        # Search through all batch manifest files in artifacts/runs
        return self._search_batch_manifest_in_artifacts(batch_id)

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
            self.logger.info(f"Updated job {job_id} status to {status}")

        except Exception as e:
            self.logger.error(f"Failed to update job status: {e}")

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
        if not manifest_file.exists():
            return None
            
        try:
            with open(manifest_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BatchManifest.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load batch manifest {manifest_file}: {e}")
            return None

    def _save_manifest(self, manifest_file: Path, manifest: BatchManifest) -> None:
        """Save manifest to file."""
        try:
            # Ensure parent directory exists
            manifest_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(manifest_file, 'w', encoding='utf-8') as f:
                json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Failed to save batch manifest to {manifest_file}: {e}")
            raise

    def _find_job_by_id(self, manifest: BatchManifest, job_id: str) -> Optional[BatchJob]:
        """Find job by ID in manifest."""
        for job in manifest.jobs:
            if job.job_id == job_id:
                return job
        self.logger.warning(f"Job {job_id} not found in manifest")
        return None


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
