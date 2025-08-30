#!/usr/bin/env python3
"""
NEW_METHOD Final Verification Test
Tests all automation types with fixes applied
"""
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.script.script_manager import run_script

async def test_new_method_final_verification():
    """Test all automation types with NEW_METHOD fixes"""
    
    print("🧪 NEW_METHOD Final Verification Test")
    print("=" * 50)
    
    test_results = []
    
    # Test 1: script type (fix personal profile issue)
    print("\n1️⃣ Testing 'script' type with NEW_METHOD profile support...")
    script_info_1 = {
        "type": "script",
        "script": "search_script.py",
        "command": "python -m pytest ${script_path} --query ${params.query}",
        "slowmo": 1000
    }
    params_1 = {"query": "NEW_METHOD test"}
    
    try:
        result_1, path_1 = await run_script(
            script_info_1, params_1, 
            headless=False, 
            save_recording_path="./tmp/record_videos",
            browser_type="chrome"
        )
        print(f"   ✅ Script result: {result_1}")
        test_results.append(("script", "✅ SUCCESS", result_1))
    except Exception as e:
        print(f"   ❌ Script error: {e}")
        test_results.append(("script", "❌ FAILED", str(e)))
    
    # Test 2: action_runner_template type (fix missing script issue)
    print("\n2️⃣ Testing 'action_runner_template' type with NEW_METHOD...")
    script_info_2 = {
        "type": "action_runner_template",
        "action_script": "nogtips_search",
        "command": "python ./tmp/myscript/unified_action_launcher.py --action ${action_script} --query ${params.query|LLMs.txt} --slowmo 2500 --countdown 1",
        "slowmo": 2500
    }
    params_2 = {"query": "NEW_METHOD action_runner"}
    
    try:
        result_2, path_2 = await run_script(
            script_info_2, params_2, 
            headless=False, 
            save_recording_path="./tmp/record_videos",
            browser_type="chrome"
        )
        print(f"   ✅ Action runner result: {result_2}")
        test_results.append(("action_runner_template", "✅ SUCCESS", result_2))
    except Exception as e:
        print(f"   ❌ Action runner error: {e}")
        test_results.append(("action_runner_template", "❌ FAILED", str(e)))
    
    # Test 3: browser-control type (should already work)
    print("\n3️⃣ Testing 'browser-control' type with NEW_METHOD...")
    script_info_3 = {
        "type": "browser-control",
        "flow": [
            {"action": "navigate", "url": "https://www.google.com", "wait_for": "#APjFqb"},
            {"action": "fill", "selector": "#APjFqb", "value": "${params.query}"},
            {"action": "keyboard_press", "selector": "Enter"}
        ],
        "slowmo": 1000
    }
    params_3 = {"query": "NEW_METHOD browser-control"}
    
    try:
        result_3, path_3 = await run_script(
            script_info_3, params_3, 
            headless=False, 
            save_recording_path="./tmp/record_videos",
            browser_type="chrome"
        )
        print(f"   ✅ Browser-control result: {result_3}")
        test_results.append(("browser-control", "✅ SUCCESS", result_3))
    except Exception as e:
        print(f"   ❌ Browser-control error: {e}")
        test_results.append(("browser-control", "❌ FAILED", str(e)))
    
    # Test 4: git-script type (fix actions/ directory issue)
    print("\n4️⃣ Testing 'git-script' type with NEW_METHOD actions/ fallback...")
    script_info_4 = {
        "type": "git-script",
        "git": "https://github.com/Nobukins/sample-tests.git",
        "script_path": "search_script.py",
        "version": "main",
        "command": "python -m pytest ${script_path} --query ${params.query}",
        "slowmo": 1000
    }
    params_4 = {"query": "NEW_METHOD git-script"}
    
    try:
        result_4, path_4 = await run_script(
            script_info_4, params_4, 
            headless=False, 
            save_recording_path="./tmp/record_videos",
            browser_type="chrome"
        )
        print(f"   ✅ Git-script result: {result_4}")
        test_results.append(("git-script", "✅ SUCCESS", result_4))
    except Exception as e:
        print(f"   ❌ Git-script error: {e}")
        test_results.append(("git-script", "❌ FAILED", str(e)))
    
    # Final summary
    print("\n" + "=" * 50)
    print("🏁 NEW_METHOD Final Verification Results:")
    print("=" * 50)
    
    for test_type, status, message in test_results:
        print(f"  {test_type:20} | {status:12} | {message[:60]}...")
    
    success_count = sum(1 for _, status, _ in test_results if "SUCCESS" in status)
    total_count = len(test_results)
    
    print(f"\n📊 Summary: {success_count}/{total_count} tests passed")
    
    if success_count == total_count:
        print("🎉 ALL NEW_METHOD TESTS PASSED! System is ready for production.")
    else:
        print("⚠️  Some tests failed. Review the issues above.")
    
    return test_results

if __name__ == "__main__":
    asyncio.run(test_new_method_final_verification())
