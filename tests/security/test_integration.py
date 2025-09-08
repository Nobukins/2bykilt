"""Integration tests for secret masking with JsonlLogger."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from src.logging.jsonl_logger import JsonlLogger
from src.security.secret_masker import create_masking_hook
from src.runtime.run_context import RunContext


class TestSecretMaskingIntegration:
    """Integration tests for secret masking with the logging system."""
    
    def test_masking_hook_integration_with_logger(self, tmp_path, monkeypatch):
        """Test that the masking hook works correctly with JsonlLogger."""
        # Set up test environment like existing logging tests
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BYKILT_RUN_ID", "masking-test")
        
        # Clear singleton instances
        JsonlLogger._instances.clear()
        RunContext._instance = None
        
        # Create logger and register masking hook
        logger = JsonlLogger.get(component="test")
        masking_hook = create_masking_hook()
        logger.register_hook(masking_hook)
        
        # Log a message with sensitive information
        logger.info(
            "User login with password=secret123 and Bearer abc123def456789012345",
            api_key="sk-1234567890abcdefgh",
            user_data={
                "password": "userpass123",
                "token": "secrettoken456"
            }
        )
        
        # Read the log file
        log_file = logger.file_path
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            log_line = f.read().strip()
        
        # Parse the JSON log entry
        log_entry = json.loads(log_line)
        
        # Verify sensitive information is masked in the message
        assert "password=***MASKED_PASSWORD***" in log_entry["msg"]
        assert "Bearer ***MASKED_TOKEN***" in log_entry["msg"]
        assert "secret123" not in log_entry["msg"]
        
        # Verify sensitive fields are masked
        assert log_entry["api_key"] == "***MASKED***"
        assert log_entry["user_data"]["password"] == "***MASKED***"
        assert log_entry["user_data"]["token"] == "***MASKED***"
        
        # Verify core log fields are preserved
        assert log_entry["level"] == "INFO"
        assert log_entry["component"] == "test"
        assert "run_id" in log_entry
    
    def test_masking_disabled_via_feature_flag(self, tmp_path, monkeypatch):
        """Test that masking can be disabled via feature flag."""
        # Mock feature flags to disable masking
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.return_value = False
            
            # Set up test environment
            monkeypatch.chdir(tmp_path)
            monkeypatch.setenv("BYKILT_RUN_ID", "disabled-test")
            
            # Clear singleton instances
            JsonlLogger._instances.clear()
            RunContext._instance = None
            
            # Create logger and register masking hook
            logger = JsonlLogger.get(component="test")
            masking_hook = create_masking_hook()
            logger.register_hook(masking_hook)
            
            # Log a message with sensitive information
            logger.info(
                "password=secret123",
                api_key="sk-1234567890abcdefgh"
            )
            
            # Read the log file
            log_file = logger.file_path
            with open(log_file, 'r') as f:
                log_line = f.read().strip()
            
            # Parse the JSON log entry
            log_entry = json.loads(log_line)
            
            # Verify sensitive information is NOT masked
            assert "password=secret123" in log_entry["msg"]
            assert log_entry["api_key"] == "sk-1234567890abcdefgh"
    
    def test_masking_performance_requirement(self, tmp_path, monkeypatch):
        """Test that masking meets the <5ms performance requirement."""
        import time
        
        # Set up test environment
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BYKILT_RUN_ID", "perf-test")
        
        # Clear singleton instances
        JsonlLogger._instances.clear()
        RunContext._instance = None
        
        # Create logger and register masking hook
        logger = JsonlLogger.get(component="test")
        masking_hook = create_masking_hook()
        logger.register_hook(masking_hook)
        
        # Create a complex log message with many secrets
        complex_data = {
            "config": {
                "database": {
                    "password": "dbpassword123",
                    "connection_string": "postgresql://user:secret123@host/db"
                },
                "api_keys": [
                    "sk-1234567890abcdefgh",
                    "pk-abcdefgh1234567890",
                    "xoxp-1234567890abcdef"
                ]
            },
            "large_list": [f"item_{i}" for i in range(100)]
        }
        
        # Measure performance
        start_time = time.time()
        logger.info(
            "Complex operation with Bearer xyz123abc456def789012345 and password=supersecret",
            **complex_data
        )
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Should be much faster than 5ms
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}ms, should be <5ms"
        
        # Verify the log was still created and masking worked
        log_file = logger.file_path
        assert log_file.exists()
        
        with open(log_file, 'r') as f:
            log_line = f.read().strip()
        
        log_entry = json.loads(log_line)
        
        # Verify masking worked
        assert "***MASKED_PASSWORD***" in log_entry["msg"]
        assert log_entry["config"]["database"]["password"] == "***MASKED***"
    
    def test_multiple_hooks_order(self, tmp_path, monkeypatch):
        """Test that masking hook works correctly with other hooks."""
        # Set up test environment
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("BYKILT_RUN_ID", "multi-hook-test")
        
        # Clear singleton instances
        JsonlLogger._instances.clear()
        RunContext._instance = None
        
        # Create logger
        logger = JsonlLogger.get(component="test")
        
        # Create a test hook that adds metadata
        def metadata_hook(record):
            record["test_metadata"] = "added_by_hook"
            return record
        
        # Register hooks in order: masking first, then metadata
        masking_hook = create_masking_hook()
        logger.register_hook(masking_hook)
        logger.register_hook(metadata_hook)
        
        # Log a message with sensitive information
        logger.info("password=secret123", api_key="sk-1234567890abcdefgh")
        
        # Read the log file
        log_file = logger.file_path
        with open(log_file, 'r') as f:
            log_line = f.read().strip()
        
        log_entry = json.loads(log_line)
        
        # Verify both hooks worked
        assert "***MASKED_PASSWORD***" in log_entry["msg"]
        assert log_entry["api_key"] == "***MASKED***"
        assert log_entry["test_metadata"] == "added_by_hook"


class TestSecretMaskingFeatureFlag:
    """Test secret masking feature flag integration."""
    
    def test_feature_flag_configuration(self):
        """Test that the feature flag can be read correctly."""
        # Test enabled
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.return_value = True
            from src.security.secret_masker import SecretMasker
            
            masker = SecretMasker.from_feature_flags()
            assert masker.enabled is True
            mock_flags.is_enabled.assert_called_with("security.secret_masking_enabled")
        
        # Test disabled
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.return_value = False
            
            masker = SecretMasker.from_feature_flags()
            assert masker.enabled is False