"""Integration tests for CSV batch processing CLI commands.

This module tests the complete CSV batch processing workflow including:
- CSV input normalization for NamedString support (Issue #198)
- Batch creation via CLI (batch start)
- Batch status checking (batch status)
- Job status updates (batch update-job)
"""
import io
import os
import subprocess
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.batch.test_csv_normalization import normalize_csv_input


class TestBatchCLIIntegration:
    """Integration tests for batch CLI commands."""

    def test_batch_start_command_creates_batch_from_csv(self):
        """Test: batch start command creates batch from CSV file.

        Command: python bykilt.py batch start tests/batch/test.csv
        Evaluates: CSV file parsing, batch creation, job generation
        """
        # Execute batch start command
        result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'start', 'tests/batch/test.csv'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        # Verify command succeeded
        assert result.returncode == 0, f"Command failed: {result.stderr}"

        # Verify output contains expected information
        output = result.stdout
        assert "🚀 Starting batch execution from tests/batch/test.csv" in output
        assert "✅ Batch created successfully!" in output
        assert "Batch ID:" in output
        assert "Run ID:" in output
        assert "Total jobs: 3" in output
        assert "Jobs directory:" in output
        assert "Manifest:" in output

    def test_batch_status_command_shows_batch_details(self):
        """Test: batch status command displays batch and job information.

        Command: python bykilt.py batch status <batch_id>
        Evaluates: Batch manifest loading, job status display, data structure compatibility
        """
        # First create a batch to get a valid batch ID
        result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'start', 'tests/batch/test.csv'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert result.returncode == 0

        # Extract batch ID from output
        output_lines = result.stdout.split('\n')
        batch_id_line = next(line for line in output_lines if "Batch ID:" in line)
        batch_id = batch_id_line.split("Batch ID: ")[1].strip()

        # Now test batch status command
        status_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status', batch_id
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        # Verify command succeeded
        assert status_result.returncode == 0, f"Status command failed: {status_result.stderr}"

        # Verify output contains expected batch information
        status_output = status_result.stdout
        assert f"📊 Getting status for batch {batch_id}" in status_output
        assert "✅ Batch status:" in status_output
        assert f"Batch ID: {batch_id}" in status_output
        assert "Run ID:" in status_output
        assert "CSV Path: tests/batch/test.csv" in status_output
        assert "Total jobs: 3" in status_output
        assert "Completed: 0" in status_output
        assert "Failed: 0" in status_output
        assert "Created:" in status_output

        # Verify job details are displayed
        assert "📋 Job details:" in status_output
        assert "⏳" in status_output  # Pending status icon
        assert "pending" in status_output

    def test_batch_update_job_command_updates_status(self):
        """Test: batch update-job command updates individual job status.

        Command: python bykilt.py batch update-job <job_id> completed
        Evaluates: Job status updates, manifest persistence, error handling
        """
        # First create a batch
        result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'start', 'tests/batch/test.csv'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert result.returncode == 0

        # Extract batch ID and get job details
        status_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status',
            result.stdout.split("Batch ID: ")[1].split()[0]
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert status_result.returncode == 0

        # Extract first job ID from status output
        status_lines = status_result.stdout.split('\n')
        job_line = next(line for line in status_lines if "⏳" in line and "_0001:" in line)
        job_id = job_line.split()[1].split(':')[0]

        # Update job status to completed
        update_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'update-job', job_id, 'completed'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        # Verify command succeeded
        assert update_result.returncode == 0, f"Update command failed: {update_result.stderr}"

        # Verify output
        update_output = update_result.stdout
        assert f"🔄 Updating job {job_id} to completed" in update_output
        assert "✅ Job status updated successfully!" in update_output

        # Verify status was actually updated by checking batch status again
        final_status_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status',
            result.stdout.split("Batch ID: ")[1].split()[0]
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert final_status_result.returncode == 0
        final_output = final_status_result.stdout
        assert "Completed: 1" in final_output  # Should now show 1 completed job
        assert f"✅ {job_id}: completed" in final_output

    def test_batch_status_command_handles_invalid_batch_id(self):
        """Test: batch status command handles non-existent batch IDs gracefully.

        Command: python bykilt.py batch status invalid-batch-id
        Evaluates: Error handling for invalid batch IDs
        """
        result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status', 'invalid-batch-id-12345'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        # Should return error code 1
        assert result.returncode == 1

        # Verify error message
        output = result.stdout + result.stderr
        assert "❌ Batch invalid-batch-id-12345 not found" in output


