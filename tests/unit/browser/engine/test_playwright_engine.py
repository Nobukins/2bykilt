"""
PlaywrightEngine ユニットテスト

BrowserEngine 契約仕様への準拠と、
既存 unlock-future 互換性を検証します。

実行:
    pytest tests/unit/browser/engine/test_playwright_engine.py -v
"""

import asyncio
import threading

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from _pytest.outcomes import OutcomeException

from src.browser.engine.playwright_engine import PlaywrightEngine
from src.browser.engine.browser_engine import LaunchContext, EngineType


def _run_async(coro_fn):
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:
            result["error"] = exc

    thread = threading.Thread(target=worker, name="playwright-engine-test", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


@pytest.fixture
def engine():
    """テスト用 PlaywrightEngine インスタンス"""
    return PlaywrightEngine()


class TestPlaywrightEngineLaunch:
    """エンジン起動テスト"""
    
    def test_launch_default_context(self, engine):
        """デフォルト設定でブラウザを起動"""
        async def _inner():
            with patch("src.browser.engine.playwright_engine.async_playwright") as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)

                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.set_default_timeout = MagicMock()
                mock_context.tracing.start = AsyncMock()

                context = LaunchContext(headless=True, trace_enabled=False)
                await engine.launch(context)

                assert engine._browser is not None
                assert engine._context is not None
                assert engine._page is not None
                mock_pw_instance.chromium.launch.assert_called_once()

        _run_async(_inner)

    def test_launch_with_trace(self, engine):
        """トレース有効化でブラウザを起動"""
        async def _inner():
            with patch("src.browser.engine.playwright_engine.async_playwright") as mock_pw:
                mock_pw_instance = AsyncMock()
                mock_pw.return_value.start = AsyncMock(return_value=mock_pw_instance)

                mock_browser = AsyncMock()
                mock_context = AsyncMock()
                mock_page = AsyncMock()

                mock_pw_instance.chromium.launch = AsyncMock(return_value=mock_browser)
                mock_browser.new_context = AsyncMock(return_value=mock_context)
                mock_context.new_page = AsyncMock(return_value=mock_page)
                mock_context.set_default_timeout = MagicMock()
                mock_context.tracing.start = AsyncMock()

                context = LaunchContext(headless=True, trace_enabled=True)
                await engine.launch(context)

                mock_context.tracing.start.assert_called_once()
                assert engine._trace_path is not None

        _run_async(_inner)


class TestPlaywrightEngineActions:
    """アクション実行テスト"""
    
    @pytest.fixture
    def launched_engine(self, engine):
        """起動済みエンジン（モック）"""
        engine._page = AsyncMock()
        engine._context = AsyncMock()
        engine._browser = AsyncMock()
        return engine
    
    def test_navigate(self, launched_engine):
        """ナビゲーション実行"""
        async def _inner():
            launched_engine._page.goto = AsyncMock()
            launched_engine._page.wait_for_load_state = AsyncMock()

            result = await launched_engine.navigate("https://example.com")

            assert result.success is True
            assert result.action_type == "navigate"
            assert result.duration_ms > 0
            launched_engine._page.goto.assert_called_once()

        _run_async(_inner)

    def test_dispatch_click(self, launched_engine):
        """クリックアクション"""
        async def _inner():
            launched_engine._page.click = AsyncMock()

            result = await launched_engine.dispatch({
                "type": "click",
                "selector": "#button"
            })

            assert result.success is True
            assert result.action_type == "click"
            launched_engine._page.click.assert_called_once_with("#button", timeout=30000)

        _run_async(_inner)

    def test_dispatch_fill(self, launched_engine):
        """フォーム入力アクション"""
        async def _inner():
            launched_engine._page.fill = AsyncMock()

            result = await launched_engine.dispatch({
                "type": "fill",
                "selector": "#input",
                "text": "test value"
            })

            assert result.success is True
            assert result.action_type == "fill"
            launched_engine._page.fill.assert_called_once_with("#input", "test value")

        _run_async(_inner)

    def test_dispatch_screenshot(self, launched_engine):
        """スクリーンショットアクション"""
        async def _inner():
            launched_engine._page.screenshot = AsyncMock(return_value=b"fake-png-bytes")

            result = await launched_engine.dispatch({
                "type": "screenshot",
                "path": "test.png"
            })

            assert result.success is True
            assert result.action_type == "screenshot"
            assert "screenshot_path" in result.artifacts

        _run_async(_inner)


class TestPlaywrightEngineMetrics:
    """メトリクス収集テスト"""
    
    def test_metrics_update(self, engine):
        """アクション実行後のメトリクス更新"""
        async def _inner():
            engine._page = AsyncMock()
            engine._page.goto = AsyncMock()
            engine._page.wait_for_load_state = AsyncMock()

            # 初期状態
            assert engine._metrics.total_actions == 0
            assert engine._metrics.successful_actions == 0

            # navigate 実行
            await engine.navigate("https://example.com")

            # メトリクス更新確認
            assert engine._metrics.total_actions == 1
            assert engine._metrics.successful_actions == 1
            assert engine._metrics.avg_latency_ms > 0

        _run_async(_inner)


class TestPlaywrightEngineShutdown:
    """シャットダウンテスト"""
    
    def test_shutdown_with_capture(self, engine):
        """最終状態キャプチャ付きシャットダウン"""
        async def _inner():
            engine._page = AsyncMock()
            engine._context = AsyncMock()
            engine._browser = AsyncMock()
            engine._playwright = AsyncMock()

            engine._context.close = AsyncMock()
            engine._browser.close = AsyncMock()
            engine._playwright.stop = AsyncMock()
            engine._page.screenshot = AsyncMock()

            await engine.shutdown(capture_final_state=True)

            engine._context.close.assert_called_once()
            engine._browser.close.assert_called_once()
            engine._playwright.stop.assert_called_once()
            assert engine._metrics.shutdown_at is not None

        _run_async(_inner)
