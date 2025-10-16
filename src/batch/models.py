"""
Batch processing data models.

This module defines the core data structures used in the batch processing system,
including jobs and manifests for tracking execution state.
"""

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any


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
    row_index: Optional[int] = None  # Row index in the original CSV
    # Row-level artifacts (Issue #175 PoC): list of {type, path, created_at, meta?}
    artifacts: Optional[List[Dict[str, Any]]] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc).isoformat()
        # Normalize artifacts container
        if self.artifacts is None:
            self.artifacts = []

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
