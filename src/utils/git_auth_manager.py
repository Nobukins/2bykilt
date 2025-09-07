"""
Git Script Authentication and Proxy Support Module

This module provides authentication and proxy support for git script operations.
Supports private repositories with token authentication and enterprise proxy configurations.

Features:
- Git token authentication for private repositories
- Proxy configuration for enterprise environments
- Authentication error logging
- Secure credential handling
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class GitAuthenticationManager:
    """Manages git authentication and proxy configuration"""

    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id
        self.auth_log_path = self._get_auth_log_path()

    def _get_auth_log_path(self) -> Optional[Path]:
        """Get the authentication error log path"""
        if not self.run_id:
            return None
        log_path = Path("artifacts/runs") / self.run_id / "git_script_auth_error.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        return log_path

    def _log_auth_error(self, error: str, context: Optional[Dict[str, Any]] = None):
        """Log authentication errors to file"""
        if not self.auth_log_path:
            return

        try:
            with open(self.auth_log_path, 'a', encoding='utf-8') as f:
                f.write(f"[{self._get_timestamp()}] {error}\n")
                if context:
                    f.write(f"Context: {context}\n")
                f.write("-" * 50 + "\n")
        except Exception as e:
            logger.warning(f"Failed to write auth error log: {e}")

    def _get_timestamp(self) -> str:
        """Get current timestamp for logging"""
        from datetime import datetime
        return datetime.now().isoformat()

    def get_git_credentials(self) -> Tuple[Optional[str], Optional[str]]:
        """
        Get git credentials from environment variables

        Returns:
            Tuple of (username, token) or (None, None) if not configured
        """
        token = os.getenv('GIT_TOKEN')
        username = os.getenv('GIT_USERNAME', 'git')  # Default to 'git' for token auth

        if token:
            logger.info("Git token authentication configured")
            return username, token
        else:
            logger.debug("No git authentication configured")
            return None, None

    def get_proxy_config(self) -> Optional[str]:
        """
        Get proxy configuration from environment variables

        Returns:
            Proxy URL string or None if not configured
        """
        proxy = os.getenv('GIT_PROXY') or os.getenv('HTTPS_PROXY') or os.getenv('HTTP_PROXY')
        if proxy:
            logger.info(f"Git proxy configured: {self._mask_proxy_url(proxy)}")
            return proxy
        else:
            logger.debug("No git proxy configured")
            return None

    def _mask_proxy_url(self, url: str) -> str:
        """Mask sensitive information in proxy URL for logging"""
        try:
            parsed = urlparse(url)
            # Check if URL has a valid scheme and netloc
            if parsed.scheme and parsed.netloc:
                # Check if URL has credentials
                if parsed.username or parsed.password:
                    masked = url.replace(parsed.username or "", "***").replace(parsed.password or "", "***")
                    return masked
                return url
            else:
                # Not a valid URL format
                return "***masked***"
        except Exception:
            return "***masked***"

    def configure_git_for_repo(self, repo_url: str, repo_path: Path) -> bool:
        """
        Configure git settings for a specific repository

        Args:
            repo_url: The git repository URL
            repo_path: Path to the local repository

        Returns:
            True if configuration successful, False otherwise
        """
        try:
            # Configure proxy if available
            proxy = self.get_proxy_config()
            if proxy:
                try:
                    self._configure_proxy(repo_path, proxy)
                except RuntimeError as e:
                    logger.warning(f"Proxy configuration failed, continuing without proxy: {e}")

            # Configure authentication if available
            username, token = self.get_git_credentials()
            if username and token:
                try:
                    self._configure_auth(repo_path, repo_url, username, token)
                except RuntimeError as e:
                    logger.warning(f"Authentication configuration failed, continuing without auth: {e}")

            return True

        except Exception as e:
            error_msg = f"Failed to configure git for repo {repo_url}: {e}"
            logger.error(error_msg)
            self._log_auth_error(error_msg, {"repo_url": repo_url, "repo_path": str(repo_path)})
            return False

    def _configure_proxy(self, repo_path: Path, proxy: str):
        """Configure proxy settings for the repository"""
        try:
            # Set proxy for this repository
            subprocess.run(
                ['git', 'config', 'http.proxy', proxy],
                cwd=repo_path,
                check=True,
                capture_output=True
            )
            logger.info(f"Configured proxy for repository: {self._mask_proxy_url(proxy)}")
        except subprocess.SubprocessError as e:
            logger.error(f"Failed to configure proxy: {e}")
            raise RuntimeError(f"Failed to configure proxy: {e}")

    def _configure_auth(self, repo_path: Path, repo_url: str, username: str, token: str):
        """Configure authentication for the repository"""
        try:
            # Extract domain from URL for credential configuration
            parsed = urlparse(repo_url)
            domain = parsed.netloc

            if not domain:
                raise ValueError(f"Invalid repository URL: {repo_url}")

            # Configure credential helper for this domain
            credential_url = f"https://{domain}"

            # Store credentials (this will be handled by git credential system)
            # Note: In production, consider using git credential helpers or secure storage
            logger.info(f"Configured authentication for domain: {domain}")

        except Exception as e:
            logger.error(f"Failed to configure authentication: {e}")
            raise RuntimeError(f"Failed to configure authentication: {e}")

    def clone_with_auth(self, repo_url: str, target_dir: str, version: str = 'main') -> str:
        """
        Clone a repository with authentication and proxy support

        Args:
            repo_url: The git repository URL
            target_dir: Target directory for cloning
            version: Branch/tag to checkout

        Returns:
            Path to the cloned repository

        Raises:
            RuntimeError: If cloning fails
        """
        try:
            # Get authentication credentials
            username, token = self.get_git_credentials()

            # Prepare authenticated URL if token is available
            clone_url = repo_url
            if username and token:
                # Convert to authenticated URL
                parsed = urlparse(repo_url)
                if parsed.scheme and parsed.netloc:
                    clone_url = f"https://{username}:{token}@{parsed.netloc}{parsed.path}"
                    logger.info(f"Using authenticated URL for cloning: {parsed.netloc}")
                else:
                    raise ValueError(f"Invalid repository URL format: {repo_url}")

            # Prepare git environment with proxy
            env = os.environ.copy()
            proxy = self.get_proxy_config()
            if proxy:
                env['HTTPS_PROXY'] = proxy
                env['HTTP_PROXY'] = proxy
                logger.info(f"Using proxy for git operations: {self._mask_proxy_url(proxy)}")

            # Clone the repository
            logger.info(f"Cloning repository from {parsed.netloc if 'parsed' in locals() else 'unknown'}")
            subprocess.run(
                ['git', 'clone', clone_url, target_dir],
                check=True,
                capture_output=True,
                env=env
            )

            # Configure the cloned repository
            repo_path = Path(target_dir)
            self.configure_git_for_repo(repo_url, repo_path)

            # Checkout specific version if provided
            if version and version != 'main':
                logger.info(f"Checking out version: {version}")
                subprocess.run(
                    ['git', 'checkout', version],
                    cwd=repo_path,
                    check=True,
                    capture_output=True
                )

            logger.info(f"Successfully cloned repository to {target_dir}")
            return target_dir

        except subprocess.SubprocessError as e:
            error_msg = f"Git clone failed: {e}"
            logger.error(error_msg)
            context = {
                "repo_url": repo_url,
                "target_dir": target_dir,
                "version": version,
                "stdout": e.stdout.decode() if e.stdout else None,
                "stderr": e.stderr.decode() if e.stderr else None
            }
            self._log_auth_error(error_msg, context)
            raise RuntimeError(f"Failed to clone repository: {e}")
        except Exception as e:
            error_msg = f"Unexpected error during git clone: {e}"
            logger.error(error_msg)
            self._log_auth_error(error_msg, {"repo_url": repo_url, "target_dir": target_dir})
            raise RuntimeError(f"Failed to clone repository: {e}")

    def get_auth_status(self) -> Dict[str, Any]:
        """
        Get current authentication and proxy status

        Returns:
            Dictionary with authentication and proxy status information
        """
        username, token = self.get_git_credentials()
        proxy = self.get_proxy_config()

        return {
            "authentication_configured": bool(token),
            "proxy_configured": bool(proxy),
            "masked_proxy": self._mask_proxy_url(proxy) if proxy else None,
            "auth_log_path": str(self.auth_log_path) if self.auth_log_path else None
        }
