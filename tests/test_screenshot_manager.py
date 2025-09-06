from src.core.screenshot_manager import capture_page_screenshot
from src.config.feature_flags import FeatureFlags
from src.core.artifact_manager import get_artifact_manager

class FakePage:
    def screenshot(self, type="png"):
        return b"fakepngdata123"  # pretend PNG bytes

def test_capture_page_screenshot_basic(tmp_path, monkeypatch):
    # enable manifest so artifact path is created
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    page = FakePage()
    path, b64 = capture_page_screenshot(page, prefix="testcap")
    assert path is not None
    assert path.exists()
    assert b64 is not None and isinstance(b64, str)
    # manifest should contain an entry
    mgr = get_artifact_manager()
    manifest = (mgr.dir / "manifest_v2.json")
    assert manifest.exists()
    data = manifest.read_text(encoding="utf-8")
    assert "screenshot" in data
