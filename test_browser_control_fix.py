#!/usr/bin/env python
"""
Test script to verify browser-control generation fix
"""
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent

def test_script_generation():
    """Test that browser_control.py is generated correctly"""
    print("🧪 Test 1: Script generation")
    
    from src.script.script_manager import generate_browser_script
    
    script_info = {
        'flow': [
            {'action': 'command', 'url': 'https://example.com', 'wait_until': 'domcontentloaded'},
        ]
    }
    params = {'query': 'test'}
    
    content = generate_browser_script(script_info, params)
    
    # Check for syntax errors in generated content
    assert '{{' not in content or '${params' in content, "Double braces should only appear in template placeholders"
    
    # Check critical lines
    assert 'return "w" if raw in {"overwrite", "write", "w"} else "a"' in content, "Set syntax should be correct"
    assert 'record = {' in content, "Dict syntax should be correct"
    
    print("  ✅ Script generation produces correct syntax")
    return True

def test_syntax_validation():
    """Test that generated script has valid Python syntax"""
    print("🧪 Test 2: Syntax validation")
    
    script_path = PROJECT_ROOT / "myscript" / "browser_control.py"
    
    if not script_path.exists():
        print("  ⚠️ browser_control.py not found, generating...")
        from src.script.script_manager import generate_browser_script
        script_info = {'flow': [{'action': 'command', 'url': 'https://example.com'}]}
        params = {'query': 'test'}
        content = generate_browser_script(script_info, params)
        script_path.write_text(content, encoding='utf-8')
    
    # Run py_compile
    result = subprocess.run(
        [sys.executable, "-m", "py_compile", str(script_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ Syntax error:\n{result.stderr}")
        return False
    
    print("  ✅ Syntax validation passed")
    return True

def test_pytest_collection():
    """Test that pytest can collect the test"""
    print("🧪 Test 3: Pytest collection")
    
    result = subprocess.run(
        [sys.executable, "-m", "pytest", 
         "myscript/browser_control.py::test_browser_control", 
         "--collect-only"],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"  ❌ Pytest collection failed:\n{result.stdout}\n{result.stderr}")
        return False
    
    if "1 test collected" not in result.stdout:
        print(f"  ❌ Expected 1 test collected, got:\n{result.stdout}")
        return False
    
    print("  ✅ Pytest collection successful")
    return True

def main():
    print("=" * 60)
    print("Browser Control Fix Verification")
    print("=" * 60)
    
    tests = [
        test_script_generation,
        test_syntax_validation,
        test_pytest_collection,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
            results.append(False)
        print()
    
    print("=" * 60)
    print(f"Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("✅ All tests passed! Browser control fix verified.")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
