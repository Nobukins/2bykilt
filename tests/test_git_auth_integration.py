#!/usr/bin/env python3
"""
Integration Test for Git Authentication and Proxy Features

This test verifies that the git authentication and proxy features work correctly
in the context of the full system.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch

from src.utils.git_auth_manager import GitAuthenticationManager
from src.script.git_script_resolver import GitScriptResolver


@pytest.mark.ci_safe
class TestGitAuthIntegration:
    """Integration tests for git authentication and proxy features"""

    def setup_method(self):
        """Set up test environment"""
        self.run_id = "integration-test-123"
        self.auth_manager = GitAuthenticationManager(run_id=self.run_id)
        self.resolver = GitScriptResolver(run_id=self.run_id)

    def teardown_method(self):
        """Clean up test environment"""
        # Clean up any test files
        if hasattr(self, 'auth_manager') and self.auth_manager.auth_log_path:
            if self.auth_manager.auth_log_path.exists():
                self.auth_manager.auth_log_path.unlink()

    def test_auth_manager_integration(self):
        """Test GitAuthenticationManager integration"""
        # Test without environment variables
        with patch.dict(os.environ, {}, clear=True):
            status = self.auth_manager.get_auth_status()
            assert status['authentication_configured'] is False
            assert status['proxy_configured'] is False

        # Test with authentication configured
        with patch.dict(os.environ, {
            'GIT_TOKEN': 'test-token-123',
            'GIT_USERNAME': 'test-user',
            'GIT_PROXY': 'http://proxy.example.com:8080'
        }):
            status = self.auth_manager.get_auth_status()
            assert status['authentication_configured'] is True
            assert status['proxy_configured'] is True
            assert 'test-user' not in status['masked_proxy']
            assert 'test-token' not in status['masked_proxy']

    def test_resolver_with_auth_manager(self):
        """Test GitScriptResolver integration with authentication manager"""
        # Verify resolver has auth_manager
        assert hasattr(self.resolver, 'auth_manager')
        assert isinstance(self.resolver.auth_manager, GitAuthenticationManager)

        # Test resolver initialization with run_id
        assert self.resolver.auth_manager.run_id == self.run_id

    def test_environment_variable_priority(self):
        """Test environment variable priority for proxy configuration"""
        # Test GIT_PROXY takes precedence over HTTPS_PROXY
        with patch.dict(os.environ, {
            'GIT_PROXY': 'http://git-proxy.example.com:8080',
            'HTTPS_PROXY': 'http://https-proxy.example.com:8080'
        }):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy == 'http://git-proxy.example.com:8080'

        # Test HTTPS_PROXY when GIT_PROXY is not set
        with patch.dict(os.environ, {
            'HTTPS_PROXY': 'http://https-proxy.example.com:8080'
        }, clear=True):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy == 'http://https-proxy.example.com:8080'

    def test_auth_error_logging(self):
        """Test authentication error logging functionality"""
        error_msg = "Test authentication error"
        context = {"operation": "clone", "repo": "test/repo"}

        self.auth_manager._log_auth_error(error_msg, context)

        # Verify log file was created
        assert self.auth_manager.auth_log_path.exists()

        # Verify log content
        with open(self.auth_manager.auth_log_path, 'r') as f:
            content = f.read()
            assert error_msg in content
            assert "operation" in content
            assert "repo" in content

    def test_mask_proxy_url_integration(self):
        """Test proxy URL masking in various scenarios"""
        # Test with credentials
        url_with_creds = "http://user:password@proxy.example.com:8080"
        masked = self.auth_manager._mask_proxy_url(url_with_creds)
        assert "user" not in masked
        assert "password" not in masked
        assert "***" in masked

        # Test without credentials
        url_no_creds = "http://proxy.example.com:8080"
        masked = self.auth_manager._mask_proxy_url(url_no_creds)
        assert masked == url_no_creds

        # Test invalid URL
        invalid_url = "not-a-valid-url-!!!"
        masked = self.auth_manager._mask_proxy_url(invalid_url)
        assert masked == "***masked***"

    def test_git_credentials_integration(self):
        """Test git credentials retrieval integration"""
        # Test with token
        with patch.dict(os.environ, {'GIT_TOKEN': 'test-token'}):
            username, token = self.auth_manager.get_git_credentials()
            assert username == 'git'  # Default username
            assert token == 'test-token'

        # Test with custom username
        with patch.dict(os.environ, {
            'GIT_TOKEN': 'test-token',
            'GIT_USERNAME': 'custom-user'
        }):
            username, token = self.auth_manager.get_git_credentials()
            assert username == 'custom-user'
            assert token == 'test-token'

        # Test without token
        with patch.dict(os.environ, {}, clear=True):
            username, token = self.auth_manager.get_git_credentials()
            assert username is None
            assert token is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
