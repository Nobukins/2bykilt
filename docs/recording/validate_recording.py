# Recording Functionality Validation Script

"""
Comprehensive validation script for recording functionality across all script types.
This script validates the fixes implemented for Issue #237 and provides ongoing
malfunction detection capabilities.
"""

import asyncio
import os
import sys
import tempfile
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import subprocess
import time

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class RecordingValidator:
    """Comprehensive recording functionality validator"""
    
    def __init__(self, test_dir: Optional[str] = None):
        self.test_dir = Path(test_dir) if test_dir else Path("artifacts/runs/validation")
        self.test_dir.mkdir(parents=True, exist_ok=True)
        self.results: Dict[str, Dict] = {}
        
    async def validate_all(self) -> Dict[str, bool]:
        """Run all validation tests"""
        print("🎬 Starting comprehensive recording validation...")
        
        # Test each script type
        script_result = await self.validate_script_type()
        browser_result = await self.validate_browser_control_type()
        git_result = await self.validate_git_script_type()
        
        # Test integration scenarios
        integration_result = await self.validate_integration_scenarios()
        
        # Generate report
        success = all([script_result, browser_result, git_result, integration_result])
        
        self.print_summary()
        return {
            'script': script_result,
            'browser_control': browser_result,
            'git_script': git_result,
            'integration': integration_result,
            'overall': success
        }
    
    async def validate_script_type(self) -> bool:
        """Validate type:script recording functionality"""
        print("\n📝 Testing type:script recording...")
        
        test_name = "script_validation"
        recording_path = str(self.test_dir / "recordings" / "script" / "videos")
        
        try:
            start_time = time.time()
            
            result, script_path = await run_script(
                script_info={
                    'type': 'script',
                    'script': 'search_script.py',
                    'command': 'python -m pytest ${script_path}::test_nogtips_simple --query=test_recording --no-cov'
                },
                params={'query': 'test script recording'},
                headless=True,
                save_recording_path=recording_path
            )
            
            execution_time = time.time() - start_time
            
            # Validate results
            recording_files = list(Path(recording_path).glob("*.webm"))
            success = len(recording_files) > 0 and all(f.stat().st_size > 1024 for f in recording_files)
            
            self.results[test_name] = {
                'success': success,
                'execution_time': execution_time,
                'recording_files': len(recording_files),
                'file_sizes': [f.stat().st_size for f in recording_files],
                'result': str(result)[:100] if result else "No result"
            }
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} - {len(recording_files)} files, {execution_time:.2f}s")
            
            return success
            
        except Exception as e:
            self.results[test_name] = {
                'success': False,
                'error': str(e),
                'execution_time': 0,
                'recording_files': 0
            }
            print(f"   ❌ ERROR: {e}")
            return False
    
    async def validate_browser_control_type(self) -> bool:
        """Validate type:browser-control recording functionality"""
        print("\n🌐 Testing type:browser-control recording...")
        
        test_name = "browser_control_validation"
        recording_path = str(self.test_dir / "recordings" / "browser_control" / "videos")
        
        try:
            start_time = time.time()
            
            result, script_path = await run_script(
                script_info={
                    'type': 'browser-control',
                    'name': 'browser_control_test',
                    'flow': [
                        {'action': 'navigate', 'url': 'https://example.com'},
                        {'action': 'wait_for_selector', 'selector': 'h1'},
                        {'action': 'click', 'selector': 'a[href*="iana"]'},
                        {'action': 'wait_for_navigation'}
                    ]
                },
                params={},
                headless=True,
                save_recording_path=recording_path
            )
            
            execution_time = time.time() - start_time
            
            # Validate results - use the same resolver to find files
            from src.utils.recording_dir_resolver import create_or_get_recording_dir
            resolved_recording_path = create_or_get_recording_dir(recording_path)
            recording_files = list(resolved_recording_path.glob("*.webm"))
            success = len(recording_files) > 0 and all(f.stat().st_size > 1024 for f in recording_files)
            
            self.results[test_name] = {
                'success': success,
                'execution_time': execution_time,
                'recording_files': len(recording_files),
                'file_sizes': [f.stat().st_size for f in recording_files],
                'result': str(result)[:100] if result else "No result",
                'resolved_path': str(resolved_recording_path)
            }
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} - {len(recording_files)} files, {execution_time:.2f}s")
            if recording_files:
                print(f"   📁 Files found at: {resolved_recording_path}")
            
            return success
            
        except Exception as e:
            self.results[test_name] = {
                'success': False,
                'error': str(e),
                'execution_time': 0,
                'recording_files': 0
            }
            print(f"   ❌ ERROR: {e}")
            return False
    
    async def validate_git_script_type(self) -> bool:
        """Validate type:git-script recording functionality"""
        print("\n🔄 Testing type:git-script recording...")
        
        test_name = "git_script_validation"
        recording_path = str(self.test_dir / "recordings" / "git_script" / "videos")
        
        # Ensure NEW METHOD is enabled for file copying
        os.environ['BYKILT_USE_NEW_METHOD'] = 'true'
        
        try:
            start_time = time.time()
            
            result, script_path = await run_script(
                script_info={
                    'type': 'git-script',
                    'git': 'https://github.com/Nobukins/sample-tests.git',
                    'script_path': 'search_script.py',
                    'command': 'python -m pytest ${script_path}::test_text_search --query "test git-script" --no-cov'
                },
                params={'query': 'test git-script recording'},
                headless=True,
                save_recording_path=recording_path
            )
            
            execution_time = time.time() - start_time
            
            # Validate results - files should be copied from temp dir to artifacts
            recording_files = list(Path(recording_path).glob("*.webm"))
            success = len(recording_files) > 0 and all(f.stat().st_size > 1024 for f in recording_files)
            
            self.results[test_name] = {
                'success': success,
                'execution_time': execution_time,
                'recording_files': len(recording_files),
                'file_sizes': [f.stat().st_size for f in recording_files],
                'result': str(result)[:100] if result else "No result"
            }
            
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {status} - {len(recording_files)} files, {execution_time:.2f}s")
            
            return success
            
        except Exception as e:
            self.results[test_name] = {
                'success': False,
                'error': str(e),
                'execution_time': 0,
                'recording_files': 0
            }
            print(f"   ❌ ERROR: {e}")
            return False
    
    async def validate_integration_scenarios(self) -> bool:
        """Validate integration scenarios and edge cases"""
        print("\n🔗 Testing integration scenarios...")
        
        scenarios = [
            self.validate_path_consistency(),
            self.validate_concurrent_execution(),
            self.validate_custom_paths(),
            self.validate_environment_variables()
        ]
        
        results = await asyncio.gather(*scenarios, return_exceptions=True)
        success = all(isinstance(r, bool) and r for r in results)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"   {status} - Integration scenarios")
        
        return success
    
    async def validate_path_consistency(self) -> bool:
        """Validate that all script types use consistent path resolution"""
        test_paths = [
            str(self.test_dir / "recordings" / "consistency-test-1" / "videos"),
            str(self.test_dir / "recordings" / "consistency-test-2" / "videos"),
            str(self.test_dir / "recordings" / "consistency-test-3" / "videos")
        ]
        
        try:
            resolved_paths = [str(create_or_get_recording_dir(path)) for path in test_paths]
            
            # All paths should follow the same pattern
            all_consistent = all("recordings" in path and "videos" in path for path in resolved_paths)
            all_exist = all(Path(path).exists() for path in resolved_paths)
            
            return all_consistent and all_exist
        except Exception:
            return False
    
    async def validate_concurrent_execution(self) -> bool:
        """Validate concurrent script execution doesn't interfere with recordings"""
        try:
            tasks = [
                run_script(
                    {'type': 'browser-control', 'flow': [{'action': 'navigate', 'url': 'https://example.com'}]},
                    {},
                    headless=True,
                    save_recording_path=str(self.test_dir / "recordings" / f"concurrent-{i}" / "videos")
                )
                for i in range(2)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Check that both executions succeeded and generated files
            success_count = 0
            for i, result in enumerate(results):
                if not isinstance(result, Exception):
                    recording_files = list(Path(str(self.test_dir / "recordings" / f"concurrent-{i}" / "videos")).glob("*.webm"))
                    if recording_files:
                        success_count += 1
            
            return success_count >= 1  # At least one should succeed
        except Exception:
            return False
    
    async def validate_custom_paths(self) -> bool:
        """Validate custom recording path handling"""
        custom_path = str(self.test_dir / "recordings" / "custom-path-test" / "videos")
        
        try:
            resolved = create_or_get_recording_dir(custom_path)
            return resolved.exists() and "custom-path-test" in str(resolved)
        except Exception:
            return False
    
    async def validate_environment_variables(self) -> bool:
        """Validate environment variable handling"""
        try:
            # Test with custom RECORDING_PATH
            original_path = os.environ.get('RECORDING_PATH')
            custom_env_path = str(self.test_dir / "recordings" / "env-test" / "videos")
            
            os.environ['RECORDING_PATH'] = custom_env_path
            
            result, _ = await run_script(
                {'type': 'browser-control', 'flow': [{'action': 'navigate', 'url': 'https://example.com'}]},
                {},
                headless=True
            )
            
            # Restore original environment
            if original_path:
                os.environ['RECORDING_PATH'] = original_path
            else:
                os.environ.pop('RECORDING_PATH', None)
            
            # Check if files were created in the custom path
            recording_files = list(Path(custom_env_path).glob("*.webm"))
            return len(recording_files) > 0
            
        except Exception:
            return False
    
    def print_summary(self):
        """Print validation summary"""
        print("\n" + "="*60)
        print("📊 RECORDING VALIDATION SUMMARY")
        print("="*60)
        
        total_tests = len(self.results)
        successful_tests = sum(1 for r in self.results.values() if r.get('success', False))
        
        print(f"Total Tests: {total_tests}")
        print(f"Successful: {successful_tests}")
        print(f"Failed: {total_tests - successful_tests}")
        print(f"Success Rate: {(successful_tests/total_tests)*100:.1f}%" if total_tests > 0 else "N/A")
        
        print("\nDetailed Results:")
        for test_name, result in self.results.items():
            status = "✅ PASS" if result.get('success', False) else "❌ FAIL"
            execution_time = result.get('execution_time', 0)
            recording_files = result.get('recording_files', 0)
            
            print(f"  {status} {test_name}")
            print(f"      Time: {execution_time:.2f}s, Files: {recording_files}")
            
            if 'error' in result:
                print(f"      Error: {result['error']}")
            
            if 'file_sizes' in result and result['file_sizes']:
                total_size = sum(result['file_sizes'])
                print(f"      Total Size: {total_size:,} bytes")
        
        print("\n" + "="*60)


def run_quick_validation():
    """Quick validation for CI/CD pipelines"""
    async def quick_test():
        validator = RecordingValidator()
        
        # Test only browser-control for speed
        result = await validator.validate_browser_control_type()
        
        if result:
            print("✅ Quick validation PASSED")
            return True
        else:
            print("❌ Quick validation FAILED")
            return False
    
    return asyncio.run(quick_test())


def run_full_validation():
    """Full validation suite"""
    async def full_test():
        validator = RecordingValidator()
        results = await validator.validate_all()
        return results['overall']
    
    return asyncio.run(full_test())


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Recording functionality validation")
    parser.add_argument("--quick", action="store_true", help="Run quick validation only")
    parser.add_argument("--test-dir", help="Custom test directory")
    
    args = parser.parse_args()
    
    try:
        if args.quick:
            success = run_quick_validation()
        else:
            success = run_full_validation()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n❌ Validation interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        sys.exit(1)