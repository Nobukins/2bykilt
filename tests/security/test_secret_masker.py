"""Tests for SecretMasker functionality (Issue #60)."""

import pytest
import time
from unittest.mock import patch, MagicMock

from src.security.secret_masker import SecretMasker, SecretPattern, create_masking_hook


class TestSecretPattern:
    """Test SecretPattern class."""
    
    def test_secret_pattern_creation(self):
        """Test creating a SecretPattern."""
        import re
        pattern = SecretPattern(
            name="test",
            pattern=re.compile(r"test"),
            replacement="***TEST***"
        )
        assert pattern.name == "test"
        assert pattern.replacement == "***TEST***"
        assert pattern.pattern.pattern == "test"


class TestSecretMasker:
    """Test SecretMasker core functionality."""
    
    def test_init_enabled(self):
        """Test SecretMasker initialization with enabled=True."""
        masker = SecretMasker(enabled=True)
        assert masker.enabled is True
    
    def test_init_disabled(self):
        """Test SecretMasker initialization with enabled=False."""
        masker = SecretMasker(enabled=False)
        assert masker.enabled is False
    
    def test_from_feature_flags_enabled(self):
        """Test creating SecretMasker from feature flags when enabled."""
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.return_value = True
            masker = SecretMasker.from_feature_flags()
            assert masker.enabled is True
            mock_flags.is_enabled.assert_called_once_with("security.secret_masking_enabled")
    
    def test_from_feature_flags_disabled(self):
        """Test creating SecretMasker from feature flags when disabled."""
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.return_value = False
            masker = SecretMasker.from_feature_flags()
            assert masker.enabled is False
    
    def test_from_feature_flags_exception_default_enabled(self):
        """Test that SecretMasker defaults to enabled when feature flags fail."""
        with patch('src.security.secret_masker.FeatureFlags') as mock_flags:
            mock_flags.is_enabled.side_effect = Exception("Feature flags not available")
            masker = SecretMasker.from_feature_flags()
            assert masker.enabled is True


class TestSecretMaskerTextMasking:
    """Test text masking functionality."""
    
    def test_mask_text_disabled(self):
        """Test that masking is skipped when disabled."""
        masker = SecretMasker(enabled=False)
        text = "password=secret123"
        result = masker.mask_text(text)
        assert result == text
    
    def test_mask_text_non_string(self):
        """Test that non-string input is returned unchanged."""
        masker = SecretMasker(enabled=True)
        assert masker.mask_text(42) == 42
        assert masker.mask_text(None) is None
    
    def test_mask_api_key_prefixes(self):
        """Test masking of API key prefixes."""
        masker = SecretMasker(enabled=True)
        
        test_cases = [
            ("sk-1234567890abcdefghijk", "***MASKED_API_KEY***"),
            ("pk-abcdefghijk1234567890", "***MASKED_API_KEY***"),
            ("xoxp-1234567890abcdefghijk", "***MASKED_API_KEY***"),
            ("xoxb-abcdefghijk1234567890", "***MASKED_API_KEY***"),
        ]
        
        for original, expected in test_cases:
            result = masker.mask_text(original)
            assert result == expected
    
    def test_mask_password_fields(self):
        """Test masking of password field patterns."""
        masker = SecretMasker(enabled=True)
        
        test_cases = [
            ("password=secret123", "password=***MASKED_PASSWORD***"),
            ("passwd: mypassword", "passwd=***MASKED_PASSWORD***"),
            ("pwd = 'mypassword123'", "pwd=***MASKED_PASSWORD***"),
            ('password="verysecret"', "password=***MASKED_PASSWORD***"),
        ]
        
        for original, expected in test_cases:
            result = masker.mask_text(original)
            assert result == expected
    
    def test_mask_bearer_token(self):
        """Test masking of Bearer tokens."""
        masker = SecretMasker(enabled=True)
        
        test_cases = [
            ("Bearer abc123def456ghi789", "Bearer ***MASKED_TOKEN***"),
            ("bearer XYZ789ABC456DEF123", "Bearer ***MASKED_TOKEN***"),
        ]
        
        for original, expected in test_cases:
            result = masker.mask_text(original)
            assert result == expected
    
    def test_mask_authorization_header(self):
        """Test masking of Authorization headers."""
        masker = SecretMasker(enabled=True)
        
        test_cases = [
            ("Authorization: abc123def456ghi789", "Authorization: ***MASKED_AUTH***"),
            ("authorization:XYZ789ABC456DEF123", "Authorization: ***MASKED_AUTH***"),
        ]
        
        for original, expected in test_cases:
            result = masker.mask_text(original)
            assert result == expected
    
    def test_mask_generic_secrets(self):
        """Test masking of generic long alphanumeric strings."""
        masker = SecretMasker(enabled=True)
        
        # 32+ character strings should be masked
        long_string = "a" * 32
        result = masker.mask_text(long_string)
        assert result == "***MASKED_GENERIC***"
        
        # Shorter strings should not be masked
        short_string = "a" * 31
        result = masker.mask_text(short_string)
        assert result == short_string
    
    def test_mask_multiple_patterns(self):
        """Test masking multiple patterns in the same text."""
        masker = SecretMasker(enabled=True)
        
        text = "sk-123456789012345678901234 and password=secret123"
        result = masker.mask_text(text)
        assert "***MASKED_API_KEY***" in result
        assert "***MASKED_PASSWORD***" in result
        assert "sk-" not in result
        assert "secret123" not in result


