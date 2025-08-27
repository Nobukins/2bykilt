"""
Git Script Path Normalization and Validation Helper

This module provides secure path normalization and validation for git-script execution,
implementing path resolution rules, security checks, and proper error handling as
specified in Issue #25.

Security Policy:
- All paths must resolve within the repository root directory
- Path traversal attempts (..) are denied
- Windows drive letters and UNC paths are denied
- Home directory expansion (~) is only allowed if result stays within repo root
- Only .py files are allowed by default
"""

import os
import platform
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Optional, Tuple, Dict, Any
from src.utils.app_logger import logger


class GitScriptPathError(Exception):
    """Base exception for git script path validation errors"""
    def __init__(self, message: str, error_code: str, path: Optional[str] = None, root: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.path = path
        self.root = root


class GitScriptPathNotFound(GitScriptPathError):
    """Exception raised when a git script path is not found"""
    def __init__(self, message: str, path: Optional[str] = None, root: Optional[str] = None):
        super().__init__(message, "git_script.path_not_found", path, root)


class GitScriptPathDenied(GitScriptPathError):
    """Exception raised when a git script path is denied for security reasons"""
    def __init__(self, message: str, path: Optional[str] = None, root: Optional[str] = None):
        super().__init__(message, "git_script.path.denied", path, root)


class GitScriptPathValidator:
    """
    Validates and normalizes git script paths with security enforcement
    
    Features:
    - Path normalization via pathlib.Path.resolve()
    - Security checks to prevent directory traversal
    - Windows path handling with deny policy
    - Home directory expansion with constraints
    - File extension validation
    """
    
    def __init__(self, repo_root: str, allowed_extensions: Optional[list] = None):
        """
        Initialize path validator
        
        Args:
            repo_root: Repository root directory (execution root)
            allowed_extensions: List of allowed file extensions (default: ['.py'])
        """
        self.repo_root = Path(repo_root).resolve()
        self.allowed_extensions = allowed_extensions or ['.py']
        
    def validate_and_normalize_path(self, user_path: str) -> Tuple[str, Dict[str, Any]]:
        """
        Validate and normalize a user-specified script path
        
        Args:
            user_path: User-specified path from llms.txt
            
        Returns:
            Tuple of (normalized_path, context_info)
            
        Raises:
            GitScriptPathDenied: If path is denied for security reasons
            GitScriptPathNotFound: If path doesn't exist after normalization
        """
        original_path = user_path
        context = {
            "original": original_path,
            "execution_root": str(self.repo_root),
            "platform": platform.system()
        }
        
        try:
            # Step 1: Basic validation
            if not user_path or not user_path.strip():
                raise GitScriptPathDenied(
                    "Empty or whitespace-only path not allowed",
                    path=original_path,
                    root=str(self.repo_root)
                )
            
            user_path = user_path.strip()
            
            # Step 2: Windows-specific security checks
            self._check_windows_paths(user_path)
            
            # Step 3: Handle home directory expansion
            if user_path.startswith('~'):
                user_path = self._expand_home_directory(user_path)
                context["home_expanded"] = True
            else:
                context["home_expanded"] = False
            
            # Step 4: Create Path object and normalize
            try:
                # Use PurePath first to detect problematic patterns
                pure_path = PurePath(user_path)
                
                # Check for suspicious patterns in pure path
                self._check_path_traversal_patterns(pure_path)
                
                # Now create actual Path and resolve
                path_obj = Path(user_path)
                
                # If path is relative, resolve it relative to repo root
                if not path_obj.is_absolute():
                    path_obj = self.repo_root / path_obj
                    context["made_absolute"] = True
                else:
                    context["made_absolute"] = False
                
                # Resolve to canonical form (strict=False allows non-existent files)
                normalized_path = path_obj.resolve(strict=False)
                context["normalized"] = str(normalized_path)
                
            except (OSError, ValueError) as e:
                raise GitScriptPathDenied(
                    f"Invalid path format: {e}",
                    path=original_path,
                    root=str(self.repo_root)
                )
            
            # Step 5: Security validation - ensure within repo root
            try:
                normalized_path.relative_to(self.repo_root)
            except ValueError:
                raise GitScriptPathDenied(
                    f"Path escapes repository root: {normalized_path} not within {self.repo_root}",
                    path=original_path,
                    root=str(self.repo_root)
                )
            
            # Step 6: Extension validation
            if self.allowed_extensions:
                if normalized_path.suffix.lower() not in [ext.lower() for ext in self.allowed_extensions]:
                    raise GitScriptPathDenied(
                        f"File extension '{normalized_path.suffix}' not allowed. Allowed: {self.allowed_extensions}",
                        path=original_path,
                        root=str(self.repo_root)
                    )
            
            # Step 7: Check if file exists
            if not normalized_path.exists():
                raise GitScriptPathNotFound(
                    f"Script file not found: {normalized_path}",
                    path=original_path,
                    root=str(self.repo_root)
                )
            
            if not normalized_path.is_file():
                raise GitScriptPathDenied(
                    f"Path is not a file: {normalized_path}",
                    path=original_path,
                    root=str(self.repo_root)
                )
            
            final_path = str(normalized_path)
            context["final_path"] = final_path
            context["validation_success"] = True
            
            return final_path, context
            
        except GitScriptPathError:
            # Re-raise our specific exceptions
            raise
        except Exception as e:
            # Catch any unexpected errors
            raise GitScriptPathDenied(
                f"Unexpected error during path validation: {e}",
                path=original_path,
                root=str(self.repo_root)
            )
    
    def _check_windows_paths(self, path: str) -> None:
        """Check for Windows-specific path patterns that should be denied"""
        # Check for drive letters (C:, D:, etc.)
        if len(path) >= 2 and path[1] == ':' and path[0].isalpha():
            raise GitScriptPathDenied(
                f"Windows drive letter paths are not allowed: {path}",
                path=path
            )
        
        # Check for Windows-specific path prefixes first (more specific)
        windows_prefixes = ['\\\\?\\', '\\\\.\\']
        for prefix in windows_prefixes:
            if path.startswith(prefix):
                raise GitScriptPathDenied(
                    f"Windows extended path syntax not allowed: {path}",
                    path=path
                )
        
        # Check for UNC paths (\\server\share) - but not the extended syntax we already checked
        if path.startswith('\\\\') or path.startswith('//'):
            raise GitScriptPathDenied(
                f"UNC paths are not allowed: {path}",
                path=path
            )
    
    def _check_path_traversal_patterns(self, pure_path: PurePath) -> None:
        """Check for path traversal patterns in the pure path"""
        path_parts = pure_path.parts
        
        # Check for .. in any part
        if '..' in path_parts:
            raise GitScriptPathDenied(
                f"Path traversal patterns ('..') are not allowed: {pure_path}",
                path=str(pure_path)
            )
        
        # Check for absolute paths that could escape
        if pure_path.is_absolute() and platform.system() != "Windows":
            # On Unix-like systems, be extra careful with absolute paths
            if str(pure_path).startswith('/'):
                # Allow absolute paths only if they would resolve within repo root
                # This will be validated later in the main flow
                pass
    
    def _expand_home_directory(self, path: str) -> str:
        """
        Expand home directory with security constraints
        
        Policy: Home expansion is only allowed if the final resolved path
        would be within the repository root directory.
        """
        try:
            expanded = os.path.expanduser(path)
            
            # Create a temporary path object to check if it would be within repo root
            temp_path = Path(expanded)
            if not temp_path.is_absolute():
                temp_path = self.repo_root / temp_path
            
            temp_resolved = temp_path.resolve(strict=False)
            
            # Check if expanded path would be within repo root
            try:
                temp_resolved.relative_to(self.repo_root)
                return expanded
            except ValueError:
                raise GitScriptPathDenied(
                    f"Home directory expansion would escape repository root: ~ -> {expanded}",
                    path=path,
                    root=str(self.repo_root)
                )
                
        except Exception as e:
            raise GitScriptPathDenied(
                f"Failed to expand home directory: {e}",
                path=path,
                root=str(self.repo_root)
            )


def validate_git_script_path(repo_root: str, user_path: str, 
                           allowed_extensions: Optional[list] = None) -> Tuple[str, Dict[str, Any]]:
    """
    Convenience function for git script path validation
    
    Args:
        repo_root: Repository root directory
        user_path: User-specified path
        allowed_extensions: List of allowed extensions (default: ['.py'])
        
    Returns:
        Tuple of (normalized_path, context_info)
        
    Raises:
        GitScriptPathError: For validation failures
    """
    validator = GitScriptPathValidator(repo_root, allowed_extensions)
    return validator.validate_and_normalize_path(user_path)