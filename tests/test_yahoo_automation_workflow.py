import asyncio
import pytest
import os
from src.modules.execution_debug_engine import ExecutionDebugEngine

@pytest.mark.asyncio
async def test_yahoo_automation_workflow():
    """Test complete yahoo.co.jp automation workflow with screenshot, h1 extraction, and tab management"""
    engine = ExecutionDebugEngine()

    # Commands for the complete workflow
    commands = [
        {
            "action": "command",
            "args": ["https://yahoo.co.jp"]
        },
        {
            "action": "screenshot",
            "args": ["yahoo_screenshot.png"]
        },
        {
            "action": "extract_content",
            "args": ["h1"]
        },
        {
            "action": "close_tab"
        }
    ]

    # Execute commands with new tab selection
    await engine.execute_commands(
        commands=commands,
        use_own_browser=True,  # Use CDP
        headless=False,
        tab_selection="new_tab",  # Open in new tab
        action_type="unlock-future"
    )

    # Verify screenshot was created
    screenshot_path = "yahoo_screenshot.png"
    assert os.path.exists(screenshot_path), f"Screenshot file {screenshot_path} was not created"

    # Clean up screenshot file
    if os.path.exists(screenshot_path):
        os.remove(screenshot_path)
