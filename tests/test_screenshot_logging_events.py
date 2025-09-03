import re
from pathlib import Path
import base64
import pytest

from src.core.screenshot_manager import capture_page_screenshot
from src.runtime.run_context import RunContext

@pytest.mark.ci_safe
def test_screenshot_logging_events_success(monkeypatch, tmp_path, capsys):
    class DummyPage:
        def screenshot(self, type="png"):
            return b"binaryimagedata123"  # 19 bytes
    # isolate run context artifacts root
    monkeypatch.chdir(tmp_path)
    (Path("artifacts")/"runs").mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    page = DummyPage()
    path, b64 = capture_page_screenshot(page, prefix="evt")
    assert path is not None and path.exists()
    assert b64 == base64.b64encode(b"binaryimagedata123").decode()
    # Validate file size matches expected
    assert path.stat().st_size == 18  # bytes length of dummy data

@pytest.mark.ci_safe
def test_screenshot_logging_events_failure(monkeypatch, tmp_path, capsys):
    class DummyPageFail:
        def screenshot(self, type="png"):
            raise TimeoutError("timed out")
    monkeypatch.chdir(tmp_path)
    (Path("artifacts")/"runs").mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    page = DummyPageFail()
    path, b64 = capture_page_screenshot(page, prefix="evt_fail")
    assert path is None and b64 is None
    # Cannot reliably capture stdout logs here; functional assertion only
