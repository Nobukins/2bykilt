"""
Test action_runner_template type recording functionality
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class TestActionRunnerTemplateTypeRecording:
    """Test recording functionality for action_runner_template type"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.myscript_dir = self.test_dir / "myscript"
        self.artifacts_dir = self.test_dir / "artifacts"
        self.myscript_dir.mkdir(parents=True)
        self.artifacts_dir.mkdir(parents=True)

        # Create a mock action script
        self.action_script_path = self.myscript_dir / "test_action.py"
        self.action_script_path.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.action_test
def test_action_runner_recording(page: Page):
    """Test action runner that should generate recording"""
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

    @patch('src.script.script_manager.process_execution')
    def test_action_runner_template_type_recording_path(self, mock_process_execution):
        """Test that action_runner_template type uses correct recording path"""
        # Mock the process execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process_execution.return_value = (mock_process, ["Test output"])

        # Test script info for action_runner_template
        script_info = {
            'type': 'action_runner_template',
            'name': 'test_action_runner',
            'action_script': 'test_action.py',
            'command': 'python -m pytest test_action.py'
        }

        params = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "action-runner-test-art" / "videos")

        with patch('os.getcwd', return_value=str(self.test_dir)):
            # Execute the script
            result, script_path = run_script(
                script_info=script_info,
                params=params,
                headless=True,
                save_recording_path=save_recording_path
            )

        # Verify the result
        assert result is not None
        assert "Action runner executed successfully" in result

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

    def test_action_runner_template_with_custom_recording_path(self):
        """Test action_runner_template with custom recording path"""
        custom_path = str(self.artifacts_dir / "custom" / "action" / "videos")

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('src.script.script_manager.process_execution') as mock_process:

            # Mock the process execution
            mock_process.return_value = (MagicMock(returncode=0), ["Success"])

            script_info = {
                'type': 'action_runner_template',
                'name': 'test_custom_action',
                'action_script': 'test_action.py',
                'command': 'python -m pytest test_action.py'
            }

            # Execute with custom recording path
            result, script_path = run_script(
                script_info=script_info,
                params={},
                headless=True,
                save_recording_path=custom_path
            )

            # Verify the recording path was resolved correctly
            call_args = mock_process.call_args
            env_vars = call_args[1]['env']
            expected_path = str(create_or_get_recording_dir(custom_path))
            assert env_vars['RECORDING_PATH'] == expected_path

    def test_action_runner_template_parameter_substitution(self):
        """Test parameter substitution in action_runner_template"""
        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('src.script.script_manager.process_execution') as mock_process:

            # Mock the process execution
            mock_process.return_value = (MagicMock(returncode=0), ["Success"])

            script_info = {
                'type': 'action_runner_template',
                'name': 'test_params',
                'action_script': 'test_action.py',
                'command': 'python -m pytest test_action.py --param ${params.test_value}'
            }

            params = {'test_value': 'test123'}

            # Execute with parameters
            result, script_path = run_script(
                script_info=script_info,
                params=params,
                headless=True
            )

            # Verify parameter substitution in command
            call_args = mock_process.call_args
            command_parts = call_args[0][0]  # args
            command_str = ' '.join(command_parts)

            # Verify parameter was substituted
            assert 'test123' in command_str
            assert '${params.test_value}' not in command_str

    def test_action_runner_template_missing_action_script(self):
        """Test action_runner_template with missing action script"""
        script_info = {
            'type': 'action_runner_template',
            'name': 'test_missing',
            # Missing action_script field
            'command': 'python test.py'
        }

        with patch('os.getcwd', return_value=str(self.test_dir)):
            # Execute the script - should fail
            result, script_path = run_script(
                script_info=script_info,
                params={},
                headless=True
            )

            # Verify the error
            assert result is not None
            assert "Action runner template requires 'action_script' field" in result

    def test_action_runner_template_missing_command(self):
        """Test action_runner_template with missing command"""
        script_info = {
            'type': 'action_runner_template',
            'name': 'test_missing_command',
            'action_script': 'test_action.py'
            # Missing command field
        }

        with patch('os.getcwd', return_value=str(self.test_dir)):
            # Execute the script - should fail
            result, script_path = run_script(
                script_info=script_info,
                params={},
                headless=True
            )

            # Verify the error
            assert result is not None
            assert "Command field is required for action_runner_template type" in result

    def test_recording_path_unified_behavior_action_runner(self):
        """Test that action_runner_template uses unified recording path"""
        paths_to_test = [
            str(self.artifacts_dir / "runs" / "action-test1-art" / "videos"),
            str(self.artifacts_dir / "runs" / "action-test2-art" / "videos"),
            str(self.artifacts_dir / "custom" / "action" / "videos"),
        ]

        for test_path in paths_to_test:
            resolved = create_or_get_recording_dir(test_path)
            assert resolved.exists()
            resolved_str = str(resolved)

            # All paths should contain artifacts and videos
            assert "artifacts" in resolved_str or "videos" in resolved_str

    def test_action_script_file_exists(self):
        """Test that action script file exists"""
        assert self.action_script_path.exists()
        assert self.action_script_path.is_file()

        content = self.action_script_path.read_text()
        assert "test_action_runner_recording" in content
        assert "RECORDING_PATH" in content