import types
from unittest import mock
from unittest.mock import Mock, MagicMock, AsyncMock, patch

import pytest

from src.ui import browser_agent


class _DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _DummyButton:
    def __init__(self):
        self.click_args = []

    def click(self, **kwargs):
        self.click_args.append(kwargs)


class _DummyState:
    def __init__(self, value):
        self.value = value


@pytest.fixture(autouse=True)
def patch_gradio(monkeypatch):
    fake_block = _DummyContext()
    fake_box = _DummyContext()
    fake_row = _DummyContext()
    buttons = []

    monkeypatch.setattr(browser_agent, "gr", mock.Mock(), raising=False)
    browser_agent.gr.Blocks.return_value = fake_block
    browser_agent.gr.Box.return_value = fake_box
    browser_agent.gr.Row.return_value = fake_row

    def button_factory(*args, **kwargs):
        button = _DummyButton()
        buttons.append(button)
        return button

    browser_agent.gr.Button.side_effect = button_factory
    browser_agent.gr.Markdown.side_effect = lambda *args, **kwargs: None
    browser_agent.gr.State.side_effect = lambda value=None: _DummyState(value)

    yield buttons

    browser_agent.gr.reset_mock()


@pytest.mark.local_only
def test_chrome_restart_dialog_wires_callable_callbacks(patch_gradio):
    buttons = patch_gradio

    dialog = browser_agent.chrome_restart_dialog()

    assert dialog is not None
    assert len(buttons) == 2

    yes_click = buttons[0].click_args[0]
    no_click = buttons[1].click_args[0]

    assert callable(yes_click["fn"])
    assert callable(no_click["fn"])
    assert yes_click["fn"]() == "yes"
    assert no_click["fn"]() == "no"


@pytest.mark.local_only
class TestRunBrowserAgent:
    """Test run_browser_agent function."""

    @pytest.mark.asyncio
    async def test_run_browser_agent_url_without_llm(self):
        """Test running browser agent with URL when LLM is disabled."""
        with patch("src.ui.browser_agent.os.getenv", return_value="false"), \
             patch("src.browser.browser_debug_manager.BrowserDebugManager") as mock_browser_mgr, \
             patch("src.utils.debug_utils.DebugUtils") as mock_debug_utils:
            
            # Mock browser manager
            mock_browser_instance = Mock()
            mock_browser_instance.initialize_with_session = AsyncMock(
                return_value={"status": "success", "session_id": "test-session"}
            )
            mock_browser_mgr.return_value = mock_browser_instance
            
            # Mock debug utils
            mock_debug_instance = Mock()
            mock_debug_instance.execute_goto_url = AsyncMock(
                return_value={"status": "success"}
            )
            mock_debug_utils.return_value = mock_debug_instance
            
            # Run with URL
            result = await browser_agent.run_browser_agent(
                task="https://example.com",
                add_infos="",
                llm_provider="",
                llm_model_name="",
                llm_num_ctx=0,
                llm_temperature=0,
                llm_base_url="",
                llm_api_key="",
                use_vision=False,
                use_own_browser=False,
                headless=True
            )
            
            # Verify result
            assert result["status"] == "success"
            assert "https://example.com" in result["message"]
            mock_debug_instance.execute_goto_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_browser_agent_task_without_llm(self):
        """Test running browser agent with task description when LLM is disabled."""
        with patch("src.ui.browser_agent.os.getenv", return_value="false"), \
             patch("src.browser.browser_debug_manager.BrowserDebugManager") as mock_browser_mgr, \
             patch("src.utils.debug_utils.DebugUtils"):
            
            # Mock browser manager
            mock_browser_instance = Mock()
            mock_browser_instance.initialize_with_session = AsyncMock(
                return_value={"status": "success", "session_id": "test-session"}
            )
            mock_browser_mgr.return_value = mock_browser_instance
            
            # Run with task (not URL)
            result = await browser_agent.run_browser_agent(
                task="search for something",
                add_infos="",
                llm_provider="",
                llm_model_name="",
                llm_num_ctx=0,
                llm_temperature=0,
                llm_base_url="",
                llm_api_key="",
                use_vision=False,
                use_own_browser=False,
                headless=True
            )
            
            # Verify result - should inform LLM is disabled
            assert result["status"] == "info"
            assert "LLM機能が無効" in result["message"]

    @pytest.mark.asyncio
    async def test_run_browser_agent_browser_init_failure(self):
        """Test handling browser initialization failure."""
        with patch("src.ui.browser_agent.os.getenv", return_value="false"), \
             patch("src.browser.browser_debug_manager.BrowserDebugManager") as mock_browser_mgr, \
             patch("src.utils.debug_utils.DebugUtils"):
            
            # Mock browser manager with initialization failure
            mock_browser_instance = Mock()
            mock_browser_instance.initialize_with_session = AsyncMock(
                return_value={"status": "error", "message": "Failed to start browser"}
            )
            mock_browser_mgr.return_value = mock_browser_instance
            
            # Run
            result = await browser_agent.run_browser_agent(
                task="https://example.com",
                add_infos="",
                llm_provider="",
                llm_model_name="",
                llm_num_ctx=0,
                llm_temperature=0,
                llm_base_url="",
                llm_api_key="",
                use_vision=False,
                use_own_browser=False,
                headless=True
            )
            
            # Verify error handling
            assert result["status"] == "error"
            assert "ブラウザの初期化に失敗" in result["message"]

    @pytest.mark.asyncio
    async def test_run_browser_agent_exception_handling(self):
        """Test exception handling in run_browser_agent."""
        with patch("src.ui.browser_agent.os.getenv", return_value="false"), \
             patch("src.browser.browser_debug_manager.BrowserDebugManager") as mock_browser_mgr, \
             patch("src.utils.debug_utils.DebugUtils"):
            
            # Mock browser manager that raises exception during init
            mock_browser_instance = Mock()
            mock_browser_instance.initialize_with_session = AsyncMock(
                side_effect=Exception("Unexpected error")
            )
            mock_browser_mgr.return_value = mock_browser_instance
            
            # Run
            result = await browser_agent.run_browser_agent(
                task="https://example.com",
                add_infos="",
                llm_provider="",
                llm_model_name="",
                llm_num_ctx=0,
                llm_temperature=0,
                llm_base_url="",
                llm_api_key="",
                use_vision=False,
                use_own_browser=False,
                headless=True
            )
            
            # Verify error handling
            assert result["status"] == "error"
            assert "実行エラー" in result["message"]
            assert "Unexpected error" in result["errors"]

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="LLM-enabled path requires complex mocking of dynamic imports")
    async def test_run_browser_agent_with_llm_enabled(self):
        """Test run_browser_agent when LLM is enabled."""
        # This test is skipped due to complexity of mocking dynamic imports
        # in the LLM-enabled code path. Manual testing recommended.
        pass


