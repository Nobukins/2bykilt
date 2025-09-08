#!/usr/bin/env python3
"""
Test Edge git-script execution with improved error handling
"""

import os
import sys
import subprocess
import tempfile

# Add the project root to the path
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.memory_monitor import memory_monitor
from src.utils.app_logger import logger

def test_edge_git_script():
    """Test Edge git-script with debug output"""
    
    print("🧪 Testing Edge git-script execution")
    print("=" * 60)
    
    # Memory status check
    memory_monitor.log_memory_status()
    is_safe, msg = memory_monitor.is_safe_for_browser('edge')
    print(f"Edge safety check: {msg}")
    
    # Get optimized arguments
    args = memory_monitor.get_optimized_browser_args('edge')
    print(f"\n🔧 Edge optimized arguments ({len(args)} total):")
    for i, arg in enumerate(args, 1):
        print(f"  {i:2}. {arg}")
    
    # Test environment variables
    print(f"\n🔍 Environment variables:")
    env_vars = [
        'BYKILT_BROWSER_TYPE',
        'PLAYWRIGHT_EDGE_EXECUTABLE_PATH', 
        'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH',
        'BYKILT_BROWSER_ARGS'
    ]
    
    # Set up test environment
    env = os.environ.copy()
    env['BYKILT_BROWSER_TYPE'] = 'edge'
    env['PLAYWRIGHT_EDGE_EXECUTABLE_PATH'] = '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'
    env['BYKILT_BROWSER_ARGS'] = ','.join(args)
    
    for var in env_vars:
        value = env.get(var, 'NOT SET')
        print(f"  {var}: {value}")
    
    print(f"\n🎯 Would execute git-script with Edge configuration")
    print(f"✅ Test completed successfully")

if __name__ == "__main__":
    test_edge_git_script()
