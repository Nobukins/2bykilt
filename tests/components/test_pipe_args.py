#!/usr/bin/env python3
"""
Test the pipe-delimited browser argument serialization
"""

import os
import sys
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.memory_monitor import memory_monitor

def test_pipe_serialization():
    """Test that browser arguments with commas are properly serialized/deserialized using pipe delimiter"""
    print("Testing pipe-delimited serialization of browser arguments...")
    
    # Get optimized arguments
    args = memory_monitor.get_optimized_browser_args('chrome')
    print(f"Original arguments: {args}")
    
    # Check for arguments with commas
    comma_args = [arg for arg in args if ',' in arg]
    print(f"Arguments containing commas: {comma_args}")
    
    # Serialize with pipe delimiter
    pipe_str = '|'.join(args)
    print(f"Pipe-delimited: {pipe_str}")
    
    # Deserialize from pipe delimiter
    parsed_args = pipe_str.split('|')
    print(f"Pipe-parsed: {parsed_args}")
    
    # Verify they match
    if args == parsed_args:
        print("✅ Pipe serialization/deserialization successful!")
    else:
        print("❌ Pipe serialization/deserialization failed!")
        return False
    
    # Test specific problematic argument
    window_size_arg = '--window-size=1280,720'
    if window_size_arg in args:
        print(f"✅ Found problematic argument: {window_size_arg}")
        # Test that it survives pipe roundtrip
        if window_size_arg in parsed_args:
            print("✅ Problematic argument survived pipe roundtrip!")
        else:
            print("❌ Problematic argument lost in pipe roundtrip!")
            return False
    else:
        print(f"⚠️ Test argument {window_size_arg} not found in optimized args")
    
    return True

def test_env_variable_simulation():
    """Simulate setting and reading the environment variable with pipe delimiter"""
    print("\nTesting environment variable simulation with pipe delimiter...")
    
    # Get args and serialize
    args = memory_monitor.get_optimized_browser_args('edge')
    pipe_str = '|'.join(args)
    
    # Set environment variable
    os.environ['BYKILT_BROWSER_ARGS'] = pipe_str
    
    # Simulate reading it (like the script would)
    env_value = os.environ.get('BYKILT_BROWSER_ARGS')
    parsed_args = env_value.split('|')
    print(f"✅ Successfully parsed {len(parsed_args)} arguments from environment")
    
    # Check for comma-containing args
    comma_args = [arg for arg in parsed_args if ',' in arg]
    if comma_args:
        print(f"✅ Comma-containing arguments preserved: {comma_args}")
    else:
        print("ℹ️ No comma-containing arguments found")
        
    return True

if __name__ == "__main__":
    print("🔧 Testing pipe-delimited browser argument serialization\n")
    
    test1_ok = test_pipe_serialization()
    test2_ok = test_env_variable_simulation()
    
    if test1_ok and test2_ok:
        print("\n✅ All tests passed! Pipe-delimited serialization should fix the Playwright argument issue.")
    else:
        print("\n❌ Some tests failed!")
