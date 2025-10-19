"""Test script type recording functionality"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, AsyncMock
from src.utils.fs_paths import get_artifacts_base_dir
from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


@pytest.mark.ci_safe
class TestScriptTypeRecording:
    """Test recording functionality for script type"""

    def setup_method(self):
        """Setup test environment"""
        self.artifacts_dir = get_artifacts_base_dir() / "runs" / "test-script-type"
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        # Use fixture script in tests directory
        self.test_script_path = Path(__file__).parent / "fixtures" / "test_recording_script.py"
        
    def teardown_method(self):
        """Clean up test environment"""
        # No cleanup needed as we use fixed fixture files
        pass

    @pytest.mark.asyncio
    @patch('os.path.exists')
    @patch('src.script.script_manager.process_execution')
    async def test_script_type_recording_path(self, mock_process_execution, mock_exists):
        """Test that script type uses correct recording path"""
        # Mock file existence checks to pass
        mock_exists.return_value = True
        
        # Mock the process execution with AsyncMock
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Test output", b""))
        mock_process_execution.return_value = (mock_process, ["Test output"])

        # Test script info
        script_info = {
            'type': 'script',
            'script': 'test_recording_script.py',
            'command': 'python test_recording_script.py'
        }

        params = {}
        save_recording_path = str(self.artifacts_dir / "runs" / "test-run-art" / "videos")

        # Execute the script
        result, script_path = await run_script(
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
        assert "artifacts" in str(resolved_path) or "videos" in str(resolved_path)

        # Test with None (should use default)
        default_path = create_or_get_recording_dir(None)
        assert default_path.exists()

    def test_script_fixture_exists(self):
        """Test that fixture script file exists"""
        assert self.test_script_path.exists(), f"Fixture script not found at {self.test_script_path}"
        assert self.test_script_path.is_file()

        content = self.test_script_path.read_text()
        assert "test_recording_verification" in content
        assert "RECORDING_PATH" in content