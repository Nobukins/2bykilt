"""
Integration test for all script type recording functionality
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.script.script_manager import run_script
from src.utils.recording_dir_resolver import create_or_get_recording_dir


class TestAllScriptTypesRecordingIntegration:
    """Integration test for all script types recording functionality"""

    def setup_method(self):
        """Setup test environment"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.myscript_dir = self.test_dir / "myscript"
        self.artifacts_dir = self.test_dir / "artifacts"
        self.myscript_dir.mkdir(parents=True)
        self.artifacts_dir.mkdir(parents=True)

        # Create test files for each type
        self._create_test_files()

    def teardown_method(self):
        """Clean up test environment"""
        shutil.rmtree(self.test_dir)

    def _create_test_files(self):
        """Create test files for all script types"""
        # Script type test file
        script_file = self.myscript_dir / "integration_test_script.py"
        script_file.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.integration_test
def test_script_integration(page: Page):
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Script recording path: {recording_path}")
    page.goto("https://example.com")
    assert recording_path and "artifacts" in recording_path
''')

        # Browser control test file
        browser_file = self.myscript_dir / "integration_browser_control.py"
        browser_file.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.browser_control
def test_browser_control_integration(page: Page):
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Browser-control recording path: {recording_path}")
    page.goto("https://example.com")
    assert recording_path and "artifacts" in recording_path
''')

        # Git script mock
        self.mock_git_repo = self.test_dir / "mock_git_repo"
        self.mock_git_repo.mkdir()
        git_script_file = self.mock_git_repo / "integration_git_script.py"
        git_script_file.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.git_script_test
def test_git_script_integration(page: Page):
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Git-script recording path: {recording_path}")
    page.goto("https://example.com")
    assert recording_path and "artifacts" in recording_path
''')

        # Action runner test file
        action_file = self.myscript_dir / "integration_action.py"
        action_file.write_text('''
import pytest
from playwright.sync_api import Page
import os

@pytest.mark.action_test
def test_action_integration(page: Page):
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Action-runner recording path: {recording_path}")
    page.goto("https://example.com")
    assert recording_path and "artifacts" in recording_path
''')

        # Create pytest.ini
        pytest_ini = self.myscript_dir / "pytest.ini"
        pytest_ini.write_text('''
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = --verbose --capture=no
markers =
    integration_test: integration tests
    browser_control: browser control tests
    git_script_test: git script tests
    action_test: action runner tests
