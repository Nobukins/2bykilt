"""
Tests for batch engine data models (BatchJob and BatchManifest).

This module tests the core data classes used in the batch execution engine,
focusing on creation, serialization, and deserialization.
"""

from tests.batch import BatchJob, BatchManifest
import pytest


@pytest.mark.ci_safe
class TestBatchJob:
    """Test BatchJob dataclass."""

    def test_batch_job_creation(self):
        """Test basic BatchJob creation."""
        job = BatchJob(
            job_id="test_0001",
            run_id="run_123",
            row_data={"name": "test", "value": "123"}
        )

        assert job.job_id == "test_0001"
        assert job.run_id == "run_123"
        assert job.row_data == {"name": "test", "value": "123"}
        assert job.status == "pending"
        assert job.created_at is not None

    def test_batch_job_to_dict(self):
        """Test BatchJob serialization."""
        job = BatchJob(
            job_id="test_0001",
            run_id="run_123",
            row_data={"name": "test"}
        )

        data = job.to_dict()
        assert data["job_id"] == "test_0001"
        assert data["run_id"] == "run_123"
        assert data["row_data"] == {"name": "test"}

    def test_batch_job_from_dict(self):
        """Test BatchJob deserialization."""
        data = {
            "job_id": "test_0001",
            "run_id": "run_123",
            "row_data": {"name": "test"},
            "status": "completed",
            "created_at": "2024-01-01T00:00:00"
        }

        job = BatchJob.from_dict(data)
        assert job.job_id == "test_0001"
        assert job.status == "completed"


@pytest.mark.ci_safe
class TestBatchManifest:
    """Test BatchManifest dataclass."""

    def test_batch_manifest_creation(self):
        """Test basic BatchManifest creation."""
        jobs = [
            BatchJob("job1", "run1", {"data": "1"}),
            BatchJob("job2", "run1", {"data": "2"})
        ]

        manifest = BatchManifest(
            batch_id="batch_123",
            run_id="run_123",
            csv_path="/path/to/file.csv",
            total_jobs=2,
            jobs=jobs
        )

        assert manifest.batch_id == "batch_123"
        assert manifest.total_jobs == 2
        assert len(manifest.jobs) == 2
        assert manifest.created_at is not None

    def test_batch_manifest_serialization(self):
        """Test BatchManifest serialization."""
        jobs = [BatchJob("job1", "run1", {"data": "1"})]
        manifest = BatchManifest(
            batch_id="batch_123",
            run_id="run_123",
            csv_path="/path/to/file.csv",
            total_jobs=1,
            jobs=jobs
        )

        data = manifest.to_dict()
        assert data["batch_id"] == "batch_123"
        assert len(data["jobs"]) == 1

        # Test deserialization
        restored = BatchManifest.from_dict(data)
        assert restored.batch_id == "batch_123"
        assert len(restored.jobs) == 1
