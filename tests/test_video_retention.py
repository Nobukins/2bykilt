import os
import time
from datetime import datetime, timedelta, timezone
RETENTION_TEST_OLD_FILE_OFFSET_DAYS = 2  # how many days back to mark old file (must exceed flag=1)
from pathlib import Path

import pytest

from src.core.artifact_manager import get_artifact_manager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext

@pytest.mark.ci_safe
def test_video_manifest_includes_retention_field(tmp_path, monkeypatch):
    """Test that video manifest includes retention_days field when configured."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTVIDEO1")
    (Path('artifacts')/ 'runs').mkdir(parents=True, exist_ok=True)
    
    # Clean state AFTER chdir - ensures ArtifactManager uses correct path
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    # Configure feature flags
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
    assert len(video_entries) == 1, f"Expected 1 video entry, got {len(video_entries)}: {[e['path'] for e in video_entries]}"
    meta = video_entries[0]['meta']
    assert 'retention_days' in meta, f"retention_days not in meta: {meta}"
    assert meta['retention_days'] == 7, f"Expected retention_days=7, got {meta['retention_days']}"

@pytest.mark.ci_safe
def test_video_retention_enforcement(tmp_path, monkeypatch):
    """Test that old videos are automatically removed based on retention policy."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTVIDEO2")
    (Path('artifacts')/ 'runs').mkdir(parents=True, exist_ok=True)
    
    # Clean state AFTER chdir
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    # Configure feature flags with 1-day retention
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

    # simulate old file by modifying mtime to RETENTION_TEST_OLD_FILE_OFFSET_DAYS days ago (microseconds stripped for determinism)
    old_ts = (
        datetime.now(timezone.utc).replace(microsecond=0)
        - timedelta(days=RETENTION_TEST_OLD_FILE_OFFSET_DAYS)
    ).timestamp()
    os.utime(old_video, (old_ts, old_ts))

    removed = mgr.enforce_video_retention()
    assert removed == 1, f"Expected 1 file removed, got {removed}"
    assert not old_video.exists(), f"Old video should be removed: {old_video}"
    assert recent_video.exists(), f"Recent video should exist: {recent_video}"
