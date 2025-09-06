import json
import logging
from pathlib import Path
import base64
import pytest

from src.core.screenshot_manager import capture_page_screenshot
from src.runtime.run_context import RunContext


class _CaptureHandler(logging.Handler):
    def __init__(self):
        super().__init__(level=logging.INFO)
        self.lines = []
    def emit(self, record: logging.LogRecord):
        """Parse screenshot event JSON from a log record and store it.

        Only records whose message contains the screenshot event prefix are considered.
        JSON decode errors are ignored (best-effort capture) but logged at DEBUG for troubleshooting.
        """
        msg = record.getMessage()
        if '"event":"screenshot.' not in msg:
            return
        # More defensive extraction: find first '{' to avoid ValueError from index()
        start_idx = msg.find('{')
        if start_idx == -1:
            logging.debug("Skip screenshot event line: missing JSON brace")
            return
        try:
            obj = json.loads(msg[start_idx:])
        except json.JSONDecodeError as e:  # narrow exception (review feedback)
            logging.debug("Skip unparsable screenshot event line: %s", e)
            return
        if isinstance(obj, dict) and obj.get("event", "").startswith("screenshot."):
            self.lines.append(obj)

def _with_capture():
    from src.utils.app_logger import logger as app_logger
    # underlying logger instance
    py_logger = app_logger.logger
    handler = _CaptureHandler()
    py_logger.addHandler(handler)
    return handler, py_logger


@pytest.mark.ci_safe
def test_screenshot_json_structure_success(monkeypatch, tmp_path, capsys):
    class DummyPage:
        def screenshot(self, type="png"):
            return b"binaryimagedata123"  # 18 bytes

    monkeypatch.chdir(tmp_path)
    (Path("artifacts") / "runs").mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    cap_handler, _ = _with_capture()
    page = DummyPage()
    path, b64 = capture_page_screenshot(page, prefix="jsonsucc")
    assert path is not None and path.exists()
    assert b64 == base64.b64encode(b"binaryimagedata123").decode()

    events = cap_handler.lines
    # Expect at least start + success (duplicate may or may not appear)
    names = [e.get("event") for e in events]
    assert "screenshot.capture.start" in names
    assert "screenshot.capture.success" in names
    success_evt = next(e for e in events if e.get("event") == "screenshot.capture.success")
    assert success_evt.get("schema_version") == 1
    assert success_evt.get("prefix") == "jsonsucc"
    assert isinstance(success_evt.get("latency_ms"), int) and success_evt["latency_ms"] >= 0
    assert success_evt.get("size_bytes") == 18
    assert "path" in success_evt
    assert success_evt.get("duplicate_copy") in (True, False)


@pytest.mark.ci_safe
def test_screenshot_json_structure_failure(monkeypatch, tmp_path, capsys):
    class DummyPageFail:
        def screenshot(self, type="png"):
            raise TimeoutError("timed out")

    monkeypatch.chdir(tmp_path)
    (Path("artifacts") / "runs").mkdir(parents=True, exist_ok=True)
    RunContext.reset()
    cap_handler, _ = _with_capture()
    page = DummyPageFail()
    path, b64 = capture_page_screenshot(page, prefix="jsonfail")
    assert path is None and b64 is None

    events = cap_handler.lines
    names = [e.get("event") for e in events]
    # Expect start + fail
    assert "screenshot.capture.start" in names
    assert "screenshot.capture.fail" in names
    fail_evt = next(e for e in events if e.get("event") == "screenshot.capture.fail")
    assert fail_evt.get("schema_version") == 1
    assert fail_evt.get("prefix") == "jsonfail"
    assert fail_evt.get("error_type") in ("transient", "fatal", "unknown")
    assert isinstance(fail_evt.get("latency_ms"), int) and fail_evt["latency_ms"] >= 0
    assert "error_message" in fail_evt