class TestSecretMaskerSensitiveKeys:
    """Test sensitive key detection."""
    
    def test_is_sensitive_key(self):
        """Test sensitive key detection."""
        masker = SecretMasker(enabled=True)
        
        sensitive_keys = [
            'password', 'secret', 'token', 'key', 'credential',
            'auth', 'session', 'cookie', 'private', 'api_key',
            'access_token', 'refresh_token', 'client_secret',
            'API_KEY', 'Password', 'SECRET'  # Case variations
        ]
        
        for key in sensitive_keys:
            assert masker._is_sensitive_key(key), f"Key '{key}' should be sensitive"
        
        non_sensitive_keys = ['name', 'id', 'email', 'username', 'data']
        for key in non_sensitive_keys:
            assert not masker._is_sensitive_key(key), f"Key '{key}' should not be sensitive"


class TestSecretMaskerDataMasking:
    """Test data structure masking."""
    
    def test_mask_data_disabled(self):
        """Test that data masking is skipped when disabled."""
        masker = SecretMasker(enabled=False)
        data = {"password": "secret123"}
        result = masker.mask_data(data)
        assert result == data
    
    def test_mask_data_dict_sensitive_keys(self):
        """Test masking of sensitive keys in dictionaries."""
        masker = SecretMasker(enabled=True)
        
        data = {
            "username": "john",
            "password": "secret123",
            "api_key": "sk-1234567890",
            "normal_field": "normal_value"
        }
        
        result = masker.mask_data(data)
        
        assert result["username"] == "john"
        assert result["password"] == "***MASKED***"
        assert result["api_key"] == "***MASKED***"
        assert result["normal_field"] == "normal_value"
    
    def test_mask_data_dict_nested(self):
        """Test masking of nested dictionaries."""
        masker = SecretMasker(enabled=True)
        
        data = {
            "config": {
                "database": {
                    "password": "dbsecret",
                    "host": "localhost"
                }
            }
        }
        
        result = masker.mask_data(data)
        
        assert result["config"]["database"]["password"] == "***MASKED***"
        assert result["config"]["database"]["host"] == "localhost"
    
    def test_mask_data_list(self):
        """Test masking of lists."""
        masker = SecretMasker(enabled=True)
        
        data = ["password=secret123", "normal text", {"token": "abc123"}]
        result = masker.mask_data(data)
        
        assert "***MASKED_PASSWORD***" in result[0]
        assert result[1] == "normal text"
        assert result[2]["token"] == "***MASKED***"
    
    def test_mask_data_string(self):
        """Test masking of string data."""
        masker = SecretMasker(enabled=True)
        
        data = "password=secret123"
        result = masker.mask_data(data)
        assert result == "password=***MASKED_PASSWORD***"
    
    def test_mask_data_other_types(self):
        """Test that other data types are returned unchanged."""
        masker = SecretMasker(enabled=True)
        
        test_values = [42, 3.14, True, None]
        for value in test_values:
            result = masker.mask_data(value)
            assert result == value


