import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.core.artifact_manager import get_artifact_manager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext

@pytest.mark.ci_safe
def test_video_manifest_includes_retention_field(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (Path('artifacts')/ 'runs').mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    FeatureFlags.set_override("artifacts.video_retention_days", 7)

    mgr = get_artifact_manager()
    videos_dir = mgr.dir / 'videos'
    videos_dir.mkdir(parents=True, exist_ok=True)
    video_file = videos_dir / 'sample.webm'
    video_file.write_bytes(b'123456')

    # register
    mgr.register_video_file(video_file)
    manifest = mgr.get_manifest(reload=True)
    video_entries = [a for a in manifest['artifacts'] if a['type'] == 'video']
    assert len(video_entries) == 1
    meta = video_entries[0]['meta']
    assert 'retention_days' in meta and meta['retention_days'] == 7

@pytest.mark.ci_safe
def test_video_retention_enforcement(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (Path('artifacts')/ 'runs').mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    FeatureFlags.set_override("artifacts.video_retention_days", 1)

    mgr = get_artifact_manager()
    videos_dir = mgr.dir / 'videos'
    videos_dir.mkdir(parents=True, exist_ok=True)

    old_video = videos_dir / 'old.mp4'
    recent_video = videos_dir / 'recent.mp4'
    old_video.write_bytes(b'old')
    recent_video.write_bytes(b'new')

    # simulate old file by modifying mtime to 2 days ago
    old_ts = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
    os.utime(old_video, (old_ts, old_ts))

    removed = mgr.enforce_video_retention()
    assert removed == 1
    assert not old_video.exists()
    assert recent_video.exists()
