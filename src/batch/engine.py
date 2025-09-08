"""
CSV-driven batch execution engine core.

This module provides the core functionality for processing CSV files
and generating batch jobs for browser automation tasks.
"""

import csv
import json
import logging
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timezone

from ..core.artifact_manager import ArtifactManager, get_artifact_manager
from ..runtime.run_context import RunContext

logger = logging.getLogger(__name__)

# Type aliases for better type hints
ConfigType = Dict[str, Union[str, int, float, bool]]

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
        }

        # Update with user configuration
        if config:
            self.config.update(config)

        # Validate configuration values
        self._validate_config()

    def _validate_config(self):
        """
        Validate configuration values to ensure they are within acceptable ranges.

        Raises:
            ValueError: If any configuration value is invalid
        """
        # Validate max_file_size_mb
        if not isinstance(self.config['max_file_size_mb'], (int, float)) or self.config['max_file_size_mb'] <= 0:
            raise ValueError(f"max_file_size_mb must be a positive number, got: {self.config['max_file_size_mb']}")

        # Validate chunk_size
        if not isinstance(self.config['chunk_size'], int) or self.config['chunk_size'] <= 0:
            raise ValueError(f"chunk_size must be a positive integer, got: {self.config['chunk_size']}")

        # Validate encoding
        if not isinstance(self.config['encoding'], str) or not self.config['encoding']:
            raise ValueError(f"encoding must be a non-empty string, got: {self.config['encoding']}")

        # Validate delimiter_fallback
        if not isinstance(self.config['delimiter_fallback'], str) or len(self.config['delimiter_fallback']) != 1:
            raise ValueError(f"delimiter_fallback must be a single character, got: {self.config['delimiter_fallback']}")

        # Validate boolean settings
        for bool_key in ['allow_path_traversal', 'validate_headers', 'skip_empty_rows']:
            if not isinstance(self.config[bool_key], bool):
                raise ValueError(f"{bool_key} must be a boolean, got: {self.config[bool_key]}")

    def parse_csv(self, csv_path: str, chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Parse CSV file and return list of row dictionaries.

        This method handles various CSV formats, encoding issues, and provides
        memory-efficient processing for large files through chunked reading.

        Args:
            csv_path: Path to CSV file (absolute or relative)
            chunk_size: Number of rows to process at once (for memory efficiency)

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
                    raise ValueError(f"Access denied: {csv_path} is outside allowed directory")

        if not csv_path_obj.exists():
            raise FileNotFoundError(f"CSV file not found: '{csv_path}'. Please verify the file path and ensure the file exists.")

        if csv_path_obj.stat().st_size == 0:
            raise ValueError(f"CSV file is empty: '{csv_path}'. The file contains no data to process.")

        # Check file size for memory considerations
        file_size_mb = csv_path_obj.stat().st_size / (1024 * 1024)
        if file_size_mb > self.config['max_file_size_mb']:
            raise ValueError(f"CSV file too large ({file_size_mb:.1f}MB). Maximum allowed: {self.config['max_file_size_mb']}MB")

        if file_size_mb > 100:  # Warn for files larger than 100MB
            self.logger.warning(f"Large CSV file detected ({file_size_mb:.1f}MB). Consider using streaming processing.")

        try:
            with open(csv_path_obj, 'r', encoding=self.config['encoding']) as f:
                # Check if file has content
                content = f.read()
                if not content.strip():
                    raise ValueError(f"CSV file contains no data: {csv_path}")

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
                    if processed_rows % self.config['chunk_size'] == 0:
                        self.logger.debug(f"Processed {processed_rows} rows from {csv_path}")

                if not rows:
                    raise ValueError(f"No valid data rows found in CSV file: {csv_path}")

                self.logger.info(f"Successfully parsed {len(rows)} valid rows from {csv_path}")
                return rows

        except UnicodeDecodeError as e:
            raise UnicodeDecodeError(e.encoding, e.object, e.start, e.end,
                                   f"Invalid file encoding in '{csv_path}'. Expected '{self.config['encoding']}' encoding. "
                                   f"Try saving the file with UTF-8 encoding or specify a different encoding in config. "
                                   f"Original error: {e}")
        except csv.Error as e:
            raise ValueError(f"Invalid CSV format in '{csv_path}': {e}. "
                           f"Please ensure the file is a valid CSV with proper formatting.")
        except Exception as e:
            raise ValueError(f"Failed to parse CSV file '{csv_path}': {e}. "
                           f"Please check the file format and contents.")

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
            raise ValueError(f"No valid rows found in CSV file: {csv_path}")

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
                row_data=row_data
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

    def _save_manifest(self, manifest_file: Path, manifest: BatchManifest):
        """Save manifest to file."""
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)


def start_batch(csv_path: str, run_context: Optional[RunContext] = None, config: Optional[ConfigType] = None) -> BatchManifest:
    """
    Start a new batch execution from CSV file.

    This is the main entry point for batch processing. It creates a BatchEngine instance
    with the provided configuration and processes the CSV file to generate jobs.

    Args:
        csv_path: Path to CSV file to process
        run_context: Optional run context (creates new if not provided)
        config: Optional configuration dictionary for BatchEngine

    Returns:
        BatchManifest for the created batch

    Raises:
        ValueError: If CSV parsing fails or configuration is invalid
        FileNotFoundError: If CSV file doesn't exist

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
