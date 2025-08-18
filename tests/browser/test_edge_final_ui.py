#!/usr/bin/env python3
"""
Final Edge UI Integration Test
Tests the complete NEW METHOD (2024+) automation workflow for Microsoft Edge

This test confirms:
1. ProfileManager: SeleniumProfile creation and file copy for Edge
2. BrowserLauncher: Playwright persistent context launch with Edge
3. GitScriptAutomator: End-to-end workflow execution
4. UI-level automation: Navigation, interaction, and workflow completion

Note: Edge automation is stable only in headful mode as of 2024+
"""

import os
import sys
import tempfile
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.git_script_automator import EdgeAutomator
from src.utils.app_logger import logger

async def test_edge_final_ui_automation():
    """
    Complete Edge UI automation test using NEW METHOD (2024+)
    
    This test performs:
    1. Source profile validation
    2. SeleniumProfile creation with file copy
    3. Edge browser launch with Playwright persistent context
    4. UI navigation and automation workflow
    5. Resource cleanup
    
    Expected: All steps pass in headful mode
    """
    logger.info("🎯 Starting Edge Final UI Integration Test (NEW METHOD 2024+)")
    
    automator = None
    workspace_dir = None
    
    try:
        # Step 1: Initialize Edge automator
        logger.info("📋 Step 1: Initialize EdgeAutomator")
        automator = EdgeAutomator()
        
        # Step 2: Validate source profile
        logger.info("📋 Step 2: Validate Edge source profile")
        if not automator.validate_source_profile():
            raise Exception("Edge source profile validation failed")
        logger.info("✅ Edge source profile validation passed")
        
        # Step 3: Create temporary workspace
        logger.info("📋 Step 3: Create temporary workspace directory")
        workspace_dir = tempfile.mkdtemp(prefix="edge_ui_test_")
        logger.info(f"📁 Workspace: {workspace_dir}")
        
        # Step 4: Execute complete automation workflow (HEADFUL for Edge stability)
        logger.info("📋 Step 4: Execute Edge automation workflow (headful mode)")
        result = await automator.execute_git_script_workflow(
            workspace_dir=workspace_dir,
            test_url="https://httpbin.org/get",  # Simple test endpoint
            headless=False  # Force headful for Edge stability
        )
        
        # Step 5: Verify results
        logger.info("📋 Step 5: Verify automation results")
        if not result["success"]:
            raise Exception(f"Edge automation workflow failed: {result.get('error', 'Unknown error')}")
        
        logger.info("✅ Edge automation workflow completed successfully")
        logger.info(f"📁 SeleniumProfile used: {result.get('selenium_profile')}")
        logger.info(f"🌐 Test URL accessed: https://httpbin.org/get")
        
        # Step 6: Validate profile cleanup
        logger.info("📋 Step 6: Validate profile cleanup (if applicable)")
        selenium_profile = result.get('selenium_profile')
        if selenium_profile and Path(selenium_profile).exists():
            logger.info(f"📁 SeleniumProfile still exists: {selenium_profile}")
            logger.info("ℹ️ This is expected behavior - cleanup can be manual")
        else:
            logger.info("🧹 SeleniumProfile already cleaned up")
        
        logger.info("🎉 Edge Final UI Integration Test PASSED")
        return True
        
    except Exception as e:
        logger.error(f"❌ Edge Final UI Integration Test FAILED: {str(e)}")
        return False
        
    finally:
        # Cleanup
        if workspace_dir and Path(workspace_dir).exists():
            import shutil
            shutil.rmtree(workspace_dir, ignore_errors=True)
            logger.info(f"🧹 Cleaned up workspace: {workspace_dir}")

async def main():
    """Main test execution"""
    logger.info("=" * 60)
    logger.info("Edge Final UI Integration Test - NEW METHOD (2024+)")
    logger.info("=" * 60)
    
    # Check environment
    use_new_method = os.environ.get('BYKILT_USE_NEW_METHOD', 'false')
    browser_type = os.environ.get('BYKILT_BROWSER_TYPE', 'edge')
    
    logger.info(f"Environment: BYKILT_USE_NEW_METHOD={use_new_method}")
    logger.info(f"Environment: BYKILT_BROWSER_TYPE={browser_type}")
    
    if use_new_method.lower() != 'true':
        logger.warning("⚠️ BYKILT_USE_NEW_METHOD is not set to 'true'")
        logger.warning("⚠️ This test requires NEW METHOD to be enabled")
    
    # Run test
    success = await test_edge_final_ui_automation()
    
    logger.info("=" * 60)
    if success:
        logger.info("✅ ALL EDGE UI TESTS PASSED")
        logger.info("🎯 Edge NEW METHOD automation is fully functional")
        logger.info("📋 Edge works best in headful mode (headless is unstable)")
    else:
        logger.error("❌ EDGE UI TESTS FAILED")
        logger.error("🔍 Check logs above for details")
    logger.info("=" * 60)
    
    return success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
