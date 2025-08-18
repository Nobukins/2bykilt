#!/usr/bin/env python3
"""
Test the new JSON-based browser argument serialization
"""

import json
import os
import sys
sys.path.append('/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.memory_monitor import memory_monitor

def test_json_serialization():
    """Test that browser arguments with commas are properly serialized/deserialized"""
    print("Testing JSON serialization of browser arguments...")
    
    # Get optimized arguments
    args = memory_monitor.get_optimized_browser_args('chrome')
    print(f"Original arguments: {args}")
    
    # Check for arguments with commas
    comma_args = [arg for arg in args if ',' in arg]
    print(f"Arguments containing commas: {comma_args}")
    
    # Serialize to JSON
    json_str = json.dumps(args)
    print(f"JSON serialized: {json_str}")
    
    # Deserialize from JSON
    parsed_args = json.loads(json_str)
    print(f"JSON deserialized: {parsed_args}")
    
    # Verify they match
    if args == parsed_args:
        print("✅ JSON serialization/deserialization successful!")
    else:
        print("❌ JSON serialization/deserialization failed!")
        return False
    
    # Test what would happen with comma-split (the old way)
    comma_split = json_str.split(',')
    print(f"What comma-split would produce: {comma_split[:5]}... (showing first 5)")
    
    # Test specific problematic argument
    window_size_arg = '--window-size=1280,720'
    if window_size_arg in args:
        print(f"✅ Found problematic argument: {window_size_arg}")
        # Test that it survives JSON roundtrip
        if window_size_arg in parsed_args:
            print("✅ Problematic argument survived JSON roundtrip!")
        else:
            print("❌ Problematic argument lost in JSON roundtrip!")
            return False
    else:
        print(f"⚠️ Test argument {window_size_arg} not found in optimized args")
    
    return True

def test_env_variable_simulation():
    """Simulate setting and reading the environment variable"""
    print("\nTesting environment variable simulation...")
    
    # Get args and serialize
    args = memory_monitor.get_optimized_browser_args('edge')
    json_str = json.dumps(args)
    
    # Set environment variable
    os.environ['BYKILT_BROWSER_ARGS'] = json_str
    
    # Simulate reading it (like the script would)
    env_value = os.environ.get('BYKILT_BROWSER_ARGS')
    try:
        parsed_args = json.loads(env_value)
        print(f"✅ Successfully parsed {len(parsed_args)} arguments from environment")
        
        # Check for comma-containing args
        comma_args = [arg for arg in parsed_args if ',' in arg]
        if comma_args:
            print(f"✅ Comma-containing arguments preserved: {comma_args}")
        else:
            print("ℹ️ No comma-containing arguments found")
            
        return True
    except json.JSONDecodeError as e:
        print(f"❌ Failed to parse arguments from environment: {e}")
        return False

if __name__ == "__main__":
    print("🔧 Testing JSON-based browser argument serialization\n")
    
    test1_ok = test_json_serialization()
    test2_ok = test_env_variable_simulation()
    
    if test1_ok and test2_ok:
        print("\n✅ All tests passed! JSON serialization should fix the Playwright argument issue.")
    else:
        print("\n❌ Some tests failed!")
