"""
Test browser-control type recording functionality
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class TestBrowserControlTypeRecording:
    """Test recording functionality for browser-control type"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.myscript_dir = self.test_dir / "myscript"
        self.artifacts_dir = self.test_dir / "artifacts"
        self.myscript_dir.mkdir(parents=True)
        self.artifacts_dir.mkdir(parents=True)

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    @patch('src.script.script_manager.process_execution')
    def test_browser_control_type_recording_path(self, mock_process_execution):
        """Test that browser-control type uses correct recording path"""
        # Mock the process execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process_execution.return_value = (mock_process, ["Test output"])

        # Test script info for browser-control
        script_info = {
            'type': 'browser-control',
            'name': 'test_browser_control',
            'flow': [
                {
                    'action': 'navigate',
                    'url': 'https://example.com'
                },
                {
                    'action': 'wait_for_selector',
                    'selector': 'h1'
                }
            ]
        }

        params = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "browser-control-test-art" / "videos")

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

        # Verify that the generated script was created in myscript directory
        assert script_path is not None
        assert "myscript" in script_path
        assert "browser_control.py" in script_path

    def test_browser_control_script_generation(self):
        """Test that browser-control script is generated correctly"""
        script_info = {
            'type': 'browser-control',
            'name': 'test_generation',
            'flow': [
                {
                    'action': 'navigate',
                    'url': 'https://example.com'
                }
            ]
        }

        params = {}

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('src.script.script_manager.process_execution') as mock_process:

            # Mock the process execution
            mock_process.return_value = (MagicMock(returncode=0), ["Success"])

            # Execute the script
            result, script_path = run_script(
                script_info=script_info,
                params=params,
                headless=True
            )

            # Verify script was generated
            assert script_path is not None
            generated_script_path = Path(script_path)
            assert generated_script_path.exists()

            # Verify script content
            content = generated_script_path.read_text()
            assert "test_browser_control" in content
            assert "https://example.com" in content
            assert "RECORDING_PATH" in content

    def test_browser_control_with_custom_recording_path(self):
        """Test browser-control with custom recording path"""
        custom_path = str(self.artifacts_dir / "custom" / "path" / "videos")

        with patch('os.getcwd', return_value=str(self.test_dir)), \
             patch('src.script.script_manager.process_execution') as mock_process:

            # Mock the process execution
            mock_process.return_value = (MagicMock(returncode=0), ["Success"])

            script_info = {
                'type': 'browser-control',
                'name': 'test_custom_path',
                'flow': [{'action': 'navigate', 'url': 'https://example.com'}]
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

    def test_recording_path_unified_behavior(self):
        """Test that all browser-control executions use unified recording path"""
        paths_to_test = [
            str(self.artifacts_dir / "runs" / "test1-art" / "videos"),
            str(self.artifacts_dir / "runs" / "test2-art" / "videos"),
            str(self.artifacts_dir / "custom" / "test3" / "videos"),
        ]

        for test_path in paths_to_test:
            resolved = create_or_get_recording_dir(test_path)
            assert resolved.exists()
            resolved_str = str(resolved)

            # All paths should contain artifacts and videos
            assert "artifacts" in resolved_str or "videos" in resolved_str