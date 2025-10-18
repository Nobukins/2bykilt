#!/usr/bin/env python3
"""
Simplified Production Validation Script

Usage:
    cd /path/to/2bykilt
    python3 scripts/validate_sandbox_simple.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path


def run_test(name: str, cmd: list) -> bool:
    """Run a test command"""
    print(f"\n{'='*60}")
    print(f"Test: {name}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print(f"✅ {name}: PASSED")
            if result.stdout:
                print(f"Output: {result.stdout[:200]}")
            return True
        else:
            print(f"❌ {name}: FAILED (exit code {result.returncode})")
            if result.stderr:
                print(f"Error: {result.stderr[:200]}")
            return False
    except Exception as e:
        print(f"⚠️  {name}: ERROR - {e}")
        return False


def main():
    print(f"\n{'#'*60}")
    print(f"# Production Validation - Simplified")
    print(f"{'#'*60}\n")
    
    results = []
    
    # Test 1: All security tests
    results.append(run_test(
        "All Security Tests",
        ["python", "-m", "pytest", "tests/security/", "-q", "--no-cov", 
         "-k", "not git_script_sandbox_integration"]
    ))
    
    # Test 2: Phase 2 tests specifically
    results.append(run_test(
        "Phase 2 Features",
        ["python", "-m", "pytest", "tests/security/test_phase2_features.py", "-v", "--no-cov"]
    ))
    
    # Test 3: Sandbox manager tests
    results.append(run_test(
        "Sandbox Manager",
        ["python", "-m", "pytest", "tests/security/test_sandbox_manager.py", "-v", "--no-cov"]
    ))
    
    # Test 4: Integration tests
    results.append(run_test(
        "Integration Tests",
        ["python", "-m", "pytest", "tests/security/test_sandbox_integration_simple.py", 
         "-v", "--no-cov"]
    ))
    
    # Summary
    print(f"\n{'='*60}")
    print("VALIDATION SUMMARY")
    print('='*60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"Total: {total} test suites")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {passed/total*100:.1f}%")
    print('='*60)
    
    if passed == total:
        print("\n✅ All validation tests passed!")
        print("Production deployment recommended.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test suite(s) failed")
        print("Review failures before production deployment.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
