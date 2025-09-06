"""Environment variable precedence tests for recording path (#28)."""
from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.utils.recording_dir_resolver import create_or_get_recording_dir
from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests
from src.runtime.run_context import RunContext


def _reset_all():
    RunContext.reset()
    reset_artifact_manager_singleton()
    _reset_feature_flags_for_tests()


def test_recording_path_env_precedence(monkeypatch, tmp_path):
    monkeypatch.setenv("BYKILT_RUN_ID", "ENVOVR1")
    _reset_all()
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    env_dir = tmp_path / "custom_env_rec"
    monkeypatch.setenv("RECORDING_PATH", str(env_dir))
    # Use new unified resolver (ArtifactManager does not yet include env precedence directly)
    p = create_or_get_recording_dir()
    assert p == env_dir
    assert p.exists()
    assert "videos" not in str(p)


def test_recording_path_env_ignored_when_empty(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "ENVOVR2")
    _reset_all()
    monkeypatch.setenv("RECORDING_PATH", "")
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    p = create_or_get_recording_dir()
    assert p.name == "videos"
