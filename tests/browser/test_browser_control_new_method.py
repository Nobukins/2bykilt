#!/usr/bin/env python3
"""
Test browser-control type with new method (GitScriptAutomator/BrowserLauncher)
"""
import asyncio
import sys
import os
import logging

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.modules.direct_browser_control import execute_direct_browser_control

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_browser_control():
    """Test browser-control action with new method"""
    print("🧪 Testing browser-control with NEW_METHOD")
    print("=" * 60)
    
    # Test action (simplified version of phrase-search from llms.txt)
    test_action = {
        "name": "test-browser-control",
        "type": "browser-control",
        "slowmo": 1000,
        "description": "Test browser-control with new method",
        "flow": [
            {
                "action": "command",
                "url": "https://nogtips.wordpress.com/2025/03/31/llms-txt%e3%81%ab%e3%81%a4%e3%81%84%e3%81%a6/",
                "wait_for": "body"
            },
            {
                "action": "extract_content"
            }
        ]
    }
    
    test_params = {
        "query": "test search"
    }
    
    print(f"📋 Test Action: {test_action['name']}")
    print("📋 Test URL: https://nogtips.wordpress.com/2025/03/31/llms-txt%e3%81%ab%e3%81%a4%e3%81%84%e3%81%a6/")
    print(f"📋 Expected behavior: Launch Chrome with profile, no warnings")
    print()
    
    try:
        # Execute the browser-control action
        result = await execute_direct_browser_control(test_action, **test_params)
        
        if result:
            print("✅ Browser-control test PASSED")
            print("💡 Check the browser that launched:")
            print("   - Should be Google Chrome (not Chromium)")
            print("   - Should use user profile")
            print("   - Should not show --no-sandbox warnings")
            print("   - Should not show Google API key warnings")
        else:
            print("❌ Browser-control test FAILED")
            
    except Exception as e:
        print(f"❌ Browser-control test ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_browser_control())
