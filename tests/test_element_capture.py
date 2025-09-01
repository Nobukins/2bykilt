import types
from pathlib import Path

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


def test_label_sanitization(monkeypatch):
    monkeypatch.setenv("BYKILT_RUN_ID", "TESTRUN124")
    page = DummyPage()
    p = capture_element_value(page, "#a", label="..//evil:name", fields=["text"])
    assert p is not None
    # filename should not start with dot or contain traversal sequences
    assert not p.name.startswith('.')
    assert '..' not in p.name
    assert '/' not in p.name
