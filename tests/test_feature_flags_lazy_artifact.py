"""
Tests for FeatureFlags lazy artifact creation functionality.

This module tests the lazy artifact creation feature added in Issue #102,
which allows controlling whether undefined flag access automatically creates
artifacts or just logs warnings.
"""

import json
import os
import pytest
from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir

from src.config.feature_flags import FeatureFlags


@pytest.mark.ci_safe
class TestLazyArtifactCreation:
    """Test suite for lazy artifact creation control."""

    def setup_method(self):
        """Reset FeatureFlags state before each test."""
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()
        # Reset to default (enabled)
        FeatureFlags.set_lazy_artifact_enabled(True)

    def teardown_method(self):
        """Clean up after each test."""
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

    def test_lazy_artifact_enabled_by_default(self, tmp_path, monkeypatch):
        """Test that lazy artifact creation is enabled by default."""
        monkeypatch.chdir(tmp_path)

        # Should be enabled by default
        assert FeatureFlags.is_lazy_artifact_enabled() is True

    def test_lazy_artifact_can_be_disabled(self, tmp_path, monkeypatch):
        """Test that lazy artifact creation can be disabled."""
        monkeypatch.chdir(tmp_path)

        # Disable lazy artifact creation
        FeatureFlags.set_lazy_artifact_enabled(False)
        assert FeatureFlags.is_lazy_artifact_enabled() is False

        # Re-enable
        FeatureFlags.set_lazy_artifact_enabled(True)
        assert FeatureFlags.is_lazy_artifact_enabled() is True

    def test_lazy_artifact_creation_on_undefined_access(self, tmp_path, monkeypatch):
        """Test that undefined flag access creates artifact when lazy creation is enabled."""
        monkeypatch.chdir(tmp_path)

        # Ensure clean state
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()
        FeatureFlags.set_lazy_artifact_enabled(True)

        # Access undefined flag - should create artifact
        result = FeatureFlags.is_enabled("undefined.test.flag")
        assert result is False  # undefined flags return False for bool

        # Check that artifact was created
        artifacts_dir = get_artifacts_base_dir() / "runs"
        if artifacts_dir.exists():
            flags_dirs = [d for d in artifacts_dir.iterdir() if d.is_dir() and d.name.endswith("-flags")]
            if flags_dirs:
                flags_dir = flags_dirs[0]
                json_file = flags_dir / "feature_flags_resolved.json"
                assert json_file.exists()

                # Verify content
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                assert "resolved" in data
                assert "generated_at" in data

    def test_no_lazy_artifact_creation_when_disabled(self, tmp_path, monkeypatch):
        """Test that undefined flag access does not create artifact when lazy creation is disabled."""
        monkeypatch.chdir(tmp_path)

        # Count existing flags directories before the test
        artifacts_dir = get_artifacts_base_dir() / "runs"
        initial_flags_dirs = 0
        if artifacts_dir.exists():
            initial_flags_dirs = len([d for d in artifacts_dir.iterdir() if d.is_dir() and d.name.endswith("-flags")])

        # Disable lazy artifact creation
        FeatureFlags.set_lazy_artifact_enabled(False)

        # Access undefined flag - should NOT create artifact
        result = FeatureFlags.is_enabled("undefined.test.flag.disabled")
        assert result is False

        # Check that no NEW artifact was created (count should be the same)
        if artifacts_dir.exists():
            current_flags_dirs = len([d for d in artifacts_dir.iterdir() if d.is_dir() and d.name.endswith("-flags")])
            assert current_flags_dirs == initial_flags_dirs, (
                f"Expected no new flags directories, but count increased "
                f"from {initial_flags_dirs} to {current_flags_dirs}"
            )

    def test_lazy_artifact_environment_variable_control(self, tmp_path, monkeypatch):
        """Test that lazy artifact creation can be controlled via environment variable."""
        # Test with environment variable set to false
        monkeypatch.setenv("BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED", "false")
        monkeypatch.chdir(tmp_path)

        # Reload should pick up environment variable
        FeatureFlags.reload()
        assert FeatureFlags.is_lazy_artifact_enabled() is False

        # Test with environment variable set to true
        monkeypatch.setenv("BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED", "true")
        FeatureFlags.reload()
        assert FeatureFlags.is_lazy_artifact_enabled() is True

        # Test with alternative true values
        for true_value in ["1", "yes", "on"]:
            monkeypatch.setenv("BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED", true_value)
            FeatureFlags.reload()
            assert FeatureFlags.is_lazy_artifact_enabled() is True

        # Test with invalid value (should default to false)
        monkeypatch.setenv("BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED", "invalid")
        FeatureFlags.reload()
        assert FeatureFlags.is_lazy_artifact_enabled() is False  # invalid values default to False

    def test_lazy_artifact_with_dump_snapshot_override(self, tmp_path, monkeypatch):
        """Test that dump_snapshot still works when lazy creation is disabled."""
        monkeypatch.chdir(tmp_path)

        # Disable lazy artifact creation
        FeatureFlags.set_lazy_artifact_enabled(False)

        # dump_snapshot should still work
        artifact_dir = FeatureFlags.dump_snapshot()
        assert isinstance(artifact_dir, Path)
        assert (artifact_dir / "feature_flags_resolved.json").exists()

    def test_lazy_artifact_multiple_undefined_accesses(self, tmp_path, monkeypatch):
        """Test that multiple undefined flag accesses only create one artifact."""
        monkeypatch.chdir(tmp_path)

        # Count existing flags directories before the test
        artifacts_dir = get_artifacts_base_dir() / "runs"
        initial_flags_dirs = 0
        if artifacts_dir.exists():
            initial_flags_dirs = len([d for d in artifacts_dir.iterdir() if d.is_dir() and d.name.endswith("-flags")])

        FeatureFlags.set_lazy_artifact_enabled(True)

        # Access multiple undefined flags
        FeatureFlags.is_enabled("undefined.flag.1")
        FeatureFlags.is_enabled("undefined.flag.2")
        FeatureFlags.get("undefined.flag.3", expected_type=str)

        # Should only have created one additional flags directory
        if artifacts_dir.exists():
            current_flags_dirs = len([d for d in artifacts_dir.iterdir() if d.is_dir() and d.name.endswith("-flags")])
            assert current_flags_dirs <= initial_flags_dirs + 1, f"Expected at most one new flags directory, but count increased from {initial_flags_dirs} to {current_flags_dirs}"


