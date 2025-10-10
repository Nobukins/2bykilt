"""
Unit tests for GIF Fallback Worker

Tests cover:
- Feature flag integration
- Queue management and deduplication
- GIF path naming convention
- Existing GIF cache priority
- Retry logic with max attempts
- Worker lifecycle (start/stop)
- Status reporting
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest import mock

import pytest

from src.workers.gif_fallback_worker import (
    ConversionTask,
    GifFallbackWorker,
    get_worker,
)


@pytest.fixture
def worker():
    """Create a fresh worker instance for each test."""
    return GifFallbackWorker()


@pytest.fixture
def temp_video_file(tmp_path):
    """Create a temporary video file for testing."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_text("fake video content")
    return str(video_path)


@pytest.fixture
def temp_video_with_gif(tmp_path):
    """Create a temporary video file with existing GIF."""
    video_path = tmp_path / "test_video.mp4"
    video_path.write_text("fake video content")
    gif_path = tmp_path / "test_video.gif"
    gif_path.write_text("fake gif content")
    return str(video_path), str(gif_path)


class TestGifPathNaming:
    """Test GIF path naming convention."""
    
    def test_get_gif_path_mp4(self, worker):
        """Test GIF path generation from MP4."""
        video_path = "/path/to/video.mp4"
        expected_gif = "/path/to/video.gif"
        assert worker.get_gif_path(video_path) == expected_gif
    
    def test_get_gif_path_webm(self, worker):
        """Test GIF path generation from WEBM."""
        video_path = "/path/to/video.webm"
        expected_gif = "/path/to/video.gif"
        assert worker.get_gif_path(video_path) == expected_gif
    
    def test_get_gif_path_preserves_directory(self, worker):
        """Test that GIF is created in same directory as video."""
        video_path = "/deep/nested/path/recording.mp4"
        gif_path = worker.get_gif_path(video_path)
        assert Path(gif_path).parent == Path(video_path).parent
    
    def test_get_gif_path_with_multiple_dots(self, worker):
        """Test GIF path with filename containing multiple dots."""
        video_path = "/path/to/my.video.file.mp4"
        expected_gif = "/path/to/my.video.file.gif"
        assert worker.get_gif_path(video_path) == expected_gif


class TestFeatureFlagIntegration:
    """Test feature flag integration."""
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    def test_is_enabled_true(self, mock_flag, worker):
        """Test worker enabled when flag is true."""
        mock_flag.return_value = True
        assert worker.is_enabled() is True
        mock_flag.assert_called_once_with("artifacts.recordings_gif_fallback_enabled")
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    def test_is_enabled_false(self, mock_flag, worker):
        """Test worker disabled when flag is false."""
        mock_flag.return_value = False
        assert worker.is_enabled() is False
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_skipped_when_disabled(self, mock_flag, worker, temp_video_file):
        """Test that enqueue is skipped when feature flag is disabled."""
        mock_flag.return_value = False
        result = await worker.enqueue(temp_video_file)
        assert result is False
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_start_skipped_when_disabled(self, mock_flag, worker):
        """Test that worker start is skipped when disabled."""
        mock_flag.return_value = False
        await worker.start()
        assert worker._running is False
        assert worker._worker_task is None


