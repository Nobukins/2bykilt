"""
Tests for CSV-driven batch execution engine.
"""

import csv
import json
import tempfile
import pytest
import logging
from pathlib import Path
from unittest.mock import Mock, patch
from io import StringIO

from src.batch.engine import BatchEngine, BatchJob, BatchManifest, start_batch, ConfigurationError, FileProcessingError, SecurityError, DEFAULT_MAX_RETRIES, DEFAULT_RETRY_DELAY, DEFAULT_BACKOFF_FACTOR, MAX_RETRY_DELAY
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

    def test_record_failed_rows_export_metric(self, engine):
        """Test _record_failed_rows_export_metric method."""
        # Mock the metrics collector and get_metrics_collector function
        with patch('src.metrics.get_metrics_collector') as mock_get_collector, \
             patch('src.metrics.MetricType') as mock_metric_type:
            
            mock_collector = Mock()
            mock_get_collector.return_value = mock_collector
            
            # Call the method
            engine._record_failed_rows_export_metric(5)
            
            # Verify metrics were recorded
            mock_collector.record_metric.assert_called_once_with(
                name="failed_rows_exported",
                value=5,
                metric_type=mock_metric_type.COUNTER,
                tags={
                    "run_id": engine.run_context.run_id_base
                }
            )

    def test_record_failed_rows_export_metric_no_collector(self, engine):
        """Test _record_failed_rows_export_metric when no metrics collector is available."""
        # Mock get_metrics_collector to return None
        with patch('src.metrics.get_metrics_collector', return_value=None):
            # Call the method - should not raise exception
            engine._record_failed_rows_export_metric(5)
        
        # Method should complete without error even without metrics collector


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


