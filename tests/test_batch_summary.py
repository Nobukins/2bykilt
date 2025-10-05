"""
Tests for batch summary generation.
"""

import json
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import Mock

from src.batch.summary import BatchSummary, BatchSummaryGenerator, generate_batch_summary


class TestBatchSummary:
    """Test BatchSummary dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        summary = BatchSummary(
            batch_id="test-batch",
            run_id="test-run",
            csv_path="batch.csv",
            total_jobs=10,
            completed_jobs=8,
            failed_jobs=2,
            pending_jobs=0,
            success_rate=80.0,
            created_at="2025-01-01T00:00:00Z"
        )

        data = summary.to_dict()
        assert data["batch_id"] == "test-batch"
        assert data["success_rate"] == 80.0
        assert data["total_jobs"] == 10

    def test_from_dict(self):
        """Test creation from dictionary."""
        data = {
            "batch_id": "test-batch",
            "run_id": "test-run",
            "csv_path": "batch.csv",
            "total_jobs": 10,
            "completed_jobs": 8,
            "failed_jobs": 2,
            "pending_jobs": 0,
            "success_rate": 80.0,
            "created_at": "2025-01-01T00:00:00Z",
            "jobs": []
        }

        summary = BatchSummary.from_dict(data)
        assert summary.batch_id == "test-batch"
        assert summary.success_rate == 80.0


class TestBatchSummaryGenerator:
    """Test BatchSummaryGenerator class."""

    def test_generate_summary_all_completed(self):
        """Test summary generation when all jobs are completed."""
        # Mock manifest and jobs
        mock_job1 = Mock()
        mock_job1.job_id = "job1"
        mock_job1.status = "completed"
        mock_job1.created_at = "2025-01-01T00:00:00Z"
        mock_job1.completed_at = "2025-01-01T00:01:00Z"
        mock_job1.error_message = None

        mock_job2 = Mock()
        mock_job2.job_id = "job2"
        mock_job2.status = "completed"
        mock_job2.created_at = "2025-01-01T00:00:00Z"
        mock_job2.completed_at = "2025-01-01T00:02:00Z"
        mock_job2.error_message = None

        mock_manifest = Mock()
        mock_manifest.batch_id = "batch1"
        mock_manifest.run_id = "run1"
        mock_manifest.total_jobs = 2
        mock_manifest.completed_jobs = 2
        mock_manifest.failed_jobs = 0
        mock_manifest.created_at = "2025-01-01T00:00:00Z"
        mock_manifest.jobs = [mock_job1, mock_job2]

        generator = BatchSummaryGenerator()
        summary = generator.generate_summary(mock_manifest)

        assert summary.batch_id == "batch1"
        assert summary.total_jobs == 2
        assert summary.completed_jobs == 2
        assert summary.failed_jobs == 0
        assert summary.pending_jobs == 0
        assert summary.success_rate == 100.0
        assert summary.completed_at == "2025-01-01T00:02:00Z"
        assert len(summary.jobs) == 2

    def test_generate_summary_with_failures(self):
        """Test summary generation with failed jobs."""
        # Mock jobs
        mock_job1 = Mock()
        mock_job1.job_id = "job1"
        mock_job1.status = "completed"
        mock_job1.created_at = "2025-01-01T00:00:00Z"
        mock_job1.completed_at = "2025-01-01T00:01:00Z"
        mock_job1.error_message = None

        mock_job2 = Mock()
        mock_job2.job_id = "job2"
        mock_job2.status = "failed"
        mock_job2.created_at = "2025-01-01T00:00:00Z"
        mock_job2.completed_at = "2025-01-01T00:02:00Z"
        mock_job2.error_message = "Test error"

        mock_job3 = Mock()
        mock_job3.job_id = "job3"
        mock_job3.status = "pending"
        mock_job3.created_at = "2025-01-01T00:00:00Z"
        mock_job3.completed_at = None
        mock_job3.error_message = None

        mock_manifest = Mock()
        mock_manifest.batch_id = "batch1"
        mock_manifest.run_id = "run1"
        mock_manifest.total_jobs = 3
        mock_manifest.completed_jobs = 1
        mock_manifest.failed_jobs = 1
        mock_manifest.created_at = "2025-01-01T00:00:00Z"
        mock_manifest.jobs = [mock_job1, mock_job2, mock_job3]

        generator = BatchSummaryGenerator()
        summary = generator.generate_summary(mock_manifest)

        assert summary.total_jobs == 3
        assert summary.completed_jobs == 1
        assert summary.failed_jobs == 1
        assert summary.pending_jobs == 1
        assert summary.success_rate == 50.0
        assert summary.completed_at is None  # Not all jobs complete

    def test_generate_summary_no_completed_jobs(self):
        """Test summary generation when no jobs are completed."""
        # Mock jobs
        mock_job1 = Mock()
        mock_job1.status = "pending"
        mock_job1.completed_at = None

        mock_job2 = Mock()
        mock_job2.status = "running"
        mock_job2.completed_at = None

        mock_manifest = Mock()
        mock_manifest.total_jobs = 2
        mock_manifest.completed_jobs = 0
        mock_manifest.failed_jobs = 0
        mock_manifest.created_at = "2025-01-01T00:00:00Z"
        mock_manifest.jobs = [mock_job1, mock_job2]

        generator = BatchSummaryGenerator()
        summary = generator.generate_summary(mock_manifest)

        assert summary.success_rate == 0.0
        assert summary.completed_at is None

    def test_save_and_load_summary(self):
        """Test saving and loading summary."""
        summary = BatchSummary(
            batch_id="test-batch",
            run_id="test-run",
            csv_path="tests/data/sample.csv",
            total_jobs=5,
            completed_jobs=4,
            failed_jobs=1,
            pending_jobs=0,
            success_rate=80.0,
            created_at="2025-01-01T00:00:00Z"
        )

        generator = BatchSummaryGenerator()

        with tempfile.TemporaryDirectory() as tmpdir:
            summary_path = Path(tmpdir) / "summary.json"

            # Save
            generator.save_summary(summary, summary_path)
            assert summary_path.exists()

            # Load
            loaded = generator.load_summary(summary_path)
            assert loaded is not None
            assert loaded.batch_id == "test-batch"
            assert loaded.success_rate == 80.0

    def test_load_summary_nonexistent_file(self):
        """Test loading summary from nonexistent file."""
        generator = BatchSummaryGenerator()
        loaded = generator.load_summary(Path("nonexistent.json"))
        assert loaded is None


class TestGenerateBatchSummary:
    """Test generate_batch_summary function."""

    def test_generate_batch_summary_from_file(self):
        """Test generating summary from manifest file."""
        # Create mock manifest data
        manifest_data = {
            "batch_id": "batch1",
            "run_id": "run1",
            "csv_path": "test.csv",
            "total_jobs": 2,
            "completed_jobs": 2,
            "failed_jobs": 0,
            "created_at": "2025-01-01T00:00:00Z",
            "jobs": [
                {
                    "job_id": "job1",
                    "run_id": "run1",
                    "row_data": {"name": "test1"},
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00Z",
                    "completed_at": "2025-01-01T00:01:00Z"
                },
                {
                    "job_id": "job2",
                    "run_id": "run1",
                    "row_data": {"name": "test2"},
                    "status": "completed",
                    "created_at": "2025-01-01T00:00:00Z",
                    "completed_at": "2025-01-01T00:02:00Z"
                }
            ]
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "manifest.json"
            summary_path = Path(tmpdir) / "summary.json"

            # Save manifest
            with open(manifest_path, 'w') as f:
                json.dump(manifest_data, f)

            # Generate summary
            summary = generate_batch_summary(manifest_path, summary_path)

            assert summary.batch_id == "batch1"
            assert summary.success_rate == 100.0
            assert summary_path.exists()

    def test_generate_batch_summary_invalid_manifest(self):
        """Test generating summary from invalid manifest file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "invalid.json"
            summary_path = Path(tmpdir) / "summary.json"

            # Save invalid JSON
            with open(manifest_path, 'w') as f:
                f.write("invalid json")

            with pytest.raises(ValueError):
                generate_batch_summary(manifest_path, summary_path)

    def test_generate_batch_summary_missing_file(self):
        """Test generating summary from missing manifest file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manifest_path = Path(tmpdir) / "missing.json"
            summary_path = Path(tmpdir) / "summary.json"

            with pytest.raises(FileNotFoundError):
                generate_batch_summary(manifest_path, summary_path)
