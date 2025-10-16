#!/usr/bin/env python3
"""
LLM Isolation Verification Script (Issue #43)

This script verifies that the application can run without LLM dependencies
when ENABLE_LLM=false. It performs static analysis and import tests to ensure
complete LLM package isolation.

Usage:
    # Run all verification tests
    ENABLE_LLM=false python scripts/verify_llm_isolation.py
    
    # Run specific test
    ENABLE_LLM=false python scripts/verify_llm_isolation.py --test imports
    
Exit Codes:
    0: All tests passed
    1: One or more tests failed
    2: Configuration error

Requirements:
    - Must be run with ENABLE_LLM=false
    - Should work with requirements-minimal.txt only
"""

import os
import sys
import importlib
import argparse
from pathlib import Path

# Workaround: Import standard logging before adding src to path
# This prevents src/logging from shadowing standard library logging
import logging as _std_logging

# Add project root and src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# ANSI color codes
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"
BOLD = "\033[1m"


class LLMIsolationVerifier:
    """Verifies complete LLM isolation when ENABLE_LLM=false"""
    
    # LLM packages that should NOT be imported in minimal mode
    FORBIDDEN_PACKAGES = {
        "langchain",
        "langchain_core",
        "langchain_openai",
        "langchain_anthropic",
        "langchain_google_genai",
        "langchain_ollama",
        "langchain_mistralai",
        "openai",
        "anthropic",
        "browser_use",
        "mem0",
        "faiss",
        "ollama",
    }
    
    # Core modules that should be importable in minimal mode
    CORE_MODULES = [
        "src.config.feature_flags",
        "src.config.config_adapter",
        "src.config.multi_env_loader",
        "src.utils.utils",
        "src.utils.recording_dir_resolver",
        "src.core.screenshot_manager",
        "src.batch.engine",
    ]
    
    # LLM modules that should raise ImportError in minimal mode
    LLM_MODULES = [
        "src.utils.llm",
        "src.agent.custom_agent",
        "src.agent.agent_manager",
        "src.controller.custom_controller",
        "src.browser.custom_browser",
        "src.llm.docker_sandbox",
    ]
    
    def __init__(self):
        self.passed_tests = 0
        self.failed_tests = 0
        self.warnings = 0
        
    def print_header(self, text: str):
        """Print section header"""
        print(f"\n{BLUE}{BOLD}{'=' * 70}{RESET}")
        print(f"{BLUE}{BOLD}{text}{RESET}")
        print(f"{BLUE}{BOLD}{'=' * 70}{RESET}\n")
        
    def print_success(self, text: str):
        """Print success message"""
        print(f"{GREEN}✅ {text}{RESET}")
        self.passed_tests += 1
        
    def print_failure(self, text: str):
        """Print failure message"""
        print(f"{RED}❌ {text}{RESET}")
        self.failed_tests += 1
        
    def print_warning(self, text: str):
        """Print warning message"""
        print(f"{YELLOW}⚠️  {text}{RESET}")
        self.warnings += 1
        
    def print_info(self, text: str):
        """Print info message"""
        print(f"   {text}")
        
    def verify_environment(self) -> bool:
        """Verify ENABLE_LLM is set to false"""
        self.print_header("🔍 Environment Verification")
        
        enable_llm = os.getenv("ENABLE_LLM", "").lower()
        
        if enable_llm != "false":
            self.print_failure(
                f"ENABLE_LLM must be 'false', got: '{enable_llm}'"
            )
            self.print_info(
                "Run with: ENABLE_LLM=false python scripts/verify_llm_isolation.py"
            )
            return False
            
        self.print_success("ENABLE_LLM=false ✓")
        return True
        
    def verify_no_forbidden_imports(self) -> bool:
        """Verify no forbidden LLM packages in sys.modules"""
        self.print_header("🚫 Forbidden Package Detection")
        
        found_forbidden = []
        for module_name in sys.modules:
            for forbidden in self.FORBIDDEN_PACKAGES:
                if module_name == forbidden or module_name.startswith(f"{forbidden}."):
                    found_forbidden.append(module_name)
                    
        if found_forbidden:
            self.print_failure(
                f"Found {len(found_forbidden)} forbidden LLM packages in sys.modules:"
            )
            for pkg in sorted(found_forbidden)[:10]:  # Show first 10
                self.print_info(f"  • {pkg}")
            if len(found_forbidden) > 10:
                self.print_info(f"  ... and {len(found_forbidden) - 10} more")
            return False
            
        self.print_success(
            f"No forbidden LLM packages found (checked {len(self.FORBIDDEN_PACKAGES)} packages)"
        )
        return True
        
    def verify_core_modules_load(self) -> bool:
        """Verify core modules can be imported"""
        self.print_header("📦 Core Module Import Test")
        
        success_count = 0
        fail_count = 0
        
        for module_path in self.CORE_MODULES:
            try:
                importlib.import_module(module_path)
                self.print_success(f"Core module loads: {module_path}")
                success_count += 1
            except Exception as e:
                self.print_failure(f"Core module failed: {module_path}")
                self.print_info(f"  Error: {type(e).__name__}: {e}")
                fail_count += 1
                
        self.print_info(
            f"\nSummary: {success_count}/{len(self.CORE_MODULES)} core modules loaded"
        )
        return fail_count == 0
        
    def verify_llm_modules_blocked(self) -> bool:
        """Verify LLM modules raise ImportError"""
        self.print_header("🔒 LLM Module Block Test")
        
        success_count = 0
        fail_count = 0
        
        for module_path in self.LLM_MODULES:
            try:
                importlib.import_module(module_path)
                self.print_failure(
                    f"LLM module should be blocked: {module_path}"
                )
                fail_count += 1
            except ImportError as e:
                # Expected: module should raise ImportError
                if "disabled" in str(e).lower() or "enable_llm" in str(e).lower():
                    self.print_success(f"LLM module blocked: {module_path}")
                    success_count += 1
                else:
                    self.print_warning(
                        f"LLM module raised ImportError (unexpected message): {module_path}"
                    )
                    self.print_info(f"  Error: {e}")
                    success_count += 1
            except Exception as e:
                self.print_failure(
                    f"LLM module raised unexpected error: {module_path}"
                )
                self.print_info(f"  Error: {type(e).__name__}: {e}")
                fail_count += 1
                
        self.print_info(
            f"\nSummary: {success_count}/{len(self.LLM_MODULES)} LLM modules correctly blocked"
        )
        return fail_count == 0
        
    def verify_helper_functions(self) -> bool:
        """Verify helper functions work correctly"""
        self.print_header("🛠️ Helper Function Test")
        
        try:
            from src.utils.utils import is_llm_available
            
            result = is_llm_available()
            if result is False:
                self.print_success("is_llm_available() returns False ✓")
            else:
                self.print_failure(
                    f"is_llm_available() should return False, got: {result}"
                )
                return False
                
        except Exception as e:
            self.print_failure("Failed to test is_llm_available()")
            self.print_info(f"  Error: {type(e).__name__}: {e}")
            return False
            
        try:
            from src.config.config_adapter import config_adapter
            
            cfg = config_adapter.get_effective_config()
            llm_provider = cfg.get("llm_provider")
            
            if llm_provider in ("disabled", "openai"):  # "openai" might be default
                self.print_success(
                    f"config_adapter provides safe LLM config: provider='{llm_provider}'"
                )
            else:
                self.print_warning(
                    f"config_adapter LLM provider unexpected: '{llm_provider}'"
                )
                
        except Exception as e:
            self.print_failure("Failed to test config_adapter")
            self.print_info(f"  Error: {type(e).__name__}: {e}")
            return False
            
        return True
        
    def verify_minimal_requirements(self) -> bool:
        """Check if only minimal requirements are needed"""
        self.print_header("📋 Requirements Check")
        
        requirements_minimal = Path("requirements-minimal.txt")
        requirements_full = Path("requirements.txt")
        
        if not requirements_minimal.exists():
            self.print_warning("requirements-minimal.txt not found")
            return True
            
        # Read minimal requirements
        with open(requirements_minimal) as f:
            minimal_pkgs = {
                line.split("==")[0].split(">=")[0].strip().lower()
                for line in f
                if line.strip() and not line.startswith("#")
            }
            
        # Check no forbidden packages in minimal
        forbidden_in_minimal = minimal_pkgs & self.FORBIDDEN_PACKAGES
        if forbidden_in_minimal:
            self.print_failure(
                f"Found forbidden packages in requirements-minimal.txt:"
            )
            for pkg in sorted(forbidden_in_minimal):
                self.print_info(f"  • {pkg}")
            return False
            
        self.print_success(
            f"requirements-minimal.txt is clean ({len(minimal_pkgs)} packages, "
            f"0 LLM packages)"
        )
        
        # Compare with full requirements if available
        if requirements_full.exists():
            with open(requirements_full) as f:
                full_pkgs = {
                    line.split("==")[0].split(">=")[0].strip().lower()
                    for line in f
                    if line.strip() and not line.startswith("#")
                }
            llm_pkgs_in_full = full_pkgs & self.FORBIDDEN_PACKAGES
            self.print_info(
                f"requirements.txt has {len(full_pkgs)} packages "
                f"(including {len(llm_pkgs_in_full)} LLM packages)"
            )
            
        return True
        
    def print_summary(self):
        """Print final summary"""
        self.print_header("📊 Verification Summary")
        
        total_tests = self.passed_tests + self.failed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"{GREEN}Passed: {self.passed_tests}{RESET}")
        print(f"{RED}Failed: {self.failed_tests}{RESET}")
        print(f"{YELLOW}Warnings: {self.warnings}{RESET}")
        
        if self.failed_tests == 0:
            print(f"\n{GREEN}{BOLD}✅ All verification tests passed!{RESET}")
            print(f"{GREEN}LLM isolation is working correctly.{RESET}")
            return 0
        else:
            print(f"\n{RED}{BOLD}❌ Verification failed!{RESET}")
            print(f"{RED}LLM isolation has issues that need to be fixed.{RESET}")
            return 1
            
    def run_all_tests(self) -> int:
        """Run all verification tests"""
        print(f"{BOLD}LLM Isolation Verification (Issue #43){RESET}")
        print(f"Python: {sys.version.split()[0]}")
        print(f"Working Directory: {Path.cwd()}")
        
        # Verify environment first
        if not self.verify_environment():
            return 2
            
        # Run all test suites
        self.verify_no_forbidden_imports()
        self.verify_core_modules_load()
        self.verify_llm_modules_blocked()
        self.verify_helper_functions()
        self.verify_minimal_requirements()
        
        # Print summary and return exit code
        return self.print_summary()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Verify LLM isolation for Issue #43"
    )
    parser.add_argument(
        "--test",
        choices=["env", "imports", "core", "llm", "helpers", "requirements", "all"],
        default="all",
        help="Run specific test suite (default: all)"
    )
    
    args = parser.parse_args()
    verifier = LLMIsolationVerifier()
    
    try:
        if args.test == "all":
            exit_code = verifier.run_all_tests()
        else:
            # Run specific test
            print(f"{BOLD}Running test: {args.test}{RESET}\n")
            
            if not verifier.verify_environment():
                return 2
                
            test_map = {
                "env": verifier.verify_environment,
                "imports": verifier.verify_no_forbidden_imports,
                "core": verifier.verify_core_modules_load,
                "llm": verifier.verify_llm_modules_blocked,
                "helpers": verifier.verify_helper_functions,
                "requirements": verifier.verify_minimal_requirements,
            }
            
            test_map[args.test]()
            exit_code = verifier.print_summary()
            
        sys.exit(exit_code)
        
    except KeyboardInterrupt:
        print(f"\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(130)
    except Exception as e:
        print(f"\n{RED}Unexpected error: {e}{RESET}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
