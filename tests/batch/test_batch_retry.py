"""
Batch retry functionality tests for BatchEngine.

This module tests:
- retry_batch_jobs() - Retry failed batch jobs
- execute_job_with_retry() - Execute individual jobs with retry logic
- Exponential backoff implementation
- Retry parameter validation
- Security (no sensitive data in logs)
- Load manifest by batch_id helper methods
"""

import logging
from unittest.mock import patch, Mock

import pytest

from tests.batch import (
    BatchEngine,
    BatchJob,
    _run_async,
)


@pytest.mark.ci_safe
class TestRetryBatchJobs:
    """Tests for retry_batch_jobs() method."""

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


@pytest.mark.ci_safe
class TestExecuteJobWithRetry:
    """Tests for execute_job_with_retry() method."""

    def test_execute_job_with_retry_success(self, engine):
        """Test successful job execution with retry."""

        async def _inner():
            job = BatchJob("test_job", "test_run", {"data": "test"})

            # Mock successful execution
            with patch.object(engine, '_execute_single_job', return_value='completed') as mock_execute:
                status = await engine.execute_job_with_retry(job, max_retries=2)

            assert status == 'completed'
            # Verify the job execution was called
            mock_execute.assert_called_once_with(job)

        _run_async(_inner)

    def test_execute_job_with_retry_input_validation(self, engine):
        """Test input validation for execute_job_with_retry."""

        async def _inner():
            # Test invalid job
            with pytest.raises(ValueError, match="job must be a BatchJob instance"):
                await engine.execute_job_with_retry("not_a_job")

            with pytest.raises(ValueError, match="job must be a BatchJob instance"):
                await engine.execute_job_with_retry(None)

            # Test invalid job_id
            job = BatchJob("", "test_run", {"data": "test"})
            with pytest.raises(ValueError, match="job.job_id must be a non-empty string"):
                await engine.execute_job_with_retry(job)

            job = BatchJob(None, "test_run", {"data": "test"})
            with pytest.raises(ValueError, match="job.job_id must be a non-empty string"):
                await engine.execute_job_with_retry(job)

            # Test invalid max_retries
            job = BatchJob("test_job", "test_run", {"data": "test"})
            with pytest.raises(ValueError, match="max_retries must be >= 0"):
                await engine.execute_job_with_retry(job, max_retries=-1)

            # Test invalid retry_delay
            with pytest.raises(ValueError, match="retry_delay must be > 0"):
                await engine.execute_job_with_retry(job, retry_delay=0)

            with pytest.raises(ValueError, match="retry_delay must be > 0"):
                await engine.execute_job_with_retry(job, retry_delay=-1)

            # Test invalid backoff_factor
            with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
                await engine.execute_job_with_retry(job, backoff_factor=1.0)

            with pytest.raises(ValueError, match="backoff_factor must be > 1.0"):
                await engine.execute_job_with_retry(job, backoff_factor=0.5)

            # Test invalid max_retry_delay
            with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
                await engine.execute_job_with_retry(job, max_retry_delay=0)

            with pytest.raises(ValueError, match="max_retry_delay must be > 0"):
                await engine.execute_job_with_retry(job, max_retry_delay=-1)

        _run_async(_inner)

    def test_execute_job_with_retry_custom_parameters(self, engine):
        """Test execute_job_with_retry with custom retry parameters."""

        async def _inner():
            job = BatchJob("test_job", "test_run", {"data": "test"})

            # Mock successful execution
            with patch.object(engine, '_execute_single_job', return_value='completed') as mock_execute:
                status = await engine.execute_job_with_retry(
                    job,
                    max_retries=3,
                    retry_delay=1.5,
                    backoff_factor=2.5,
                    max_retry_delay=20.0
                )

            assert status == 'completed'
            mock_execute.assert_called_once_with(job)

        _run_async(_inner)


