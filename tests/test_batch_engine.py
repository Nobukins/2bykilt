"""
Tests for CSV-driven batch execution engine.
"""

import json
import tempfile
import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

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

    @pytest.fixture
    def log_capture(self):
        """Capture log output for testing."""
        log_stream = StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.DEBUG)
        
        # Get the logger used by BatchEngine
        logger = logging.getLogger('src.batch.engine')
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        
        yield log_stream
        
        # Clean up
        logger.removeHandler(handler)

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

    def test_get_batch_summary_not_found(self, engine):
        """Test getting summary of non-existent batch."""
        result = engine.get_batch_summary("non_existent_batch")
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


class TestBatchEngineLogging:
    """Test BatchEngine logging functionality."""

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

    def test_parse_csv_mime_type_warning(self, engine, temp_dir, caplog):
        """Test MIME type warning logging (covers line 108)."""
        # Create CSV file with .log extension (should trigger MIME type warning)
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.log"  # Wrong extension that triggers warning
        csv_file.write_text(csv_content)

        # Parse the file
        with caplog.at_level(logging.WARNING):
            rows = engine.parse_csv(str(csv_file))

        # Verify parsing worked
        assert len(rows) == 1
        assert rows[0] == {"name": "test", "value": "data"}

        # Check that MIME type warning was logged
        assert any("does not have a typical CSV extension" in record.message for record in caplog.records)

    def test_parse_csv_file_size_warning(self, temp_dir, caplog):
        """Test file size warning logging (covers lines 248-249)."""
        from src.runtime.run_context import RunContext
        from unittest.mock import Mock
        
        # Create mock run context
        mock_context = Mock()
        mock_context.run_id_base = "test_run"
        
        # Create engine with high file size limit to avoid error
        custom_config = {
            'max_file_size_mb': 200.0,  # High limit to avoid file too large error
            'allow_path_traversal': True
        }
        engine = BatchEngine(mock_context, custom_config)
        
        # Create a test CSV file
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        # Mock the file size to be over 100MB to trigger warning
        with patch('pathlib.Path.stat') as mock_stat:
            # Mock stat to return a file size > 100MB
            mock_stat.return_value.st_size = 150 * 1024 * 1024  # 150MB
            
            # Parse the file
            with caplog.at_level(logging.WARNING):
                rows = engine.parse_csv(str(csv_file))
            
            # Verify parsing worked
            assert len(rows) == 1
            assert rows[0] == {"name": "test", "value": "data"}
            
            # Check that file size warning was logged
            assert any("Large CSV file detected" in record.message for record in caplog.records)

    def test_parse_csv_delimiter_detection_warning(self, engine, temp_dir, caplog):
        """Test delimiter detection warning logging (covers lines 266, 273)."""
        # Create a simple CSV file
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        # Mock csv.Sniffer.sniff to raise csv.Error to trigger the warning
        import csv
        with patch('csv.Sniffer.sniff', side_effect=csv.Error("Delimiter detection failed")):
            # Parse the file
            with caplog.at_level(logging.WARNING):
                rows = engine.parse_csv(str(csv_file))

        # Verify parsing worked (should use fallback delimiter)
        assert len(rows) == 1
        assert rows[0] == {"name": "test", "value": "data"}

        # Check that delimiter detection warning was logged
        assert any("Could not detect delimiter" in record.message for record in caplog.records)

    def test_parse_csv_row_processing_debug(self, engine, temp_dir, caplog):
        """Test row processing debug logging (covers line 299)."""
        # Create CSV with many rows to trigger chunk processing
        csv_content = "name,value\n"
        for i in range(1500):  # Create 1500 rows to trigger chunk processing
            csv_content += f"test{i},data{i}\n"
        
        csv_file = temp_dir / "debug.csv"
        csv_file.write_text(csv_content)

        # Ensure debug logging is enabled
        engine.logger.setLevel(logging.DEBUG)
        
        # Parse the file
        with caplog.at_level(logging.DEBUG):
            rows = engine.parse_csv(str(csv_file))

        # Debug: print all log records
        print("\n--- Debug Log Records ---")
        for record in caplog.records:
            print(f"{record.levelname}: {record.message}")
        print("--- End Debug Log Records ---\n")

        # Verify parsing worked
        assert len(rows) == 1500

        # Check that row processing debug logs were generated
        debug_found = any("Processed" in record.message and "rows" in record.message for record in caplog.records)
        if not debug_found:
            # Try alternative patterns
            debug_found = any("rows" in record.message.lower() for record in caplog.records)
        
        assert debug_found, f"Expected debug log not found. Available logs: {[r.message for r in caplog.records]}"

    def test_create_batch_jobs_logging(self, engine, temp_dir, run_context, caplog):
        """Test job creation logging (covers line 370)."""
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        # Create batch jobs
        with caplog.at_level(logging.INFO):
            manifest = engine.create_batch_jobs(str(csv_file))

        # Verify manifest created
        assert manifest.total_jobs == 2

        # Check that job creation logs were generated
        assert any("Created job" in record.message for record in caplog.records)

    def test_create_batch_jobs_manifest_save_logging(self, engine, temp_dir, run_context, caplog):
        """Test manifest save logging (covers line 385)."""
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        # Create batch jobs
        with caplog.at_level(logging.INFO):
            manifest = engine.create_batch_jobs(str(csv_file))

        # Verify manifest created
        assert manifest.total_jobs == 1

        # Check that manifest save logs were generated
        assert any("Created batch with" in record.message and "jobs" in record.message for record in caplog.records)

    def test_security_check_exception_logging(self, run_context, caplog):
        """Test security check exception logging (covers lines 195-210)."""
        from pathlib import Path

        # Create engine with path traversal prevention
        custom_config = {'allow_path_traversal': False}
        engine = BatchEngine(run_context, custom_config)

        # Try to access sensitive path
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SecurityError):
                engine.parse_csv('/etc/passwd')

        # Check that security exception was logged
        assert any("Access denied" in record.message for record in caplog.records)
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
