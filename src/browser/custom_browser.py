import asyncio
import pdb
from typing import List
from datetime import datetime

from playwright.async_api import Browser as PlaywrightBrowser
from playwright.async_api import (
    BrowserContext as PlaywrightBrowserContext,
)
from playwright.async_api import (
    Playwright,
    async_playwright,
)
from browser_use.browser.browser import Browser
from browser_use.browser.context import BrowserContext, BrowserContextConfig
from playwright.async_api import BrowserContext as PlaywrightBrowserContext
import logging

from .custom_context import CustomBrowserContext

logger = logging.getLogger(__name__)

class CustomBrowser(Browser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.action_history = []
        self.current_test_results = None

    async def new_context(
        self,
        config: BrowserContextConfig = BrowserContextConfig()
    ) -> CustomBrowserContext:
        context = CustomBrowserContext(config=config, browser=self)
        context.on("browserevent", self._handle_browser_event)
        return context

    async def _handle_browser_event(self, event: dict):
        """Handle browser events and update action history"""
        self.action_history.append({
            "timestamp": datetime.now().isoformat(),
            "event": event
        })

    def get_action_history(self) -> List[dict]:
        """Return the browser action history"""
        return self.action_history

    def update_test_results(self, results: dict):
        """Update current test execution results"""
        self.current_test_results = results
        logger.info(f"Updated test results: {results}")

    async def execute_browser_action(self, action_data: dict) -> dict:
        """Execute a browser action with specified parameters"""
        try:
            if not self.current_context:
                raise ValueError("No active browser context")

            result = await self.current_context.execute_action(
                action_type=action_data["params"]["action"],
                selector=action_data["params"].get("selector"),
                value=action_data["params"].get("value")
            )

            return {
                "success": True,
                "result": result,
                "action": action_data
            }
        except Exception as e:
            logger.error(f"Browser action execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "action": action_data
            }

class CustomBrowserContext(BrowserContext):
    def __init__(self, config=None, browser=None):
        super().__init__(config=config, browser=browser)
        self._event_handlers = {}

    def on(self, event: str, handler):
        """Register event handler"""
        if event not in self._event_handlers:
            self._event_handlers[event] = []
        self._event_handlers[event].append(handler)
        
    def emit(self, event: str, *args, **kwargs):
        """Emit event to registered handlers"""
        if event in self._event_handlers:
            for handler in self._event_handlers[event]:
                handler(*args, **kwargs)
