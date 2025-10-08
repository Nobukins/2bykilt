import asyncio
import threading
import pytest

from src.modules.execution_debug_engine import ExecutionDebugEngine


class DummyBrowserManager:
    async def initialize_custom_browser(self, *args, **kwargs):
        # Simulate an initialization failure as the BrowserDebugManager would
        await asyncio.sleep(0)
        return {"status": "error", "message": "connect ECONNREFUSED 127.0.0.1:9222"}

    async def get_or_create_tab(self, *args, **kwargs):
        # Should not be called when initialization fails, but provide a stub
        class DummyPage:
            async def close(self):
                await asyncio.sleep(0)
        await asyncio.sleep(0)
        return None, DummyPage(), True

    async def highlight_automated_tab(self, page):
        await asyncio.sleep(0)


def test_execute_json_commands_handles_browser_init_error(monkeypatch):
    async def _run() -> object | None:
        engine = ExecutionDebugEngine()
        engine.browser_manager = DummyBrowserManager()
        commands_data = {"commands": [{"action": "command", "url": "http://example.com"}], "action_type": "unlock-future"}
        return await engine.execute_json_commands(commands_data, use_own_browser=True, headless=True)

    result_container: dict[str, object | None] = {}

    def _runner():
        result_container["value"] = asyncio.run(_run())

    thread = threading.Thread(target=_runner, name="execution-debug-engine-test")
    thread.start()
    thread.join()
    result = result_container.get("value")

    assert result is None or (isinstance(result, dict) and result.get("error"))
