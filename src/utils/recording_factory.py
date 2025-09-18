"""
Unified Recording Factory - Issue #221

Provides centralized recording initialization for all run types (script, browser-control, git-script).
Ensures consistent recording behavior across different execution paths.

Features:
- Unified recorder initialization
- Consistent path resolution
- Manifest metadata registration
- Error handling with warnings
"""

import logging
import os
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from src.utils.recording_dir_resolver import create_or_get_recording_dir
from src.core.artifact_manager import ArtifactManager, ArtifactEntry

logger = logging.getLogger(__name__)

class RecordingFactory:
    """Unified factory for recording initialization across all run types."""

    @staticmethod
    def init_recorder(run_context: Dict[str, Any]) -> Optional['RecorderContext']:
        """
        Initialize recorder for the given run context.

        Args:
            run_context: Dictionary containing run parameters including:
                - save_recording_path: Explicit recording path (optional)
                - run_id: Unique run identifier
                - run_type: Type of run (script, browser-control, git-script)
                - enable_recording: Whether recording is enabled

        Returns:
            RecorderContext if recording is enabled, None otherwise
        """
        try:
            # Check if recording is enabled
            enable_recording = run_context.get('enable_recording', True)
            if not enable_recording:
                logger.debug("Recording disabled for this run")
                return None

            # Get recording path
            save_recording_path = run_context.get('save_recording_path')
            recording_path = create_or_get_recording_dir(save_recording_path)

            # Get run metadata
            run_id = run_context.get('run_id', 'unknown')
            run_type = run_context.get('run_type', 'unknown')

            logger.info(f"Initializing recorder: path={recording_path}, run_id={run_id}, type={run_type}")

            return RecorderContext(recording_path, run_id, run_type)

        except Exception as e:
            logger.warning(f"Failed to initialize recorder: {e}", extra={
                'event': 'recording_init_failed',
                'reason': str(e),
                'run_type': run_context.get('run_type', 'unknown')
            })
            return None

class RecorderContext:
    """Context manager for recording operations."""

    def __init__(self, recording_path: Path, run_id: str, run_type: str):
        self.recording_path = recording_path
        self.run_id = run_id
        self.run_type = run_type
        self.recording_file = None
        self._manifest_registered = False

    async def __aenter__(self):
        """Enter the recording context."""
        try:
            # Ensure recording directory exists
            self.recording_path.mkdir(parents=True, exist_ok=True)

            # Generate unique recording filename
            timestamp = self._get_timestamp()
            self.recording_file = self.recording_path / f"{self.run_type}_{self.run_id}_{timestamp}.webm"

            # Register in manifest
            await self._register_manifest()

            logger.info(f"Recording started: {self.recording_file}")
            return self

        except Exception as e:
            logger.warning(f"Failed to start recording: {e}", extra={
                'event': 'recording_start_failed',
                'reason': str(e),
                'run_type': self.run_type,
                'run_id': self.run_id
            })
            return None

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit the recording context."""
        try:
            if self.recording_file and self.recording_file.exists():
                # Update manifest with completion status
                await self._update_manifest_completion(exc_type is not None)

                logger.info(f"Recording completed: {self.recording_file}")
            else:
                logger.warning("Recording file was not created", extra={
                    'event': 'recording_file_missing',
                    'run_type': self.run_type,
                    'run_id': self.run_id
                })

        except Exception as e:
            logger.warning(f"Error during recording cleanup: {e}", extra={
                'event': 'recording_cleanup_failed',
                'reason': str(e)
            })

    def _get_timestamp(self) -> str:
        """Get current timestamp for filename."""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    async def _register_manifest(self):
        """Register recording in artifact manifest."""
        if self._manifest_registered:
            return

        try:
            # Get artifact manager
            artifact_manager = ArtifactManager()

            # Create artifact entry
            entry = ArtifactEntry(
                type="video",
                path=str(self.recording_file),
                created_at=datetime.now(timezone.utc).isoformat(),
                size=None,  # Will be set when file is created
                meta={
                    'run_id': self.run_id,
                    'run_type': self.run_type,
                    'start_time': self._get_timestamp(),
                    'status': 'in_progress'
                }
            )

            # Add to manifest
            artifact_manager.add_entry(entry)

            self._manifest_registered = True
            logger.debug(f"Recording registered in manifest: {self.run_id}")

        except Exception as e:
            logger.warning(f"Failed to register recording in manifest: {e}")

    async def _update_manifest_completion(self, has_error: bool = False):
        """Update manifest with completion status."""
        if not self._manifest_registered:
            return

        try:
            # Log completion status (manifest update would require more complex implementation)
            status = 'completed' if not has_error else 'failed'
            file_size = self.recording_file.stat().st_size if self.recording_file and self.recording_file.exists() else 0

            logger.debug(f"Recording completion: {self.run_id}, status={status}, size={file_size}")

        except Exception as e:
            logger.warning(f"Failed to update recording completion: {e}")

# Convenience function for backward compatibility
def init_recorder(run_context: Dict[str, Any]) -> Optional[RecorderContext]:
    """
    Initialize recorder for the given run context.

    This is a convenience function that delegates to RecordingFactory.init_recorder.
    """
    return RecordingFactory.init_recorder(run_context)