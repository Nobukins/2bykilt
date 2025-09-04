from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests
from src.runtime.run_context import RunContext


def test_unified_recording_path_default_enabled(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "ROLL91A")
    RunContext.reset(); reset_artifact_manager_singleton(); _reset_feature_flags_for_tests()
    # No explicit override -> should use unified path (videos dir under artifacts)
    d = ArtifactManager.resolve_recording_dir()
    assert d.name == "videos"
    # path should include run artifacts directory structure
    assert "art" in d.parent.name or d.parent.name.endswith("-art")


def test_unified_recording_path_legacy_warning(monkeypatch, caplog):
    monkeypatch.setenv("BYKILT_RUN_ID", "ROLL91B")
    RunContext.reset(); reset_artifact_manager_singleton(); _reset_feature_flags_for_tests()
    FeatureFlags.set_override("artifacts.unified_recording_path", False)
    caplog.set_level("WARNING")
    d = ArtifactManager.resolve_recording_dir()
    assert d.name == "record_videos"
    msgs = [r.message for r in caplog.records if "Legacy recording path in use" in r.message]
    assert len(msgs) == 1
    ArtifactManager.resolve_recording_dir()
    msgs2 = [r.message for r in caplog.records if "Legacy recording path in use" in r.message]
    assert len(msgs2) == 1
