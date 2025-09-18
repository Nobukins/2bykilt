#!/usr/bin/env python3
"""
Test script to simulate Issue #220 browser-control failure scenario
"""
import asyncio
import sys
import os

# Import using proper package structure
from src.modules.direct_browser_control import execute_direct_browser_control

async def test_issue_220_scenario():
    """Test the actual Issue #220 scenario - browser-control execution failure"""
    print("Testing Issue #220 scenario: browser-control execution failure...")

    # Simulate a typical browser-control action that might fail
    action = {
        "name": "search_and_click",
        "flow": [
            {"action": "command", "url": "https://httpbin.org/html"},
            {"action": "wait_for", "selector": "h1"},
            {"action": "extract_text", "selector": "h1"}
        ],
        "slowmo": 1000
    }

    try:
        print("Executing browser-control action with multiple steps...")
        result = await execute_direct_browser_control(action, **{"browser_type": "chrome"})

        if result:
            print("✅ Issue #220 scenario test PASSED - browser-control executed successfully")
            return True
        else:
            print("❌ Issue #220 scenario test FAILED - browser-control execution returned False")
            return False

    except Exception as e:
        print(f"❌ Issue #220 scenario test FAILED - Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

async def test_error_scenario():
    """Test error handling scenario"""
    print("\nTesting error handling scenario...")

    # Action with invalid selector that should cause an error
    action = {
        "name": "error_test",
        "flow": [
            {"action": "command", "url": "https://httpbin.org/html"},
            {"action": "wait_for", "selector": "non-existent-selector"},
            {"action": "click", "selector": "also-non-existent"}
        ],
        "slowmo": 500
    }

    try:
        result = await execute_direct_browser_control(action, **{"browser_type": "chrome"})

        if not result:
            print("✅ Error handling test PASSED - properly handled error scenario")
            return True
        else:
            print("❌ Error handling test FAILED - should have returned False for error")
            return False

    except Exception as e:
        print(f"✅ Error handling test PASSED - Exception properly caught: {e}")
        return True

async def main():
    """Run all tests"""
    print("=" * 60)
    print("BROWSER-CONTROL FAILURE FIX VERIFICATION")
    print("=" * 60)

    # Test Issue #220 scenario
    test1_result = await test_issue_220_scenario()

    # Test error handling
    test2_result = await test_error_scenario()

    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)
    print(f"Issue #220 scenario test: {'PASSED' if test1_result else 'FAILED'}")
    print(f"Error handling test: {'PASSED' if test2_result else 'FAILED'}")

    overall_result = test1_result and test2_result
    print(f"\nOverall result: {'ALL TESTS PASSED' if overall_result else 'SOME TESTS FAILED'}")

    return overall_result

if __name__ == "__main__":
    result = asyncio.run(main())
    print(f"\nFinal result: {result}")
    sys.exit(0 if result else 1)