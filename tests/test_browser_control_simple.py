#!/usr/bin/env python3
"""
Simple test script to verify browser-control execution works
"""
import asyncio
import pytest
import os
import sys
import threading
from _pytest.outcomes import OutcomeException

# Import using proper package structure
from src.modules.direct_browser_control import execute_direct_browser_control

def _run_async(coro_fn):
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:  # pragma: no cover - bubble up
            result["error"] = exc

    thread = threading.Thread(target=worker, name="browser-control-simple", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


@pytest.mark.local_only
def test_simple_browser_control():
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
        result = _run_async(lambda: execute_direct_browser_control(action, **{"browser_type": "chrome"}))
        print(f"Browser control execution result: {result}")
        assert result
    except Exception as e:  # pragma: no cover - diagnostic aid
        print(f"Error during browser control execution: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        test_simple_browser_control()
        print("Test completed with result: True")
        sys.exit(0)
    except Exception:
        print("Test completed with result: False")
        sys.exit(1)