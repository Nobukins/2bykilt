import base64
from pathlib import Path
from datetime import datetime, timezone

import pytest

from src.core.artifact_manager import get_artifact_manager, reset_artifact_manager_singleton
from src.core.screenshot_manager import capture_page_screenshot
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


@pytest.mark.ci_safe
def test_artifact_manifest_integrated_flow(tmp_path, monkeypatch):
    """Issue #38: Regression suite minimal integrated flow.

    Validates that after enabling manifest v2 and unified recording:
      * Registering a video adds a video entry (with retention_days meta)
      * Capturing a screenshot adds a screenshot entry (format + path)
      * Element capture adds element_capture entry
    Ensures no regressions in unified path interactions.
    """
    monkeypatch.chdir(tmp_path)
    (Path("artifacts") / "runs").mkdir(parents=True, exist_ok=True)
    # Reset singletons / flags
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    FeatureFlags.set_override("artifacts.unified_recording_path", True)
    FeatureFlags.set_override("artifacts.video_retention_days", 5)

    mgr = get_artifact_manager()

    # --- Video registration ---
    videos_dir = mgr.dir / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    video_file = videos_dir / "sample.mp4"
    video_file.write_bytes(b"videodata123")
    mgr.register_video_file(video_file)

    # --- Screenshot capture (dummy page) ---
    class _DummyPage:
        def screenshot(self, type="png"):
            return b"imagebytesXYZ"  # 13 bytes

    capture_page_screenshot(_DummyPage(), prefix="regshot")

    # --- Element capture ---
    element_path = mgr.save_element_capture("#main", "Hello", "val")
    assert element_path.exists()

    # Reload manifest and validate entries
    manifest = mgr.get_manifest(reload=True)
    artifacts = manifest.get("artifacts", [])
    types = [a.get("type") for a in artifacts]
    # Expect at least one of each (video, screenshot, element_capture)
    assert "video" in types
    assert "screenshot" in types
    assert "element_capture" in types

    # Video entry assertions
    video_entries = [a for a in artifacts if a.get("type") == "video"]
    assert len(video_entries) == 1
    v_meta = video_entries[0].get("meta", {})
    assert v_meta.get("retention_days") == 5
    assert v_meta.get("final_ext") == ".mp4"

    # Screenshot entry assertions
    sc_entries = [a for a in artifacts if a.get("type") == "screenshot"]
    assert sc_entries, "Expected at least one screenshot entry"
    sc_meta = sc_entries[0].get("meta", {})
    assert sc_meta.get("format") == "png"

    # Element capture assertions
    el_entries = [a for a in artifacts if a.get("type") == "element_capture"]
    assert el_entries, "Expected element_capture entry"
    el_meta = el_entries[0].get("meta", {})
    assert el_meta.get("selector") == "#main"

    # Basic timestamp sanity (created_at fields ISO and recent)
    for a in artifacts:
        created_at = a.get("created_at")
        assert created_at
        # parse-able and not far future
        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        assert dt <= datetime.now(timezone.utc)