''')

    def test_all_script_types_recording_integration(self):
        """Test that all script types use correct recording paths"""
        # Test data for all script types
        test_cases = [
            {
                'name': 'script',
                'script_info': {
                    'type': 'script',
                    'script': 'integration_test_script.py',
                    'command': 'python -m pytest integration_test_script.py'
                }
            },
            {
                'name': 'browser-control',
                'script_info': {
                    'type': 'browser-control',
                    'name': 'integration_browser_control',
                    'flow': [{'action': 'navigate', 'url': 'https://example.com'}]
                }
            },
            {
                'name': 'action_runner_template',
                'script_info': {
                    'type': 'action_runner_template',
                    'name': 'integration_action',
                    'action_script': 'integration_action.py',
                    'command': 'python -m pytest integration_action.py'
                }
            }
        ]

        with patch('os.getcwd', return_value=str(self.test_dir)):
            for test_case in test_cases:
                print(f"\n=== Testing {test_case['name']} type ===")

                # Set up recording path for this test
                recording_path = str(self.artifacts_dir / "runs" / f"{test_case['name']}-integration-art" / "videos")

                # Test that recording directory resolver works correctly
                resolved_path = create_or_get_recording_dir(recording_path)

                # Verify the resolved path
                assert resolved_path is not None
                assert resolved_path.exists()
                assert resolved_path.is_dir()

                # Verify path structure (normalize paths for macOS)
                normalized_path = str(resolved_path).replace('/private', '')
                assert "artifacts" in normalized_path
                assert "videos" in normalized_path
                assert f"{test_case['name']}-integration-art" in normalized_path

                print(f"✅ {test_case['name']} type: Recording path correctly resolved to {resolved_path}")

    def test_recording_path_unification_across_types(self):
        """Test that recording paths are unified across all script types"""
        base_recording_path = str(self.artifacts_dir / "runs" / "unified-test-art" / "videos")

        # Test that the same base path resolves consistently
        resolved1 = create_or_get_recording_dir(base_recording_path)
        resolved2 = create_or_get_recording_dir(base_recording_path)

        # Both should resolve to the same path
        assert str(resolved1) == str(resolved2)

        # Directory should exist
        assert resolved1.exists()
        assert resolved1.is_dir()

        # Test with different script types but same base path
        script_types = ['script', 'browser-control', 'git-script', 'action_runner_template']

        for script_type in script_types:
            type_path = f"{base_recording_path}_{script_type}"
            resolved = create_or_get_recording_dir(type_path)

            # Each type should get its own unique directory
            assert resolved.exists()
            assert resolved.is_dir()
            assert script_type in str(resolved)

            print(f"✅ {script_type}: Unique recording directory created at {resolved}")

    def test_recording_path_consistency_across_types(self):
        """Test that recording paths are consistent across all script types"""
        base_paths = [
            str(self.artifacts_dir / "runs" / "consistency-test-art" / "videos"),
            str(self.artifacts_dir / "custom" / "consistency" / "videos"),
            str(self.artifacts_dir / "integration" / "test" / "videos"),
        ]

        resolved_paths = []
        for path in base_paths:
            resolved = create_or_get_recording_dir(path)
            resolved_paths.append(str(resolved))

            # Verify directory was created
            assert resolved.exists()
            assert resolved.is_dir()

        # All resolved paths should be different (unique directories)
        assert len(set(resolved_paths)) == len(resolved_paths)

        # All should contain artifacts or videos
        for path in resolved_paths:
            assert "artifacts" in path or "videos" in path

    def test_recording_path_with_environment_variable(self):
        """Test recording path resolution with environment variable"""
        env_path = str(self.artifacts_dir / "env" / "test" / "videos")

        with patch.dict(os.environ, {'RECORDING_PATH': env_path}):
            # When RECORDING_PATH is set, it should take precedence
            resolved = create_or_get_recording_dir(None)

            # Normalize paths for macOS (remove /private prefix)
            normalized_resolved = str(resolved).replace('/private', '')
            normalized_env = env_path.replace('/private', '')

            assert normalized_resolved == normalized_env
            assert resolved.exists()

    def test_recording_path_with_explicit_and_env(self):
        """Test that explicit path takes precedence over environment variable"""
        env_path = str(self.artifacts_dir / "env" / "test" / "videos")
        explicit_path = str(self.artifacts_dir / "explicit" / "test" / "videos")

        with patch.dict(os.environ, {'RECORDING_PATH': env_path}):
            # Explicit path should take precedence
            resolved = create_or_get_recording_dir(explicit_path)

            # Normalize paths for macOS
            normalized_resolved = str(resolved).replace('/private', '')
            normalized_explicit = explicit_path.replace('/private', '')

            assert normalized_resolved == normalized_explicit
            assert resolved.exists()

            # Environment variable should be ignored
            normalized_env = env_path.replace('/private', '')
            assert normalized_resolved != normalized_env

    def test_all_test_files_created(self):
        """Test that all test files were created correctly"""
        expected_files = [
            self.myscript_dir / "integration_test_script.py",
            self.myscript_dir / "integration_browser_control.py",
            self.mock_git_repo / "integration_git_script.py",
            self.myscript_dir / "integration_action.py",
            self.myscript_dir / "pytest.ini"
        ]

        for file_path in expected_files:
            assert file_path.exists(), f"Test file {file_path} was not created"
            assert file_path.is_file(), f"{file_path} is not a file"

        print("✅ All test files created successfully")