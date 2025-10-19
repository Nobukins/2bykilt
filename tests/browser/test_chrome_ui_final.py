#!/usr/bin/env python3
"""
Final UI Browser Automation Test - Chrome Configuration
Tests the complete NEW METHOD with Chrome browser for real automation
"""

import asyncio
import pytest
import os
import sys
import tempfile
from pathlib import Path
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.mark.local_only
async def test_chrome_ui_automation():
    """Test complete UI automation with Chrome browser"""
    
    print("🚀 Final Chrome UI Automation Test - NEW METHOD")
    print("=" * 60)
    
    # Verify environment setup
    print(f"🔍 BYKILT_USE_NEW_METHOD: {os.environ.get('BYKILT_USE_NEW_METHOD', 'Not set')}")
    print(f"🔍 BYKILT_BROWSER_TYPE: {os.environ.get('BYKILT_BROWSER_TYPE', 'Not set')}")
    print(f"🔍 DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', 'Not set')}")
    print()
    
    try:
        from src.utils.git_script_automator import ChromeAutomator
        
        # Step 1: Initialize Chrome Automator
        print("📋 Step 1: Initializing Chrome Automator...")
        chrome_profile = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        
        if not Path(chrome_profile).exists():
            print("❌ Chrome profile not found - please ensure Chrome is installed")
            return False
            
        automator = ChromeAutomator()
        print(f"✅ Chrome Automator initialized")
        print(f"📁 Profile path: {automator.source_profile_dir}")
        
        # Step 2: Validate source profile
        print("\n📋 Step 2: Validating Chrome profile...")
        if not automator.validate_source_profile():
            print("❌ Chrome profile validation failed")
            return False
            
        info = automator.get_automation_info()
        print(f"✅ Profile validation passed")
        print(f"📊 Essential files found: {len(info['profile_manager']['essential_files_found'])}")
        print(f"📊 Browser executable exists: {info['browser_launcher']['executable_exists']}")
        
        # Step 3: Create temporary workspace
        print("\n📋 Step 3: Creating test workspace...")
        test_workspace = tempfile.mkdtemp(prefix="bykilt_chrome_test_")
        print(f"📁 Workspace: {test_workspace}")
        
        # Step 4: Execute complete automation workflow
        print("\n📋 Step 4: Executing Chrome automation workflow...")
        print("🎯 Target: https://example.com")
        
        result = await automator.execute_git_script_workflow(
            workspace_dir=test_workspace,
            test_url="https://example.com",
            headless=False  # Use headed mode for UI verification
        )
        
        # Step 5: Analyze results
        print("\n📋 Step 5: Analyzing results...")
        print("=" * 40)
        
        if result["success"]:
            print("🎉 SUCCESS: Chrome automation completed!")
            print(f"✅ Browser type: {result['browser_type']}")
            print(f"✅ Page title: {result.get('page_title', 'N/A')}")
            print(f"✅ SeleniumProfile created: {Path(result['selenium_profile']).exists()}")
            print(f"📁 SeleniumProfile path: {result['selenium_profile']}")
            
            # Additional verification
            selenium_profile = result['selenium_profile']
            essential_files = [
                "Default/Preferences",
                "Default/Cookies", 
                "Local State"
            ]
            
            print(f"\n🔍 Verifying SeleniumProfile contents:")
            for file_path in essential_files:
                target_file = Path(selenium_profile) / file_path
                status = "✅" if target_file.exists() else "❌"
                print(f"  {status} {file_path}")
            
            success = True
            
        else:
            print("❌ FAILED: Chrome automation failed")
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
            success = False
        
        # Step 6: Cleanup
        print(f"\n📋 Step 6: Cleanup...")
        cleanup_result = automator.cleanup_selenium_profile()
        print(f"🗑️ SeleniumProfile cleanup: {'✅' if cleanup_result else '❌'}")
        
        try:
            shutil.rmtree(test_workspace, ignore_errors=True)
            print(f"🗑️ Test workspace cleanup: ✅")
        except Exception as e:
            print(f"🗑️ Test workspace cleanup: ❌ {e}")
        
        return success
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test execution"""
    print("🌟 Chrome UI Automation Test with NEW METHOD")
    print("⚡ Powered by ProfileManager + BrowserLauncher + GitScriptAutomator")
    print()
    
    success = await test_chrome_ui_automation()
    
    print("\n" + "=" * 60)
    if success:
        print("🎊 CHROME TEST COMPLETED SUCCESSFULLY!")
        print("🎯 Ready for production use with Chrome browser")
    else:
        print("💥 CHROME TEST FAILED!")
        print("🔧 Please check the error messages above")
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
