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


@pytest.mark.ci_safe
def test_resolve_recording_dir_explicit_path(setup_test):
    """Test explicit path takes precedence."""
    explicit = "/tmp/custom/recordings"
    result = ArtifactManager.resolve_recording_dir(explicit)
    # On macOS, /tmp is a symlink to /private/tmp, so resolve() normalizes it
    expected = Path(explicit).resolve()
    assert result == expected


@pytest.mark.ci_safe
def test_resolve_recording_dir_flag_enabled(setup_test):
    """Test unified path when flag is enabled (default)."""
    with patch('src.runtime.run_context.RunContext.get') as mock_rc:
        mock_artifact_dir = Path("/tmp/test-artifacts/runs/test-art")
        mock_rc.return_value.artifact_dir.return_value = mock_artifact_dir
        
        with patch('pathlib.Path.mkdir'):  # Mock mkdir to avoid filesystem issues
            result = ArtifactManager.resolve_recording_dir()
            expected = mock_artifact_dir / "videos"
            assert result == expected


@pytest.mark.ci_safe
def test_resolve_recording_dir_unified_path_always(setup_test, caplog):
    """Test unified path is always used (Issue #353 - no legacy fallback)."""
    # Issue #353: Always use unified path regardless of flag state
    with patch('src.runtime.run_context.RunContext.get') as mock_rc:
        mock_artifact_dir = Path("/tmp/test-artifacts/runs/test-art")
        mock_rc.return_value.artifact_dir.return_value = mock_artifact_dir
        
        with patch('pathlib.Path.mkdir'):  # Mock mkdir to avoid filesystem issues
            result = ArtifactManager.resolve_recording_dir()
            expected = mock_artifact_dir / "videos"
            assert result == expected
            # Should use unified path, not legacy ./tmp/record_videos
            assert "videos" in str(result)


@pytest.mark.ci_safe
def test_resolve_recording_dir_env_var_fallback(setup_test, monkeypatch):
    """Test RECORDING_PATH env var is respected (Issue #353)."""
    monkeypatch.setenv("RECORDING_PATH", "/custom/recording/path")
    
    with patch('src.utils.recording_dir_resolver.create_or_get_recording_dir') as mock_resolver:
        mock_resolver.return_value = Path("/tmp/test-recordings").resolve()
        
        with patch('pathlib.Path.mkdir'):  # Mock mkdir
            ArtifactManager.resolve_recording_dir()
            # Should call create_or_get_recording_dir
            mock_resolver.assert_called_once()


@pytest.mark.ci_safe
def test_resolve_recording_dir_explicit_overrides_env(setup_test):
    """Test explicit path takes precedence over env var (Issue #353)."""
    explicit = "/tmp/explicit/path"
    result = ArtifactManager.resolve_recording_dir(explicit)
    expected = Path(explicit).resolve()
    assert result == expected


@pytest.mark.ci_safe
def test_resolve_recording_dir_unified_path_consistent(setup_test, caplog):
    """Test unified path is consistently used (Issue #353)."""
    with patch('src.runtime.run_context.RunContext.get') as mock_rc:
        mock_artifact_dir = Path("/tmp/test-artifacts/runs/test-art")
        mock_rc.return_value.artifact_dir.return_value = mock_artifact_dir
        
        with patch('pathlib.Path.mkdir'):
            # Multiple calls should return same unified path
            result1 = ArtifactManager.resolve_recording_dir()
            result2 = ArtifactManager.resolve_recording_dir()
            expected = mock_artifact_dir / "videos"
            assert result1 == expected
            assert result2 == expected
            # No warnings should be logged (no legacy fallback)
            assert len(caplog.records) == 0