import json
from pathlib import Path
from src.utils.fs_paths import get_artifacts_base_dir

from src.core.artifact_manager import ArtifactManager, reset_artifact_manager_singleton
from src.runtime.run_context import RunContext
from src.config.feature_flags import FeatureFlags


def _read_manifest_text(mgr) -> str:
    mp = mgr.manifest_path
    return mp.read_text(encoding="utf-8") if mp.exists() else ""


def test_manifest_flag_off(tmp_path, monkeypatch):
    # Fresh context
    monkeypatch.setenv("BYKILT_RUN_ID", "MFLAGOFF1")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", False)
    # Remove any leftover artifacts directory for this run id to avoid contamination
    leftover_dir = get_artifacts_base_dir() / "runs" / "MFLAGOFF1-art"
    if leftover_dir.exists():
        import shutil
        try:
            shutil.rmtree(leftover_dir)
        except (OSError, PermissionError):  # narrow expected cleanup errors
            pass
    mgr = ArtifactManager()
    pre_artifacts = []
    if mgr.manifest_path.exists():
        try:
            pre_data = json.loads(_read_manifest_text(mgr))
            pre_artifacts = pre_data.get("artifacts", [])
        except Exception:
            pass
    # create a screenshot (will still write file, but not manifest entry)
    img_path = mgr.save_screenshot_bytes(b"fakepngbytes", prefix="offcase")
    assert img_path.exists()
    if mgr.manifest_path.exists():
        data = json.loads(_read_manifest_text(mgr))
        after_artifacts = data.get("artifacts", [])
        # Count should not increase
        assert len(after_artifacts) == len(pre_artifacts)
        # No path with the new prefix should exist
        def is_offcase_png_path(artifact: dict) -> bool:
            path = artifact.get("path", "")
            return path.endswith(".png") and "offcase_" in path

        assert not any(is_offcase_png_path(a) for a in after_artifacts)


def test_manifest_basic_entries_increment(tmp_path, monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "MFLAGON1")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    mgr = ArtifactManager()
    pre = 0
    if mgr.manifest_path.exists():
        try:
            pre_data = json.loads(_read_manifest_text(mgr))
            pre = len([a for a in pre_data.get("artifacts", []) if a.get("type") == "screenshot"])
        except Exception:
            pass
    mgr.save_screenshot_bytes(b"one", prefix="inc1")
    mgr.save_screenshot_bytes(b"two", prefix="inc2")
    data = json.loads(_read_manifest_text(mgr))
    screenshots = [a for a in data["artifacts"] if a["type"] == "screenshot"]
    assert len(screenshots) - pre == 2


def test_element_capture_entry(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "MFLAGON2")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    mgr = ArtifactManager()
    pre = 0
    if mgr.manifest_path.exists():
        try:
            pre_data = json.loads(_read_manifest_text(mgr))
            pre = len([a for a in pre_data.get("artifacts", []) if a.get("type") == "element_capture"])
        except Exception:
            pass
    p = mgr.save_element_capture("#login", text="Hello", value="val")
    assert p.exists()
    data = json.loads(_read_manifest_text(mgr))
    ec = [a for a in data["artifacts"] if a["type"] == "element_capture"]
    assert len(ec) - pre == 1
    assert any(e["meta"].get("selector") == "#login" for e in ec)


def test_video_entry_when_enabled(monkeypatch, tmp_path):
    monkeypatch.setenv("BYKILT_RUN_ID", "MFLAGON3")
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    mgr = ArtifactManager()
    vdir = mgr.dir / "videos"
    vdir.mkdir(parents=True, exist_ok=True)
    sample = vdir / "sample.mp4"
    sample.write_bytes(b"FAKEVID")
    pre = 0
    if mgr.manifest_path.exists():
        try:
            pre_data = json.loads(_read_manifest_text(mgr))
            pre = len([a for a in pre_data.get("artifacts", []) if a.get("type") == "video"])
        except Exception:
            pass
    mgr.register_video_file(sample)
    data = json.loads(_read_manifest_text(mgr))
    vids = [a for a in data["artifacts"] if a["type"] == "video"]
    assert len(vids) - pre == 1
