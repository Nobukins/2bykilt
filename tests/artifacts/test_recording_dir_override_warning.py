"""Tests for ArtifactManager.resolve_recording_dir with override source detection (Issue #106)."""
import os
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


"""Tests for ArtifactManager.resolve_recording_dir with override source detection (Issue #106)."""
import os
import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


def _clear_legacy_warning_flag():
    """Helper function to clear the legacy recording warning flag."""
    if hasattr(ArtifactManager, '_bykilt_legacy_recording_warned'):
        delattr(ArtifactManager, '_bykilt_legacy_recording_warned')


@pytest.fixture
def setup_test():
    """Reset all state before each test."""
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()
    # Clear any previous warning flag
    _clear_legacy_warning_flag()
    yield
    # Cleanup after test
    _clear_legacy_warning_flag()


def test_resolve_recording_dir_explicit_path(setup_test):
    """Test explicit path takes precedence."""
    explicit = "/tmp/custom/recordings"
    result = ArtifactManager.resolve_recording_dir(explicit)
    # On macOS, /tmp is a symlink to /private/tmp, so resolve() normalizes it
    expected = Path(explicit).resolve()
    assert result == expected


def test_resolve_recording_dir_flag_enabled(setup_test):
    """Test unified path when flag is enabled (default)."""
    with patch('src.runtime.run_context.RunContext.get') as mock_rc:
        mock_artifact_dir = Path("/tmp/test-artifacts/runs/test-art")
        mock_rc.return_value.artifact_dir.return_value = mock_artifact_dir
        
        with patch('pathlib.Path.mkdir'):  # Mock mkdir to avoid filesystem issues
            result = ArtifactManager.resolve_recording_dir()
            expected = mock_artifact_dir / "videos"
            assert result == expected


def test_resolve_recording_dir_legacy_no_override(setup_test, caplog):
    """Test legacy path when flag is false but not explicitly overridden."""
    # Set flag to false via file default (not override)
    with patch.object(FeatureFlags, 'is_enabled', return_value=False):
        with patch.object(FeatureFlags, 'get_override_source', return_value=None):
            with caplog.at_level(logging.WARNING):
                result = ArtifactManager.resolve_recording_dir()
                assert "record_videos" in str(result)
                # Should not log warning when not explicitly overridden
                assert len(caplog.records) == 0


def test_resolve_recording_dir_legacy_runtime_override(setup_test, caplog):
    """Test legacy path with runtime override triggers warning."""
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    
    with caplog.at_level(logging.WARNING):
        result = ArtifactManager.resolve_recording_dir()
        assert "record_videos" in str(result)
        
        # Should log warning for explicit runtime override
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "artifact.recording.legacy_path.forced" in record.__dict__.get('event', '')
        assert "runtime" in str(record.__dict__.get('override_source', ''))


def test_resolve_recording_dir_legacy_env_override(setup_test, caplog, monkeypatch):
    """Test legacy path with environment override triggers warning."""
    monkeypatch.setenv("BYKILT_FLAG_ARTIFACTS_UNIFIED_RECORDING_PATH", "false")
    FeatureFlags.reload()
    
    with caplog.at_level(logging.WARNING):
        result = ArtifactManager.resolve_recording_dir()
        assert "record_videos" in str(result)
        
        # Should log warning for explicit environment override
        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.levelname == "WARNING"
        assert "artifact.recording.legacy_path.forced" in record.__dict__.get('event', '')
        assert "environment" in str(record.__dict__.get('override_source', ''))


def test_resolve_recording_dir_warning_once_per_process(setup_test, caplog):
    """Test warning is emitted only once per process."""
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    
    with caplog.at_level(logging.WARNING):
        # First call should warn
        ArtifactManager.resolve_recording_dir()
        assert len(caplog.records) == 1
        
        # Second call should not warn again
        ArtifactManager.resolve_recording_dir()
        assert len(caplog.records) == 1