@pytest.mark.ci_safe
class TestExponentialBackoff:
    """Tests for exponential backoff logic."""

    def test_execute_job_with_retry_exponential_backoff(self, engine):
        """Test that exponential backoff works correctly."""

        async def _inner():
            job = BatchJob("test_job", "test_run", {"data": "test"})

            # Mock execution to always fail
            with patch.object(engine, '_execute_single_job', side_effect=Exception("Test failure")):
                with patch('time.sleep') as mock_sleep:
                    with pytest.raises(Exception):
                        await engine.execute_job_with_retry(
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

        _run_async(_inner)

    def test_execute_job_with_retry_max_delay_cap(self, engine):
        """Test that max_retry_delay caps the exponential backoff."""

        async def _inner():
            job = BatchJob("test_job", "test_run", {"data": "test"})

            # Mock execution to always fail
            with patch.object(engine, '_execute_single_job', side_effect=Exception("Test failure")):
                with patch('time.sleep') as mock_sleep:
                    with pytest.raises(Exception):
                        await engine.execute_job_with_retry(
                            job,
                            max_retries=3,
                            retry_delay=1.0,
                            backoff_factor=4.0,  # High backoff factor
                            max_retry_delay=5.0  # Low cap
                        )

            # Verify sleep was called with capped delays
            # First retry: 1.0s, Second retry: 4.0s, Third retry: 16.0s (capped to 5.0s)
            expected_calls = [((1.0,), {}), ((4.0,), {}), ((5.0,), {})]
            mock_sleep.assert_has_calls(expected_calls)

        _run_async(_inner)


@pytest.mark.ci_safe
class TestJobExecutionValidation:
    """Tests for job execution validation."""

    def test_simulate_job_execution_parameter_validation(self, engine):
        """Test parameter validation in _simulate_job_execution."""

        async def _inner():
            job = BatchJob("test_job", "test_run", {"data": "test"})

            # Test missing task/command field
            with pytest.raises(ValueError, match="has no 'task' or 'command' field"):
                await engine._simulate_job_execution(job)
            
            # Test empty row data
            job_no_data = BatchJob("test_job", "test_run", {})
            with pytest.raises(ValueError, match="has no row data"):
                await engine._simulate_job_execution(job_no_data)

        _run_async(_inner)

    def test_simulate_job_execution_failure_scenarios(self, engine):
        """Test various failure scenarios in simulation."""

        async def _inner():
            # Test missing task field
            job_no_task = BatchJob("test_job", "test_run", {"name": "fail"})
            with pytest.raises(ValueError, match="has no 'task' or 'command' field"):
                await engine._simulate_job_execution(job_no_task)

            # Test invalid command
            job_invalid_cmd = BatchJob("test_job", "test_run", {"task": "@invalid_command"})
            with patch('src.config.standalone_prompt_evaluator.pre_evaluate_prompt_standalone') as mock_eval:
                mock_eval.return_value = {'is_command': False}
                with pytest.raises(ValueError, match="is not a valid pre-registered command"):
                    await engine._simulate_job_execution(job_invalid_cmd)

        _run_async(_inner)


@pytest.mark.ci_safe
class TestRetrySecurityAndLogging:
    """Tests for security and logging in retry functionality."""

    def test_log_security_no_sensitive_data(self, engine, caplog):
        """Test that sensitive data is not logged."""

        async def _inner():
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
                        await engine.execute_job_with_retry(job, max_retries=1)

            # Check that sensitive data is not in logs
            log_messages = [record.message for record in caplog.records]
            for message in log_messages:
                assert "secret123" not in message
                assert "sk-1234567890abcdef" not in message
                assert "4111111111111111" not in message

            # But should contain safe information
            assert any("test_job" in msg for msg in log_messages)
            assert any("Exception" in msg for msg in log_messages)

        _run_async(_inner)


@pytest.mark.ci_safe
class TestManifestHelpers:
    """Tests for manifest helper methods."""

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
