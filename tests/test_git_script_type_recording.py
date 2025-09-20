"""
Test git-script type recording functionality
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class TestGitScriptTypeRecording:
    """Test recording functionality for git-script type"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.artifacts_dir = self.test_dir / "artifacts"
        self.artifacts_dir.mkdir(parents=True)

        # Mock git repository structure
        self.mock_repo_dir = self.test_dir / "mock_repo"
        self.mock_repo_dir.mkdir()

        # Create a mock test script in the mock repo
        self.mock_script_path = self.mock_repo_dir / "test_git_script.py"
        self.mock_script_path.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.git_script_test
def test_git_script_recording(page: Page):
    """Test git script that should generate recording"""
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Recording path: {recording_path}")

    # Navigate to a simple page
    page.goto("https://example.com")
    page.wait_for_load_state("networkidle")

    # Perform some actions
    page.click("text=More information")
    page.wait_for_load_state("networkidle")

    # Verify recording path is set
    assert recording_path is not None
    assert "artifacts" in recording_path
    assert "videos" in recording_path
''')

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    @patch('src.script.script_manager.clone_git_repo')
    @patch('src.script.script_manager.process_execution')
    def test_git_script_type_recording_path(self, mock_process_execution, mock_clone_repo):
        """Test that git-script type uses correct recording path"""
        # Mock the git clone
        mock_clone_repo.return_value = str(self.mock_repo_dir)

        # Mock the process execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process_execution.return_value = (mock_process, ["Test output"])

        # Test script info for git-script
        script_info = {
            'type': 'git-script',
            'name': 'test_git_script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'test_git_script.py',
            'command': 'python -m pytest test_git_script.py'
        }

        params = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "git-script-test-art" / "videos")

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('os.environ', {'BYKILT_USE_NEW_METHOD': 'false'}):  # Use legacy method for testing

            # Execute the script
            result, script_path = run_script(
                script_info=script_info,
                params=params,
                headless=True,
                save_recording_path=save_recording_path
            )

        # Verify the result
        assert result is not None
        assert "Script executed successfully" in result

        # Verify that process_execution was called with correct environment
        call_args = mock_process_execution.call_args
        assert call_args is not None

        # Check that RECORDING_PATH environment variable was set correctly
        env_vars = call_args[1]['env']  # kwargs
        assert 'RECORDING_PATH' in env_vars

        # Verify the recording path uses unified resolver
        expected_recording_path = str(create_or_get_recording_dir(save_recording_path))
        assert env_vars['RECORDING_PATH'] == expected_recording_path

        # Verify the path contains artifacts and videos
        assert "artifacts" in expected_recording_path
        assert "videos" in expected_recording_path

    @patch('src.script.script_manager.clone_git_repo')
    @patch('src.script.script_manager.process_execution')
    def test_git_script_with_custom_recording_path(self, mock_process_execution, mock_clone_repo):
        """Test git-script with custom recording path"""
        # Mock the git clone
        mock_clone_repo.return_value = str(self.mock_repo_dir)

        # Mock the process execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process_execution.return_value = (mock_process, ["Test output"])

        custom_path = str(self.artifacts_dir / "custom" / "git" / "videos")

        script_info = {
            'type': 'git-script',
            'name': 'test_custom_git',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'test_git_script.py',
            'command': 'python -m pytest test_git_script.py'
        }

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('os.environ', {'BYKILT_USE_NEW_METHOD': 'false'}):

            # Execute with custom recording path
            result, script_path = run_script(
                script_info=script_info,
                params={},
                headless=True,
                save_recording_path=custom_path
            )

            # Verify the recording path was resolved correctly
            call_args = mock_process_execution.call_args
            env_vars = call_args[1]['env']
            expected_path = str(create_or_get_recording_dir(custom_path))
            assert env_vars['RECORDING_PATH'] == expected_path

    @patch('src.script.script_manager.clone_git_repo')
    def test_git_script_script_not_found(self, mock_clone_repo):
        """Test git-script when script file doesn't exist"""
        # Mock the git clone
        mock_clone_repo.return_value = str(self.mock_repo_dir)

        # Remove the mock script
        self.mock_script_path.unlink()

        script_info = {
            'type': 'git-script',
            'name': 'test_missing_script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'missing_script.py'
        }

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('os.environ', {'BYKILT_USE_NEW_METHOD': 'false'}):

            # Execute the script - should fail
            result, script_path = run_script(
                script_info=script_info,
                params={},
                headless=True
            )

            # Verify the error
            assert result is not None
            assert "Script not found" in result

    def test_git_script_recording_path_resolution(self):
        """Test that git-script recording path resolution works correctly"""
        test_paths = [
            str(self.artifacts_dir / "runs" / "git-test1-art" / "videos"),
            str(self.artifacts_dir / "runs" / "git-test2-art" / "videos"),
            str(self.artifacts_dir / "git" / "custom" / "videos"),
        ]

        for test_path in test_paths:
            resolved = create_or_get_recording_dir(test_path)
            assert resolved.exists()
            resolved_str = str(resolved)

            # Should contain artifacts or videos in the path
            assert "artifacts" in resolved_str or "videos" in resolved_str

    def test_git_script_mock_repo_setup(self):
        """Test that mock repository is set up correctly"""
        assert self.mock_repo_dir.exists()
        assert self.mock_script_path.exists()

        content = self.mock_script_path.read_text()
        assert "test_git_script_recording" in content
        assert "RECORDING_PATH" in content
        assert "https://example.com" in content