from pathlib import Path
import pytest
from src.core.artifact_manager import get_artifact_manager
from src.config.feature_flags import FeatureFlags

@pytest.mark.ci_safe
def test_video_metrics_increment(tmp_path, monkeypatch):
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    FeatureFlags.set_override("artifacts.video_target_container", "auto")
    manager = get_artifact_manager()
    video_dir = manager.dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    v1 = video_dir / "m1.webm"
    v1.write_bytes(b"RIFFXXXXwebmfake1")
    manager.register_video_file(v1)
    metrics = manager.get_video_metrics()
    assert metrics["videos_total"] >= 1
    assert metrics["videos_transcoded"] >= 0
    assert metrics["video_bytes_total"] >= len(b"RIFFXXXXwebmfake1")
