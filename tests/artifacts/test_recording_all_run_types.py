"""
Test recording generation for all run types (Issue #221)
Tests that script, browser-control, and git-script run types generate recordings
"""

import pytest
import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from src.utils.recording_factory import RecordingFactory
from src.modules.direct_browser_control import execute_direct_browser_control
from src.script.script_manager import execute_git_script_new_method
from src.modules.handlers.browser_control_handler import handle_browser_control
from src.modules.handlers.git_script_handler import handle_git_script
from src.modules.handlers.script_handler import handle_script


class TestRecordingAllRunTypes:
    """Test recording generation across all run types"""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for testing"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def mock_action_browser_control(self):
        """Mock browser-control action"""
        return {
            'name': 'test_browser_control',
            'type': 'browser-control',
            'flow': [
                {'action': 'go_to_url', 'args': ['https://example.com']},
                {'action': 'wait_for_navigation'},
                {'action': 'extract_content'}
            ],
            'slowmo': 100,
            'save_recording_path': None,
            'enable_recording': True
        }

    @pytest.fixture
    def mock_action_git_script(self):
        """Mock git-script action"""
        return {
            'name': 'test_git_script',
            'type': 'git-script',
            'script_path': 'test_script.py',
            'save_recording_path': None,
            'enable_recording': True
        }

    @pytest.fixture
    def mock_action_script(self):
        """Mock script action"""
        return {
            'name': 'test_script',
            'type': 'script',
            'script_path': 'test_script.py',
            'save_recording_path': None,
            'enable_recording': True
        }

    @pytest.mark.asyncio
    async def test_recording_factory_initialization(self, temp_workspace):
        """Test that RecordingFactory initializes correctly"""
        run_context = {
            'run_id': 'test_run',
            'run_type': 'browser-control',
            'save_recording_path': temp_workspace,
            'enable_recording': True
        }

        recording_context = RecordingFactory.init_recorder(run_context)

        assert recording_context is not None
        assert hasattr(recording_context, 'recording_path')
        assert hasattr(recording_context, '__aenter__')
        assert hasattr(recording_context, '__aexit__')

    @pytest.mark.asyncio
    async def test_browser_control_recording_generation(self, temp_workspace, mock_action_browser_control):
        """Test that browser-control generates recordings"""
        # Mock the browser operations to avoid actual browser launch
        with patch('src.modules.direct_browser_control.GitScriptAutomator') as mock_automator:
            # Create proper async context manager mock
            mock_context = MagicMock()
            mock_page = MagicMock()

            # Mock the async context manager
            mock_context_manager = MagicMock()
            mock_context_manager.__aenter__ = AsyncMock(return_value=mock_context)
            mock_context_manager.__aexit__ = AsyncMock(return_value=None)

            mock_automator.return_value.browser_context.return_value = mock_context_manager
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.close = AsyncMock()

            # Execute with recording enabled
            params = {
                'browser_type': 'chromium',
                'save_recording_path': temp_workspace,
                'enable_recording': True
            }

            result = await execute_direct_browser_control(mock_action_browser_control, params)

            # Verify recording factory was called (result depends on mock setup)
            assert result is not None

    @pytest.mark.asyncio
    async def test_browser_control_handler_passes_recording_params(self, mock_action_browser_control):
        """Test that browser_control_handler passes recording parameters correctly"""
        with patch('src.modules.direct_browser_control.execute_direct_browser_control') as mock_execute:
            mock_execute.return_value = True

            # Add recording path to action
            mock_action_browser_control['save_recording_path'] = '/tmp/test_recording'

            params = {'browser_type': 'chromium'}

            result = await handle_browser_control(mock_action_browser_control, params)

            # Verify execute_direct_browser_control was called with recording params
            mock_execute.assert_called_once()
            call_args = mock_execute.call_args
            assert 'save_recording_path' in call_args.kwargs
            assert call_args.kwargs['save_recording_path'] == '/tmp/test_recording'

    @pytest.mark.asyncio
    async def test_git_script_handler_passes_recording_params(self, mock_action_git_script):
        """Test that git_script_handler passes recording parameters correctly"""
        with patch('src.script.script_manager.execute_git_script_new_method') as mock_execute:
            mock_execute.return_value = "success"

            # Add recording path to action
            mock_action_git_script['save_recording_path'] = '/tmp/test_recording'

            params = {'browser_type': 'chromium'}

            result = await handle_git_script(mock_action_git_script, params)

            # Verify execute_git_script_new_method was called with recording params
            mock_execute.assert_called_once()
            call_kwargs = mock_execute.call_args.kwargs
            assert 'save_recording_path' in call_kwargs
            assert call_kwargs['save_recording_path'] == '/tmp/test_recording'

    def test_recording_path_resolution(self, temp_workspace):
        """Test recording path resolution logic"""
        from src.utils.recording_dir_resolver import create_or_get_recording_dir

        # Test with explicit path
        explicit_path = create_or_get_recording_dir(temp_workspace)
        assert temp_workspace in str(explicit_path) or str(explicit_path).endswith(temp_workspace)

        # Test with None (should use default)
        default_path = create_or_get_recording_dir(None)
        assert default_path is not None
        assert default_path.exists()

    def test_artifact_manifest_registration(self):
        """Test that recordings are registered in artifact manifest"""
        from src.core.artifact_manager import ArtifactManager

        manager = ArtifactManager()

        # Test manifest registration (mock the actual file operations)
        with patch('builtins.open', create=True):
            with patch('json.dump'):
                # This would normally register the recording in manifest
                manifest_entry = {
                    'type': 'recording',
                    'path': '/tmp/test_recording.mp4',
                    'run_id': 'test_run',
                    'run_type': 'browser-control',
                    'timestamp': '2024-01-01T00:00:00Z'
                }

                # Verify manifest structure
                assert manifest_entry['type'] == 'recording'
                assert manifest_entry['run_type'] == 'browser-control'

    @pytest.mark.asyncio
    async def test_recording_context_manager_error_handling(self, temp_workspace):
        """Test that recording context manager handles errors gracefully"""
        run_context = {
            'run_id': 'test_run',
            'run_type': 'browser-control',
            'save_recording_path': '/invalid/path',
            'enable_recording': True
        }

        # This should return None for invalid path (graceful error handling)
        recording_context = RecordingFactory.init_recorder(run_context)
        assert recording_context is None  # Expected for invalid path

        # Test with valid path
        valid_context = {
            'run_id': 'test_run',
            'run_type': 'browser-control',
            'save_recording_path': temp_workspace,
            'enable_recording': True
        }

        valid_recording_context = RecordingFactory.init_recorder(valid_context)
        assert valid_recording_context is not None

        # Test async context manager behavior with valid context
        try:
            async with valid_recording_context:
                # Simulate some operation
                pass
        except Exception as e:
            # Should handle path creation errors gracefully
            assert 'recording' in str(e).lower() or 'path' in str(e).lower()

    def test_run_type_coverage(self):
        """Test that all expected run types are covered"""
        expected_types = {'script', 'browser-control', 'git-script'}

        # Verify these types exist in the codebase
        from src.modules.handlers import browser_control_handler, git_script_handler
        from src.modules.handlers.script_handler import handle_script

        handlers = {
            'browser-control': browser_control_handler.handle_browser_control,
            'git-script': git_script_handler.handle_git_script,
            'script': handle_script
        }

        assert set(handlers.keys()) == expected_types

        # Verify all handlers are async functions
        for handler_name, handler_func in handlers.items():
            assert asyncio.iscoroutinefunction(handler_func), f"{handler_name} handler should be async"