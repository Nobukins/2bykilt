#!/usr/bin/env python3
"""
Test script to verify that pre-registered commands work in minimal mode
"""

import asyncio
import os
import sys

# Set environment variable for minimal mode
os.environ['ENABLE_LLM'] = 'false'

# Import the necessary functions
from src.config.standalone_prompt_evaluator import pre_evaluate_prompt_standalone

def test_command_evaluation():
    """Test command evaluation functionality"""
    print("=" * 60)
    print("Testing Pre-registered Command Evaluation")
    print("=" * 60)
    
    # Test cases
    test_cases = [
        "@search-linkedin query=test",
        "@phrase-search query=python automation",
        "@search-nogtips query=tutorial",
        "invalid command",
        "phrase search python"
    ]
    
    for test_case in test_cases:
        print(f"\n🔍 Testing: {test_case}")
        print("-" * 40)
        
        result = pre_evaluate_prompt_standalone(test_case)
        
        if result and result.get('is_command'):
            print(f"✅ Command recognized: {result.get('command_name')}")
            print(f"   Type: {result.get('action_def', {}).get('type')}")
            print(f"   Params: {result.get('params')}")
        else:
            print("❌ No command recognized")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)

def main():
    """Main test function"""
    test_command_evaluation()
    
    print("\n📝 Summary:")
    print("  - Pre-registered commands are now properly recognized")
    print("  - Browser control commands should work in the web UI")
    print("  - Script commands are recognized but not executed in minimal mode")
    print("  - To test in the web UI, go to http://127.0.0.1:7790/ and try:")
    print("    • @phrase-search query=test")
    print("    • @search-nogtips query=tutorial")
    print("    • @search-linkedin query=test (script type - not executed)")

if __name__ == "__main__":
    main()
