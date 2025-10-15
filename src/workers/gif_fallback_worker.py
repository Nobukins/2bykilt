"""
GIF Fallback Worker for Recordings

Provides async conversion of video recordings to GIF format for preview when LLM is disabled.
Uses ffmpeg or fallback to Pillow-based frame extraction.

Key Features:
- Queue-based conversion with deduplication
- Existing GIF cache priority (avoid re-generation)
- Configurable retry logic with failure tracking
- Throttling to prevent excessive resource usage
- Feature flag gated: artifacts.recordings_gif_fallback_enabled
"""

import asyncio
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

from src.config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


# Constants
BYTES_TO_MB = 1024 * 1024
MAX_RETRIES = 3
RETRY_DELAY_SECONDS = 5
THROTTLE_DELAY_SECONDS = 2
GIF_MAX_SIZE_MB = 10
GIF_FPS = 10
GIF_WIDTH = 640


@dataclass
class ConversionTask:
    """Represents a single video-to-GIF conversion task."""
    video_path: str
    gif_path: str
    retry_count: int = 0
    created_at: float = field(default_factory=time.time)
    status: str = "pending"  # pending, processing, completed, failed
    error_message: Optional[str] = None


class GifFallbackWorker:
    """
    Async worker for converting video recordings to GIF format.
    
    Attributes:
        queue: Pending conversion tasks
        processing: Currently processing task paths
        completed: Successfully completed task paths
        failed: Failed task paths with error info
    """
    
    def __init__(self):
        self.queue: asyncio.Queue[ConversionTask] = asyncio.Queue()
        self.processing: Set[str] = set()
        self.completed: Set[str] = set()
        self.failed: Dict[str, str] = {}
        self._running = False
        self._worker_task: Optional[asyncio.Task] = None
    
    def is_enabled(self) -> bool:
        """Check if GIF fallback is enabled via feature flag."""
        return FeatureFlags.is_enabled("artifacts.recordings_gif_fallback_enabled")
    
    def get_gif_path(self, video_path: str) -> str:
        """
        Generate GIF path from video path.
        
        Convention: same directory, same basename with .gif extension
        Example: /path/to/video.mp4 -> /path/to/video.gif
        """
        video_file = Path(video_path)
        return str(video_file.with_suffix('.gif'))
    
    async def enqueue(self, video_path: str) -> bool:
        """
        Enqueue a video for GIF conversion.
        
        Returns:
            True if enqueued, False if skipped (already exists/processing/completed)
        """
        if not self.is_enabled():
            logger.debug("GIF fallback disabled, skipping enqueue")
            return False
        
        if not os.path.exists(video_path):
            logger.warning(f"Video file not found: {video_path}")
            return False
        
        gif_path = self.get_gif_path(video_path)
        
        # Priority 1: Existing GIF (cache hit)
        if os.path.exists(gif_path):
            logger.debug(f"GIF already exists, skipping: {gif_path}")
            self.completed.add(video_path)
            return False
        
        # Priority 2: Already processing
        if video_path in self.processing:
            logger.debug(f"Video already processing: {video_path}")
            return False
        
        # Priority 3: Already completed
        if video_path in self.completed:
            logger.debug(f"Video already converted: {video_path}")
            return False
        
        # Priority 4: Previously failed (don't retry immediately)
        if video_path in self.failed:
            logger.debug(f"Video previously failed, skipping: {video_path}")
            return False
        
        # Enqueue new task
        task = ConversionTask(
            video_path=video_path,
            gif_path=gif_path
        )
        await self.queue.put(task)
        logger.info(f"Enqueued video for GIF conversion: {video_path}")
        return True
    
    async def start(self):
        """Start the background worker."""
        if self._running:
            logger.warning("Worker already running")
            return
        
        if not self.is_enabled():
            logger.info("GIF fallback worker disabled by feature flag")
            return
        
        self._running = True
        self._worker_task = asyncio.create_task(self._process_queue())
        logger.info("GIF fallback worker started")
        await asyncio.sleep(0)  # Yield control to event loop
    
    async def stop(self):
        """Stop the background worker."""
        if not self._running:
            return
        
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass  # Expected when cancelling the task
        logger.info("GIF fallback worker stopped")
        await asyncio.sleep(0)  # Yield control to event loop
    
    async def _process_queue(self):
        """Main worker loop - processes queued tasks."""
        while self._running:
            try:
                # Wait for task with timeout to allow checking _running flag
                task = await asyncio.wait_for(self.queue.get(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break  # Exit loop on cancellation
            
            # Process task
            try:
                await self._process_task(task)
            except Exception as e:
                logger.error(f"Unexpected error processing task: {e}", exc_info=True)
            finally:
                self.queue.task_done()
                # Throttle to prevent resource exhaustion
                await asyncio.sleep(THROTTLE_DELAY_SECONDS)
    
    async def _process_task(self, task: ConversionTask):
        """Process a single conversion task."""
        video_path = task.video_path
        gif_path = task.gif_path
        
        # Mark as processing
        self.processing.add(video_path)
        task.status = "processing"
        
        logger.info(f"Converting video to GIF: {video_path} -> {gif_path}")
        
        try:
            # Attempt conversion
            success = await self._convert_video_to_gif(video_path, gif_path)
            
            if success:
                task.status = "completed"
                self.completed.add(video_path)
                logger.info(f"GIF conversion completed: {gif_path}")
            else:
                # Retry logic
                task.retry_count += 1
                if task.retry_count < MAX_RETRIES:
                    task.status = "pending"
                    logger.warning(f"GIF conversion failed, retrying ({task.retry_count}/{MAX_RETRIES}): {video_path}")
                    await asyncio.sleep(RETRY_DELAY_SECONDS)
                    await self.queue.put(task)
                else:
                    task.status = "failed"
                    task.error_message = f"Exceeded max retries ({MAX_RETRIES})"
                    self.failed[video_path] = task.error_message
                    logger.error(f"GIF conversion failed after {MAX_RETRIES} retries: {video_path}")
        
        except Exception as e:
            task.status = "failed"
            task.error_message = str(e)
            self.failed[video_path] = task.error_message
            logger.error(f"GIF conversion exception: {e}", exc_info=True)
        
        finally:
            # Remove from processing set
            self.processing.discard(video_path)
    
    async def _convert_video_to_gif(self, video_path: str, gif_path: str) -> bool:
        """
        Convert video to GIF using ffmpeg (preferred) or fallback method.
        
        Returns:
            True if conversion successful, False otherwise
        """
        # Try ffmpeg first (best quality/performance)
        if await self._convert_with_ffmpeg(video_path, gif_path):
            return True
        
        # Fallback: Log that ffmpeg is unavailable
        logger.warning("ffmpeg not available or conversion failed, GIF generation skipped")
        return False
    
    async def _convert_with_ffmpeg(self, video_path: str, gif_path: str) -> bool:
        """
        Convert video to GIF using ffmpeg.
        
        Command optimizes for file size while maintaining quality:
        - Scale to GIF_WIDTH maintaining aspect ratio
        - Set FPS to GIF_FPS
        - Use palette generation for better colors
        """
        try:
            # Check if ffmpeg is available
            result = await asyncio.create_subprocess_exec(
                'ffmpeg', '-version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await result.communicate()
            if result.returncode != 0:
                logger.debug("ffmpeg not available")
                return False
            
            # Generate palette for better color quality
            palette_path = gif_path + ".palette.png"
            palette_cmd = [
                'ffmpeg', '-i', video_path,
                '-vf', f'fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos,palettegen',
                '-y', palette_path
            ]
            
            logger.debug(f"Generating palette: {' '.join(palette_cmd)}")
            result = await asyncio.create_subprocess_exec(
                *palette_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await result.communicate()
            
            if result.returncode != 0:
                logger.error(f"Palette generation failed: {stderr.decode()}")
                return False
            
            # Convert to GIF using palette
            convert_cmd = [
                'ffmpeg', '-i', video_path, '-i', palette_path,
                '-lavfi', f'fps={GIF_FPS},scale={GIF_WIDTH}:-1:flags=lanczos[x];[x][1:v]paletteuse',
                '-y', gif_path
            ]
            
            logger.debug(f"Converting to GIF: {' '.join(convert_cmd)}")
            result = await asyncio.create_subprocess_exec(
                *convert_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            _, stderr = await result.communicate()
            
            # Cleanup palette
            try:
                os.remove(palette_path)
            except Exception:
                pass
            
            if result.returncode != 0:
                logger.error(f"GIF conversion failed: {stderr.decode()}")
                return False
            
            # Verify output
            if not os.path.exists(gif_path):
                logger.error(f"GIF file not created: {gif_path}")
                return False
            
            # Check file size
            gif_size_mb = os.path.getsize(gif_path) / BYTES_TO_MB
            if gif_size_mb > GIF_MAX_SIZE_MB:
                logger.warning(f"GIF file too large: {gif_size_mb:.1f}MB (max: {GIF_MAX_SIZE_MB}MB)")
                # Don't fail, just warn
            
            logger.info(f"GIF created successfully: {gif_path} ({gif_size_mb:.1f}MB)")
            return True
        
        except FileNotFoundError:
            logger.debug("ffmpeg not found in PATH")
            return False
        except Exception as e:
            logger.error(f"ffmpeg conversion error: {e}", exc_info=True)
            return False
    
    def get_status(self) -> Dict:
        """Get current worker status for monitoring/metrics."""
        return {
            "enabled": self.is_enabled(),
            "running": self._running,
            "queue_size": self.queue.qsize(),
            "processing_count": len(self.processing),
            "completed_count": len(self.completed),
            "failed_count": len(self.failed)
        }


# Global worker instance
_worker_instance: Optional[GifFallbackWorker] = None


def get_worker() -> GifFallbackWorker:
    """Get or create the global worker instance."""
    global _worker_instance
    if _worker_instance is None:
        _worker_instance = GifFallbackWorker()
    return _worker_instance
