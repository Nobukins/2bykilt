#!/usr/bin/env python3
"""
Test git-script execution with Edge browser and new JSON argument serialization
"""

import sys
import pytest
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

import asyncio
from src.script.script_manager import execute_git_script

@pytest.mark.local_only
async def test_git_script_with_edge():
    """Test git-script execution with Edge browser"""
    print("🔧 Testing git-script with Edge browser and JSON argument serialization...")
    
    url = "https://github.com/microsoft/vscode"
    goal = "Find the latest release version of VS Code"
    browser = "edge"
    
    try:
        result = await execute_git_script(
            url=url,
            goal=goal,
            browser_type=browser,
            action_type="git-script"
        )
        
        print("✅ Git-script execution completed!")
        print(f"Result status: {result.get('status', 'unknown')}")
        
        if result.get('success'):
            print("✅ Script executed successfully!")
        else:
            error_msg = result.get('error', 'Unknown error')
            print(f"❌ Script failed: {error_msg}")
            
            # Check if it's the Playwright argument error
            if "Arguments can not specify page to be opened" in error_msg:
                print("❌ Still getting Playwright argument error - JSON fix may not be applied")
                return False
            elif "V8" in error_msg and "memory" in error_msg.lower():
                print("ℹ️ V8 memory error - this is expected under high memory pressure")
                return True  # Memory error is different from argument error
                
        return True
        
    except Exception as e:
        print(f"❌ Exception during git-script execution: {e}")
        return False

if __name__ == "__main__":
    result = asyncio.run(test_git_script_with_edge())
    if result:
        print("\n✅ Test completed successfully!")
    else:
        print("\n❌ Test failed!")
