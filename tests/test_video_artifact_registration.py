import os
from pathlib import Path
from src.core.artifact_manager import get_artifact_manager
from src.config.feature_flags import FeatureFlags


def test_register_video_artifact(tmp_path, monkeypatch):
    # Enable manifest v2
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    manager = get_artifact_manager()
    video_dir = manager.dir / "videos"
    video_dir.mkdir(parents=True, exist_ok=True)
    sample_video = video_dir / "sample.webm"
    sample_video.write_bytes(b"RIFFXXXXwebmfake")

    # Force target container auto (no transcode)
    FeatureFlags.set_override("artifacts.video_target_container", "auto")
    out = manager.register_video_file(sample_video)
    assert out.exists()

    manifest = (manager.dir / "manifest_v2.json")
    assert manifest.exists()
    data = manifest.read_text(encoding="utf-8")
    assert "sample.webm" in data

    # Switch to mp4 target (transcode disabled so original kept)
    FeatureFlags.set_override("artifacts.video_target_container", "mp4")
    FeatureFlags.set_override("artifacts.video_transcode_enabled", False)
    out2 = manager.register_video_file(sample_video)
    assert out2.suffix.lower() == ".webm"  # no change without transcode
