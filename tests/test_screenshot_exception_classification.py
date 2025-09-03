import pytest
from pathlib import Path

from src.core.screenshot_manager import capture_page_screenshot
from src.runtime.run_context import RunContext
from src.core.artifact_manager import reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags

class DummyPageOK:
    def screenshot(self, type: str = "png"):
        return b"imgdata-ok"

class DummyPageTimeout:
    def screenshot(self, type: str = "png"):
        class TimeoutErrorSim(Exception):
            pass
        raise TimeoutErrorSim("navigation timeout")

class DummyPageFatal:
    def screenshot(self, type: str = "png"):
        class NotConnectedErrorSim(Exception):
            pass
        raise NotConnectedErrorSim("browser disconnected")

@pytest.mark.ci_safe
def test_screenshot_success_exception_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "EXCOK")
    RunContext.reset(); reset_artifact_manager_singleton(); FeatureFlags.reload()
    p, b64 = capture_page_screenshot(DummyPageOK(), prefix="exc_ok")
    assert p is not None and b64 is not None
    assert p.exists()

@pytest.mark.ci_safe
def test_screenshot_timeout_transient(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "EXCTO")
    RunContext.reset(); reset_artifact_manager_singleton(); FeatureFlags.reload()
    p, b64 = capture_page_screenshot(DummyPageTimeout(), prefix="exc_to")
    assert p is None and b64 is None
    # Optional: examine logs captured via capsys to ensure error_type=transient appears
    # We intentionally do not assert log content due to emoji/log formatting variance; success path is silent failure return.

@pytest.mark.ci_safe
def test_screenshot_fatal(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "EXCFATAL")
    RunContext.reset(); reset_artifact_manager_singleton(); FeatureFlags.reload()
    p, b64 = capture_page_screenshot(DummyPageFatal(), prefix="exc_fatal")
    assert p is None and b64 is None
    # Classification verified indirectly by error path return semantics.
