import asyncio
import pytest

from src.modules.execution_debug_engine import ExecutionDebugEngine


class DummyBrowserManager:
    async def initialize_custom_browser(self, *args, **kwargs):
        # Simulate an initialization failure as the BrowserDebugManager would
        return {"status": "error", "message": "connect ECONNREFUSED 127.0.0.1:9222"}

    async def get_or_create_tab(self, *args, **kwargs):
        # Should not be called when initialization fails, but provide a stub
        class DummyPage:
            async def close(self):
                pass
        return None, DummyPage(), True

    async def highlight_automated_tab(self, page):
        pass


@pytest.mark.asyncio
async def test_execute_json_commands_handles_browser_init_error(monkeypatch):
    engine = ExecutionDebugEngine()
    # Replace the browser_manager with our dummy one that returns an error
    engine.browser_manager = DummyBrowserManager()

    # Prepare minimal commands_data
    commands_data = {"commands": [{"action": "command", "url": "http://example.com"}], "action_type": "unlock-future"}

    # execute_json_commands should not raise KeyError and should return/exit gracefully
    result = await engine.execute_json_commands(commands_data, use_own_browser=True, headless=True)

    # Expect None or an error dict indicating browser init failure
    assert result is None or (isinstance(result, dict) and result.get("error"))
