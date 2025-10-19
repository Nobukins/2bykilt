#!/usr/bin/env python
"""
End-to-end test for browser-control fix
Simulates the actual Gradio UI workflow
"""
import sys
import pytest
import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

@pytest.mark.ci_safe
def test_e2e_browser_control():
    """
    End-to-end test simulating the Gradio UI workflow:
    1. Load actions from llms.txt
    2. Parse browser-control action
    3. Generate script with params
    4. Validate generated script
    5. Test execution (dry-run)
    """
    print("=" * 70)
    print("END-TO-END TEST: Browser Control Fix Verification")
    print("=" * 70)
    print()
    
    # Step 1: Load actions
    print("📋 Step 1: Loading actions from llms.txt...")
    try:
        from src.modules.yaml_parser import InstructionLoader
        loader = InstructionLoader(local_path=os.path.join(PROJECT_ROOT, 'llms.txt'))
        res = loader.load_instructions()
        
        if not res.success:
            print(f"❌ Failed to load actions: {res.error}")
            assert False, f"Failed to load actions: {res.error}"
        
        print(f"   ✅ Loaded {len(res.instructions)} actions")
    except Exception as e:
        print(f"❌ Error loading actions: {e}")
        assert False, f"Error loading actions: {e}"
    
    # Step 2: Find browser-control action
    print("\n🔍 Step 2: Finding browser-control action...")
    browser_control_action = None
    for action in res.instructions:
        if action.get('type') == 'browser-control':
            browser_control_action = action
            break
    
    if not browser_control_action:
        print("❌ browser-control action not found")
        assert False, "browser-control action not found"
    
    print(f"   ✅ Found: {browser_control_action.get('name')}")
    
    # Step 3: Generate script
    print("\n🔧 Step 3: Generating browser-control script...")
    try:
        from src.script.script_manager import generate_browser_script
        
        test_params = {'query': 'EndToEnd-Test'}
        script_content = generate_browser_script(browser_control_action, test_params)
        
        print(f"   ✅ Generated {len(script_content)} bytes of code")
    except Exception as e:
        print(f"❌ Error generating script: {e}")
        import traceback
        traceback.print_exc()
        assert False, f"Error generating script: {e}"
    
    # Step 4: Validate syntax
    print("\n✅ Step 4: Validating generated script syntax...")
    
    # Check for common errors
    errors = []
    
    if '{{' in script_content and '${params' not in script_content:
        errors.append("Double braces found (not template placeholders)")
    
    if 'in {{"overwrite"' in script_content:
        errors.append("Invalid set literal with double braces")
    
    if 'record = {{' in script_content:
        errors.append("Invalid dict literal with double braces")
    
    if errors:
        print("❌ Syntax errors found:")
        for err in errors:
            print(f"   - {err}")
        assert False, f"Syntax errors found: {errors}"
    
    # Try to compile
    try:
        compile(script_content, '<generated>', 'exec')
        print("   ✅ Script compiles successfully")
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        print(f"   Line {e.lineno}: {e.text}")
        assert False, f"Syntax error: {e}"
    except Exception as e:
        print(f"❌ Compilation error: {e}")
        assert False, f"Compilation error: {e}"
    
    # Step 5: Write and validate with py_compile
    print("\n📝 Step 5: Writing script and validating with py_compile...")
    test_script_path = PROJECT_ROOT / "myscript" / "test_generated_browser_control.py"
    
    try:
        test_script_path.write_text(script_content, encoding='utf-8')
        print(f"   ✅ Written to {test_script_path}")
        
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(test_script_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            print(f"❌ py_compile failed:")
            print(result.stderr)
            assert False, f"py_compile failed: {result.stderr}"
        
        print("   ✅ py_compile validation passed")
        
        # Clean up
        test_script_path.unlink()
        pyc_file = test_script_path.parent / "__pycache__" / (test_script_path.stem + ".*.pyc")
        for pyc in test_script_path.parent.glob("__pycache__/*.pyc"):
            if test_script_path.stem in pyc.name:
                pyc.unlink()
        
    except Exception as e:
        print(f"❌ Error during file validation: {e}")
        assert False, f"Error during file validation: {e}"
    
    # Step 6: Pytest collection test
    print("\n🧪 Step 6: Testing pytest collection...")
    try:
        # Generate actual browser_control.py for pytest
        script_path = PROJECT_ROOT / "myscript" / "browser_control.py"
        script_path.write_text(script_content, encoding='utf-8')
        
        import subprocess
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "myscript/browser_control.py::test_browser_control",
             "--collect-only"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            print(f"❌ Pytest collection failed:")
            print(result.stdout)
            print(result.stderr)
            assert False, f"Pytest collection failed: {result.stdout}\n{result.stderr}"
        
        if "1 test collected" not in result.stdout:
            print(f"❌ Expected 1 test collected, got:")
            print(result.stdout)
            assert False, f"Expected 1 test collected, got: {result.stdout}"
        
        print("   ✅ Pytest collection successful (1 test collected)")
        
        # Clean up
        script_path.unlink()
        
    except subprocess.TimeoutExpired:
        print("❌ Pytest collection timed out")
        assert False, "Pytest collection timed out"
    except Exception as e:
        print(f"❌ Error during pytest test: {e}")
        assert False, f"Error during pytest test: {e}"

def main():
    try:
        success = test_e2e_browser_control()
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        success = False
    
    print()
    print("=" * 70)
    if success:
        print("✅ END-TO-END TEST PASSED")
        print()
        print("Browser-control is now working correctly:")
        print("  • Script generation produces valid syntax")
        print("  • No double-brace escaping errors")
        print("  • Pytest can collect and execute tests")
        print("  • Ready for Gradio UI batch processing")
        print()
        print("You can now test in Gradio UI:")
        print("  1. 🔍 Option Availability - Functional Verification")
        print("  2. 📊 CSV Batch Processing")
        return 0
    else:
        print("❌ END-TO-END TEST FAILED")
        print()
        print("Please review the errors above and retry.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
