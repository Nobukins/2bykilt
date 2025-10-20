from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
import pytest
from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests
from src.runtime.run_context import RunContext


def _legacy_msgs(caplog):
    return [r.message for r in caplog.records if "Legacy recording path" in r.message]


@pytest.mark.ci_safe
def test_unified_recording_path_default_enabled(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "ROLL91A")
    # Reset singletons & flags (split per PEP8 for readability)
    RunContext.reset()
    reset_artifact_manager_singleton()
    _reset_feature_flags_for_tests()
    # No explicit override -> should use unified path (videos dir under artifacts)
    d = ArtifactManager.resolve_recording_dir()
    assert d.name == "videos"
    # path should include run artifacts directory structure
    assert "art" in d.parent.name or d.parent.name.endswith("-art")


@pytest.mark.ci_safe
def test_unified_recording_path_always_enabled(monkeypatch, caplog):
    """Test unified recording path is always used (Issue #353 - no legacy fallback)."""
    monkeypatch.setenv("BYKILT_RUN_ID", "ROLL91B")
    RunContext.reset()
    reset_artifact_manager_singleton()
    _reset_feature_flags_for_tests()
    # Issue #353: Legacy fallback removed - always use unified path
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    caplog.set_level("WARNING")
    d = ArtifactManager.resolve_recording_dir()
    # Even with flag False, should use unified path (not legacy ./tmp/record_videos)
    assert d.name == "videos"
    assert "art" in d.parent.name or d.parent.name.endswith("-art")
    # Multiple calls should work consistently
    d2 = ArtifactManager.resolve_recording_dir()
    assert d2 == d