class TestQueueManagement:
    """Test queue management and deduplication."""
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_new_video(self, mock_flag, worker, temp_video_file):
        """Test enqueueing a new video."""
        mock_flag.return_value = True
        result = await worker.enqueue(temp_video_file)
        assert result is True
        assert worker.queue.qsize() == 1
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_nonexistent_video(self, mock_flag, worker):
        """Test enqueueing a nonexistent video file."""
        mock_flag.return_value = True
        result = await worker.enqueue("/nonexistent/video.mp4")
        assert result is False
        assert worker.queue.qsize() == 0
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_existing_gif(self, mock_flag, worker, temp_video_with_gif):
        """Test that existing GIF prevents re-enqueueing."""
        mock_flag.return_value = True
        video_path, _ = temp_video_with_gif
        result = await worker.enqueue(video_path)
        assert result is False  # Skipped due to existing GIF
        assert worker.queue.qsize() == 0
        assert video_path in worker.completed
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_duplicate_prevention(self, mock_flag, worker, temp_video_file):
        """Test that duplicate videos are not enqueued."""
        mock_flag.return_value = True
        
        # First enqueue
        result1 = await worker.enqueue(temp_video_file)
        assert result1 is True
        assert worker.queue.qsize() == 1
        
        # Mark as processing
        worker.processing.add(temp_video_file)
        
        # Second enqueue (should be skipped)
        result2 = await worker.enqueue(temp_video_file)
        assert result2 is False
        assert worker.queue.qsize() == 1  # No duplicate added
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_completed_video(self, mock_flag, worker, temp_video_file):
        """Test that completed videos are not re-enqueued."""
        mock_flag.return_value = True
        worker.completed.add(temp_video_file)
        
        result = await worker.enqueue(temp_video_file)
        assert result is False
        assert worker.queue.qsize() == 0
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_enqueue_failed_video(self, mock_flag, worker, temp_video_file):
        """Test that previously failed videos are not re-enqueued."""
        mock_flag.return_value = True
        worker.failed[temp_video_file] = "Previous failure"
        
        result = await worker.enqueue(temp_video_file)
        assert result is False
        assert worker.queue.qsize() == 0


class TestRetryLogic:
    """Test retry logic and failure tracking."""
    
    def test_conversion_task_initial_state(self):
        """Test conversion task initial state."""
        task = ConversionTask(
            video_path="/path/video.mp4",
            gif_path="/path/video.gif"
        )
        assert task.retry_count == 0
        assert task.status == "pending"
        assert task.error_message is None
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    @mock.patch('src.workers.gif_fallback_worker.GifFallbackWorker._convert_video_to_gif')
    async def test_retry_on_failure(self, mock_convert, mock_flag, worker, temp_video_file):
        """Test that failed conversions are retried."""
        mock_flag.return_value = True
        mock_convert.return_value = False  # Simulate failure
        
        # Create and process a task manually
        gif_path = worker.get_gif_path(temp_video_file)
        task = ConversionTask(video_path=temp_video_file, gif_path=gif_path)
        
        await worker._process_task(task)
        
        # First failure should trigger retry
        assert task.retry_count == 1
        assert task.status == "pending"
        assert worker.queue.qsize() == 1  # Re-enqueued
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    @mock.patch('src.workers.gif_fallback_worker.GifFallbackWorker._convert_video_to_gif')
    async def test_max_retries_exceeded(self, mock_convert, mock_flag, worker, temp_video_file):
        """Test that tasks fail after max retries."""
        mock_flag.return_value = True
        mock_convert.return_value = False  # Always fail
        
        gif_path = worker.get_gif_path(temp_video_file)
        task = ConversionTask(video_path=temp_video_file, gif_path=gif_path)
        task.retry_count = 2  # Already retried twice
        
        await worker._process_task(task)
        
        # Should fail permanently after 3rd attempt
        assert task.status == "failed"
        assert temp_video_file in worker.failed
        assert "max retries" in worker.failed[temp_video_file].lower()
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    @mock.patch('src.workers.gif_fallback_worker.GifFallbackWorker._convert_video_to_gif')
    async def test_successful_conversion_no_retry(self, mock_convert, mock_flag, worker, temp_video_file):
        """Test that successful conversions don't retry."""
        mock_flag.return_value = True
        mock_convert.return_value = True  # Success
        
        gif_path = worker.get_gif_path(temp_video_file)
        task = ConversionTask(video_path=temp_video_file, gif_path=gif_path)
        
        await worker._process_task(task)
        
        assert task.status == "completed"
        assert task.retry_count == 0
        assert temp_video_file in worker.completed
        assert worker.queue.qsize() == 0  # Not re-enqueued


