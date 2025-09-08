"""
GitScriptPathValidator - Enhanced path validation system for Issue #25
Provides security-first path validation, normalization, and error handling for git-script execution.
"""
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class GitScriptPathValidationResult:
    """Path validation result"""
    is_valid: bool
    normalized_path: Optional[str]
    error_code: Optional[str]
    error_message: Optional[str]
    security_warnings: list[str]


class GitScriptPathNotFound(Exception):
    """Exception raised when git script path is not found"""
    def __init__(self, path: str, error_code: str = "git_script.path_not_found"):
        self.path = path
        self.error_code = error_code
        super().__init__(f"Git script path not found: {path}")


class GitScriptPathDenied(Exception):
    """Exception raised when git script path is denied for security reasons"""
    def __init__(self, path: str, reason: str, error_code: str = "git_script.path.denied"):
        self.path = path
        self.reason = reason
        self.error_code = error_code
        super().__init__(f"Git script path denied: {path} - {reason}")


class GitScriptPathValidator:
    """
    Enhanced path validation system for git-script execution
    
    Features:
    - Path traversal prevention
    - Windows security validation
    - Extension validation
    - Repository root enforcement
    - Home directory safety
    """
    
    def __init__(self, repo_root: str, allowed_extensions: Optional[list[str]] = None):
        """
        Initialize path validator
        
        Args:
            repo_root: Root directory of the git repository
            allowed_extensions: List of allowed file extensions (default: ['.py'])
        """
        self.repo_root = Path(repo_root).resolve()
        self.allowed_extensions = allowed_extensions or ['.py']
        
        logger.info(f"🔒 GitScriptPathValidator initialized for repo: {self.repo_root}")
    
    def validate_and_normalize_path(self, user_path: str) -> GitScriptPathValidationResult:
        """
        Validate and normalize a user-provided path
        
        Args:
            user_path: User-provided path string
            
        Returns:
            ValidationResult with normalized path or error details
        """
        logger.info(f"🔍 Validating path: {user_path}")
        
        security_warnings = []
        
        try:
            # Step 1: Basic path resolution
            path = Path(user_path)
            
            # Handle home directory expansion
            if str(path).startswith('~'):
                expanded_path = path.expanduser()
                if not str(expanded_path).startswith(str(self.repo_root)):
                    raise GitScriptPathDenied(
                        user_path, 
                        "Home directory expansion would escape repository root",
                        "git_script.path.home_escape"
                    )
                path = expanded_path
                security_warnings.append("Home directory expansion used")
            
            # Step 2: Resolve the path
            resolved_path = path.resolve()
            
            # Step 3: Repository root enforcement
            if not str(resolved_path).startswith(str(self.repo_root)):
                raise GitScriptPathDenied(
                    user_path,
                    "Path escapes repository root",
                    "git_script.path.root_escape"
                )
            
            # Step 4: Path traversal prevention
            try:
                # Check if path contains .. components that would escape
                resolved_path.relative_to(self.repo_root)
            except ValueError:
                raise GitScriptPathDenied(
                    user_path,
                    "Path traversal attempt detected",
                    "git_script.path.traversal"
                )
            
            # Step 5: Windows security checks
            path_str = str(resolved_path)
            if os.name == 'nt':  # Windows
                # Block drive letters
                if len(path_str) >= 3 and path_str[1:3] == ':\\':
                    raise GitScriptPathDenied(
                        user_path,
                        "Windows drive letter not allowed",
                        "git_script.path.windows_drive"
                    )
                
                # Block UNC paths
                if path_str.startswith('\\\\'):
                    raise GitScriptPathDenied(
                        user_path,
                        "Windows UNC path not allowed",
                        "git_script.path.windows_unc"
                    )
            
            # Step 6: Extension validation
            if self.allowed_extensions:
                file_extension = resolved_path.suffix.lower()
                if file_extension not in [ext.lower() for ext in self.allowed_extensions]:
                    raise GitScriptPathDenied(
                        user_path,
                        f"File extension '{file_extension}' not allowed. Allowed: {self.allowed_extensions}",
                        "git_script.path.extension_denied"
                    )
            
            # Step 7: File existence check
            if not resolved_path.exists():
                raise GitScriptPathNotFound(user_path)
            
            if not resolved_path.is_file():
                raise GitScriptPathDenied(
                    user_path,
                    "Path is not a file",
                    "git_script.path.not_file"
                )
            
            # Success
            normalized_path = str(resolved_path)
            logger.info(f"✅ Path validated and normalized: {user_path} -> {normalized_path}")
            
            if security_warnings:
                logger.warning(f"⚠️ Security warnings for {user_path}: {security_warnings}")
            
            return GitScriptPathValidationResult(
                is_valid=True,
                normalized_path=normalized_path,
                error_code=None,
                error_message=None,
                security_warnings=security_warnings
            )
            
        except GitScriptPathNotFound as e:
            logger.error(f"❌ Path not found: {user_path}")
            return GitScriptPathValidationResult(
                is_valid=False,
                normalized_path=None,
                error_code=e.error_code,
                error_message=str(e),
                security_warnings=security_warnings
            )
            
        except GitScriptPathDenied as e:
            logger.error(f"❌ Path denied: {user_path} - {e.reason}")
            return GitScriptPathValidationResult(
                is_valid=False,
                normalized_path=None,
                error_code=e.error_code,
                error_message=str(e),
                security_warnings=security_warnings
            )
            
        except Exception as e:
            logger.error(f"❌ Unexpected error validating path {user_path}: {e}")
            return GitScriptPathValidationResult(
                is_valid=False,
                normalized_path=None,
                error_code="git_script.path.validation_error",
                error_message=f"Path validation failed: {str(e)}",
                security_warnings=security_warnings
            )
    
    def get_validation_info(self) -> Dict[str, Any]:
        """Get validator configuration information"""
        return {
            "repo_root": str(self.repo_root),
            "allowed_extensions": self.allowed_extensions,
            "platform": os.name,
            "is_windows": os.name == 'nt'
        }


def validate_git_script_path(repo_root: str, user_path: str, allowed_extensions: Optional[list[str]] = None) -> Tuple[str, GitScriptPathValidationResult]:
    """
    Convenience function to validate a git script path
    
    Args:
        repo_root: Root directory of the git repository
        user_path: User-provided path string
        allowed_extensions: List of allowed file extensions
        
    Returns:
        Tuple of (normalized_path, validation_result)
        
    Raises:
        GitScriptPathNotFound: If path is not found
        GitScriptPathDenied: If path is denied for security reasons
    """
    validator = GitScriptPathValidator(repo_root, allowed_extensions)
    result = validator.validate_and_normalize_path(user_path)
    
    if not result.is_valid:
        if result.error_code == "git_script.path_not_found":
            raise GitScriptPathNotFound(user_path)
        else:
            raise GitScriptPathDenied(user_path, result.error_message or "Unknown security violation")
    
    return result.normalized_path, result