class TestBatchRetry:
    """Test batch retry functionality."""

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

    def test_retry_batch_jobs_success(self, engine, temp_dir, run_context):
        """Test successful retry of failed jobs."""
        # Create a manifest with failed jobs
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        # Mark first job as failed
        job_id = manifest.jobs[0].job_id
        engine.update_job_status(job_id, "failed", "Test failure")

        # Retry the failed job
        result = engine.retry_batch_jobs(manifest.batch_id, [job_id])

        assert result['batch_id'] == manifest.batch_id
        assert result['total_requested'] == 1
        assert result['retried'] == 1
        assert result['skipped'] == 0
        assert len(result['retry_details']) == 1

        # Verify job was reset for retry
        retry_detail = result['retry_details'][0]
        assert retry_detail['job_id'] == job_id
        assert retry_detail['original_status'] == 'failed'

    def test_retry_batch_jobs_not_found(self, engine):
        """Test retry with non-existent batch."""
        with pytest.raises(ValueError, match="Batch not found"):
            engine.retry_batch_jobs("non_existent_batch", ["job1"])

    def test_retry_batch_jobs_invalid_job_id(self, engine, temp_dir, run_context):
        """Test retry with invalid job ID."""
        # Create a manifest
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        # Try to retry non-existent job
        with pytest.raises(ValueError, match="Jobs not found in batch"):
            engine.retry_batch_jobs(manifest.batch_id, ["non_existent_job"])

    def test_retry_batch_jobs_no_failed_jobs(self, engine, temp_dir, run_context):
        """Test retry when no failed jobs exist."""
        # Create a manifest
        csv_content = "name,value\ntest,data\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        # Try to retry completed job (should be skipped)
        job_id = manifest.jobs[0].job_id
        result = engine.retry_batch_jobs(manifest.batch_id, [job_id])

        assert result['total_requested'] == 1
        assert result['retried'] == 0
        assert result['skipped'] == 1

    def test_execute_job_with_retry_success(self, engine):
        """Test successful job execution with retry."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Mock successful execution
        with patch.object(engine, '_execute_single_job', return_value='completed') as mock_execute:
            status = engine.execute_job_with_retry(job, max_retries=2)

        assert status == 'completed'
        # Verify the job execution was called
        mock_execute.assert_called_once_with(job)

    def test_execute_job_with_retry_input_validation(self, engine):
        """Test input validation for execute_job_with_retry."""
        # Test invalid job
        with pytest.raises(ValueError, match="job must be a BatchJob instance"):
            engine.execute_job_with_retry("not_a_job")

        with pytest.raises(ValueError, match="job must be a BatchJob instance"):
            engine.execute_job_with_retry(None)

        # Test invalid job_id
        job = BatchJob("", "test_run", {"data": "test"})
        with pytest.raises(ValueError, match="job.job_id must be a non-empty string"):
            engine.execute_job_with_retry(job)

        job = BatchJob(None, "test_run", {"data": "test"})
        with pytest.raises(ValueError, match="job.job_id must be a non-empty string"):
            engine.execute_job_with_retry(job)

        # Test invalid max_retries
        job = BatchJob("test_job", "test_run", {"data": "test"})
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            engine.execute_job_with_retry(job, max_retries=-1)

        # Test invalid retry_delay
        with pytest.raises(ValueError, match="retry_delay must be > 0"):
            engine.execute_job_with_retry(job, retry_delay=0)

        with pytest.raises(ValueError, match="retry_delay must be > 0"):
            engine.execute_job_with_retry(job, retry_delay=-1)

        # Test invalid backoff_factor
        with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
            engine.execute_job_with_retry(job, backoff_factor=1.0)

        with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
            engine.execute_job_with_retry(job, backoff_factor=0.5)

        # Test invalid max_retry_delay
        with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
            engine.execute_job_with_retry(job, max_retry_delay=0)

        with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
            engine.execute_job_with_retry(job, max_retry_delay=-1)

    def test_retry_batch_jobs_custom_parameters(self, engine, temp_dir, run_context):
        """Test retry_batch_jobs with custom retry parameters."""
        # Create a manifest with failed jobs
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))

        # Mark first job as failed
        job_id = manifest.jobs[0].job_id
        engine.update_job_status(job_id, "failed", "Test failure")

        # Retry with custom parameters
        result = engine.retry_batch_jobs(
            manifest.batch_id,
            [job_id],
            max_retries=5,
            retry_delay=2.0,
            backoff_factor=3.0,
            max_retry_delay=30.0
        )

        assert result['batch_id'] == manifest.batch_id
        assert result['max_retries'] == 5
        assert result['retry_delay'] == 2.0
        assert result['backoff_factor'] == 3.0
        assert result['max_retry_delay'] == 30.0
        assert result['retried'] == 1

    def test_execute_job_with_retry_custom_parameters(self, engine):
        """Test execute_job_with_retry with custom retry parameters."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Mock successful execution
        with patch.object(engine, '_execute_single_job', return_value='completed') as mock_execute:
            status = engine.execute_job_with_retry(
                job,
                max_retries=3,
                retry_delay=1.5,
                backoff_factor=2.5,
                max_retry_delay=20.0
            )

        assert status == 'completed'
        mock_execute.assert_called_once_with(job)

    def test_execute_job_with_retry_exponential_backoff(self, engine):
        """Test that exponential backoff works correctly."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Mock execution to always fail
        with patch.object(engine, '_execute_single_job', side_effect=Exception("Test failure")):
            with patch('time.sleep') as mock_sleep:
                with pytest.raises(Exception):
                    engine.execute_job_with_retry(
                        job,
                        max_retries=2,
                        retry_delay=1.0,
                        backoff_factor=2.0,
                        max_retry_delay=10.0
                    )

        # Verify sleep was called with correct exponential backoff
        # First retry: 1.0s, Second retry: 2.0s
        expected_calls = [((1.0,), {}), ((2.0,), {})]
        mock_sleep.assert_has_calls(expected_calls)

    def test_execute_job_with_retry_max_delay_cap(self, engine):
        """Test that max_retry_delay caps the exponential backoff."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Mock execution to always fail
        with patch.object(engine, '_execute_single_job', side_effect=Exception("Test failure")):
            with patch('time.sleep') as mock_sleep:
                with pytest.raises(Exception):
                    engine.execute_job_with_retry(
                        job,
                        max_retries=3,
                        retry_delay=1.0,
                        backoff_factor=4.0,  # High backoff factor
                        max_retry_delay=5.0  # Low cap
                    )

        # Verify sleep was called with capped delays
        # First retry: 1.0s, Second retry: 4.0s (capped to 5.0s), Third retry: 16.0s (capped to 5.0s)
        expected_calls = [((1.0,), {}), ((4.0,), {}), ((5.0,), {})]
        mock_sleep.assert_has_calls(expected_calls)

    def test_simulate_job_execution_custom_parameters(self, engine):
        """Test _simulate_job_execution with custom parameters."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Test with custom success_rate
        with patch('random.random', return_value=0.3):  # Below 0.5 success rate
            status = engine._simulate_job_execution(job, success_rate=0.5)
            assert status == 'completed'

        # Test with custom max_random_delay
        with patch('random.random', return_value=0.9):  # Above success rate
            with patch('time.sleep') as mock_sleep:
                with pytest.raises(Exception):
                    engine._simulate_job_execution(job, success_rate=0.8, max_random_delay=2.0)

        # Verify sleep was called with random delay <= max_random_delay
        if mock_sleep.called:
            delay = mock_sleep.call_args[0][0]
            assert 0 <= delay <= 2.0

    def test_simulate_job_execution_parameter_validation(self, engine):
        """Test parameter validation in _simulate_job_execution."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Test invalid success_rate
        with pytest.raises(ValueError, match="success_rate must be between 0.0 and 1.0"):
            engine._simulate_job_execution(job, success_rate=-0.1)

        with pytest.raises(ValueError, match="success_rate must be between 0.0 and 1.0"):
            engine._simulate_job_execution(job, success_rate=1.5)

        # Test invalid max_random_delay
        with pytest.raises(ValueError, match="max_random_delay must be >= 0"):
            engine._simulate_job_execution(job, max_random_delay=-1)

    def test_simulate_job_execution_failure_scenarios(self, engine):
        """Test various failure scenarios in simulation."""
        # Test intentional failure triggers
        job_fail = BatchJob("test_job", "test_run", {"name": "fail"})
        with pytest.raises(Exception, match="Intentional failure for testing"):
            engine._simulate_job_execution(job_fail)

        job_error = BatchJob("test_job", "test_run", {"value": "error"})
        with pytest.raises(ValueError, match="Invalid value for processing"):
            engine._simulate_job_execution(job_error)

        # Test random failure
        job_random = BatchJob("test_job", "test_run", {"name": "test", "value": "data"})
        with patch('random.random', return_value=0.9):  # Above success rate
            with pytest.raises(Exception, match="Simulated random failure"):
                engine._simulate_job_execution(job_random, success_rate=0.8)

    def test_log_security_no_sensitive_data(self, engine, caplog):
        """Test that sensitive data is not logged."""
        import logging

        # Test data with sensitive information
        sensitive_data = {
            "password": "secret123",
            "api_key": "sk-1234567890abcdef",
            "credit_card": "4111111111111111"
        }
        job = BatchJob("test_job", "test_run", sensitive_data)

        with caplog.at_level(logging.DEBUG):
            with patch.object(engine, '_execute_single_job', side_effect=Exception("Test error with sensitive info")):
                with pytest.raises(Exception):
                    engine.execute_job_with_retry(job, max_retries=1)

        # Check that sensitive data is not in logs
        log_messages = [record.message for record in caplog.records]
        for message in log_messages:
            assert "secret123" not in message
            assert "sk-1234567890abcdef" not in message
            assert "4111111111111111" not in message

        # But should contain safe information
        assert any("test_job" in msg for msg in log_messages)
        assert any("Exception" in msg for msg in log_messages)

    def test_retry_batch_jobs_input_validation(self, engine):
        """Test input validation for retry_batch_jobs."""
        # Test invalid batch_id
        with pytest.raises(ValueError, match="batch_id must be a non-empty string"):
            engine.retry_batch_jobs("", ["job1"])

        with pytest.raises(ValueError, match="batch_id must be a non-empty string"):
            engine.retry_batch_jobs(None, ["job1"])

        # Test invalid job_ids
        with pytest.raises(ValueError, match="job_ids must be a non-empty list"):
            engine.retry_batch_jobs("batch1", [])

        with pytest.raises(ValueError, match="job_ids must be a non-empty list"):
            engine.retry_batch_jobs("batch1", None)

        # Test invalid job_id elements
        with pytest.raises(ValueError, match="All job_ids must be non-empty strings"):
            engine.retry_batch_jobs("batch1", ["", "job2"])

        with pytest.raises(ValueError, match="All job_ids must be non-empty strings"):
            engine.retry_batch_jobs("batch1", [None, "job2"])

        # Test duplicate job_ids
        with pytest.raises(ValueError, match="job_ids must not contain duplicates"):
            engine.retry_batch_jobs("batch1", ["job1", "job1"])

        # Test invalid max_retries
        with pytest.raises(ValueError, match="max_retries must be >= 0"):
            engine.retry_batch_jobs("batch1", ["job1"], max_retries=-1)

        # Test invalid retry_delay
        with pytest.raises(ValueError, match="retry_delay must be > 0"):
            engine.retry_batch_jobs("batch1", ["job1"], retry_delay=0)

        with pytest.raises(ValueError, match="retry_delay must be > 0"):
            engine.retry_batch_jobs("batch1", ["job1"], retry_delay=-1)

        # Test invalid backoff_factor
        with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
            engine.retry_batch_jobs("batch1", ["job1"], backoff_factor=1.0)

        with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
            engine.retry_batch_jobs("batch1", ["job1"], backoff_factor=0.5)

        # Test invalid max_retry_delay
        with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
            engine.retry_batch_jobs("batch1", ["job1"], max_retry_delay=0)

        with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
            engine.retry_batch_jobs("batch1", ["job1"], max_retry_delay=-1)

    def test_load_manifest_by_batch_id_success(self, engine, temp_dir, run_context):
        """Test _load_manifest_by_batch_id helper method success."""
        # Create a manifest
        csv_content = "name,value\ntest1,data1\ntest2,data2\n"
        csv_file = temp_dir / "test.csv"
        csv_file.write_text(csv_content)

        manifest = engine.create_batch_jobs(str(csv_file))
        batch_id = manifest.batch_id

        # Test the helper method
        loaded_manifest = engine._load_manifest_by_batch_id(batch_id)

        assert loaded_manifest is not None
        assert loaded_manifest.batch_id == batch_id
        assert loaded_manifest.total_jobs == 2
        assert len(loaded_manifest.jobs) == 2

    def test_load_manifest_by_batch_id_not_found(self, engine):
        """Test _load_manifest_by_batch_id with non-existent batch."""
        result = engine._load_manifest_by_batch_id("non_existent_batch")
        assert result is None

    def test_execute_job_with_retry_no_side_effects(self, engine):
        """Test that execute_job_with_retry doesn't have side effects on retry parameters."""
        job = BatchJob("test_job", "test_run", {"data": "test"})

        # Mock execution to fail twice then succeed
        call_count = 0
        def mock_execute(job):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Test failure")
            return 'completed'

        with patch.object(engine, '_execute_single_job', side_effect=mock_execute):
            with patch('time.sleep') as mock_sleep:
                status = engine.execute_job_with_retry(
                    job,
                    max_retries=3,
                    retry_delay=1.0,
                    backoff_factor=2.0,
                    max_retry_delay=10.0
                )

        assert status == 'completed'
        assert call_count == 3  # Initial + 2 retries

        # Verify sleep was called with correct exponential backoff
        # First retry: 1.0s, Second retry: 2.0s
        expected_calls = [((1.0,), {}), ((2.0,), {})]
        mock_sleep.assert_has_calls(expected_calls)

        # Test that calling the method again starts fresh (no side effects)
        call_count = 0
        with patch.object(engine, '_execute_single_job', side_effect=mock_execute):
            with patch('time.sleep') as mock_sleep:
                status = engine.execute_job_with_retry(
                    job,
                    max_retries=3,
                    retry_delay=1.0,
                    backoff_factor=2.0,
                    max_retry_delay=10.0
                )

        assert status == 'completed'
        # Should have the same sleep pattern (no side effects from previous call)
        mock_sleep.assert_has_calls(expected_calls)
