"""
Test case to reproduce browser-control failure
"""
import pytest
import asyncio
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
from playwright.async_api import Error

from src.modules.direct_browser_control import execute_direct_browser_control

from _pytest.outcomes import OutcomeException

def _run_async(coro_fn):
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:
            result["error"] = exc

    thread = threading.Thread(target=worker, name="test-browser-control", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


@pytest.mark.ci_safe
class TestBrowserControlFailure:
    """Test cases to reproduce and fix browser-control execution failures"""

    def test_browser_control_basic_execution(self):
        """Test basic browser-control execution with minimal flow"""
        async def _inner():
            # Create action for testing
            action = {
                'name': 'test_search',
                'type': 'browser-control',
                'flow': [
                    {
                        'action': 'command',
                        'url': 'https://www.google.com'
                    },
                    {
                        'action': 'wait_for',
                        'selector': 'input[name="q"]'
                    }
                ],
                'slowmo': 500
            }

            # Test execution with mocked browser components
            with patch('src.modules.direct_browser_control.convert_flow_to_commands') as mock_convert, \
                 patch('src.modules.direct_browser_control.get_timeout_manager') as mock_get_timeout:

                # Mock the conversion function
                mock_convert.return_value = [
                    {'action': 'go_to_url', 'args': ['https://www.google.com']},
                    {'action': 'wait_for_element', 'args': ['input[name="q"]']}
                ]

                # Mock timeout manager
                mock_timeout_manager = MagicMock()
                mock_timeout_manager.is_cancelled.return_value = False

                async def mock_apply(coro, scope):
                    return await coro

                mock_timeout_manager.apply_timeout_to_coro = AsyncMock(side_effect=mock_apply)
                mock_get_timeout.return_value = mock_timeout_manager

                # Mock GitScriptAutomator and browser components
                with patch('src.modules.direct_browser_control.GitScriptAutomator') as mock_automator_class, \
                     patch('src.browser.browser_config.BrowserConfig') as mock_browser_config_class:

                    mock_automator = MagicMock()
                    mock_automator_class.return_value = mock_automator

                    mock_context = MagicMock()
                    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                    mock_context.__aexit__ = AsyncMock(return_value=None)
                    mock_automator.browser_context.return_value = mock_context

                    mock_page = MagicMock()
                    mock_context.new_page = AsyncMock(return_value=mock_page)
                    mock_page.close = AsyncMock()
                    mock_page.goto = AsyncMock()
                    mock_page.wait_for_selector = AsyncMock()
                    mock_page.keyboard = MagicMock()
                    mock_page.keyboard.press = AsyncMock()

                    mock_browser_config = MagicMock()
                    mock_browser_config.get_current_browser.return_value = "chromium"
                    mock_browser_config_class.return_value = mock_browser_config

                    # Execute the browser control
                    result = await execute_direct_browser_control(action)

                    # Verify the result
                    assert result is True

                    # Verify that browser_context was called
                    mock_automator.browser_context.assert_called_once()

                    # Verify that page operations were attempted
                    mock_context.new_page.assert_called_once()
                    mock_page.goto.assert_called_once_with("https://www.google.com", wait_until="domcontentloaded")

        _run_async(_inner)

    def test_browser_control_with_recording_path(self):
        """Test browser-control execution with recording path configuration"""
        async def _inner():
            # Create action with recording expectation
            action = {
                'name': 'test_with_recording',
                'type': 'browser-control',
                'flow': [
                    {
                        'action': 'command',
                        'url': 'https://example.com'
                    }
                ],
                'slowmo': 100
            }

            # Test with temporary recording directory
            with tempfile.TemporaryDirectory() as temp_dir:
                recording_path = Path(temp_dir) / "recordings"
                recording_path.mkdir(exist_ok=True)

                # Mock environment variable
                with patch.dict(os.environ, {'RECORDING_PATH': str(recording_path)}):
                    with patch('src.modules.direct_browser_control.convert_flow_to_commands') as mock_convert, \
                         patch('src.modules.direct_browser_control.get_timeout_manager') as mock_get_timeout:
                        # Mock conversion
                        mock_convert.return_value = [
                            {'action': 'go_to_url', 'args': ['https://example.com']}
                        ]

                        # Mock timeout manager
                        mock_timeout_manager = MagicMock()
                        mock_timeout_manager.is_cancelled.return_value = False

                        async def mock_apply(coro, scope):
                            return await coro

                        mock_timeout_manager.apply_timeout_to_coro = AsyncMock(side_effect=mock_apply)
                        mock_get_timeout.return_value = mock_timeout_manager

                        # Mock GitScriptAutomator
                        with patch('src.modules.direct_browser_control.GitScriptAutomator') as mock_automator_class, \
                             patch('src.browser.browser_config.BrowserConfig') as mock_browser_config_class:
                            mock_automator = MagicMock()
                            mock_automator_class.return_value = mock_automator

                            # Mock browser context
                            mock_context = MagicMock()
                            mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                            mock_context.__aexit__ = AsyncMock(return_value=None)
                            mock_automator.browser_context.return_value = mock_context

                            mock_page = MagicMock()
                            mock_context.new_page = AsyncMock(return_value=mock_page)
                            mock_page.close = AsyncMock()
                            mock_page.goto = AsyncMock()

                            mock_browser_config = MagicMock()
                            mock_browser_config.get_current_browser.return_value = "firefox"
                            mock_browser_config_class.return_value = mock_browser_config

                            # Execute
                            result = await execute_direct_browser_control(action)

                            # Verify
                            assert result is True

        _run_async(_inner)

    def test_browser_control_error_handling(self):
        """Test error handling in browser-control execution"""
        async def _inner():
            action = {
                'name': 'test_error_handling',
                'type': 'browser-control',
                'flow': [
                    {
                        'action': 'command',
                        'url': 'https://invalid-url-that-will-fail.com'
                    }
                ],
                'slowmo': 100
            }

            # Test with mocked failure
            with patch('src.modules.direct_browser_control.convert_flow_to_commands') as mock_convert, \
                 patch('src.modules.direct_browser_control.get_timeout_manager') as mock_get_timeout:
                # Mock conversion
                mock_convert.return_value = [
                    {'action': 'go_to_url', 'args': ['https://invalid-url-that-will-fail.com']}
                ]

                # Mock timeout manager
                mock_timeout_manager = MagicMock()
                mock_timeout_manager.is_cancelled.return_value = False

                async def mock_apply(coro, scope):
                    return await coro

                mock_timeout_manager.apply_timeout_to_coro = AsyncMock(side_effect=mock_apply)
                mock_get_timeout.return_value = mock_timeout_manager

                # Mock GitScriptAutomator to raise exception
                with patch('src.modules.direct_browser_control.GitScriptAutomator') as mock_automator_class, \
                     patch('src.browser.browser_config.BrowserConfig') as mock_browser_config_class:
                    mock_automator = MagicMock()
                    mock_automator_class.return_value = mock_automator

                    # Mock browser context to raise exception
                    mock_context = MagicMock()
                    mock_context.__aenter__ = AsyncMock(return_value=mock_context)
                    mock_context.__aexit__ = AsyncMock(return_value=None)
                    mock_automator.browser_context.return_value = mock_context

                    mock_context.new_page = AsyncMock(side_effect=Error("Browser initialization failed"))

                    mock_browser_config = MagicMock()
                    mock_browser_config.get_current_browser.return_value = "chromium"
                    mock_browser_config_class.return_value = mock_browser_config

                    # Execute and expect failure
                    result = await execute_direct_browser_control(action)

                    # Verify failure is handled gracefully
                    assert result is False

        _run_async(_inner)