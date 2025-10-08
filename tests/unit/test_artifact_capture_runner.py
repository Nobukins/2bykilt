from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from templates import artifact_capture_runner as runner


class _FakeBrowser:
    async def new_context(self, **kwargs):
        self.kwargs = kwargs
        return _FakeContext()

    async def close(self) -> None:  # pragma: no cover - noop
        pass


class _FakeContext:
    async def new_page(self):
        return MagicMock()

    async def close(self) -> None:  # pragma: no cover - noop
        pass


class _FakeBrowserType:
    def __init__(self):
        self.launch_calls = []

    async def launch(self, headless=True):
        self.launch_calls.append(headless)
        return _FakeBrowser()


class _AsyncPlaywrightStub:
    def __init__(self):
        self.browser_type = _FakeBrowserType()

    async def __aenter__(self):
        return SimpleNamespace(
            chromium=self.browser_type,
            firefox=self.browser_type,
            webkit=self.browser_type,
        )

    async def __aexit__(self, exc_type, exc, tb):  # pragma: no cover - noop
        pass


@pytest.mark.asyncio
async def test_run_nogtips_variant_invokes_run_actions(monkeypatch, tmp_path):
    play_stub = _AsyncPlaywrightStub()
    monkeypatch.setattr(runner, "async_playwright", lambda: play_stub)

    run_actions_mock = AsyncMock()
    monkeypatch.setattr("myscript.actions.nogtips_search.run_actions", run_actions_mock)

    finalize_mock = AsyncMock(return_value=Path(tmp_path / "videos/test.webm"))
    monkeypatch.setattr("myscript.bin.demo_artifact_capture._finalize_video_capture", finalize_mock)
    register_mock = MagicMock()
    monkeypatch.setattr("myscript.bin.demo_artifact_capture._register_video_artifact", register_mock)

    monkeypatch.setattr(runner, "RunContext", SimpleNamespace(get=lambda: SimpleNamespace()))
    monkeypatch.setattr(
        runner,
        "get_artifact_manager",
        lambda: SimpleNamespace(dir=tmp_path / "runs"),
    )
    artifact_assert_mock = MagicMock()
    monkeypatch.setattr(runner, "_assert_artifacts_created", artifact_assert_mock)

    args = Namespace(
        variant="nogtips",
        query="LLMs.txt",
        prefix=None,
        fields=None,
        browser="chromium",
        headed=False,
        url=None,
        selector=None,
    )

    await runner._run_variant(args)

    run_actions_mock.assert_awaited_once()
    _, kwargs = run_actions_mock.await_args
    assert kwargs["capture_artifacts"] is True
    assert kwargs["artifact_prefix"] == "nogtips_capture"
    assert kwargs["fields"] == ["text", "html"]
    register_mock.assert_called_once()
    artifact_assert_mock.assert_called_once()
