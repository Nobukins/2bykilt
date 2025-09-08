"""
Tests for CSV-driven batch execution engine.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.batch.engine import BatchEngine, BatchJob, BatchManifest, start_batch
from src.runtime.run_context import RunContext


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


class TestBatchEngine:
    """Test BatchEngine functionality."""

    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for tests."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def run_context(self, temp_dir):
        """Create mock run context."""
        context = Mock(spec=RunContext)
        context.run_id_base = "test_run_123"
        def artifact_dir_mock(component):
            path = temp_dir / f"{context.run_id_base}-{component}"
            path.mkdir(parents=True, exist_ok=True)
            return path
        context.artifact_dir = artifact_dir_mock
        return context

    @pytest.fixture
    def engine(self, run_context):
        """Create BatchEngine instance."""
        return BatchEngine(run_context)

    def test_parse_csv_basic(self, engine, temp_dir):
        """Test basic CSV parsing."""
        csv_content = "name,value\nAlice,25\nBob,30\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        assert len(rows) == 2
        assert rows[0] == {"name": "Alice", "value": "25"}
        assert rows[1] == {"name": "Bob", "value": "30"}

    def test_parse_csv_empty_rows(self, engine, temp_dir):
        """Test CSV parsing with empty rows."""
        csv_content = "name,value\nAlice,25\n,\nBob,30\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        assert len(rows) == 2  # Empty row should be skipped
        assert rows[0] == {"name": "Alice", "value": "25"}
        assert rows[1] == {"name": "Bob", "value": "30"}

    def test_parse_csv_file_not_found(self, engine):
        """Test CSV parsing with non-existent file."""
        with pytest.raises(FileNotFoundError):
            engine.parse_csv("/non/existent/file.csv")

    def test_parse_csv_empty_file(self, engine, temp_dir):
        """Test CSV parsing with empty file."""
        csv_file = temp_dir / "empty.csv"
        csv_file.write_text("")

        with pytest.raises(ValueError, match="CSV file is empty"):
            engine.parse_csv(str(csv_file))

    def test_parse_csv_no_data_rows(self, engine, temp_dir):
        """Test CSV parsing with header only."""
        csv_content = "name,value\n"  # Only header, no data
        csv_file = temp_dir / "header_only.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(ValueError, match="No valid data rows found"):
            engine.parse_csv(str(csv_file))

    def test_parse_csv_special_characters(self, engine, temp_dir):
        """Test CSV parsing with special characters and unicode."""
        csv_content = "name,value\nJosé,café\n测试,数据\n"
        csv_file = temp_dir / "special_chars.csv"
        csv_file.write_text(csv_content, encoding='utf-8')

        rows = engine.parse_csv(str(csv_file))

        assert len(rows) == 2
        assert rows[0] == {"name": "José", "value": "café"}
        assert rows[1] == {"name": "测试", "value": "数据"}

    def test_parse_csv_large_file(self, engine, temp_dir):
        """Test CSV parsing with large file (1000+ rows)."""
        # Create large CSV content
        rows = ["name,value"]
        for i in range(1000):
            rows.append(f"test{i},data{i}")

        csv_content = "\n".join(rows)
        csv_file = temp_dir / "large.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        assert len(rows) == 1000
        assert rows[0] == {"name": "test0", "value": "data0"}
        assert rows[-1] == {"name": "test999", "value": "data999"}

    def test_parse_csv_invalid_delimiter_detection(self, engine, temp_dir):
        """Test CSV parsing when delimiter detection fails."""
        # Create CSV with unusual format that might confuse sniffer
        csv_content = "name|value\ntest|data\n"
        csv_file = temp_dir / "unusual.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        # Should still parse correctly with fallback to comma
        assert len(rows) == 1
        assert rows[0] == {"name": "test", "value": "data"}

    def test_parse_csv_malformed_csv(self, engine, temp_dir):
        """Test CSV parsing with malformed content."""
        # Create malformed CSV
        csv_content = "name,value\ntest1,data1\ntest2"  # Missing comma
        csv_file = temp_dir / "malformed.csv"
        csv_file.write_text(csv_content)

        # Should handle gracefully
        rows = engine.parse_csv(str(csv_file))
        assert len(rows) >= 1  # At least the first valid row

    def test_create_batch_jobs(self, engine, temp_dir, run_context):
        """Test batch job creation."""
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        assert manifest.run_id == run_context.run_id_base
        assert manifest.csv_path == str(csv_file)
        assert manifest.total_jobs == 2
        assert len(manifest.jobs) == 2

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

        with pytest.raises(ValueError, match="No valid rows found"):
            engine.create_batch_jobs(str(csv_file))

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
        updated_manifest = engine.get_batch_status(manifest.batch_id)
        assert updated_manifest is not None
        assert updated_manifest.jobs[0].status == "completed"
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
        updated_manifest = engine.get_batch_status(manifest.batch_id)
        assert updated_manifest is not None
        assert updated_manifest.jobs[0].status == "failed"
        assert updated_manifest.jobs[0].error_message == "Test error"
        assert updated_manifest.failed_jobs == 1

    def test_get_batch_status_not_found(self, engine):
        """Test getting status of non-existent batch."""
        result = engine.get_batch_status("non_existent_batch")
        assert result is None

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


class TestStartBatch:
    """Test start_batch function."""

    @patch('src.batch.engine.RunContext.get')
    def test_start_batch_with_new_context(self, mock_get, tmp_path):
        """Test start_batch with new run context."""
        # Mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        mock_context.artifact_dir = Mock(return_value=tmp_path)
        mock_get.return_value = mock_context

        # Create test CSV
        csv_content = "name,value\ntest,data\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock BatchEngine
        with patch('src.batch.engine.BatchEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_manifest = Mock()
            mock_engine.create_batch_jobs.return_value = mock_manifest
            mock_engine_class.return_value = mock_engine

            result = start_batch(str(csv_file))

            assert result == mock_manifest
            mock_get.assert_called_once()
            mock_engine.create_batch_jobs.assert_called_once_with(str(csv_file))

    def test_start_batch_with_provided_context(self, tmp_path):
        """Test start_batch with provided run context."""
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        mock_context.artifact_dir = Mock(return_value=tmp_path)

        # Create test CSV
        csv_content = "name,value\ntest,data\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        # Mock BatchEngine
        with patch('src.batch.engine.BatchEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_manifest = Mock()
            mock_engine.create_batch_jobs.return_value = mock_manifest
            mock_engine_class.return_value = mock_engine

            result = start_batch(str(csv_file), mock_context)

            assert result == mock_manifest
            mock_engine.create_batch_jobs.assert_called_once_with(str(csv_file))
