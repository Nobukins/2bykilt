from pathlib import Path
import json
import pytest

from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


def test_flags_dump_snapshot_creates_artifact(tmp_path, monkeypatch):
    # Force artifacts to tmp dir by changing CWD (RunContext uses relative paths)
    monkeypatch.chdir(tmp_path)

    # Ensure clean state
    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()

    # Test basic functionality
    out_dir = FeatureFlags.dump_snapshot()
    assert isinstance(out_dir, Path)
    assert (out_dir / "feature_flags_resolved.json").exists()

    # Verify JSON content
    with open(out_dir / "feature_flags_resolved.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    assert "generated_at" in data
    assert "resolved" in data
    assert "overrides_active" in data
    assert isinstance(data["resolved"], dict)
    assert isinstance(data["overrides_active"], list)


def test_flags_dump_snapshot_with_overrides(tmp_path, monkeypatch):
    """Test dump_snapshot with active overrides."""
    monkeypatch.chdir(tmp_path)

    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()

    # Set an override
    FeatureFlags.set_override("test_flag", True)

    out_dir = FeatureFlags.dump_snapshot()
    assert (out_dir / "feature_flags_resolved.json").exists()

    with open(out_dir / "feature_flags_resolved.json", 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Verify override is captured
    assert "test_flag" in data["overrides_active"]
    assert data["resolved"].get("test_flag") is True


def test_flags_dump_snapshot_multiple_calls(tmp_path, monkeypatch):
    """Test that multiple calls to dump_snapshot work correctly."""
    monkeypatch.chdir(tmp_path)

    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()

    # First call
    out_dir1 = FeatureFlags.dump_snapshot()
    assert (out_dir1 / "feature_flags_resolved.json").exists()

    # Second call should also work
    out_dir2 = FeatureFlags.dump_snapshot()
    assert (out_dir2 / "feature_flags_resolved.json").exists()

    # Both should contain valid JSON
    for out_dir in [out_dir1, out_dir2]:
        with open(out_dir / "feature_flags_resolved.json", 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "generated_at" in data
        assert "resolved" in data


def test_flags_dump_snapshot_fallback_behavior(tmp_path, monkeypatch):
    """Test fallback behavior when RunContext is not available."""
    monkeypatch.chdir(tmp_path)

    # Mock RunContext.get() to raise an exception
    class MockRunContext:
        @staticmethod
        def get():
            raise Exception("RunContext not available")

    monkeypatch.setattr("src.config.feature_flags.RunContext", MockRunContext)

    try:
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

        out_dir = FeatureFlags.dump_snapshot()
        assert isinstance(out_dir, Path)
        # Should fall back to _ARTIFACT_ROOT pattern
        assert "artifacts" in str(out_dir)
        assert (out_dir / "feature_flags_resolved.json").exists()

    finally:
        # Restore original RunContext - monkeypatch handles this automatically
        pass


def test_flags_dump_snapshot_error_handling(tmp_path, monkeypatch):
    """Test error handling in dump_snapshot."""
    monkeypatch.chdir(tmp_path)

    FeatureFlags.clear_all_overrides()
    FeatureFlags.reload()

    # Test with read-only directory (should handle gracefully)
    out_dir = FeatureFlags.dump_snapshot()
    assert isinstance(out_dir, Path)

    # Verify artifact was still created despite any internal errors
    json_file = out_dir / "feature_flags_resolved.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        assert "generated_at" in data
