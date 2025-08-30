#!/usr/bin/env python3
"""
Complete Integration Test for NEW METHOD (2024+)
Tests the full git-script automation workflow using both Chrome and Edge

This test confirms:
1. NEW METHOD integration in script_manager.py
2. Complete git-script workflow execution 
3. ProfileManager + BrowserLauncher integration
4. Chrome and Edge automation stability
5. Environment variable control (BYKILT_USE_NEW_METHOD)
"""

import os
import sys
import asyncio
import tempfile
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.script.script_manager import execute_script
from src.utils.app_logger import logger

async def test_chrome_git_script():
    """Test git-script execution with Chrome using NEW METHOD"""
    logger.info("🎯 Testing Chrome git-script with NEW METHOD")
    
    # Set Chrome for this test
    os.environ['BYKILT_BROWSER_TYPE'] = 'chrome'
    
    # Create a simple test script info
    script_info = {
        'type': 'git-script',
        'git': 'https://github.com/octocat/Hello-World.git',
        'script_path': 'README.md',  # Simple file that exists
        'version': 'main',
        'command': 'echo "Testing git-script: ${script_path}"'
    }
    
    params = {}
    
    try:
        result, script_path = await execute_script(
            script_info=script_info,
            params=params,
            headless=False,  # Headful for stability
            save_recording_path=None,
            browser_type='chrome'
        )
        
        logger.info(f"Chrome git-script result: {result}")
        logger.info(f"Chrome script path: {script_path}")
        
        if "NEW METHOD git-script executed successfully" in result:
            logger.info("✅ Chrome git-script with NEW METHOD PASSED")
            return True
        else:
            logger.error("❌ Chrome git-script with NEW METHOD FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Chrome git-script failed with exception: {str(e)}")
        return False

async def test_edge_git_script():
    """Test git-script execution with Edge using NEW METHOD"""
    logger.info("🎯 Testing Edge git-script with NEW METHOD")
    
    # Set Edge for this test
    os.environ['BYKILT_BROWSER_TYPE'] = 'edge'
    
    # Create a simple test script info
    script_info = {
        'type': 'git-script',
        'git': 'https://github.com/octocat/Hello-World.git',
        'script_path': 'README.md',  # Simple file that exists
        'version': 'main',
        'command': 'echo "Testing git-script: ${script_path}"'
    }
    
    params = {}
    
    try:
        result, script_path = await execute_script(
            script_info=script_info,
            params=params,
            headless=False,  # Headful for Edge stability
            save_recording_path=None,
            browser_type='edge'
        )
        
        logger.info(f"Edge git-script result: {result}")
        logger.info(f"Edge script path: {script_path}")
        
        if "NEW METHOD git-script executed successfully" in result:
            logger.info("✅ Edge git-script with NEW METHOD PASSED")
            return True
        else:
            logger.error("❌ Edge git-script with NEW METHOD FAILED")
            return False
            
    except Exception as e:
        logger.error(f"❌ Edge git-script failed with exception: {str(e)}")
        return False

async def main():
    """Main test execution"""
    logger.info("=" * 80)
    logger.info("Complete Integration Test - NEW METHOD (2024+) Git-Script Workflow")
    logger.info("=" * 80)
    
    # Check environment
    use_new_method = os.environ.get('BYKILT_USE_NEW_METHOD', 'false')
    logger.info(f"Environment: BYKILT_USE_NEW_METHOD={use_new_method}")
    
    if use_new_method.lower() != 'true':
        logger.error("❌ BYKILT_USE_NEW_METHOD must be set to 'true' for this test")
        return False
    
    # Run tests
    chrome_success = await test_chrome_git_script()
    edge_success = await test_edge_git_script()
    
    logger.info("=" * 80)
    logger.info("Test Results Summary:")
    logger.info(f"✅ Chrome git-script: {'PASSED' if chrome_success else 'FAILED'}")
    logger.info(f"✅ Edge git-script: {'PASSED' if edge_success else 'FAILED'}")
    
    overall_success = chrome_success and edge_success
    
    if overall_success:
        logger.info("🎉 ALL INTEGRATION TESTS PASSED")
        logger.info("🎯 NEW METHOD (2024+) is fully functional for both browsers")
        logger.info("📋 Git-script automation is working correctly")
    else:
        logger.error("❌ SOME INTEGRATION TESTS FAILED")
        logger.error("🔍 Check individual test results above")
    
    logger.info("=" * 80)
    
    return overall_success

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
