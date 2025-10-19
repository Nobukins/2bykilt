#!/usr/bin/env python3
"""
Git Authentication Manager Tests

Tests for GitAuthenticationManager class and authentication functionality.
"""

import os
import tempfile
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.utils.git_auth_manager import GitAuthenticationManager


@pytest.mark.ci_safe
class TestGitAuthenticationManager:
    """Test cases for GitAuthenticationManager"""

    def setup_method(self):
        """Set up test environment"""
        self.run_id = "test-run-123"
        self.auth_manager = GitAuthenticationManager(run_id=self.run_id)

    def teardown_method(self):
        """Clean up test environment"""
        # Clean up any test files
        if hasattr(self, 'auth_manager') and self.auth_manager.auth_log_path:
            if self.auth_manager.auth_log_path.exists():
                self.auth_manager.auth_log_path.unlink()

    def test_initialization(self):
        """Test GitAuthenticationManager initialization"""
        assert self.auth_manager.run_id == self.run_id
        assert self.auth_manager.auth_log_path is not None
        assert "git_script_auth_error.log" in str(self.auth_manager.auth_log_path)

    def test_get_git_credentials_no_env(self):
        """Test getting git credentials when no environment variables are set"""
        with patch.dict(os.environ, {}, clear=True):
            username, token = self.auth_manager.get_git_credentials()
            assert username is None
            assert token is None

    def test_get_git_credentials_with_token(self):
        """Test getting git credentials when GIT_TOKEN is set"""
        test_token = "test-token-123"
        with patch.dict(os.environ, {'GIT_TOKEN': test_token}):
            username, token = self.auth_manager.get_git_credentials()
            assert username == 'git'  # Default username
            assert token == test_token

    def test_get_git_credentials_with_custom_username(self):
        """Test getting git credentials with custom username"""
        test_token = "test-token-123"
        test_username = "test-user"
        with patch.dict(os.environ, {
            'GIT_TOKEN': test_token,
            'GIT_USERNAME': test_username
        }):
            username, token = self.auth_manager.get_git_credentials()
            assert username == test_username
            assert token == test_token

    def test_get_proxy_config_no_env(self):
        """Test getting proxy config when no environment variables are set"""
        with patch.dict(os.environ, {}, clear=True):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy is None

    def test_get_proxy_config_git_proxy(self):
        """Test getting proxy config from GIT_PROXY"""
        test_proxy = "http://proxy.example.com:8080"
        with patch.dict(os.environ, {'GIT_PROXY': test_proxy}):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy == test_proxy

    def test_get_proxy_config_https_proxy(self):
        """Test getting proxy config from HTTPS_PROXY"""
        test_proxy = "http://proxy.example.com:8080"
        with patch.dict(os.environ, {'HTTPS_PROXY': test_proxy}):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy == test_proxy

    def test_get_proxy_config_priority(self):
        """Test proxy config priority (GIT_PROXY takes precedence)"""
        git_proxy = "http://git-proxy.example.com:8080"
        https_proxy = "http://https-proxy.example.com:8080"
        with patch.dict(os.environ, {
            'GIT_PROXY': git_proxy,
            'HTTPS_PROXY': https_proxy
        }):
            proxy = self.auth_manager.get_proxy_config()
            assert proxy == git_proxy

    def test_mask_proxy_url_simple(self):
        """Test masking simple proxy URL"""
        test_proxy = "http://user:pass@proxy.example.com:8080"
        masked = self.auth_manager._mask_proxy_url(test_proxy)
        assert "user" not in masked
        assert "pass" not in masked
        assert "***" in masked

    def test_mask_proxy_url_no_credentials(self):
        """Test masking proxy URL without credentials"""
        test_proxy = "http://proxy.example.com:8080"
        masked = self.auth_manager._mask_proxy_url(test_proxy)
        assert masked == test_proxy

    def test_mask_proxy_url_invalid(self):
        """Test masking invalid proxy URL"""
        test_proxy = "not-a-url-at-all-!!!"
        masked = self.auth_manager._mask_proxy_url(test_proxy)
        assert masked == "***masked***"

    @patch('subprocess.run')
    def test_configure_git_for_repo_success(self, mock_subprocess):
        """Test successful git repository configuration"""
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, {
            'GIT_TOKEN': 'test-token',
            'GIT_PROXY': 'http://proxy.example.com:8080'
        }):
            repo_path = Path("/tmp/test-repo")
            result = self.auth_manager.configure_git_for_repo(
                "https://github.com/user/repo.git",
                repo_path
            )
            assert result is True
            # Verify subprocess calls for proxy and auth configuration
            assert mock_subprocess.call_count >= 1

    @patch('src.utils.git_auth_manager.GitAuthenticationManager._configure_auth')
    def test_configure_git_for_repo_failure(self, mock_configure_auth):
        """Test git repository configuration failure"""
        # Mock authentication configuration to fail
        mock_configure_auth.side_effect = RuntimeError("Authentication configuration failed")

        with patch.dict(os.environ, {'GIT_TOKEN': 'test-token'}):
            repo_path = Path("/tmp/test-repo")
            result = self.auth_manager.configure_git_for_repo(
                "https://github.com/user/repo.git",
                repo_path
            )
            assert result is True  # Should still return True as auth failure is handled gracefully

    @patch('src.utils.git_auth_manager.GitAuthenticationManager.get_git_credentials')
    def test_configure_git_for_repo_critical_failure(self, mock_get_credentials):
        """Test git repository configuration critical failure"""
        # Mock get_git_credentials to raise an unexpected exception
        mock_get_credentials.side_effect = Exception("Unexpected error")

        repo_path = Path("/tmp/test-repo")
        result = self.auth_manager.configure_git_for_repo(
            "https://github.com/user/repo.git",
            repo_path
        )
        assert result is False  # Should return False for critical failures

    def test_log_auth_error(self):
        """Test authentication error logging"""
        error_msg = "Test authentication error"
        context = {"repo": "test-repo", "action": "clone"}

        self.auth_manager._log_auth_error(error_msg, context)

        # Verify log file was created and contains expected content
        assert self.auth_manager.auth_log_path.exists()
        with open(self.auth_manager.auth_log_path, 'r') as f:
            content = f.read()
            assert error_msg in content
            assert "repo" in content
            assert "action" in content

    def test_get_auth_status_no_config(self):
        """Test getting auth status when no configuration is present"""
        with patch.dict(os.environ, {}, clear=True):
            status = self.auth_manager.get_auth_status()
            assert status['authentication_configured'] is False
            assert status['proxy_configured'] is False
            assert status['masked_proxy'] is None
            assert status['auth_log_path'] is not None

    def test_get_auth_status_with_config(self):
        """Test getting auth status when configuration is present"""
        with patch.dict(os.environ, {
            'GIT_TOKEN': 'test-token',
            'GIT_PROXY': 'http://user:pass@proxy.example.com:8080'
        }):
            status = self.auth_manager.get_auth_status()
            assert status['authentication_configured'] is True
            assert status['proxy_configured'] is True
            assert "user" not in status['masked_proxy']
            assert "pass" not in status['masked_proxy']
            assert "***" in status['masked_proxy']

    @patch('subprocess.run')
    @patch('tempfile.mkdtemp')
    def test_clone_with_auth_success(self, mock_mkdtemp, mock_subprocess):
        """Test successful authenticated repository cloning"""
        mock_mkdtemp.return_value = "/tmp/test-repo-dir"
        mock_subprocess.return_value = MagicMock(returncode=0)

        with patch.dict(os.environ, {
            'GIT_TOKEN': 'test-token',
            'GIT_PROXY': 'http://proxy.example.com:8080'
        }):
            result = self.auth_manager.clone_with_auth(
                "https://github.com/user/repo.git",
                "/tmp/test-repo",
                "main"
            )
            assert result == "/tmp/test-repo"
            # Verify git clone was called
            mock_subprocess.assert_called()

    @patch('subprocess.run')
    def test_clone_with_auth_failure(self, mock_subprocess):
        """Test authenticated repository cloning failure"""
        mock_subprocess.side_effect = Exception("Clone failed")

        with patch.dict(os.environ, {'GIT_TOKEN': 'test-token'}):
            with pytest.raises(RuntimeError, match="Failed to clone repository"):
                self.auth_manager.clone_with_auth(
                    "https://github.com/user/repo.git",
                    "/tmp/test-repo",
                    "main"
                )

    def test_clone_with_auth_no_auth(self):
        """Test repository cloning without authentication"""
        with patch.dict(os.environ, {}, clear=True):
            with patch('subprocess.run') as mock_subprocess:
                mock_subprocess.return_value = MagicMock(returncode=0)

                result = self.auth_manager.clone_with_auth(
                    "https://github.com/user/repo.git",
                    "/tmp/test-repo",
                    "main"
                )
                assert result == "/tmp/test-repo"
                # Verify git clone was called without auth URL modification
                mock_subprocess.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__])
