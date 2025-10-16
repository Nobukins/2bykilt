"""
Batch lifecycle tests for BatchEngine.

This module tests:
- Batch job creation and manifest generation
- Job status updates (pending, completed, failed, stopped)
- Batch summary retrieval
- stop_batch functionality
- Manifest persistence and reloading
"""

import json
from pathlib import Path

import pytest

from tests.batch import (
    BatchEngine,
    BatchManifest,
    FileProcessingError,
    _run_async,
)
from src.batch.engine import BATCH_MANIFEST_FILENAME


class TestBatchJobCreation:
    """Tests for batch job creation and manifest generation."""

    def test_create_batch_jobs(self, engine, temp_dir, run_context):
        """Test batch job creation."""
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        assert manifest.run_id == run_context.run_id_base
        assert manifest.csv_path == str(csv_file)
        assert manifest.total_jobs == 2

    def test_create_batch_jobs_with_job_files(self, engine, temp_dir, run_context):
        """Test that batch job creation creates individual job files."""
        csv_content = "name,value\nfoo,1\nbar,2\n"
        csv_file = temp_dir / "simple.csv"
        csv_file.write_text(csv_content)
        
        manifest = engine.create_batch_jobs(str(csv_file))
        
        # Check job files created
        jobs_dir = temp_dir / "test_run_123-jobs"
        assert jobs_dir.exists()

        job_files = list(jobs_dir.glob("*.json"))
        assert len(job_files) == 2

        # Check manifest file created
        manifest_file = temp_dir / "test_run_123-batch" / "batch_manifest.json"
        assert manifest_file.exists()

        # Verify manifest content
        with open(manifest_file, 'r') as f:
            data = json.load(f)
            assert data["total_jobs"] == 2
            assert len(data["jobs"]) == 2

    def test_create_batch_jobs_empty_csv(self, engine, temp_dir):
        """Test batch job creation with empty CSV."""
        csv_content = "name,value\n"  # Only header
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(FileProcessingError, match="Failed to parse CSV file"):
            engine.create_batch_jobs(str(csv_file))


class TestJobStatusUpdates:
    """Tests for job status updates and manifest synchronization."""

    def test_update_job_status(self, engine, temp_dir, run_context):
        """Test job status update."""
        # Create a manifest first
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        # Update job status
        engine.update_job_status(job_id, "completed")

        # Verify status updated
        updated_manifest = engine.get_batch_summary(manifest.batch_id)
        assert updated_manifest is not None
        assert updated_manifest.jobs[0]['status'] == "completed"
        assert updated_manifest.completed_jobs == 1

    def test_update_job_status_with_error(self, engine, temp_dir, run_context):
        """Test job status update with error message."""
        # Create a manifest first
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        # Update job status with error
        engine.update_job_status(job_id, "failed", "Test error")

        # Verify status and error updated
        updated_manifest = engine.get_batch_summary(manifest.batch_id)
        assert updated_manifest is not None
        assert updated_manifest.jobs[0]['status'] == "failed"
        assert updated_manifest.jobs[0]['error_message'] == "Test error"
        assert updated_manifest.failed_jobs == 1

    def test_update_job_status_not_found(self, engine, temp_dir, run_context):
        """Test updating status of non-existent job."""
        # Create empty manifest file
        manifest_dir = temp_dir / "test_run_123-batch"
        manifest_dir.mkdir(parents=True, exist_ok=True)
        manifest_file = manifest_dir / "batch_manifest.json"
        manifest_file.write_text('{"batch_id": "test", "jobs": []}')

        # Try to update non-existent job
        engine.update_job_status("non_existent_job", "completed")
        # Should not raise exception, just log warning


class TestBatchSummary:
    """Tests for batch summary retrieval and reporting."""

    def test_get_batch_summary(self, engine, temp_dir, run_context):
        """Test getting batch summary."""
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        # Get summary
        summary = engine.get_batch_summary(manifest.batch_id)
        assert summary is not None
        assert summary.total_jobs == 2
        assert len(summary.jobs) == 2

    def test_get_batch_summary_not_found(self, engine):
        """Test getting summary of non-existent batch."""
        result = engine.get_batch_summary("non_existent_batch")
        assert result is None


class TestStopBatch:
    """Tests for stop_batch functionality."""

    def test_stop_batch_marks_pending_jobs_stopped(self, engine, temp_dir, run_context):
        """stop_batch should mark pending/running jobs as 'stopped' and persist manifest."""
        from src.batch.engine import BatchEngine, BatchManifest, BATCH_MANIFEST_FILENAME
        import json
        
        # Prepare CSV with three jobs
        csv_content = "name,value\na,1\nb,2\nc,3\n"
        csv_file = temp_dir / "jobs.csv"
        csv_file.write_text(csv_content)
        manifest = engine.create_batch_jobs(str(csv_file))
        batch_id = manifest.batch_id
        
        # Simulate one job completed, one failed, one pending
        manifest.jobs[0].status = 'completed'
        manifest.completed_jobs = 1
        manifest.jobs[1].status = 'failed'
        manifest.failed_jobs = 1
        
        # Persist modified manifest to disk
        manifest_path = run_context.artifact_dir('batch') / BATCH_MANIFEST_FILENAME
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        
        # Stop batch
        result = engine.stop_batch(batch_id)
        assert result['batch_id'] == batch_id
        assert result['stopped_jobs'] == 1  # only the remaining pending one
        
        # Reload manifest and verify statuses
        with open(manifest_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        reloaded = BatchManifest.from_dict(data)
        statuses = {j.job_id: j.status for j in reloaded.jobs}
        assert list(statuses.values()).count('stopped') == 1
        assert list(statuses.values()).count('completed') == 1
        assert list(statuses.values()).count('failed') == 1

    def test_stop_batch_invalid_id(self, engine):
        """stop_batch with invalid id raises ValueError."""
        with pytest.raises(ValueError, match="Batch not found"):
            engine.stop_batch("non-existent")

    def test_retry_metrics_still_available_after_stop_batch_addition(self, engine, temp_dir):
        """Ensure _record_retry_metrics still callable after adding stop_batch (regression guard)."""
        # create simple CSV with 2 rows
        csv_file = temp_dir / 'simple.csv'
        csv_file.write_text('name,value\nfoo,1\nbar,2\n')
        manifest = engine.create_batch_jobs(str(csv_file))
        # should not raise
        engine._record_retry_metrics(manifest.batch_id, 0)
        assert len(manifest.jobs) == 2
