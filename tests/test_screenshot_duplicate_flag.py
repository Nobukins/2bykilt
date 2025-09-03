import os
from pathlib import Path

import pytest

from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext
from src.core.screenshot_manager import capture_page_screenshot
from src.core.artifact_manager import reset_artifact_manager_singleton


class DummyPage:
    def __init__(self, content: bytes = b"imgdata"):
        self._content = content
    def screenshot(self, type: str = "png"):
        return self._content


@pytest.mark.ci_safe
def test_screenshot_duplicate_flag_on(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "SCRDUPON")
    RunContext.reset(); reset_artifact_manager_singleton(); FeatureFlags.reload()
    # ensure flag on
    FeatureFlags.set_override("artifacts.screenshot.user_named_copy_enabled", True)

    page = DummyPage()
    path, _ = capture_page_screenshot(page, prefix="sample")
    assert path is not None
    pdir = path.parent
    # duplicate user-named file should exist (prefix_<timestamp>.png) -> we derive by glob
    dup_files = [p for p in pdir.glob("sample_*.png") if p.name != path.name]
    assert len(dup_files) == 1

@pytest.mark.ci_safe
def test_screenshot_duplicate_flag_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "SCRDUPOFF")
    RunContext.reset(); reset_artifact_manager_singleton(); FeatureFlags.reload()
    FeatureFlags.set_override("artifacts.screenshot.user_named_copy_enabled", False)

    page = DummyPage()
    path, _ = capture_page_screenshot(page, prefix="only")
    assert path is not None
    pdir = path.parent
    dup_files = [p for p in pdir.glob("only_*.png") if p.name != path.name]
    assert len(dup_files) == 0
