#!/usr/bin/env python3
"""
Test suite for git_script path validation (Issue #25)

Tests path normalization, security validation, Windows path handling,
and all the requirements specified in Issue #25 checklist.
"""

import os
import sys
import tempfile
import pytest
import platform
from pathlib import Path
from unittest.mock import patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.runner.git_script_path import (
    GitScriptPathValidator,
    GitScriptPathError,
    GitScriptPathNotFound,
    GitScriptPathDenied,
    validate_git_script_path
)


class TestGitScriptPathValidation:
    """Test git script path validation functionality"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "test_repo"
            repo_root.mkdir()
            
            # Create test files
            (repo_root / "script.py").write_text("# Test script")
            (repo_root / "subdir").mkdir()
            (repo_root / "subdir" / "nested_script.py").write_text("# Nested script")
            (repo_root / "not_python.txt").write_text("Not a Python file")
            
            yield str(repo_root)
    
    def test_simple_relative_path(self, temp_repo):
        """Test basic relative path resolution"""
        validator = GitScriptPathValidator(temp_repo)
        
        path, context = validator.validate_and_normalize_path("script.py")
        
        assert path == str(Path(temp_repo) / "script.py")
        assert context["original"] == "script.py"
        assert context["made_absolute"] is True
        assert context["validation_success"] is True
    
    def test_nested_relative_path(self, temp_repo):
        """Test nested relative path resolution"""
        validator = GitScriptPathValidator(temp_repo)
        
        path, context = validator.validate_and_normalize_path("subdir/nested_script.py")
        
        assert path == str(Path(temp_repo) / "subdir" / "nested_script.py")
        assert context["original"] == "subdir/nested_script.py"
        assert context["validation_success"] is True
    
    def test_current_directory_path(self, temp_repo):
        """Test ./ path resolution"""
        validator = GitScriptPathValidator(temp_repo)
        
        path, context = validator.validate_and_normalize_path("./script.py")
        
        assert path == str(Path(temp_repo) / "script.py")
        assert context["original"] == "./script.py"
        assert context["validation_success"] is True
    
    def test_path_traversal_denied(self, temp_repo):
        """Test that .. path traversal is denied"""
        validator = GitScriptPathValidator(temp_repo)
        
        with pytest.raises(GitScriptPathDenied) as exc_info:
            validator.validate_and_normalize_path("../escape.py")
        
        assert "path traversal" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "git_script.path.denied"
    
    def test_absolute_path_outside_repo_denied(self, temp_repo):
        """Test that absolute paths outside repo are denied"""
        validator = GitScriptPathValidator(temp_repo)
        
        # Create a file outside the repo
        with tempfile.NamedTemporaryFile(suffix=".py", delete=False) as f:
            outside_path = f.name
        
        try:
            with pytest.raises(GitScriptPathDenied) as exc_info:
                validator.validate_and_normalize_path(outside_path)
            
            assert "escapes repository root" in str(exc_info.value)
            assert exc_info.value.error_code == "git_script.path.denied"
        finally:
            os.unlink(outside_path)
    
    def test_missing_file(self, temp_repo):
        """Test that missing files raise GitScriptPathNotFound"""
        validator = GitScriptPathValidator(temp_repo)
        
        with pytest.raises(GitScriptPathNotFound) as exc_info:
            validator.validate_and_normalize_path("nonexistent.py")
        
        assert "not found" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "git_script.path_not_found"
    
    def test_extension_validation(self, temp_repo):
        """Test file extension validation"""
        validator = GitScriptPathValidator(temp_repo)
        
        with pytest.raises(GitScriptPathDenied) as exc_info:
            validator.validate_and_normalize_path("not_python.txt")
        
        assert "extension" in str(exc_info.value).lower()
        assert ".py" in str(exc_info.value)
        assert exc_info.value.error_code == "git_script.path.denied"
    
    def test_custom_extensions(self, temp_repo):
        """Test custom allowed extensions"""
        validator = GitScriptPathValidator(temp_repo, allowed_extensions=['.txt', '.py'])
        
        # Should work with custom extension
        path, context = validator.validate_and_normalize_path("not_python.txt")
        assert path == str(Path(temp_repo) / "not_python.txt")
    
    def test_empty_path(self, temp_repo):
        """Test empty path validation"""
        validator = GitScriptPathValidator(temp_repo)
        
        with pytest.raises(GitScriptPathDenied):
            validator.validate_and_normalize_path("")
        
        with pytest.raises(GitScriptPathDenied):
            validator.validate_and_normalize_path("   ")
    
    @pytest.mark.skipif(platform.system() == "Windows", reason="Unix-specific test")
    def test_home_directory_expansion_allowed(self, temp_repo):
        """Test home directory expansion when result is within repo"""
        validator = GitScriptPathValidator(temp_repo)
        
        # Create a symbolic scenario where ~ expands to something within repo
        # This is a bit artificial but tests the logic
        with patch('os.path.expanduser') as mock_expand:
            mock_expand.return_value = str(Path(temp_repo) / "script.py")
            
            path, context = validator.validate_and_normalize_path("~/script.py")
            
            assert context["home_expanded"] is True
            assert path == str(Path(temp_repo) / "script.py")
    
    def test_home_directory_expansion_denied(self, temp_repo):
        """Test home directory expansion when result is outside repo"""
        validator = GitScriptPathValidator(temp_repo)
        
        with pytest.raises(GitScriptPathDenied) as exc_info:
            validator.validate_and_normalize_path("~/outside_repo.py")
        
        assert "escape" in str(exc_info.value).lower()
        assert exc_info.value.error_code == "git_script.path.denied"


class TestWindowsPathHandling:
    """Test Windows-specific path handling"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "test_repo"
            repo_root.mkdir()
            (repo_root / "script.py").write_text("# Test script")
            yield str(repo_root)
    
    def test_drive_letter_denied(self, temp_repo):
        """Test that Windows drive letter paths are denied"""
        validator = GitScriptPathValidator(temp_repo)
        
        test_paths = ["C:\\script.py", "D:\\folder\\script.py", "Z:\\script.py"]
        
        for path in test_paths:
            with pytest.raises(GitScriptPathDenied) as exc_info:
                validator.validate_and_normalize_path(path)
            
            assert "drive letter" in str(exc_info.value).lower()
            assert exc_info.value.error_code == "git_script.path.denied"
    
    def test_unc_paths_denied(self, temp_repo):
        """Test that UNC paths are denied"""
        validator = GitScriptPathValidator(temp_repo)
        
        test_paths = [
            "\\\\server\\share\\script.py",
            "//server/share/script.py",
            "\\\\?\\C:\\script.py",
            "\\\\.\\pipe\\script.py"
        ]
        
        for path in test_paths:
            with pytest.raises(GitScriptPathDenied) as exc_info:
                validator.validate_and_normalize_path(path)
            
            assert exc_info.value.error_code == "git_script.path.denied"
    
    def test_windows_extended_syntax_denied(self, temp_repo):
        """Test that Windows extended path syntax is denied"""
        validator = GitScriptPathValidator(temp_repo)
        
        test_paths = [
            "\\\\?\\C:\\script.py",
            "\\\\.\\C:\\script.py"
        ]
        
        for path in test_paths:
            with pytest.raises(GitScriptPathDenied) as exc_info:
                validator.validate_and_normalize_path(path)
            
            assert "extended path" in str(exc_info.value).lower()


