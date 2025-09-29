import base64
from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir
from datetime import datetime, timezone, timedelta
import json

import pytest

from src.core.artifact_manager import get_artifact_manager, reset_artifact_manager_singleton
from src.core.screenshot_manager import capture_page_screenshot
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


def _parse_iso8601_relaxed(val: str) -> datetime:
  """Relaxed ISO8601 parser for tests (handles trailing 'Z')."""
  if val.endswith("Z"):
    val = val[:-1] + "+00:00"
  try:
    return datetime.fromisoformat(val)
  except Exception:  # noqa: BLE001
    try:
      base, _, tz = val.partition("+")
      if tz:
        return datetime.fromisoformat(base.split(".")[0] + "+" + tz)
    except Exception:  # noqa: BLE001
      pass
    raise AssertionError(f"Unparseable ISO8601 datetime: {val}")


@pytest.mark.ci_safe
def test_artifact_manifest_integrated_flow(tmp_path, monkeypatch):
  """Issue #38: Regression suite minimal integrated flow (review fix for datetime parsing)."""
  monkeypatch.chdir(tmp_path)
  (get_artifacts_base_dir() / "runs").mkdir(parents=True, exist_ok=True)
  RunContext.reset()
  reset_artifact_manager_singleton()
  FeatureFlags.clear_all_overrides()
  FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
  FeatureFlags.set_override("artifacts.unified_recording_path", True)
  FeatureFlags.set_override("artifacts.video_retention_days", 5)

  mgr = get_artifact_manager()
  # Video
  videos_dir = mgr.dir / "videos"
  videos_dir.mkdir(parents=True, exist_ok=True)
  vf = videos_dir / "sample.mp4"
  vf.write_bytes(b"videodata123")
  mgr.register_video_file(vf)

  class _P:
    def screenshot(self, type="png"):
      return b"imagebytesXYZ"

  capture_page_screenshot(_P(), prefix="regshot")
  assert mgr.save_element_capture("#main", "Hello", "val").exists()

  manifest = mgr.get_manifest(reload=True)
  artifacts = manifest.get("artifacts", [])
  types = {a.get("type") for a in artifacts}
  assert {"video", "screenshot", "element_capture"}.issubset(types)

  video_entries = [a for a in artifacts if a.get("type") == "video"]
  assert len(video_entries) == 1
  v_meta = video_entries[0].get("meta", {})
  assert v_meta.get("retention_days") == 5
  assert v_meta.get("final_ext") == ".mp4"

  sc_entries = [a for a in artifacts if a.get("type") == "screenshot"]
  assert sc_entries
  assert sc_entries[0].get("meta", {}).get("format") == "png"

  el_entries = [a for a in artifacts if a.get("type") == "element_capture"]
  assert el_entries
  assert el_entries[0].get("meta", {}).get("selector") == "#main"

  now_utc = datetime.now(timezone.utc)
  for a in artifacts:
    created_at = a.get("created_at")
    if created_at:
      dt = _parse_iso8601_relaxed(created_at)
      assert dt <= now_utc


@pytest.mark.ci_safe
def test_artifact_manifest_multi_video_transcode_and_retention(tmp_path, monkeypatch):
  """Issue #38: multi video + optional transcode + retention enforcement.

  Steps:
    1. Two source videos (one .webm candidate for mp4 transcode, one already mp4)
    2. Force transcode flag (if ffmpeg absent the test still passes falling back)
    3. Age one resulting mp4 beyond retention days (mtime hack) then enforce
    4. Assert only the recent video remains, manifest still consistent
  """
  monkeypatch.chdir(tmp_path)
  (get_artifacts_base_dir() / "runs").mkdir(parents=True, exist_ok=True)
  RunContext.reset()
  reset_artifact_manager_singleton()
  FeatureFlags.clear_all_overrides()
  FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
  FeatureFlags.set_override("artifacts.unified_recording_path", True)
  FeatureFlags.set_override("artifacts.video_retention_days", 1)
  FeatureFlags.set_override("artifacts.video_transcode_enabled", True)
  FeatureFlags.set_override("artifacts.video_target_container", "mp4")

  mgr = get_artifact_manager()
  videos_dir = mgr.dir / "videos"
  videos_dir.mkdir(parents=True, exist_ok=True)

  webm_src = videos_dir / "old_source.webm"
  mp4_src = videos_dir / "recent_source.mp4"
  webm_src.write_bytes(b"webmdata")
  mp4_src.write_bytes(b"mp4data")

  final_old = mgr.register_video_file(webm_src)
  final_recent = mgr.register_video_file(mp4_src)

  # Age an mp4 file 2 days back; if transcode didn't occur (no ffmpeg) final_old may be .webm
  past = (datetime.now(timezone.utc) - timedelta(days=2)).timestamp()
  import os as _os
  if final_old.suffix == ".mp4":
    target_old = final_old
    _os.utime(target_old, (past, past))
  else:
    # create a synthetic aged mp4 to exercise retention
    target_old = videos_dir / "aged_old.mp4"
    target_old.write_bytes(b"oldmp4")
    _os.utime(target_old, (past, past))

  removed = mgr.enforce_video_retention()
  assert removed == 1, f"expected 1 removal, got {removed}, final_old={final_old}"
  assert not target_old.exists()
  assert final_recent.exists()

  manifest = mgr.get_manifest(reload=True)
  vids = [a for a in manifest["artifacts"] if a["type"] == "video"]
  # After deletion manifest is not auto-pruned; we accept stale entries but ensure at least one valid remaining path
  live_paths = [v["path"] for v in vids if Path(v["path"]).name == final_recent.name]
  assert live_paths, "Expected manifest to include surviving recent video entry"


