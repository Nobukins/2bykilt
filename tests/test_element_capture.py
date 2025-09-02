from pathlib import Path
import pytest

from src.core.element_capture import capture_element_value
from src.core.artifact_manager import get_artifact_manager

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
    # Redirect artifact root via RunContext env override
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN123")
    page = DummyPage()
    p = capture_element_value(page, "#a", label="sample", fields=["text","value","html"])
    assert p is not None
    assert p.exists()
    content = p.read_text(encoding="utf-8")
    assert "TEXT:" in content and "HTML:" in content and "VALUE:" in content
    # manifest entry present
    mgr = get_artifact_manager()
    mpath = mgr.manifest_path
    assert mpath.exists()
    data = mpath.read_text(encoding="utf-8")
    assert "element_capture" in data


@pytest.mark.ci_safe
def test_label_sanitization(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN124")
    page = DummyPage()
    p = capture_element_value(page, "#a", label="..//evil:name", fields=["text"])
    assert p is not None
    # filename should not start with dot or contain traversal sequences
    assert not p.name.startswith('.')
    assert '..' not in p.name
    assert '/' not in p.name


@pytest.mark.ci_safe
def test_partial_fields(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN125")
    page = DummyPage()
    p = capture_element_value(page, "#a", label="partial", fields=["value"])  # only value
    assert p is not None
    content = p.read_text(encoding="utf-8")
    assert content.startswith("VALUE:")


class FailingLocator(DummyLocator):
    def inner_text(self, timeout: int = 0):  # noqa: ARG002
        raise RuntimeError("boom text")
    def inner_html(self, timeout: int = 0):  # noqa: ARG002
        raise RuntimeError("boom html")


class MixedPage(DummyPage):
    def __init__(self):
        self.locators = {"#bad": FailingLocator(), "#ok": DummyLocator()}


@pytest.mark.ci_safe
def test_failure_branches(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN126")
    page = MixedPage()
    # Should return None because all fields fail
    res = capture_element_value(page, "#bad", label="bad", fields=["text","html"])
    assert res is None
    # Mixed success
    res2 = capture_element_value(page, "#ok", label="ok", fields=["text","html"])
    assert res2 is not None and res2.exists()
