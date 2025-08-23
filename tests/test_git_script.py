"""
Test for git-script functionality in BrowserAutomationManager
"""
import pytest
import os
import tempfile
import logging
from unittest.mock import patch, MagicMock
from src.modules.automation_manager import BrowserAutomationManager

# Setup logging for tests
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TestGitScriptExecution:
    """Test class for git-script execution functionality"""
    
    def setup_method(self):
        """Setup test environment"""
        self.manager = BrowserAutomationManager()
        
    def test_git_script_action_detection(self):
        """Test that git-script actions are properly detected and routed"""
        # Sample git-script action from llms.txt
        action = {
            'name': 'test-git-script',
            'type': 'git-script',
            'git': 'https://github.com/Nobukins/sample-tests.git',
            'script_path': 'search_script.py',
            'version': 'main',
            'command': 'pytest ${script_path} --query ${params.query}',
            'timeout': 120,
            'slowmo': 1000,
            'params': [
                {
                    'name': 'query',
                    'required': True,
                    'type': 'string',
                    'description': 'Search query to execute'
                }
            ]
        }
        
        # Register the action
        self.manager.register_action(action)
        
        # Verify action is registered
        assert 'test-git-script' in self.manager.actions
        assert self.manager.actions['test-git-script']['type'] == 'git-script'
        
    @patch('src.script.script_manager.run_script')
    @patch('asyncio.run')
    def test_git_script_execution_success(self, mock_asyncio_run, mock_run_script):
        """Test successful git-script execution"""
        # Mock successful execution
        mock_asyncio_run.return_value = ("Script executed successfully", "/tmp/script.py")
        
        # Sample git-script action
        action = {
            'name': 'test-git-script',
            'type': 'git-script',
            'git': 'https://github.com/Nobukins/sample-tests.git',
            'script_path': 'search_script.py',
            'version': 'main',
            'command': 'pytest ${script_path} --query ${params.query}',
            'timeout': 120,
            'slowmo': 1000
        }
        
        # Register and execute the action
        self.manager.register_action(action)
        
        # Capture logs to verify git_script: start message
        with patch('src.modules.automation_manager.logger') as mock_logger:
            result = self.manager.execute_action('test-git-script', query='test query')
            
            # Verify execution result
            assert result is True
            
            # Verify required log messages
            mock_logger.info.assert_any_call("git_script: start - Executing git-script action: test-git-script")
            mock_logger.info.assert_any_call("git_script: cloning repository https://github.com/Nobukins/sample-tests.git")
            mock_logger.info.assert_any_call("git_script: executing script search_script.py")
            mock_logger.info.assert_any_call("git_script: completed successfully - Script executed successfully")
    
    @patch('src.script.script_manager.run_script')
    @patch('asyncio.run')  
    def test_git_script_execution_failure(self, mock_asyncio_run, mock_run_script):
        """Test git-script execution failure handling"""
        # Mock failed execution
        mock_asyncio_run.return_value = ("Script execution failed with exit code 1", None)
        
        action = {
            'name': 'test-git-script-fail',
            'type': 'git-script',
            'git': 'https://github.com/Nobukins/sample-tests.git',
            'script_path': 'search_script.py',
            'command': 'pytest ${script_path} --query ${params.query}'
        }
        
        self.manager.register_action(action)
        
        with patch('src.modules.automation_manager.logger') as mock_logger:
            result = self.manager.execute_action('test-git-script-fail', query='test query')
            
            # Verify execution failed
            assert result is False
            
            # Verify error logging
            mock_logger.error.assert_any_call("git_script: failed - Script execution failed with exit code 1")
    
    def test_git_script_missing_required_fields(self):
        """Test git-script validation for missing required fields"""
        # Action missing git field
        action_missing_git = {
            'name': 'invalid-git-script-1',
            'type': 'git-script',
            'script_path': 'search_script.py',
            'command': 'pytest ${script_path}'
        }
        
        # Action missing script_path field
        action_missing_script_path = {
            'name': 'invalid-git-script-2', 
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'command': 'pytest ${script_path}'
        }
        
        # Action missing command field
        action_missing_command = {
            'name': 'invalid-git-script-3',
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'search_script.py'
        }
        
        self.manager.register_action(action_missing_git)
        self.manager.register_action(action_missing_script_path)
        self.manager.register_action(action_missing_command)
        
        with patch('src.modules.automation_manager.logger') as mock_logger:
            # Test missing git field
            result1 = self.manager.execute_action('invalid-git-script-1')
            assert result1 is False
            mock_logger.error.assert_any_call("git-script action requires 'git' and 'script_path' fields")
            
            # Test missing script_path field
            result2 = self.manager.execute_action('invalid-git-script-2')
            assert result2 is False
            
            # Test missing command field  
            result3 = self.manager.execute_action('invalid-git-script-3')
            assert result3 is False
            mock_logger.error.assert_any_call("git-script action requires 'command' field")

    def test_git_script_parameter_validation(self):
        """Test parameter validation for git-script actions"""
        action = {
            'name': 'test-params',
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'test.py',
            'command': 'pytest ${script_path} --query ${params.query}',
            'params': [
                {
                    'name': 'query',
                    'required': True,
                    'type': 'string'
                }
            ]
        }
        
        self.manager.register_action(action)
        
        # Test missing required parameter
        with patch('src.modules.automation_manager.logger') as mock_logger:
            result = self.manager.execute_action('test-params')  # Missing required 'query' param
            assert result is False
            mock_logger.error.assert_any_call("Missing required parameters for action 'test-params': query")