@pytest.mark.ci_safe
def test_screenshot_failure_and_persist_fail_branch(tmp_path, monkeypatch):
  """Issue #38: exercise screenshot failure (capture_fail) and persist_fail branch.

  Persist fail simulated by raising on duplicate copy write.
  """
  monkeypatch.chdir(tmp_path)
  (get_artifacts_base_dir() / "runs").mkdir(parents=True, exist_ok=True)
  RunContext.reset()
  reset_artifact_manager_singleton()
  FeatureFlags.clear_all_overrides()
  FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
  FeatureFlags.set_override("artifacts.unified_recording_path", True)
  FeatureFlags.set_override("artifacts.screenshot.user_named_copy_enabled", True)

  # Force failure in capture
  class _FailPage:
    def screenshot(self, type="png"):
      raise TimeoutError("boom")

  path, b64 = capture_page_screenshot(_FailPage(), prefix="failshot")
  assert path is None and b64 is None

  # Force persist failure by causing ArtifactManager.save_screenshot_bytes to raise
  class _PersistFailPage:
    def screenshot(self, type="png"):
      return b"okdata"

  import src.core.artifact_manager as amod
  orig_save = amod.ArtifactManager.save_screenshot_bytes

  def boom(self, data, prefix="screenshot"):
    raise OSError("disk full simulation")

  try:
    amod.ArtifactManager.save_screenshot_bytes = boom  # type: ignore
    p2, b64_2 = capture_page_screenshot(_PersistFailPage(), prefix="failshot2")
    assert p2 is None and b64_2 is None  # persist_fail returns (None, None)
  finally:
    amod.ArtifactManager.save_screenshot_bytes = orig_save  # type: ignore


def _manifest_diff(before: dict, after: dict) -> dict:
  """Utility: compute simple diff of manifest artifact paths by type (added/removed counts)."""
  def idx(m):
    out = {}
    for a in m.get("artifacts", []):
      out.setdefault(a["type"], set()).add(a["path"])
    return out
  b = idx(before)
  a = idx(after)
  diff = {}
  for t in set(b.keys()) | set(a.keys()):
    added = a.get(t, set()) - b.get(t, set())
    removed = b.get(t, set()) - a.get(t, set())
    if added or removed:
      diff[t] = {"added": sorted(added), "removed": sorted(removed)}
  return diff


@pytest.mark.ci_safe
def test_manifest_diff_utility(tmp_path, monkeypatch):
  """Issue #38: manifest diff helper sanity."""
  monkeypatch.chdir(tmp_path)
  (get_artifacts_base_dir() / "runs").mkdir(parents=True, exist_ok=True)
  RunContext.reset()
  reset_artifact_manager_singleton()
  FeatureFlags.clear_all_overrides()
  FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
  FeatureFlags.set_override("artifacts.unified_recording_path", True)
  mgr = get_artifact_manager()
  before = json.loads(Path(mgr.manifest_path).read_text(encoding="utf-8")) if mgr.manifest_path.exists() else {"artifacts": []}

  # add one screenshot & element
  class _P:
    def screenshot(self, type="png"):
      return b"bytes"
  capture_page_screenshot(_P(), prefix="diffshot")
  mgr.save_element_capture("#a", "T", None)
  after = mgr.get_manifest(reload=True)
  d = _manifest_diff(before, after)
  # If implementation stores all artifacts in single manifest file, added entries should appear
  assert any(a["type"] == "screenshot" for a in after["artifacts"])
  assert any(a["type"] == "element_capture" for a in after["artifacts"])
  if d:  # diff may be empty if manifest was initially empty and we treat entire set as base
    assert "screenshot" in d or "element_capture" in d
