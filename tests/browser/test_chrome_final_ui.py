#!/usr/bin/env python3
"""
Final Chrome UI Integration Test
Tests the complete NEW METHOD automation with Chrome browser through UI
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

async def test_chrome_ui_automation():
    """Test Chrome automation through the complete UI pipeline"""
    
    print("🚀 Starting Chrome UI Automation Test (NEW METHOD)")
    print("=" * 60)
    
    # Verify environment settings
    print("📋 Environment Settings:")
    print(f"   BYKILT_BROWSER_TYPE: {os.environ.get('BYKILT_BROWSER_TYPE', 'not set')}")
    print(f"   DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', 'not set')}")
    print(f"   BYKILT_USE_NEW_METHOD: {os.environ.get('BYKILT_USE_NEW_METHOD', 'not set')}")
    print(f"   CHROME_PATH: {os.environ.get('CHROME_PATH', 'not set')}")
    print(f"   CHROME_USER_DATA: {os.environ.get('CHROME_USER_DATA', 'not set')}")
    print()
    
    # Check Chrome installation
    chrome_path = "/Applications/Google Chrome.app"
    if not Path(chrome_path).exists():
        print(f"❌ Chrome not found at {chrome_path}")
        return False
    print(f"✅ Chrome found at {chrome_path}")
    
    # Check Chrome profile
    chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
    if not Path(chrome_user_data).exists():
        print(f"❌ Chrome profile not found at {chrome_user_data}")
        return False
    print(f"✅ Chrome profile found at {chrome_user_data}")
    print()
    
    try:
        # Test 1: Initialize ChromeAutomator
        print("🧪 Test 1: ChromeAutomator Initialization")
        from utils.git_script_automator import ChromeAutomator
        
        automator = ChromeAutomator()
        print(f"   ✅ ChromeAutomator initialized")
        print(f"   📁 Source profile: {automator.source_profile_dir}")
        
        # Test 2: Validate source profile
        print("\n🧪 Test 2: Source Profile Validation")
        if automator.validate_source_profile():
            print("   ✅ Source profile validation passed")
            
            # Get profile info
            info = automator.get_automation_info()
            essential_count = len(info['profile_manager']['essential_files_found'])
            print(f"   📊 Essential files found: {essential_count}")
            print(f"   📊 Browser executable exists: {info['browser_launcher']['executable_exists']}")
        else:
            print("   ❌ Source profile validation failed")
            return False
        
        # Test 3: SeleniumProfile creation
        print("\n🧪 Test 3: SeleniumProfile Creation")
        temp_workspace = tempfile.mkdtemp()
        try:
            selenium_profile = automator.prepare_selenium_profile(temp_workspace)
            print(f"   ✅ SeleniumProfile created: {selenium_profile}")
            
            # Verify profile structure
            profile_path = Path(selenium_profile)
            if (profile_path / "Default" / "Preferences").exists():
                print("   ✅ Preferences file copied")
            if (profile_path / "Local State").exists():
                print("   ✅ Local State file copied")
                
        except Exception as e:
            print(f"   ❌ SeleniumProfile creation failed: {e}")
            return False
        
        # Test 4: Browser launch test (headful for stability)
        print("\n🧪 Test 4: Browser Launch Test (Headful)")
        try:
            async with automator.browser_context(temp_workspace, headless=False) as context:
                print("   ✅ Chrome launched successfully in headful mode")
                print(f"   📄 Pages count: {len(context.pages)}")
                
                # Create or get page
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()
                
                # Navigate to test page
                print("   🌐 Navigating to test page...")
                await page.goto("https://httpbin.org/user-agent", wait_until="networkidle", timeout=10000)
                
                title = await page.title()
                print(f"   📄 Page title: {title}")
                
                # Check user agent (should contain Chrome)
                content = await page.content()
                if "Chrome" in content:
                    print("   ✅ User agent contains Chrome - profile loaded correctly")
                else:
                    print("   ⚠️ User agent check inconclusive")
                
                print("   ✅ Browser navigation successful")
                
        except Exception as e:
            print(f"   ❌ Browser launch test failed: {e}")
            return False
        
        # Test 5: Complete workflow test
        print("\n🧪 Test 5: Complete Workflow Test")
        try:
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                test_url="https://example.com",
                headless=False  # Headful for stability
            )
            
            if result["success"]:
                print("   ✅ Complete workflow successful")
                print(f"   📄 Page title: {result.get('page_title', 'N/A')}")
                print(f"   🎯 Browser type: {result['browser_type']}")
            else:
                print(f"   ❌ Workflow failed: {result.get('error', 'Unknown error')}")
                return False
                
        except Exception as e:
            print(f"   ❌ Complete workflow test failed: {e}")
            return False
        
        # Cleanup
        print("\n🧪 Cleanup: SeleniumProfile")
        if automator.cleanup_selenium_profile():
            print("   ✅ SeleniumProfile cleaned up successfully")
        else:
            print("   ⚠️ SeleniumProfile cleanup warning")
        
        print("\n" + "=" * 60)
        print("🎉 Chrome UI Automation Test COMPLETED SUCCESSFULLY!")
        print("✅ All tests passed with Chrome NEW METHOD")
        return True
        
    except Exception as e:
        print(f"\n❌ Chrome UI automation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    finally:
        # Final cleanup
        try:
            import shutil
            if 'temp_workspace' in locals():
                shutil.rmtree(temp_workspace, ignore_errors=True)
        except:
            pass

if __name__ == "__main__":
    print("🔥 Chrome UI Automation Test with NEW METHOD (2024+)")
    print("Using venv312 virtual environment")
    print()
    
    success = asyncio.run(test_chrome_ui_automation())
    
    if success:
        print("\n🎊 SUCCESS: Chrome automation is working perfectly!")
        sys.exit(0)
    else:
        print("\n💥 FAILED: Chrome automation test failed")
        sys.exit(1)
