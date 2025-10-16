"""
Batch execution and logging tests for BatchEngine.

This module tests:
- start_batch() function - Entry point for batch execution
- Logging functionality (MIME type warnings, file size warnings, delimiter detection)
- Job creation and execution logging
- Security check exception logging
- Batch execution with different contexts and configurations
"""

import logging
from pathlib import Path
from unittest.mock import patch, Mock

import pytest

from tests.batch import (
    BatchEngine,
    _run_async,
)
from src.batch.engine import start_batch


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

            async def _inner():
                return await start_batch(str(csv_file), execute_immediately=False)

            result = _run_async(_inner)

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

            async def _inner():
                return await start_batch(str(csv_file), mock_context, execute_immediately=False)

            result = _run_async(_inner)

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

            async def _inner():
                return await start_batch(str(csv_file), mock_context, custom_config, execute_immediately=False)

            result = _run_async(_inner)

            assert result == mock_manifest
            # Verify BatchEngine was created with config
            mock_engine_class.assert_called_once_with(mock_context, custom_config)
            mock_engine.create_batch_jobs.assert_called_once_with(str(csv_file))


class TestBatchEngineLogging:
    """Test BatchEngine logging functionality."""

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
        from tests.batch import SecurityError

        # Create engine with path traversal prevention
        custom_config = {'allow_path_traversal': False}
        engine = BatchEngine(run_context, custom_config)

        # Try to access sensitive path
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SecurityError):
                engine.parse_csv('/etc/passwd')

        # Check that security exception was logged
        assert any("Access denied" in record.message for record in caplog.records)
