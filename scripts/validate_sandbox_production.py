#!/usr/bin/env python3
"""
Production Validation Script for Sandbox Implementation

This script validates the sandbox implementation in a production-like environment.
It performs comprehensive tests covering:
- Basic execution
- Resource limits
- Timeout handling
- Access control
- Monitoring
- Audit logging

Usage:
    python scripts/validate_sandbox_production.py [--mode {warn|enforce}] [--verbose]
"""

import argparse
import json
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

from security.sandbox_manager import SandboxManager, SandboxConfig
from security.filesystem_access_control import FileSystemAccessControl, FileSystemPolicy
from security.network_access_control import NetworkAccessControl, NetworkPolicy
from security.runtime_monitor import SecurityMonitor, get_security_monitor
from security.audit_logger import AuditLogger, get_audit_logger


class ProductionValidator:
    """Validates sandbox in production-like scenarios"""
    
    def __init__(self, mode: str = "enforce", verbose: bool = False):
        self.mode = mode
        self.verbose = verbose
        self.results: List[Tuple[str, bool, str]] = []
        
    def log(self, message: str):
        """Log message if verbose"""
        if self.verbose:
            print(f"[INFO] {message}")
            
    def test(self, name: str, func):
        """Run a test and record result"""
        print(f"\n{'='*60}")
        print(f"Test: {name}")
        print('='*60)
        
        try:
            func()
            self.results.append((name, True, "PASSED"))
            print(f"✅ {name}: PASSED")
            return True
        except AssertionError as e:
            self.results.append((name, False, str(e)))
            print(f"❌ {name}: FAILED - {e}")
            return False
        except Exception as e:
            self.results.append((name, False, f"ERROR: {e}"))
            print(f"⚠️  {name}: ERROR - {e}")
            return False
    
    def test_basic_execution(self):
        """Test basic command execution in sandbox"""
        self.log("Testing basic execution...")
        
        config = SandboxConfig(
            enabled=True,
            mode=self.mode,
            timeout_seconds=10
        )
        
        with tempfile.TemporaryDirectory() as workspace:
            manager = SandboxManager(config, workspace)
            result = manager.execute(["echo", "Hello Production"])
            
            assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
            assert "Hello Production" in result.stdout, "Expected output not found"
            self.log(f"Output: {result.stdout}")
    
    def test_resource_limits(self):
        """Test resource limit enforcement"""
        self.log("Testing resource limits...")
        
        config = SandboxConfig(
            enabled=True,
            mode="enforce",  # Always enforce for this test
            timeout_seconds=5,
            cpu_time_limit=2,
            memory_limit_mb=100
        )
        
        with tempfile.TemporaryDirectory() as workspace:
            manager = SandboxManager(config, workspace)
            
            # CPU intensive task (should be limited)
            result = manager.execute([
                "python", "-c",
                "import time; start=time.time(); x=0\nwhile time.time()-start<10: x+=1"
            ])
            
            # Should be killed by CPU limit (exit code != 0)
            self.log(f"CPU limit test: exit_code={result.exit_code}, killed={result.killed}")
            assert result.exit_code != 0 or result.killed, "CPU limit not enforced"
    
    def test_timeout_enforcement(self):
        """Test timeout enforcement"""
        self.log("Testing timeout...")
        
        config = SandboxConfig(
            enabled=True,
            mode="enforce",
            timeout_seconds=2
        )
        
        with tempfile.TemporaryDirectory() as workspace:
            manager = SandboxManager(config, workspace)
            
            start_time = time.time()
            result = manager.execute(["sleep", "10"])
            elapsed = time.time() - start_time
            
            self.log(f"Timeout test: elapsed={elapsed:.2f}s, killed={result.killed}")
            assert result.killed, "Process not killed by timeout"
            assert elapsed < 5, f"Timeout took too long: {elapsed}s"
    
    def test_filesystem_access_control(self):
        """Test filesystem access control"""
        self.log("Testing filesystem access control...")
        
        with tempfile.TemporaryDirectory() as workspace:
            policy = FileSystemPolicy(
                workspace_root=workspace,
                read_only=False,
                allowed_paths=[workspace],
                denied_paths=[]
            )
            
            controller = FileSystemAccessControl(policy)
            
            # Test workspace access (should be allowed)
            workspace_file = Path(workspace) / "test.txt"
            from security.filesystem_access_control import AccessMode
            assert controller.check_access(str(workspace_file), AccessMode.WRITE), \
                "Workspace write access denied"
            
            # Test path traversal (should be blocked)
            traversal_path = Path(workspace) / ".." / "etc" / "passwd"
            assert not controller.check_access(str(traversal_path), AccessMode.READ), \
                "Path traversal not blocked"
            
            # Test sensitive path (should be blocked)
            assert not controller.check_access("/etc/passwd", AccessMode.READ), \
                "Sensitive path not blocked"
            
            self.log("Filesystem access control working correctly")
    
    def test_network_access_control(self):
        """Test network access control"""
        self.log("Testing network access control...")
        
        policy = NetworkPolicy(
            default_allow=True,
            allowed_hosts=["api.github.com", "*.openai.com"],
            denied_hosts=[]
        )
        
        controller = NetworkAccessControl(policy)
        
        # Test allowed host
        assert controller.check_host_access("api.github.com"), \
            "Allowed host blocked"
        
        # Test wildcard match
        assert controller.check_host_access("api.openai.com"), \
            "Wildcard match failed"
        
        # Test metadata service (should be blocked)
        assert not controller.check_host_access("169.254.169.254"), \
            "Metadata service not blocked"
        
        # Test localhost (should be blocked)
        assert not controller.check_host_access("localhost"), \
            "Localhost not blocked"
        
        # Test private IP (should be blocked)
        assert not controller.check_host_access("192.168.1.1"), \
            "Private IP not blocked"
        
        self.log("Network access control working correctly")
    
    def test_security_monitoring(self):
        """Test security event monitoring"""
        self.log("Testing security monitoring...")
        
        monitor = get_security_monitor()
        
        # Record test events
        from security.runtime_monitor import EventType, AlertSeverity
        
        initial_count = len(monitor.get_all_events())
        
        monitor.record_event(
            EventType.PROCESS_KILLED,
            AlertSeverity.WARNING,
            {"reason": "CPU limit exceeded", "test": "production_validation"}
        )
        
        monitor.record_event(
            EventType.TIMEOUT,
            AlertSeverity.ERROR,
            {"duration": 30, "test": "production_validation"}
        )
        
        # Check events recorded
        events = monitor.get_all_events()
        assert len(events) > initial_count, "Events not recorded"
        
        # Check statistics
        stats = monitor.get_statistics()
        assert stats['total_events'] > 0, "Statistics not updated"
        
        self.log(f"Recorded {len(events)} total events")
        self.log(f"Statistics: {stats}")
    
    def test_audit_logging(self):
        """Test audit logging"""
        self.log("Testing audit logging...")
        
        logger = get_audit_logger()
        
        # Clear any existing entries for clean test
        initial_entries = logger.read_recent_entries(limit=100)
        initial_count = len(initial_entries)
        
        # Log sandbox execution
        logger.log_sandbox_execution(
            command=["echo", "test"],
            workspace="/tmp/test",
            exit_code=0,
            execution_time=0.5,
            resource_usage={"cpu_time": 0.1, "memory_mb": 10}
        )
        
        # Log file access
        logger.log_file_access(
            path="/tmp/test/file.txt",
            operation="write",
            allowed=True
        )
        
        # Log network access
        logger.log_network_access(
            host="api.github.com",
            port=443,
            protocol="https",
            allowed=True
        )
        
        # Verify entries
        recent = logger.read_recent_entries(limit=10)
        assert len(recent) > initial_count, "Audit entries not recorded"
        
        # Check statistics
        stats = logger.get_statistics()
        assert stats['total_entries'] > 0, "Audit statistics not updated"
        
        self.log(f"Recorded {len(recent)} audit entries")
        self.log(f"Audit statistics: {stats}")
    
    def test_integration_scenario(self):
        """Test realistic integration scenario"""
        self.log("Testing integration scenario...")
        
        # Simulate a git-script execution with all security features
        config = SandboxConfig(
            enabled=True,
            mode=self.mode,
            timeout_seconds=10,
            cpu_time_limit=5,
            memory_limit_mb=256
        )
        
        with tempfile.TemporaryDirectory() as workspace:
            # Create test script
            script_path = Path(workspace) / "test_script.sh"
            script_path.write_text("#!/bin/bash\necho 'Integration test'\ndate\n")
            script_path.chmod(0o755)
            
            # Execute with monitoring
            monitor = get_security_monitor()
            logger = get_audit_logger()
            
            manager = SandboxManager(config, workspace)
            result = manager.execute(["bash", str(script_path)])
            
            assert result.exit_code == 0, f"Script failed: {result.stderr}"
            assert "Integration test" in result.stdout, "Script output missing"
            
            self.log("Integration scenario completed successfully")
    
    def run_all_tests(self) -> bool:
        """Run all validation tests"""
        print(f"\n{'#'*60}")
        print(f"# Production Sandbox Validation")
        print(f"# Mode: {self.mode}")
        print(f"# Verbose: {self.verbose}")
        print(f"{'#'*60}\n")
        
        # Run tests
        self.test("Basic Execution", self.test_basic_execution)
        self.test("Resource Limits", self.test_resource_limits)
        self.test("Timeout Enforcement", self.test_timeout_enforcement)
        self.test("Filesystem Access Control", self.test_filesystem_access_control)
        self.test("Network Access Control", self.test_network_access_control)
        self.test("Security Monitoring", self.test_security_monitoring)
        self.test("Audit Logging", self.test_audit_logging)
        self.test("Integration Scenario", self.test_integration_scenario)
        
        # Print summary
        print(f"\n{'='*60}")
        print("VALIDATION SUMMARY")
        print('='*60)
        
        passed = sum(1 for _, success, _ in self.results if success)
        failed = len(self.results) - passed
        
        for name, success, message in self.results:
            status = "✅ PASSED" if success else f"❌ FAILED: {message}"
            print(f"{name:40s} {status}")
        
        print(f"\n{'='*60}")
        print(f"Total: {len(self.results)} tests")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        print(f"Success Rate: {passed/len(self.results)*100:.1f}%")
        print('='*60)
        
        return failed == 0


def main():
    parser = argparse.ArgumentParser(
        description="Validate sandbox implementation in production-like environment"
    )
    parser.add_argument(
        "--mode",
        choices=["warn", "enforce"],
        default="enforce",
        help="Sandbox mode (default: enforce)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    validator = ProductionValidator(mode=args.mode, verbose=args.verbose)
    success = validator.run_all_tests()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
