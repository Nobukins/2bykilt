"""
Git Script Resolver Module

This module provides functionality to resolve git-script references by:
1. Detecting git_script candidates from various sources
2. Resolving scripts in order: absolute path -> relative path -> llms.txt
3. Fetching scripts from GitHub repositories
4. Providing proper error handling and logging

Part of Issue #44 implementation for git_script bug fix.
"""

import os
import re
import tempfile
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from urllib.parse import urlparse

from src.utils.app_logger import logger


class GitScriptCandidate:
    """Represents a git script candidate with metadata"""

    def __init__(self, name: str, git_url: str, script_path: str, version: str = 'main'):
        self.name = name
        self.git_url = git_url
        self.script_path = script_path
        self.version = version

    def __repr__(self):
        return f"GitScriptCandidate(name='{self.name}', git='{self.git_url}', script='{self.script_path}', version='{self.version}')"


class GitScriptResolver:
    """Resolves git-script references from various sources"""

    # Class constants for configuration
    DEFAULT_CACHE_DIR_NAME = 'bykilt_gitscripts'
    DEFAULT_GIT_TIMEOUT = 10  # seconds

    def __init__(self, cache_dir_name: Optional[str] = None, git_timeout: Optional[int] = None):
        self.cache_dir_name = cache_dir_name or self.DEFAULT_CACHE_DIR_NAME
        self.git_timeout = git_timeout or self.DEFAULT_GIT_TIMEOUT
        self.cache_dir = os.path.join(tempfile.gettempdir(), self.cache_dir_name)
        os.makedirs(self.cache_dir, exist_ok=True)

    async def resolve_git_script(self, script_name: str, params: Optional[Dict[str, str]] = None) -> Optional[Dict[str, Any]]:
        """
        Resolve a git-script by name, following the resolution order:
        1. Absolute path (if script_name is a full path)
        2. Relative path (if script_name contains path separators)
        3. llms.txt lookup (search for matching action)

        Args:
            script_name: Name or path of the script to resolve
            params: Optional parameters for script resolution

        Returns:
            Dict containing resolved script info, or None if not found
        """
        logger.info(f"🔍 Resolving git-script: {script_name}")

        # Resolution Order 1: Absolute path
        if os.path.isabs(script_name):
            resolved = await self._resolve_absolute_path(script_name)
            if resolved:
                logger.info(f"✅ Resolved as absolute path: {script_name}")
                return resolved

        # Resolution Order 2: Relative path with separators
        if '/' in script_name or '\\' in script_name:
            resolved = await self._resolve_relative_path(script_name)
            if resolved:
                logger.info(f"✅ Resolved as relative path: {script_name}")
                return resolved

        # Resolution Order 3: llms.txt lookup
        resolved = await self._resolve_from_llms_txt(script_name)
        if resolved:
            logger.info(f"✅ Resolved from llms.txt: {script_name}")
            return resolved

        logger.warning(f"❌ Could not resolve git-script: {script_name}")
        return None

    async def _resolve_absolute_path(self, script_path: str) -> Optional[Dict[str, Any]]:
        """Resolve script from absolute path"""
        try:
            if os.path.exists(script_path):
                # Extract git info from path if possible
                git_info = self._extract_git_info_from_path(script_path)
                if git_info:
                    return {
                        'type': 'git-script',
                        'git': git_info['git_url'],
                        'script_path': git_info['script_path'],
                        'version': git_info.get('version', 'main'),
                        'resolved_from': 'absolute_path'
                    }
                else:
                    # Local file, not from git
                    return {
                        'type': 'script',
                        'script': os.path.basename(script_path),
                        'resolved_from': 'absolute_path'
                    }
        except Exception as e:
            logger.error(f"Error resolving absolute path {script_path}: {e}")

        return None

    async def _resolve_relative_path(self, script_path: str) -> Optional[Dict[str, Any]]:
        """Resolve script from relative path"""
        try:
            # Try to find the script in common locations
            search_paths = [
                '.',  # Current directory
                'scripts',  # Scripts directory
                'src/scripts',  # Source scripts directory
                'tmp/myscript',  # Temp scripts directory
            ]

            for base_path in search_paths:
                full_path = os.path.join(base_path, script_path)
                if os.path.exists(full_path):
                    # Check if it's in a git repository
                    git_info = self._extract_git_info_from_path(full_path)
                    if git_info:
                        return {
                            'type': 'git-script',
                            'git': git_info['git_url'],
                            'script_path': git_info['script_path'],
                            'version': git_info.get('version', 'main'),
                            'resolved_from': 'relative_path'
                        }
                    else:
                        return {
                            'type': 'script',
                            'script': script_path,
                            'resolved_from': 'relative_path'
                        }
        except Exception as e:
            logger.error(f"Error resolving relative path {script_path}: {e}")

        return None

    async def _resolve_from_llms_txt(self, script_name: str) -> Optional[Dict[str, Any]]:
        """Resolve script from llms.txt configuration"""
        try:
            from src.config.llms_parser import load_actions_config

            actions_config = load_actions_config()
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                actions = actions_config['actions']
            elif isinstance(actions_config, list):
                actions = actions_config
            else:
                logger.warning("Invalid llms.txt format")
                return None

            # Search for matching git-script action
            for action in actions:
                if (action.get('name') == script_name and
                    action.get('type') == 'git-script'):

                    # Validate required fields
                    git_url = action.get('git')
                    script_path = action.get('script_path')

                    if not git_url or not script_path:
                        logger.warning(f"Incomplete git-script definition for {script_name}")
                        continue

                    return {
                        'type': 'git-script',
                        'git': git_url,
                        'script_path': script_path,
                        'version': action.get('version', 'main'),
                        'command': action.get('command'),
                        'params': action.get('params', []),
                        'timeout': action.get('timeout'),
                        'slowmo': action.get('slowmo'),
                        'resolved_from': 'llms.txt'
                    }

        except Exception as e:
            logger.error(f"Error resolving from llms.txt: {e}")

        return None

    def _extract_git_info_from_path(self, file_path: str) -> Optional[Dict[str, str]]:
        """Extract git repository information from file path"""
        try:
            # Validate file_path to prevent command injection
            if not file_path or not isinstance(file_path, str):
                logger.warning(f"Invalid file_path provided: {file_path}")
                return None

            # Normalize path and check for potentially unsafe patterns
            normalized_path = os.path.normpath(file_path)
            if os.path.isabs(normalized_path):
                # For absolute paths, ensure they don't contain suspicious patterns
                if any(part in ['..', '.', ''] for part in normalized_path.split(os.sep)):
                    logger.warning(f"Potentially unsafe absolute path: {file_path}")
                    return None

            # Get directory containing the file
            file_dir = os.path.dirname(normalized_path)
            if not file_dir or file_dir == '.':
                file_dir = '.'

            # Check if the file is inside a git repository
            result = subprocess.run(
                ['git', 'rev-parse', '--show-toplevel'],
                cwd=file_dir,
                capture_output=True,
                text=True,
                timeout=self.git_timeout
            )

            if result.returncode == 0:
                repo_root = result.stdout.strip()

                # Validate repo_root is safe
                if not repo_root or not os.path.isabs(repo_root):
                    logger.warning(f"Invalid repository root: {repo_root}")
                    return None

                # Get remote URL
                result = subprocess.run(
                    ['git', 'remote', 'get-url', 'origin'],
                    cwd=repo_root,
                    capture_output=True,
                    text=True,
                    timeout=self.git_timeout
                )

                if result.returncode == 0:
                    git_url = result.stdout.strip()

                    # Validate git URL format
                    if not self._is_safe_git_url(git_url):
                        logger.warning(f"Potentially unsafe git URL: {git_url}")
                        return None

                    # Get current branch/version
                    result = subprocess.run(
                        ['git', 'rev-parse', '--abbrev-ref', 'HEAD'],
                        cwd=repo_root,
                        capture_output=True,
                        text=True,
                        timeout=self.git_timeout
                    )

                    version = 'main'
                    if result.returncode == 0:
                        version = result.stdout.strip()
                        # Validate version string
                        if not self._is_safe_git_ref(version):
                            logger.warning(f"Potentially unsafe git ref: {version}")
                            version = 'main'

                    # Calculate relative script path
                    script_path = os.path.relpath(normalized_path, repo_root)

                    # Validate script path
                    if not self._is_safe_script_path(script_path):
                        logger.warning(f"Potentially unsafe script path: {script_path}")
                        return None

                    return {
                        'git_url': git_url,
                        'script_path': script_path,
                        'version': version
                    }

        except (subprocess.TimeoutExpired, subprocess.SubprocessError, FileNotFoundError, ValueError) as e:
            logger.debug(f"Could not extract git info from {file_path}: {e}")

        return None

    def _is_safe_git_url(self, url: str) -> bool:
        """Check if git URL is safe to use"""
        if not url or not isinstance(url, str):
            return False

        # Only allow GitHub URLs
        if not url.startswith(('https://github.com/', 'git@github.com:')):
            return False

        # Basic validation - no shell metacharacters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
        if any(char in url for char in dangerous_chars):
            return False

        return True

    def _is_safe_git_ref(self, ref: str) -> bool:
        """Check if git reference (branch/tag) is safe"""
        if not ref or not isinstance(ref, str):
            return False

        # Limit length
        if len(ref) > 100:
            return False

        # No dangerous characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r', '..']
        if any(char in ref for char in dangerous_chars):
            return False

        # No absolute paths
        if ref.startswith('/'):
            return False

        return True

    def _is_safe_script_path(self, path: str) -> bool:
        """Check if script path is safe"""
        if not path or not isinstance(path, str):
            return False

        # Normalize path
        normalized = os.path.normpath(path)

        # No absolute paths
        if os.path.isabs(normalized):
            return False

        # No directory traversal
        if '..' in normalized.split(os.sep):
            return False

        # No dangerous characters
        dangerous_chars = [';', '&', '|', '`', '$', '(', ')', '<', '>', '\n', '\r']
        if any(char in path for char in dangerous_chars):
            return False

        return True

    async def fetch_script_from_github(self, git_url: str, script_path: str, version: str = 'main') -> Optional[str]:
        """
        Fetch a script from GitHub repository

        Args:
            git_url: GitHub repository URL
            script_path: Path to script within repository
            version: Branch/tag to fetch from

        Returns:
            Local path to fetched script, or None if failed
        """
        try:
            # Validate inputs
            if not self._is_safe_git_url(git_url):
                logger.error(f"Unsafe git URL: {git_url}")
                return None

            if not self._is_safe_script_path(script_path):
                logger.error(f"Unsafe script path: {script_path}")
                return None

            if not self._is_safe_git_ref(version):
                logger.error(f"Unsafe git ref: {version}")
                return None

            logger.info(f"📥 Fetching script from {git_url}@{version}:{script_path}")

            # Parse repository name from URL
            parsed_url = urlparse(git_url)
            if 'github.com' not in parsed_url.netloc:
                logger.error(f"Not a GitHub URL: {git_url}")
                return None

            repo_name = Path(parsed_url.path).stem
            if not repo_name:
                logger.error(f"Could not extract repository name from URL: {git_url}")
                return None

            repo_dir = os.path.join(self.cache_dir, repo_name)

            # Clone or update repository
            if os.path.exists(repo_dir):
                # Update existing repository
                logger.info(f"Updating existing repository: {repo_dir}")
                subprocess.run(['git', 'fetch', '--all'], cwd=repo_dir, check=True)
                subprocess.run(['git', 'reset', '--hard', f'origin/{version}'], cwd=repo_dir, check=True)
            else:
                # Clone new repository
                logger.info(f"Cloning repository to: {repo_dir}")
                subprocess.run(['git', 'clone', git_url, repo_dir], check=True)
                subprocess.run(['git', 'checkout', version], cwd=repo_dir, check=True)

            # Verify script exists
            full_script_path = os.path.join(repo_dir, script_path)
            if not os.path.exists(full_script_path):
                logger.error(f"Script not found: {full_script_path}")
                return None

            logger.info(f"✅ Script fetched successfully: {full_script_path}")
            return full_script_path

        except subprocess.SubprocessError as e:
            logger.error(f"Git operation failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Error fetching script from GitHub: {e}")
            return None

    async def validate_script_info(self, script_info: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate git-script information

        Args:
            script_info: Script information dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            # Check required fields
            if script_info.get('type') != 'git-script':
                return False, "Not a git-script type"

            git_url = script_info.get('git')
            if not git_url:
                return False, "Missing 'git' field"

            script_path = script_info.get('script_path')
            if not script_path:
                return False, "Missing 'script_path' field"

            # Validate GitHub URL format
            parsed_url = urlparse(git_url)
            if parsed_url.netloc != 'github.com':
                return False, f"Not a valid GitHub URL: {git_url}"

            # Validate script path (comprehensive security check)
            normalized_path = os.path.normpath(script_path)
            if (os.path.isabs(normalized_path) or
                normalized_path.startswith('..') or
                any(part == '..' for part in normalized_path.split(os.sep))):
                return False, f"Potentially unsafe script path: {script_path}"

            return True, "Valid"

        except Exception as e:
            return False, f"Validation error: {str(e)}"

    async def get_script_candidates(self, search_term: str) -> List[GitScriptCandidate]:
        """
        Get all git-script candidates matching search term

        Args:
            search_term: Term to search for in script names

        Returns:
            List of matching GitScriptCandidate objects
        """
        candidates = []

        try:
            from src.config.llms_parser import load_actions_config

            actions_config = load_actions_config()
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                actions = actions_config['actions']
            elif isinstance(actions_config, list):
                actions = actions_config
            else:
                return candidates

            # Search for matching git-script actions
            for action in actions:
                if (action.get('type') == 'git-script' and
                    search_term.lower() in action.get('name', '').lower()):

                    git_url = action.get('git')
                    script_path = action.get('script_path')
                    version = action.get('version', 'main')

                    if git_url and script_path:
                        candidate = GitScriptCandidate(
                            name=action.get('name'),
                            git_url=git_url,
                            script_path=script_path,
                            version=version
                        )
                        candidates.append(candidate)

        except Exception as e:
            logger.error(f"Error getting script candidates: {e}")

        return candidates


# Global resolver instance with thread safety
_git_script_resolver = None
_resolver_lock = None

def get_git_script_resolver(cache_dir_name: Optional[str] = None, git_timeout: Optional[int] = None) -> GitScriptResolver:
    """Get global git script resolver instance (thread-safe)"""
    global _git_script_resolver, _resolver_lock

    # Initialize lock if not already done
    if _resolver_lock is None:
        import threading
        _resolver_lock = threading.Lock()

    # Thread-safe singleton pattern
    if _git_script_resolver is None:
        with _resolver_lock:
            # Double-check pattern
            if _git_script_resolver is None:
                _git_script_resolver = GitScriptResolver(cache_dir_name=cache_dir_name, git_timeout=git_timeout)

    return _git_script_resolver
