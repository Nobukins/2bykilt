import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from myscript.actions import nogtips_search


class _StubRunContext:
    @staticmethod
    def get():
        return SimpleNamespace()


class _DummyPage:
    async def wait_for_timeout(self, ms: int) -> None:
        self.wait_timeout = ms
        await asyncio.sleep(0)

    async def wait_for_selector(self, selector: str, **kwargs) -> None:
        timeout = kwargs.get("timeout")
        self.selector_waited = (selector, timeout)
        await asyncio.sleep(0)


@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_capture_search_artifacts_invokes_helpers(monkeypatch):
    screenshot_mock = AsyncMock(return_value=(Path("/tmp/screenshot.png"), None))
    element_mock = AsyncMock(return_value=Path("/tmp/elements.txt"))

    monkeypatch.setattr(nogtips_search, "async_capture_page_screenshot", screenshot_mock)
    monkeypatch.setattr(nogtips_search, "async_capture_element_value", element_mock)
    monkeypatch.setattr(nogtips_search, "RunContext", _StubRunContext)
    monkeypatch.setattr(
        nogtips_search,
        "get_artifact_manager",
        lambda: SimpleNamespace(dir=Path("/tmp/run")),
    )

    page = _DummyPage()
    await nogtips_search._capture_search_artifacts(
        page,
        query="Playwright",
        artifact_prefix="test",
        fields=["text", "html"],
    )

    screenshot_mock.assert_awaited_once()
    element_mock.assert_awaited_once_with(
        page,
        selector="main",
        label="test_results",
        fields=["text", "html"],
    )
    assert getattr(page, "wait_timeout", None) == 1000
    assert getattr(page, "selector_waited", None) == ("main", 5000)
