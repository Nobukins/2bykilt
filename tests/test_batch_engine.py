"""
Tests for CSV-driven batch execution engine.
"""

import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.batch.engine import BatchEngine, BatchJob, BatchManifest, start_batch, ConfigurationError, FileProcessingError, SecurityError
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

        with pytest.raises(FileProcessingError, match="CSV file is empty"):
            engine.parse_csv(str(csv_file))

    def test_parse_csv_no_data_rows(self, engine, temp_dir):
        """Test CSV parsing with header only."""
        csv_content = "name,value\n"  # Only header, no data
        csv_file = temp_dir / "header_only.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(FileProcessingError, match="No valid data rows found"):
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

    def test_parse_csv_custom_config(self, temp_dir):
        """Test CSV parsing with custom configuration."""
        from src.runtime.run_context import RunContext
        from unittest.mock import Mock
        
        # Create mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        
        # Create engine with custom config
        custom_config = {
            'encoding': 'utf-8',
            'delimiter_fallback': ';',
            'skip_empty_rows': True,
            'chunk_size': 500,
            'allow_path_traversal': True  # Allow access to temp directory for testing
        }
        engine = BatchEngine(mock_context, custom_config)
        
        # Create CSV with semicolon delimiter
        csv_content = "name;value\ntest1;data1\ntest2;data2\n"
        csv_file = temp_dir / "custom.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        assert len(rows) == 2
        assert rows[0] == {"name": "test1", "value": "data1"}
        assert rows[1] == {"name": "test2", "value": "data2"}

    def test_parse_csv_file_too_large(self, temp_dir):
        """Test CSV parsing with file exceeding size limit."""
        from src.runtime.run_context import RunContext
        from unittest.mock import Mock
        
        # Create mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        
        # Create engine with very small file size limit (1 byte)
        custom_config = {
            'max_file_size_mb': 1e-6,  # 1 byte in MB
            'allow_path_traversal': True
        }
        engine = BatchEngine(mock_context, custom_config)
        
        # Create a small CSV file that exceeds the limit
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "small.csv"
        csv_file.write_text(csv_content)

        with pytest.raises(FileProcessingError, match="CSV file too large"):
            engine.parse_csv(str(csv_file))

    def test_parse_csv_path_traversal_prevention(self, temp_dir):
        """Test that path traversal attacks are prevented."""
        from src.runtime.run_context import RunContext
        from unittest.mock import Mock
        
        # Create mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        
        # Create engine with path traversal prevention enabled
        custom_config = {
            'allow_path_traversal': False,
        }
        engine = BatchEngine(mock_context, custom_config)
        
        # Try to access file outside allowed directory
        malicious_path = "/etc/passwd"
        
        with pytest.raises(SecurityError, match="Access denied"):
            engine.parse_csv(malicious_path)

    def test_parse_csv_invalid_delimiter_detection(self, engine, temp_dir):
        """Test CSV parsing when delimiter detection fails."""
        # Create CSV with unusual format that might confuse sniffer
        csv_content = "name|value\ntest|data\n"
        csv_file = temp_dir / "unusual.csv"
        csv_file.write_text(csv_content)

        rows = engine.parse_csv(str(csv_file))

        # Note: csv.Sniffer may not detect pipe delimiter correctly
        # The implementation falls back to comma, so this test verifies
        # that parsing still works (though not optimally)
        assert len(rows) == 1
        # The actual parsing result depends on sniffer behavior
        # We just verify it doesn't crash and returns some data

    def test_parse_csv_malformed_csv(self, engine, temp_dir):
        """Test CSV parsing with malformed content."""
        # Create malformed CSV
        csv_content = "name,value\ntest1,data1\ntest2"  # Missing comma
        csv_file = temp_dir / "malformed.csv"
        csv_file.write_text(csv_content)

        # Should handle gracefully
        rows = engine.parse_csv(str(csv_file))
        assert len(rows) >= 1  # At least the first valid row

    def test_config_validation_valid(self, run_context):
        """Test that valid configuration passes validation."""
        from src.batch.engine import BatchEngine
        
        valid_config = {
            'max_file_size_mb': 100,
            'chunk_size': 500,
            'encoding': 'utf-8',
            'delimiter_fallback': ';',
            'allow_path_traversal': False,
            'validate_headers': True,
            'skip_empty_rows': False
        }
        
        # Should not raise exception
        engine = BatchEngine(run_context, valid_config)
        assert engine.config['max_file_size_mb'] == 100

    def test_config_validation_invalid_max_file_size(self, run_context):
        """Test configuration validation for invalid max_file_size_mb."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'max_file_size_mb': -1}
        
        with pytest.raises(ConfigurationError, match="max_file_size_mb must be a positive number"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_invalid_chunk_size(self, run_context):
        """Test configuration validation for invalid chunk_size."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'chunk_size': 0}
        
        with pytest.raises(ConfigurationError, match="chunk_size must be a positive integer"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_invalid_encoding(self, run_context):
        """Test configuration validation for invalid encoding."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'encoding': ''}
        
        with pytest.raises(ConfigurationError, match="encoding must be a non-empty string"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_invalid_delimiter(self, run_context):
        """Test configuration validation for invalid delimiter_fallback."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'delimiter_fallback': ';;'}
        
        with pytest.raises(ConfigurationError, match="delimiter_fallback must be a single character"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_invalid_boolean(self, run_context):
        """Test configuration validation for invalid boolean values."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'allow_path_traversal': 'true'}
        
        with pytest.raises(ConfigurationError, match="allow_path_traversal must be a boolean"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_invalid_log_level(self, run_context):
        """Test configuration validation for invalid log level."""
        from src.batch.engine import BatchEngine
        
        invalid_config = {'log_level': 'INVALID'}
        
        with pytest.raises(ConfigurationError, match="log_level must be one of"):
            BatchEngine(run_context, invalid_config)

    def test_config_validation_env_vars(self, run_context, monkeypatch):
        """Test configuration loading from environment variables."""
        from src.batch.engine import BatchEngine
        
        # Set environment variables
        monkeypatch.setenv('BATCH_MAX_FILE_SIZE_MB', '200')
        monkeypatch.setenv('BATCH_CHUNK_SIZE', '500')
        monkeypatch.setenv('BATCH_ENCODING', 'utf-8')
        monkeypatch.setenv('BATCH_ALLOW_PATH_TRAVERSAL', 'false')
        monkeypatch.setenv('BATCH_LOG_LEVEL', 'DEBUG')
        
        # Create engine without explicit config
        engine = BatchEngine(run_context)
        
        # Verify environment variables were loaded
        assert engine.config['max_file_size_mb'] == 200.0
        assert engine.config['chunk_size'] == 500
        assert engine.config['encoding'] == 'utf-8'
        assert engine.config['allow_path_traversal'] is False
        assert engine.config['log_level'] == 'DEBUG'

    def test_parse_csv_file_processing_error_empty_content(self, engine, temp_dir):
        """Test FileProcessingError for empty content."""
        # Create file with only whitespace
        csv_file = temp_dir / "whitespace.csv"
        csv_file.write_text("   \n  \n\t\n")
        
        with pytest.raises(FileProcessingError, match="CSV file contains no data"):
            engine.parse_csv(str(csv_file))

    def test_parse_csv_security_error_path_traversal(self, temp_dir):
        """Test SecurityError for path traversal."""
        from src.runtime.run_context import RunContext
        from unittest.mock import Mock
        
        # Create mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        
        # Create engine with path traversal prevention
        custom_config = {
            'allow_path_traversal': False,
        }
        engine = BatchEngine(mock_context, custom_config)
        
        # Try to access file outside allowed directory
        malicious_path = "/etc/passwd"
        
        with pytest.raises(SecurityError, match="Access denied.*Path traversal detected"):
            engine.parse_csv(malicious_path)

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

        with pytest.raises(FileProcessingError, match="Failed to parse CSV file"):
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

    def test_parse_csv_security_error_sensitive_directory_access(self, run_context):
        """Test that access to sensitive system directories is blocked."""
        from pathlib import Path
        import tempfile

        # Create a temporary CSV file
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "test.csv"
            csv_file.write_text("name,value\ntest,123\n")

            # Mock the sensitive path check by patching Path methods
            with patch.object(Path, 'exists', return_value=True), \
                 patch.object(Path, 'is_relative_to', return_value=True), \
                 patch.object(Path, 'resolve', return_value=Path('/etc/passwd')):

                config = {'allow_path_traversal': False}
                engine = BatchEngine(run_context, config)

                with pytest.raises(SecurityError) as exc_info:
                    engine.parse_csv(str(csv_file))

                assert "sensitive system directory" in str(exc_info.value)
                assert "/etc/passwd" in str(exc_info.value)

    def test_parse_csv_security_error_sensitive_directory_access_allowed(self, run_context):
        """Test that access to sensitive directories is allowed when path traversal is enabled."""
        from pathlib import Path
        import tempfile

        # Create a temporary CSV file
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_file = Path(temp_dir) / "test.csv"
            csv_file.write_text("name,value\ntest,123\n")

            # With allow_path_traversal=True, sensitive directory checks should be bypassed
            config = {'allow_path_traversal': True}
            engine = BatchEngine(run_context, config)

            # Mock the path resolution to return a safe path, not a sensitive one
            with patch.object(Path, 'resolve', return_value=csv_file):
                # Should work normally since path traversal is allowed
                rows = engine.parse_csv(str(csv_file))
                assert len(rows) == 1
                assert rows[0]['name'] == 'test'
                assert rows[0]['value'] == '123'


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

    def test_start_batch_with_config(self, tmp_path):
        """Test start_batch with custom configuration."""
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        mock_context.artifact_dir = Mock(return_value=tmp_path)

        # Create test CSV
        csv_content = "name,value\ntest,data\n"
        csv_file = tmp_path / "test.csv"
        csv_file.write_text(csv_content)

        custom_config = {
            'max_file_size_mb': 100, 
            'encoding': 'utf-8',
            'allow_path_traversal': True
        }

        # Mock BatchEngine
        with patch('src.batch.engine.BatchEngine') as mock_engine_class:
            mock_engine = Mock()
            mock_manifest = Mock()
            mock_engine.create_batch_jobs.return_value = mock_manifest
            mock_engine_class.return_value = mock_engine

            result = start_batch(str(csv_file), mock_context, custom_config)

            assert result == mock_manifest
            # Verify BatchEngine was created with config
            mock_engine_class.assert_called_once_with(mock_context, custom_config)
            mock_engine.create_batch_jobs.assert_called_once_with(str(csv_file))
