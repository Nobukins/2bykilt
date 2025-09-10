"""
Batch progress and summary generation.

This module provides functionality to generate batch execution summaries
and progress reports from batch manifests.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class BatchSummary:
    """Summary of batch execution results."""
    batch_id: str
    run_id: str
    total_jobs: int
    completed_jobs: int
    failed_jobs: int
    pending_jobs: int
    success_rate: float
    created_at: str
    completed_at: Optional[str] = None
    jobs: List[Dict[str, Any]] = None

    def __post_init__(self):
        if self.jobs is None:
            self.jobs = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BatchSummary':
        """Create from dictionary."""
        return cls(**data)


class BatchSummaryGenerator:
    """
    Generates batch execution summaries from manifests.

    This class provides methods to create comprehensive summaries of batch
    execution results, including progress metrics and job status breakdowns.
    """

    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.BatchSummaryGenerator")

    def generate_summary(self, manifest) -> BatchSummary:
        """
        Generate batch summary from manifest.

        Args:
            manifest: Batch manifest to summarize

        Returns:
            BatchSummary with aggregated statistics
        """
        # Calculate job counts
        completed_jobs = sum(1 for job in manifest.jobs if job.status == 'completed')
        failed_jobs = sum(1 for job in manifest.jobs if job.status == 'failed')
        pending_jobs = sum(1 for job in manifest.jobs if job.status in ['pending', 'running'])

        # Calculate success rate
        total_completed = completed_jobs + failed_jobs
        success_rate = (completed_jobs / total_completed * 100) if total_completed > 0 else 0.0

        # Determine completion time
        completed_at = None
        if pending_jobs == 0 and manifest.jobs:
            # Find the latest completion time
            completion_times = [
                job.completed_at for job in manifest.jobs
                if job.completed_at and job.status in ['completed', 'failed']
            ]
            if completion_times:
                completed_at = max(completion_times)

        # Create job summaries
        jobs_summary = []
        for job in manifest.jobs:
            job_summary = {
                'job_id': job.job_id,
                'status': job.status,
                'created_at': job.created_at,
                'completed_at': job.completed_at,
                'error_message': job.error_message if job.status == 'failed' else None
            }
            jobs_summary.append(job_summary)

        summary = BatchSummary(
            batch_id=manifest.batch_id,
            run_id=manifest.run_id,
            total_jobs=manifest.total_jobs,
            completed_jobs=completed_jobs,
            failed_jobs=failed_jobs,
            pending_jobs=pending_jobs,
            success_rate=round(success_rate, 2),
            created_at=manifest.created_at,
            completed_at=completed_at,
            jobs=jobs_summary
        )

        self.logger.info(f"Generated summary for batch {manifest.batch_id}: "
                        f"{completed_jobs}/{manifest.total_jobs} completed, "
                        f"{failed_jobs} failed, {pending_jobs} pending")

        return summary

    def save_summary(self, summary: BatchSummary, output_path: Path):
        """
        Save batch summary to JSON file.

        Args:
            summary: Batch summary to save
            output_path: Path to save the summary JSON
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary.to_dict(), f, indent=2, ensure_ascii=False)

        self.logger.info(f"Saved batch summary to {output_path}")

    def load_summary(self, summary_path: Path) -> Optional[BatchSummary]:
        """
        Load batch summary from JSON file.

        Args:
            summary_path: Path to the summary JSON file

        Returns:
            BatchSummary if file exists and is valid, None otherwise
        """
        if not summary_path.exists():
            return None

        try:
            with open(summary_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return BatchSummary.from_dict(data)
        except Exception as e:
            self.logger.error(f"Failed to load batch summary from {summary_path}: {e}")
            return None


def generate_batch_summary(manifest_path: Path, output_path: Path) -> BatchSummary:
    """
    Generate and save batch summary from manifest file.

    This is a convenience function that loads a manifest, generates a summary,
    and saves it to the specified output path.

    Args:
        manifest_path: Path to batch manifest JSON file
        output_path: Path to save the summary JSON file

    Returns:
        Generated BatchSummary

    Raises:
        FileNotFoundError: If manifest file doesn't exist
        ValueError: If manifest is invalid
    """
    if not manifest_path.exists():
        raise FileNotFoundError(f"Batch manifest not found: {manifest_path}")

    # Load manifest
    try:
        with open(manifest_path, 'r', encoding='utf-8') as f:
            manifest_data = json.load(f)
            # Import here to avoid circular import
            from .engine import BatchManifest
            manifest = BatchManifest.from_dict(manifest_data)
    except Exception as e:
        raise ValueError(f"Invalid batch manifest: {manifest_path}")

    # Generate and save summary
    generator = BatchSummaryGenerator()
    summary = generator.generate_summary(manifest)
    generator.save_summary(summary, output_path)

    return summary
