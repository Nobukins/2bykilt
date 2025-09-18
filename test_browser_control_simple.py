#!/usr/bin/env python3
"""
Simple test script to verify browser-control execution works
"""
import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.modules.direct_browser_control import execute_direct_browser_control

async def test_simple_browser_control():
    """Test simple browser-control execution"""
    print("Testing browser-control execution...")

    # Simple action to test
    action = {
        "name": "simple_test",
        "flow": [
            {"action": "command", "url": "https://httpbin.org/html"}
        ],
        "slowmo": 500
    }

    try:
        result = await execute_direct_browser_control(action, browser_type="chrome")
        print(f"Browser control execution result: {result}")
        return result
    except Exception as e:
        print(f"Error during browser control execution: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_simple_browser_control())
    print(f"Test completed with result: {result}")
    sys.exit(0 if result else 1)