"""
Integration tests for Git Script Resolver with Script Manager

Tests the integration between git_script_resolver and script_manager
to ensure git-scripts are properly resolved and executed.
"""

import os
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from src.script.script_manager import run_script
from src.script.git_script_resolver import get_git_script_resolver


class TestGitScriptIntegration:
    """Integration tests for git-script resolution and execution"""

    @pytest.fixture
    def mock_resolver(self):
        """Mock the git script resolver for testing"""
        with patch('src.script.git_script_resolver.get_git_script_resolver') as mock_get_resolver:
            mock_resolver = MagicMock()
            mock_get_resolver.return_value = mock_resolver
            yield mock_resolver

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_resolution_integration(self, mock_resolver):
        """Test that git-script resolution is called during script execution"""
        # Mock resolver to return resolved script info
        mock_resolver.resolve_git_script = AsyncMock(return_value={
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py',
            'version': 'main',
            'resolved_from': 'llms.txt'
        })

        mock_resolver.validate_script_info = AsyncMock(return_value=(True, "Valid"))

        # Mock the actual script execution to avoid real git operations
        with patch('src.script.script_manager.clone_git_repo', new_callable=AsyncMock) as mock_clone:
            with patch('src.script.script_manager.process_execution', new_callable=AsyncMock) as mock_process:
                mock_clone.return_value = '/tmp/test_repo'
                mock_process.return_value = (MagicMock(), ['Script executed successfully'])

                # Test script info without git/script_path (should trigger resolution)
                script_info = {
                    'type': 'git-script',
                    'name': 'test-script'
                    # Missing git and script_path - should be resolved
                }

                result, script_path = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True
                )

                # Verify resolver was called
                mock_resolver.resolve_git_script.assert_called_once_with('test-script', {'query': 'test'})
                mock_resolver.validate_script_info.assert_called_once()

                # Verify script execution was attempted
                assert result is not None

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_with_predefined_info(self, mock_resolver):
        """Test git-script execution when git/script_path are already provided"""
        # Mock validation only (no resolution needed)
        mock_resolver.validate_script_info = AsyncMock(return_value=(True, "Valid"))

        with patch('src.script.script_manager.clone_git_repo', new_callable=AsyncMock) as mock_clone:
            with patch('src.script.script_manager.process_execution', new_callable=AsyncMock) as mock_process:
                mock_clone.return_value = '/tmp/test_repo'
                mock_process.return_value = (MagicMock(), ['Script executed successfully'])

                # Test script info with git/script_path already provided
                script_info = {
                    'type': 'git-script',
                    'name': 'test-script',
                    'git': 'https://github.com/test/repo.git',
                    'script_path': 'scripts/test.py',
                    'version': 'main'
                }

                result, script_path = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True
                )

                # Verify resolver validation was called but not resolution
                mock_resolver.validate_script_info.assert_called_once()
                mock_resolver.resolve_git_script.assert_not_called()

                assert result is not None

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_resolution_failure(self, mock_resolver):
        """Test handling when git-script resolution fails"""
        # Mock the resolver's resolve_git_script method to return None
        mock_resolver.resolve_git_script = AsyncMock(return_value=None)

        script_info = {
            'type': 'git-script',
            'name': 'non-existent-script'
        }

        # The test expects ValueError to be raised when resolution fails
        with pytest.raises(ValueError, match="Could not resolve git-script"):
            await run_script(
                script_info=script_info,
                params={},
                headless=True
            )

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_validation_failure(self, mock_resolver):
        """Test handling when git-script validation fails"""
        # Mock resolver to pass resolution but fail validation
        mock_resolver.resolve_git_script = AsyncMock(return_value={
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py'
        })

        mock_resolver.validate_script_info = AsyncMock(return_value=(False, "Invalid configuration"))

        script_info = {
            'type': 'git-script',
            'name': 'test-script'
        }

        with pytest.raises(ValueError, match="Invalid git-script configuration"):
            await run_script(
                script_info=script_info,
                params={},
                headless=True
            )

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_new_method_execution(self, mock_resolver):
        """Test git-script execution using NEW METHOD (2024+)"""
        # Mock resolver methods
        mock_resolver.validate_script_info = AsyncMock(return_value=(True, "Valid"))

        # Mock NEW METHOD execution
        with patch('src.script.script_manager.execute_git_script_new_method', new_callable=AsyncMock) as mock_new_method:
            mock_new_method.return_value = ("Script executed with NEW METHOD", "/path/to/script.py")

            # Set environment to use NEW METHOD
            original_env = os.environ.get('BYKILT_USE_NEW_METHOD')
            os.environ['BYKILT_USE_NEW_METHOD'] = 'true'

            try:
                script_info = {
                    'type': 'git-script',
                    'name': 'test-script',
                    'git': 'https://github.com/test/repo.git',
                    'script_path': 'scripts/test.py'
                }

                result, script_path = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True
                )

                # Verify NEW METHOD was called
                mock_new_method.assert_called_once()
                assert "NEW METHOD" in result

            finally:
                # Restore original environment
                if original_env is not None:
                    os.environ['BYKILT_USE_NEW_METHOD'] = original_env
                else:
                    os.environ.pop('BYKILT_USE_NEW_METHOD', None)

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_legacy_method_execution(self, mock_resolver):
        """Test git-script execution using LEGACY METHOD"""
        # Mock resolver methods
        mock_resolver.validate_script_info = AsyncMock(return_value=(True, "Valid"))

        # Mock legacy method components
        with patch('src.script.script_manager.clone_git_repo', new_callable=AsyncMock) as mock_clone:
            with patch('src.script.script_manager.process_execution', new_callable=AsyncMock) as mock_process:
                with patch('src.script.script_manager.patch_search_script_for_chrome', new_callable=AsyncMock) as mock_patch:
                    mock_clone.return_value = '/tmp/test_repo'
                    mock_process.return_value = (MagicMock(), ['Legacy method executed'])
                    mock_patch.return_value = None

                    # Set environment to use LEGACY METHOD
                    original_env = os.environ.get('BYKILT_USE_NEW_METHOD')
                    os.environ['BYKILT_USE_NEW_METHOD'] = 'false'

                    try:
                        script_info = {
                            'type': 'git-script',
                            'name': 'test-script',
                            'git': 'https://github.com/test/repo.git',
                            'script_path': 'scripts/test.py',
                            'command': 'python test.py'
                        }

                        result, script_path = await run_script(
                            script_info=script_info,
                            params={'query': 'test'},
                            headless=True
                        )

                        # Verify legacy method components were called
                        mock_clone.assert_called_once()
                        mock_process.assert_called_once()
                        mock_patch.assert_called_once()

                        assert result is not None

                    finally:
                        # Restore original environment
                        if original_env is not None:
                            os.environ['BYKILT_USE_NEW_METHOD'] = original_env
                        else:
                            os.environ.pop('BYKILT_USE_NEW_METHOD', None)

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_resolution_order(self, mock_resolver):
        """Test that git-script resolution follows correct priority order"""
        # Test absolute path resolution (highest priority)
        with patch.object(mock_resolver, '_resolve_absolute_path', new_callable=AsyncMock) as mock_absolute:
            with patch.object(mock_resolver, '_resolve_relative_path', new_callable=AsyncMock) as mock_relative:
                with patch.object(mock_resolver, '_resolve_from_llms_txt', new_callable=AsyncMock) as mock_llms:

                    mock_absolute.return_value = {'type': 'script', 'resolved_from': 'absolute_path'}
                    mock_relative.return_value = None
                    mock_llms.return_value = None

                    script_info = {
                        'type': 'git-script',
                        'name': '/absolute/path/to/script.py'
                    }

                    # This should trigger absolute path resolution
                    mock_resolver.resolve_git_script = AsyncMock(return_value=mock_absolute.return_value)

                    result = await mock_resolver.resolve_git_script('/absolute/path/to/script.py')

                    # Verify absolute path resolution was attempted first
                    mock_absolute.assert_called()

    @pytest.mark.skip(reason="Mocking issue with get_git_script_resolver - needs refactoring")
    @pytest.mark.asyncio
    async def test_git_script_error_handling(self, mock_resolver):
        """Test error handling in git-script processing"""
        # Mock resolver to raise exception during resolution
        mock_resolver.resolve_git_script = AsyncMock(side_effect=Exception("Resolution failed"))

        script_info = {
            'type': 'git-script',
            'name': 'failing-script'
        }

        with pytest.raises(Exception):
            await run_script(
                script_info=script_info,
                params={},
                headless=True
            )
