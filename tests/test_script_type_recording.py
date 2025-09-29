"""
Test script type recording functionality
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.utils.fs_paths import get_artifacts_base_dir

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class TestScriptTypeRecording:
    """Test recording functionality for script type"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.myscript_dir = self.test_dir / "myscript"
        self.artifacts_dir = get_artifacts_base_dir() / "runs" / "test-script-type"
        self.myscript_dir.mkdir(parents=True)
        self.artifacts_dir.mkdir(parents=True)

        # Create a test script
        self.test_script_path = self.myscript_dir / "test_script.py"
        self.test_script_path.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.script_test
def test_script_recording(page: Page):
    """Test script that should generate recording"""
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

        # Create pytest.ini
        pytest_ini = self.myscript_dir / "pytest.ini"
        pytest_ini.write_text('''
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = --verbose --capture=no
markers =
    script_test: mark tests as script type tests
''')

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    @patch('src.script.script_manager.process_execution')
    def test_script_type_recording_path(self, mock_process_execution):
        """Test that script type uses correct recording path"""
        # Mock the process execution
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.communicate.return_value = (b"Test output", b"")
        mock_process_execution.return_value = (mock_process, ["Test output"])

        # Test script info
        script_info = {
            'type': 'script',
            'script': 'test_script.py',
            'command': 'python -m pytest test_script.py'
        }

        params = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "test-run-art" / "videos")

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

    def test_recording_dir_resolver_integration(self):
        """Test that recording directory resolver works correctly"""
        # Test with explicit path
        explicit_path = str(self.artifacts_dir / "runs" / "custom-run-art" / "videos")
        resolved_path = create_or_get_recording_dir(explicit_path)

        assert resolved_path.exists()
        assert "artifacts" in str(resolved_path)
        assert "videos" in str(resolved_path)

        # Test with None (should use default)
        default_path = create_or_get_recording_dir(None)
        assert default_path.exists()

    def test_script_file_exists(self):
        """Test that test script file exists"""
        assert self.test_script_path.exists()
        assert self.test_script_path.is_file()

        content = self.test_script_path.read_text()
        assert "test_script_recording" in content
        assert "RECORDING_PATH" in content