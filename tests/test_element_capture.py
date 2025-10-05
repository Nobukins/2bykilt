from pathlib import Path
import pytest

from src.core.element_capture import capture_element_value
from src.core.artifact_manager import get_artifact_manager, reset_artifact_manager_singleton
from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext

class DummyLocator:
    def __init__(self, text: str = "Hello World", html: str = "<div>Hello World</div>"):
        self._text = text
        self._html = html

    def inner_text(self, timeout: int = 0):  # noqa: ARG002
        return self._text

    def inner_html(self, timeout: int = 0):  # noqa: ARG002
        return self._html

    def input_value(self, timeout: int = 0):  # noqa: ARG002
        return "input-val"

class DummyPage:
    def __init__(self):
        self.locators = {"#a": DummyLocator()}

    def locator(self, sel: str):
        return self.locators[sel]

@pytest.mark.ci_safe
def test_capture_element_value(tmp_path, monkeypatch):
    """Test capturing element values with text, value, and HTML fields."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN123")
    
    # Clean state AFTER chdir - ensures ArtifactManager uses correct path
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    # Enable manifest v2 to ensure manifest is created
    FeatureFlags.set_override("artifacts.enable_manifest_v2", True)
    
    page = DummyPage()
    p = capture_element_value(page, "#a", label="sample", fields=["text","value","html"])
    assert p is not None, "Element capture should return a path"
    assert p.exists(), f"Element capture file should exist: {p}"
    content = p.read_text(encoding="utf-8")
    assert "TEXT:" in content, "Content should include TEXT field"
    assert "HTML:" in content, "Content should include HTML field"
    assert "VALUE:" in content, "Content should include VALUE field"
    
    # manifest entry present
    mgr = get_artifact_manager()
    mpath = mgr.manifest_path
    assert mpath.exists(), f"Manifest should exist: {mpath}"
    data = mpath.read_text(encoding="utf-8")
    assert "element_capture" in data, "Manifest should contain element_capture entry"


@pytest.mark.ci_safe
def test_label_sanitization(tmp_path, monkeypatch):
    """Test that label sanitization prevents path traversal attacks."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN124")
    
    # Clean state AFTER chdir
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    page = DummyPage()
    p = capture_element_value(page, "#a", label="..//evil:name", fields=["text"])
    assert p is not None, "Element capture should return a path"
    # filename should not start with dot or contain traversal sequences
    assert not p.name.startswith('.'), f"Filename should not start with dot: {p.name}"
    assert '..' not in p.name, f"Filename should not contain ..: {p.name}"
    assert '/' not in p.name, f"Filename should not contain /: {p.name}"


@pytest.mark.ci_safe
def test_partial_fields(tmp_path, monkeypatch):
    """Test capturing only specific fields."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN125")
    
    # Clean state AFTER chdir
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    page = DummyPage()
    p = capture_element_value(page, "#a", label="partial", fields=["value"])  # only value
    assert p is not None, "Element capture should return a path"
    content = p.read_text(encoding="utf-8")
    assert content.startswith("VALUE:"), f"Content should start with VALUE:: {content}"


class FailingLocator(DummyLocator):
    def inner_text(self, timeout: int = 0):  # noqa: ARG002
        raise RuntimeError("boom text")
    def inner_html(self, timeout: int = 0):  # noqa: ARG002
        raise RuntimeError("boom html")


class MixedPage(DummyPage):
    def __init__(self):
        self.locators = {"#bad": FailingLocator(), "#ok": DummyLocator()}


@pytest.mark.ci_safe
def test_failure_branches(tmp_path, monkeypatch):
    """Test error handling when element capture fails."""
    # Change directory FIRST
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN126")
    
    # Clean state AFTER chdir
    RunContext.reset()
    reset_artifact_manager_singleton()
    FeatureFlags.clear_all_overrides()
    
    page = MixedPage()
    # Should return None because all fields fail
    res = capture_element_value(page, "#bad", label="bad", fields=["text","html"])
    assert res is None, "Should return None when all fields fail"
    # Mixed success
    res2 = capture_element_value(page, "#ok", label="ok", fields=["text","html"])
    assert res2 is not None, "Should return path when capture succeeds"
    assert res2.exists(), f"Captured file should exist: {res2}"