class TestConvenienceFunction:
    """Test the convenience function validate_git_script_path"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "test_repo"
            repo_root.mkdir()
            (repo_root / "script.py").write_text("# Test script")
            yield str(repo_root)
    
    def test_convenience_function_success(self, temp_repo):
        """Test the convenience function with valid path"""
        path, context = validate_git_script_path(temp_repo, "script.py")
        
        assert path == str(Path(temp_repo) / "script.py")
        assert context["validation_success"] is True
    
    def test_convenience_function_failure(self, temp_repo):
        """Test the convenience function with invalid path"""
        with pytest.raises(GitScriptPathDenied):
            validate_git_script_path(temp_repo, "../escape.py")


# Regression tests as required by Issue #25
class TestGitScriptRegression:
    """Regression tests for Issue #25 requirements"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "test_repo"
            repo_root.mkdir()
            (repo_root / "script.py").write_text("# Test script")
            (repo_root / "subdir").mkdir()
            (repo_root / "subdir" / "nested.py").write_text("# Nested script")
            yield str(repo_root)
    
    def test_git_script_relative(self, temp_repo):
        """Regression test: test_git_script_relative"""
        validator = GitScriptPathValidator(temp_repo)
        
        # Test various relative path forms
        relative_paths = [
            "script.py",
            "./script.py", 
            "subdir/nested.py",
            "./subdir/nested.py"
        ]
        
        for path in relative_paths:
            result_path, context = validator.validate_and_normalize_path(path)
            assert Path(result_path).exists()
            assert context["validation_success"] is True
    
    def test_git_script_missing(self, temp_repo):
        """Regression test: test_git_script_missing"""
        validator = GitScriptPathValidator(temp_repo)
        
        missing_paths = [
            "nonexistent.py",
            "missing/path.py",
            "subdir/missing.py"
        ]
        
        for path in missing_paths:
            with pytest.raises(GitScriptPathNotFound) as exc_info:
                validator.validate_and_normalize_path(path)
            
            assert exc_info.value.error_code == "git_script.path_not_found"
    
    def test_git_script_windows(self, temp_repo):
        """Regression test: test_git_script_windows"""
        validator = GitScriptPathValidator(temp_repo)
        
        # Test all Windows-specific patterns
        windows_paths = [
            "C:\\script.py",
            "D:\\folder\\script.py", 
            "\\\\server\\share\\script.py",
            "\\\\?\\C:\\script.py",
            "\\\\.\\pipe\\script.py"
        ]
        
        for path in windows_paths:
            with pytest.raises(GitScriptPathDenied) as exc_info:
                validator.validate_and_normalize_path(path)
            
            assert exc_info.value.error_code == "git_script.path.denied"


if __name__ == "__main__":
    pytest.main([__file__])