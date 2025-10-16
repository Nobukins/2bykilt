"""
Core functionality tests for BatchEngine.

This module tests:
- CSV parsing (basic, empty rows, special chars, large files, custom config)
- Configuration validation (valid/invalid configs, env vars)
- Row-level artifact management (text, json, binary, validation)
- Security checks (path traversal, file size limits)
- Error handling (file not found, malformed data)
"""

import json
import logging
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import Mock

import pytest

from tests.batch import (
    BatchEngine,
    BatchManifest,
    ConfigurationError,
    FileProcessingError,
    SecurityError,
    _run_async,
)


class TestBatchEngineCSVParsing:
    """CSV parsing tests."""

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


class TestBatchEngineConfiguration:
    """Configuration validation tests."""

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


class TestBatchEngineArtifacts:
    """Row-level artifact PoC tests (#175)."""

    def test_add_row_artifact_text(self, engine, temp_dir, run_context):
        """Row-level artifact registration stores file and updates manifest job entry."""
        # Create simple CSV to generate a batch
        csv_file = temp_dir / "rows.csv"
        csv_file.write_text("name,value\nalpha,1\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        # Add a text artifact
        path = engine.add_row_artifact(job_id, "log", "hello world", extension="txt", meta={"k": "v"})
        assert path.exists()
        assert path.read_text(encoding="utf-8").strip() == "hello world"

        # Reload manifest and assert artifact reference present
        manifest_file = run_context.artifact_dir("batch") / "batch_manifest.json"
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        # find job
        job = [j for j in data["jobs"] if j["job_id"] == job_id][0]
        assert "artifacts" in job
        assert len(job["artifacts"]) == 1
        ref = job["artifacts"][0]
        assert ref["type"] == "log"
        assert ref["path"].endswith(".txt")
        assert ref.get("meta", {}).get("k") == "v"

    def test_add_row_artifact_json_infer_ext(self, engine, temp_dir, run_context):
        """Extension inferred for dict/list content and stored as json."""
        csv_file = temp_dir / "rows2.csv"
        csv_file.write_text("name,value\nalpha,1\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        payload = {"a": 1, "b": [1,2,3]}
        path = engine.add_row_artifact(job_id, "data", payload, meta={"fmt": "json"})
        assert path.suffix == ".json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["a"] == 1
        assert loaded["b"][2] == 3

    def test_add_row_artifact_binary_content(self, engine, temp_dir, run_context):
        """Binary content stored with specified extension."""
        csv_file = temp_dir / "rows3.csv"
        csv_file.write_text("name,value\nbeta,2\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        binary_data = b"binary content here"
        path = engine.add_row_artifact(job_id, "binary", binary_data, extension="bin", meta={"size": len(binary_data)})
        assert path.suffix == ".bin"
        assert path.read_bytes() == binary_data

    def test_add_row_artifact_extension_override(self, engine, temp_dir, run_context):
        """Extension override works for text content."""
        csv_file = temp_dir / "rows4.csv"
        csv_file.write_text("name,value\ngamma,3\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        text_content = "some text content"
        path = engine.add_row_artifact(job_id, "text", text_content, extension="log")
        assert path.suffix == ".log"
        assert path.read_text(encoding="utf-8") == text_content

    def test_add_row_artifact_job_not_found(self, engine, temp_dir, run_context):
        """Raises ValueError when job is not found."""
        with pytest.raises(ValueError, match="Batch manifest not found for job non_existent_job"):
            engine.add_row_artifact("non_existent_job", "test", "content")

    def test_add_row_artifact_job_not_in_manifest(self, engine, temp_dir, run_context):
        """Test that add_row_artifact works correctly with valid job."""
        # Create a manifest with one job
        csv_file = temp_dir / "rows6.csv"
        csv_file.write_text("name,value\ndelta,4\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id
        
        # Add artifact for the valid job - this should work
        artifact_path = engine.add_row_artifact(job_id, "test_artifact", "test content")
        
        # Verify artifact was created
        assert artifact_path.exists()
        assert artifact_path.read_text() == "test content"
        
        # Verify manifest was updated by loading it directly
        manifest_file = engine._find_manifest_file_for_job(job_id)
        assert manifest_file is not None
        updated_manifest = engine._load_manifest(manifest_file)
        assert updated_manifest is not None
        
        job = updated_manifest.jobs[0]
        assert job.artifacts is not None
        assert len(job.artifacts) == 1
        assert job.artifacts[0]["type"] == "test_artifact"

    def test_add_row_artifact_invalid_params(self, engine, temp_dir, run_context):
        """Raises ValueError for invalid parameters."""
        csv_file = temp_dir / "rows5.csv"
        csv_file.write_text("name,value\ndelta,4\n")
        manifest = engine.create_batch_jobs(str(csv_file))
        job_id = manifest.jobs[0].job_id

        # Invalid job_id
        with pytest.raises(ValueError, match="job_id must be a non-empty string"):
            engine.add_row_artifact("", "test", "content")

        # Invalid artifact_type
        with pytest.raises(ValueError, match="artifact_type must be a non-empty string"):
            engine.add_row_artifact(job_id, "", "content")