class TestWorkerLifecycle:
    """Test worker start/stop lifecycle."""
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_start_worker(self, mock_flag, worker):
        """Test starting the worker."""
        mock_flag.return_value = True
        await worker.start()
        assert worker._running is True
        assert worker._worker_task is not None
        await worker.stop()
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_start_already_running(self, mock_flag, worker):
        """Test starting an already running worker."""
        mock_flag.return_value = True
        await worker.start()
        first_task = worker._worker_task
        
        await worker.start()  # Start again
        assert worker._worker_task is first_task  # Same task
        
        await worker.stop()
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_stop_worker(self, mock_flag, worker):
        """Test stopping the worker."""
        mock_flag.return_value = True
        await worker.start()
        assert worker._running is True
        
        await worker.stop()
        assert worker._running is False
    
    async def test_stop_not_running(self, worker):
        """Test stopping a worker that's not running."""
        await worker.stop()  # Should not raise
        assert worker._running is False


class TestStatusReporting:
    """Test status reporting for monitoring."""
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    def test_get_status_initial(self, mock_flag, worker):
        """Test initial status."""
        mock_flag.return_value = True
        status = worker.get_status()
        
        assert status["enabled"] is True
        assert status["running"] is False
        assert status["queue_size"] == 0
        assert status["processing_count"] == 0
        assert status["completed_count"] == 0
        assert status["failed_count"] == 0
    
    @mock.patch('src.workers.gif_fallback_worker.FeatureFlags.is_enabled')
    async def test_get_status_with_activity(self, mock_flag, worker, temp_video_file):
        """Test status with active tasks."""
        mock_flag.return_value = True
        
        # Add to queue
        await worker.enqueue(temp_video_file)
        
        # Simulate processing
        worker.processing.add("/another/video.mp4")
        
        # Simulate completed
        worker.completed.add("/completed/video.mp4")
        
        # Simulate failed
        worker.failed["/failed/video.mp4"] = "Error"
        
        status = worker.get_status()
        assert status["queue_size"] == 1
        assert status["processing_count"] == 1
        assert status["completed_count"] == 1
        assert status["failed_count"] == 1


class TestGlobalWorkerInstance:
    """Test global worker instance singleton pattern."""
    
    def test_get_worker_singleton(self):
        """Test that get_worker returns same instance."""
        worker1 = get_worker()
        worker2 = get_worker()
        assert worker1 is worker2
    
    def test_get_worker_creates_instance(self):
        """Test that get_worker creates instance if none exists."""
        worker = get_worker()
        assert isinstance(worker, GifFallbackWorker)


class TestFfmpegConversion:
    """Test ffmpeg conversion logic."""
    
    @mock.patch('src.workers.gif_fallback_worker.asyncio.create_subprocess_exec')
    async def test_ffmpeg_not_available(self, mock_exec, worker, temp_video_file):
        """Test fallback when ffmpeg is not available."""
        # Simulate ffmpeg not found
        mock_exec.side_effect = FileNotFoundError("ffmpeg not found")
        
        gif_path = worker.get_gif_path(temp_video_file)
        result = await worker._convert_with_ffmpeg(temp_video_file, gif_path)
        
        assert result is False
    
    @mock.patch('src.workers.gif_fallback_worker.asyncio.create_subprocess_exec')
    async def test_ffmpeg_version_check_fails(self, mock_exec, worker, temp_video_file):
        """Test when ffmpeg version check fails."""
        # Mock process with non-zero return code
        mock_process = mock.AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = mock.AsyncMock(return_value=(b"", b"error"))
        mock_exec.return_value = mock_process
        
        gif_path = worker.get_gif_path(temp_video_file)
        result = await worker._convert_with_ffmpeg(temp_video_file, gif_path)
        
        assert result is False


# Apply pytest markers for test categorization
pytestmark = [pytest.mark.unit, pytest.mark.asyncio]