@pytest.mark.ci_safe
def test_ensure_flags_artifact_helper_integration(tmp_path, monkeypatch):
    """Test integration with ensure_flags_artifact_helper."""
    from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact_helper

    monkeypatch.chdir(tmp_path)

    # Use helper to create artifact
    artifact_dir = ensure_flags_artifact_helper(tmp_path)
    assert isinstance(artifact_dir, Path)
    assert (artifact_dir / "feature_flags_resolved.json").exists()

    # Verify it's a valid JSON file
    with open(artifact_dir / "feature_flags_resolved.json", 'r', encoding='utf-8') as f:
        data = json.load(f)
    assert "generated_at" in data
    assert "resolved" in data


@pytest.mark.ci_safe
def test_ensure_flags_artifact_with_overrides_helper(tmp_path, monkeypatch):
    """Test ensure_flags_artifact_with_overrides_helper functionality."""
    from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact_with_overrides_helper

    monkeypatch.chdir(tmp_path)

    overrides = {
        "test.enabled": True,
        "test.value": "test_string",
        "test.number": 42
    }

    # Create artifact with overrides
    artifact_dir = ensure_flags_artifact_with_overrides_helper(overrides, tmp_path)
    assert isinstance(artifact_dir, Path)
    assert (artifact_dir / "feature_flags_resolved.json").exists()

    # Verify overrides are in the artifact
    with open(artifact_dir / "feature_flags_resolved.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    resolved = data["resolved"]
    assert resolved.get("test.enabled") is True
    assert resolved.get("test.value") == "test_string"
    assert resolved.get("test.number") == 42

    # Verify overrides are active
    assert "test.enabled" in data["overrides_active"]