class TestSecretMaskerLogRecordMasking:
    """Test log record masking functionality."""
    
    def test_mask_log_record_disabled(self):
        """Test that log record masking is skipped when disabled."""
        masker = SecretMasker(enabled=False)
        record = {"msg": "password=secret123", "password": "secret"}
        result = masker.mask_log_record(record)
        assert result == record
    
    def test_mask_log_record_basic(self):
        """Test basic log record masking."""
        masker = SecretMasker(enabled=True)
        
        record = {
            "ts": "2023-01-01T00:00:00Z",
            "seq": 1,
            "level": "INFO",
            "msg": "User logged in with password=secret123",
            "component": "auth",
            "run_id": "test-run",
            "api_key": "sk-1234567890abcdefghijk",
            "username": "john"
        }
        
        result = masker.mask_log_record(record)
        
        # Core fields should be unchanged
        assert result["ts"] == record["ts"]
        assert result["seq"] == record["seq"]
        assert result["level"] == record["level"]
        assert result["component"] == record["component"]
        assert result["run_id"] == record["run_id"]
        
        # Message should be masked
        assert "password=***MASKED_PASSWORD***" in result["msg"]
        assert "secret123" not in result["msg"]
        
        # Sensitive fields should be masked
        assert result["api_key"] == "***MASKED***"
        
        # Non-sensitive fields should be unchanged
        assert result["username"] == "john"
    
    def test_mask_log_record_creates_copy(self):
        """Test that masking creates a copy and doesn't mutate original."""
        masker = SecretMasker(enabled=True)
        
        record = {"msg": "password=secret123", "password": "secret"}
        original_record = record.copy()
        
        result = masker.mask_log_record(record)
        
        # Original should be unchanged
        assert record == original_record
        # Result should be different
        assert result != record
    
    def test_mask_log_record_performance_tracking(self):
        """Test that performance is tracked and warnings added if slow."""
        masker = SecretMasker(enabled=True)
        
        # Mock time.time to simulate slow processing
        with patch('src.security.secret_masker.time.time') as mock_time:
            mock_time.side_effect = [0.0, 0.01]  # 10ms processing time
            
            record = {"msg": "test message"}
            result = masker.mask_log_record(record)
            
            assert "warnings" in result
            assert any("secret_masking_slow" in warning for warning in result["warnings"])
    
    def test_mask_log_record_performance_requirement(self):
        """Test that masking meets performance requirement (<5ms)."""
        masker = SecretMasker(enabled=True)
        
        # Create a reasonably complex log record
        record = {
            "msg": "password=secret123 and Bearer abc123def456ghi789",
            "api_key": "sk-1234567890abcdefghijk",
            "config": {
                "database": {"password": "dbsecret"},
                "tokens": ["token1", "token2", "token3"]
            },
            "large_list": [f"item_{i}" for i in range(100)]
        }
        
        start_time = time.time()
        result = masker.mask_log_record(record)
        processing_time = (time.time() - start_time) * 1000
        
        # Should be much faster than 5ms for typical workloads
        assert processing_time < 5.0, f"Processing took {processing_time:.2f}ms, should be <5ms"
        
        # Verify masking still works
        assert "***MASKED_PASSWORD***" in result["msg"]
        assert result["api_key"] == "***MASKED***"


class TestMaskingHook:
    """Test the masking hook functionality."""
    
    def test_create_masking_hook(self):
        """Test creating a masking hook."""
        with patch('src.security.secret_masker.SecretMasker.from_feature_flags') as mock_from_ff:
            mock_masker = MagicMock()
            mock_from_ff.return_value = mock_masker
            
            hook = create_masking_hook()
            
            assert callable(hook)
            mock_from_ff.assert_called_once()
    
    def test_masking_hook_calls_mask_log_record(self):
        """Test that the masking hook calls mask_log_record."""
        with patch('src.security.secret_masker.SecretMasker.from_feature_flags') as mock_from_ff:
            mock_masker = MagicMock()
            mock_from_ff.return_value = mock_masker
            
            hook = create_masking_hook()
            test_record = {"msg": "test"}
            
            hook(test_record)
            
            mock_masker.mask_log_record.assert_called_once_with(test_record)
    
    def test_masking_hook_integration(self):
        """Test the masking hook with real masking."""
        hook = create_masking_hook()
        
        record = {
            "msg": "password=secret123",
            "api_key": "sk-1234567890abcdefghijk"
        }
        
        result = hook(record)
        
        assert "***MASKED_PASSWORD***" in result["msg"]
        # Note: api_key masking depends on feature flag being enabled


class TestIntegration:
    """Integration tests for secret masking."""
    
    def test_end_to_end_masking(self):
        """Test end-to-end secret masking functionality."""
        masker = SecretMasker(enabled=True)
        
        # Simulate a complex log record with various secret types
        record = {
            "ts": "2023-01-01T00:00:00Z",
            "seq": 1,
            "level": "INFO",
            "msg": "Login attempt: Bearer xyz789abc456def123 for user with sk-1234567890abcdefghijk",
            "component": "auth",
            "run_id": "test-run",
            "request_data": {
                "password": "userpassword123",
                "api_key": "pk-abcdefghijk1234567890",
                "headers": {
                    "Authorization": "Bearer secrettoken123",
                    "X-API-Key": "secret-key-value"
                }
            },
            "metadata": {
                "user_id": 12345,
                "ip_address": "192.168.1.1"
            }
        }
        
        result = masker.mask_log_record(record)
        
        # Verify message masking
        assert "Bearer ***MASKED_TOKEN***" in result["msg"]
        assert "***MASKED_API_KEY***" in result["msg"]
        assert "Bearer xyz789abc456def123" not in result["msg"]
        assert "sk-1234567890abcdefghijk" not in result["msg"]
        
        # Verify nested data masking
        assert result["request_data"]["password"] == "***MASKED***"
        assert result["request_data"]["api_key"] == "***MASKED***"
        assert result["request_data"]["headers"]["Authorization"] == "***MASKED***"
        
        # Verify non-sensitive data is preserved
        assert result["metadata"]["user_id"] == 12345
        assert result["metadata"]["ip_address"] == "192.168.1.1"
        
        # Verify core log fields are preserved
        assert result["ts"] == record["ts"]
        assert result["component"] == record["component"]
        assert result["run_id"] == record["run_id"]