@pytest.mark.local_only
class TestShowRestartDialog:
    """Test show_restart_dialog function."""

    @pytest.mark.asyncio
    async def test_show_restart_dialog_yes_macos(self):
        """Test Chrome restart on macOS when user confirms."""
        with patch("src.ui.browser_agent.chrome_restart_dialog") as mock_dialog, \
             patch("src.ui.browser_agent.sys.platform", "darwin"), \
             patch("src.ui.browser_agent.subprocess.run") as mock_run, \
             patch("src.ui.browser_agent.subprocess.Popen") as mock_popen, \
             patch("src.ui.browser_agent.time.sleep"), \
             patch("src.ui.browser_agent.os.getenv") as mock_getenv:
            
            # Mock dialog
            mock_dialog_instance = Mock()
            mock_dialog_instance.launch = AsyncMock(return_value="yes")
            mock_dialog.return_value = mock_dialog_instance
            
            # Mock environment
            mock_getenv.side_effect = lambda key, default=None: {
                "CHROME_PATH": "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "CHROME_DEBUGGING_PORT": "9222",
                "CHROME_USER_DATA": ""
            }.get(key, default)
            
            # Run
            result = await browser_agent.show_restart_dialog()
            
            # Verify Chrome was killed and restarted
            mock_run.assert_called_once()
            mock_popen.assert_called_once()
            assert "再起動しました" in result

    @pytest.mark.asyncio
    async def test_show_restart_dialog_no(self):
        """Test when user cancels restart."""
        with patch("src.ui.browser_agent.chrome_restart_dialog") as mock_dialog:
            
            # Mock dialog - user clicks no
            mock_dialog_instance = Mock()
            mock_dialog_instance.launch = AsyncMock(return_value="no")
            mock_dialog.return_value = mock_dialog_instance
            
            # Run
            result = await browser_agent.show_restart_dialog()
            
            # Verify operation was cancelled
            assert "キャンセル" in result

    @pytest.mark.asyncio
    async def test_show_restart_dialog_error_handling(self):
        """Test error handling in show_restart_dialog."""
        with patch("src.ui.browser_agent.chrome_restart_dialog") as mock_dialog, \
             patch("src.ui.browser_agent.sys.platform", "darwin"), \
             patch("src.ui.browser_agent.subprocess.run", side_effect=Exception("Process error")), \
             patch("src.ui.browser_agent.time.sleep"):
            
            # Mock dialog - user confirms
            mock_dialog_instance = Mock()
            mock_dialog_instance.launch = AsyncMock(return_value="yes")
            mock_dialog.return_value = mock_dialog_instance
            
            # Run
            result = await browser_agent.show_restart_dialog()
            
            # Verify error is handled
            assert "エラーが発生しました" in result
