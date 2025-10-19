#!/usr/bin/env python3

import os
import sys
import subprocess
import tempfile
import shutil
import pytest

@pytest.mark.ci_safe
def test_git_script_chrome():
    """Test that git-script uses Chrome when PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH is set"""
    
    # Set up environment variables
    env = os.environ.copy()
    env['BYKILT_BROWSER_TYPE'] = 'chrome'
    env['DEFAULT_BROWSER'] = 'chrome'
    
    # Find Chrome executable path
    chrome_path = None
    possible_chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        '/usr/bin/google-chrome',
        '/usr/bin/google-chrome-stable'
    ]
    
    for path in possible_chrome_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    
    if not chrome_path:
        print("ERROR: Chrome not found in expected locations")
        return False
    
    env['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = chrome_path
    print(f"Using Chrome executable: {chrome_path}")
    
    # Create a temporary git script that just checks the browser executable
    test_script_content = '''# test_chrome_check.py 
import pytest
from playwright.async_api import async_playwright
import asyncio
import os

@pytest.mark.ci_safe
@pytest.mark.asyncio
async def test_chrome_executable() -> None:
    async with async_playwright() as p:
        # Get the Chrome executable path from environment variable if available
        chrome_executable = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH")
        launch_options = {
            'headless': True,  # Use headless for this test
            'args': ['--no-sandbox', '--disable-setuid-sandbox']
        }
        
        # Add executable_path if Chrome path is provided
        if chrome_executable:
            launch_options['executable_path'] = chrome_executable
            print(f"Using Chrome executable: {chrome_executable}")
        else:
            print("No Chrome executable specified, using default Chromium")
            
        browser = await p.chromium.launch(**launch_options)
        
        # Create a page to get more detailed browser info
        page = await browser.new_page()
        
        # Get browser info
        version = browser.version
        print(f"Browser version: {version}")
        
        # Get user agent to better identify the browser
        user_agent = await page.evaluate("navigator.userAgent")
        print(f"User agent: {user_agent}")
        
        # Check if it's actually Chrome (look for Chrome in user agent)
        is_chrome = "Chrome" in user_agent and "Chromium" not in user_agent
        print(f"Is Chrome: {is_chrome}")
        
        await page.close()
        await browser.close()
        
        # Assert that we're using Chrome
        assert is_chrome, f"Expected Chrome but got version: {version}, user agent: {user_agent}"

if __name__ == "__main__":
    asyncio.run(test_chrome_executable())
'''
    
    # Write the test script to a temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script_content)
        test_script_path = f.name
    
    try:
        # Run the test script
        result = subprocess.run([
            sys.executable, test_script_path
        ], env=env, capture_output=True, text=True, timeout=30)
        
        print("STDOUT:")
        print(result.stdout)
        if result.stderr:
            print("STDERR:")
            print(result.stderr)
        
        success = result.returncode == 0 and "Is Chrome: True" in result.stdout
        if success:
            print("✅ Git-script Chrome test PASSED")
        else:
            print("❌ Git-script Chrome test FAILED")
            
        return success
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        return False
    except Exception as e:
        print(f"❌ Test failed with exception: {e}")
        return False
    finally:
        # Clean up
        try:
            os.unlink(test_script_path)
        except:
            pass

if __name__ == "__main__":
    success = test_git_script_chrome()
    sys.exit(0 if success else 1)
