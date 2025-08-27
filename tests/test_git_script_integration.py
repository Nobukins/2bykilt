#!/usr/bin/env python3
"""
Integration test for GIT_SCRIPT_V2 feature flag
Tests the integration between script_manager.py and the new path validation
"""

import os
import sys
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, AsyncMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# Import what we need from script_manager
from src.script.script_manager import execute_git_script_new_method


class TestGitScriptIntegration:
    """Test integration of GIT_SCRIPT_V2 with script_manager.py"""
    
    @pytest.fixture
    def temp_repo(self):
        """Create a temporary repository structure"""
        with tempfile.TemporaryDirectory() as temp_dir:
            repo_root = Path(temp_dir) / "test_repo"
            repo_root.mkdir()
            
            # Create a test Python script
            script_content = '''#!/usr/bin/env python3
print("Test script executed successfully")
'''
            (repo_root / "test_script.py").write_text(script_content)
            (repo_root / "subdir").mkdir()
            (repo_root / "subdir" / "nested_script.py").write_text(script_content)
            
            yield str(repo_root)
    
    @pytest.mark.asyncio
    async def test_v2_validation_enabled_success(self, temp_repo):
        """Test GIT_SCRIPT_V2=true with valid path"""
        
        # Mock the clone_git_repo function to return our temp repo
        with patch('src.script.script_manager.clone_git_repo') as mock_clone:
            mock_clone.return_value = temp_repo
            
            # Mock the automator classes
            with patch('src.script.script_manager.EdgeAutomator') as mock_edge:
                mock_automator = AsyncMock()
                mock_automator.validate_source_profile.return_value = True  # Sync method
                mock_automator.execute_git_script_workflow = AsyncMock(return_value={
                    "success": True,
                    "selenium_profile": "/tmp/test_profile"
                })
                mock_edge.return_value = mock_automator
                
                # Set environment variables
                with patch.dict(os.environ, {'GIT_SCRIPT_V2': 'true'}):
                    script_info = {
                        'git': 'https://github.com/test/repo.git',
                        'script_path': 'test_script.py',
                        'version': 'main'
                    }
                    
                    result, path = await execute_git_script_new_method(
                        script_info=script_info,
                        params={},
                        headless=True,
                        save_recording_path=None,
                        browser_type='edge'
                    )
                    
                    assert "executed successfully" in result
                    assert path == str(Path(temp_repo) / "test_script.py")
    
    @pytest.mark.asyncio 
    async def test_v2_validation_enabled_path_traversal_denied(self, temp_repo):
        """Test GIT_SCRIPT_V2=true with path traversal attempt"""
        
        # Mock the clone_git_repo function
        with patch('src.script.script_manager.clone_git_repo') as mock_clone:
            mock_clone.return_value = temp_repo
            
            # Set environment variables
            with patch.dict(os.environ, {'GIT_SCRIPT_V2': 'true'}):
                script_info = {
                    'git': 'https://github.com/test/repo.git',
                    'script_path': '../escape.py',  # Path traversal attempt
                    'version': 'main'
                }
                
                result, path = await execute_git_script_new_method(
                    script_info=script_info,
                    params={},
                    headless=True,
                    save_recording_path=None,
                    browser_type='edge'
                )
                
                assert "Path validation failed" in result
                assert path is None
    
    @pytest.mark.asyncio
    async def test_v2_validation_disabled_legacy_behavior(self, temp_repo):
        """Test GIT_SCRIPT_V2=false uses legacy validation"""
        
        # Mock the clone_git_repo function
        with patch('src.script.script_manager.clone_git_repo') as mock_clone:
            mock_clone.return_value = temp_repo
            
            # Mock the automator classes  
            with patch('src.script.script_manager.EdgeAutomator') as mock_edge:
                mock_automator = AsyncMock()
                mock_automator.validate_source_profile.return_value = True  # Sync method
                mock_automator.execute_git_script_workflow = AsyncMock(return_value={
                    "success": True,
                    "selenium_profile": "/tmp/test_profile"
                })
                mock_edge.return_value = mock_automator
                
                # Set environment variables - disable V2
                with patch.dict(os.environ, {'GIT_SCRIPT_V2': 'false'}):
                    script_info = {
                        'git': 'https://github.com/test/repo.git',
                        'script_path': 'test_script.py',
                        'version': 'main'
                    }
                    
                    result, path = await execute_git_script_new_method(
                        script_info=script_info,
                        params={},
                        headless=True,
                        save_recording_path=None,
                        browser_type='edge'
                    )
                    
                    assert "executed successfully" in result
                    assert path == str(Path(temp_repo) / "test_script.py")
    
    @pytest.mark.asyncio
    async def test_v2_validation_missing_file(self, temp_repo):
        """Test GIT_SCRIPT_V2=true with missing file"""
        
        # Mock the clone_git_repo function
        with patch('src.script.script_manager.clone_git_repo') as mock_clone:
            mock_clone.return_value = temp_repo
            
            # Set environment variables
            with patch.dict(os.environ, {'GIT_SCRIPT_V2': 'true'}):
                script_info = {
                    'git': 'https://github.com/test/repo.git',
                    'script_path': 'nonexistent.py',
                    'version': 'main'
                }
                
                result, path = await execute_git_script_new_method(
                    script_info=script_info,
                    params={},
                    headless=True,
                    save_recording_path=None,
                    browser_type='edge'
                )
                
                assert "Path validation failed" in result
                assert "not found" in result.lower()
                assert path is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])