class TestCSVInputNormalizationIntegration:
    """Integration tests for CSV input normalization with CLI."""

    def test_csv_normalization_with_named_string_mock(self):
        """Test: CSV normalization handles NamedString-like objects correctly.

        Evaluates: NamedString support in CSV input normalization (Issue #198)
        """
        # Create mock NamedString object (simulating Gradio upload)
        class MockNamedString:
            def __init__(self, value):
                self.value = value

        csv_content = "template_type,template_name,param\nscript,test-script,query=test"
        named_string = MockNamedString(csv_content)

        # Test normalization function
        result = normalize_csv_input(named_string)
        expected = csv_content.encode('utf-8')
        assert result == expected

    def test_csv_normalization_with_file_like_object(self):
        """Test: CSV normalization handles file-like objects correctly.

        Evaluates: File-like object support in CSV input normalization
        """
        csv_content = b"template_type,template_name,param\nscript,test-script,query=test"
        file_like = io.BytesIO(csv_content)

        result = normalize_csv_input(file_like)
        assert result == csv_content

    def test_csv_normalization_with_path_string(self):
        """Test: CSV normalization handles file path strings correctly.

        Evaluates: File path support in CSV input normalization
        """
        csv_content = b"template_type,template_name,param\nscript,test-script,query=test"

        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False) as f:
            f.write(csv_content)
            temp_path = f.name

        try:
            result = normalize_csv_input(temp_path)
            assert result == csv_content
        finally:
            os.remove(temp_path)

    def test_csv_normalization_unsupported_type_raises_error(self):
        """Test: CSV normalization raises error for unsupported input types.

        Evaluates: Error handling for invalid input types
        """
        with pytest.raises(ValueError, match="Unsupported CSV input type"):
            normalize_csv_input(12345)


class TestBatchWorkflowEndToEnd:
    """End-to-end tests for complete batch processing workflow."""

    def test_complete_batch_workflow(self):
        """Test: Complete batch workflow from creation to completion.

        Commands:
        1. python bykilt.py batch start tests/batch/test.csv
        2. python bykilt.py batch status <batch_id>
        3. python bykilt.py batch update-job <job_id> completed (for each job)

        Evaluates: Full batch processing lifecycle, data persistence, status tracking
        """
        # Step 1: Create batch
        start_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'start', 'tests/batch/test.csv'
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert start_result.returncode == 0
        batch_id = start_result.stdout.split("Batch ID: ")[1].split()[0]

        # Step 2: Check initial status
        status_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status', batch_id
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert status_result.returncode == 0
        assert "Total jobs: 3" in status_result.stdout
        assert "Completed: 0" in status_result.stdout

        # Step 3: Update all jobs to completed
        for i in range(1, 4):  # Jobs are 0001, 0002, 0003
            job_id = f"{status_result.stdout.split('Run ID: ')[1].split()[0]}_{i:04d}"

            update_result = subprocess.run([
                'python', 'bykilt.py', 'batch', 'update-job', job_id, 'completed'
            ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

            assert update_result.returncode == 0

        # Step 4: Verify all jobs completed
        final_status_result = subprocess.run([
            'python', 'bykilt.py', 'batch', 'status', batch_id
        ], capture_output=True, text=True, cwd=Path(__file__).parent.parent.parent)

        assert final_status_result.returncode == 0
        final_output = final_status_result.stdout
        assert "Completed: 3" in final_output
        assert "Failed: 0" in final_output

        # Verify all jobs show as completed
        lines = final_output.split('\n')
        job_lines = [line for line in lines if '✅' in line and ': completed' in line]
        assert len(job_lines) == 3


if __name__ == "__main__":
    pytest.main([__file__])