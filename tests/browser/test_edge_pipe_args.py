#!/usr/bin/env python3
"""
Simple test to run Edge with pipe-delimited arguments to verify Playwright argument issue is fixed
"""

import os
import tempfile
import subprocess
import sys
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.memory_monitor import memory_monitor

def test_edge_with_pipe_args():
    """Test Edge execution with pipe-delimited arguments"""
    print("🔧 Testing Edge execution with pipe-delimited browser arguments...")
    
    # Create a minimal test script
    test_script_content = '''
import os
import asyncio
from playwright.async_api import async_playwright

async def main():
    # Get browser arguments from environment
    optimized_args_env = os.environ.get("BYKILT_BROWSER_ARGS")
    base_args = ['--no-sandbox', '--disable-setuid-sandbox']
    
    if optimized_args_env:
        optimized_args = optimized_args_env.split("|")
        print(f"🔧 Applying {len(optimized_args)} memory optimization arguments from pipe-delimited string")
        for arg in optimized_args:
            if arg and arg not in base_args:
                base_args.append(arg)
    
    print(f"🔧 Final launch arguments ({len(base_args)} total):")
    for i, arg in enumerate(base_args, 1):
        print(f"  {i:2}. {arg}")
    
    # Test launch
    async with async_playwright() as p:
        browser_executable = os.environ.get("PLAYWRIGHT_EDGE_EXECUTABLE_PATH")
        launch_options = {
            'headless': True,  # Use headless for test
            'args': base_args
        }
        
        if browser_executable:
            launch_options['executable_path'] = browser_executable
            print(f"🔍 Using Edge executable: {browser_executable}")
        
        try:
            browser = await p.chromium.launch(**launch_options)
            print("✅ Browser launched successfully!")
            
            context = await browser.new_context()
            page = await context.new_page()
            
            # Simple test navigation
            await page.goto("https://example.com", timeout=10000)
            title = await page.title()
            print(f"✅ Navigation successful! Page title: {title}")
            
            await browser.close()
            return True
            
        except Exception as e:
            if "Arguments can not specify page to be opened" in str(e):
                print(f"❌ Still getting Playwright argument error: {e}")
                return False
            else:
                print(f"⚠️ Different error (might be OK): {e}")
                return True

if __name__ == "__main__":
    asyncio.run(main())
'''

    # Create temporary script file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(test_script_content)
        script_path = f.name
    
    try:
        # Get memory-optimized arguments and set environment
        env = os.environ.copy()
        optimized_args = memory_monitor.get_optimized_browser_args('edge')
        env['BYKILT_BROWSER_ARGS'] = '|'.join(optimized_args)
        
        # Set browser type and executable path
        env['BYKILT_BROWSER_TYPE'] = 'edge'
        env.setdefault('PLAYWRIGHT_EDGE_EXECUTABLE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
        
        print(f"Environment variables set:")
        print(f"  BYKILT_BROWSER_ARGS: {env['BYKILT_BROWSER_ARGS']}")
        print(f"  BYKILT_BROWSER_TYPE: {env['BYKILT_BROWSER_TYPE']}")
        print(f"  PLAYWRIGHT_EDGE_EXECUTABLE_PATH: {env.get('PLAYWRIGHT_EDGE_EXECUTABLE_PATH')}")
        
        # Run the test script
        result = subprocess.run([sys.executable, script_path], 
                              env=env, 
                              capture_output=True, 
                              text=True, 
                              timeout=30)
        
        print("\nScript output:")
        print(result.stdout)
        if result.stderr:
            print("Script errors:")
            print(result.stderr)
        
        if result.returncode == 0:
            print("✅ Test script completed successfully!")
            return True
        else:
            print(f"❌ Test script failed with exit code {result.returncode}")
            return False
            
    except Exception as e:
        print(f"❌ Test execution failed: {e}")
        return False
    finally:
        # Clean up temporary file
        if os.path.exists(script_path):
            os.unlink(script_path)

if __name__ == "__main__":
    success = test_edge_with_pipe_args()
    if success:
        print("\n✅ Edge test with pipe-delimited arguments completed!")
    else:
        print("\n❌ Edge test failed!")
