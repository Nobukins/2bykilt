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


@pytest.mark.ci_safe
class TestGitScriptIntegration:
    """Integration tests for git-script resolution and execution"""

    @pytest.fixture
    def mock_resolver(self):
        """Create a mock git script resolver for testing"""
        mock_resolver = MagicMock()
        # Set up common async methods
        mock_resolver.resolve_git_script = AsyncMock()
        mock_resolver.validate_script_info = AsyncMock()
        return mock_resolver

    @pytest.mark.asyncio
    async def test_git_script_resolution_integration(self, mock_resolver):
        """Test that git-script resolution is called during script execution"""
        # Mock resolver to return resolved script info
        mock_resolver.resolve_git_script.return_value = {
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py',
            'version': 'main',
            'resolved_from': 'llms.txt'
        }

        mock_resolver.validate_script_info.return_value = (True, "Valid")

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

                result, _ = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True,
                    git_script_resolver=mock_resolver
                )

                # Verify resolver was called
                mock_resolver.resolve_git_script.assert_called_once_with('test-script', {'query': 'test'})
                mock_resolver.validate_script_info.assert_called_once()

                # Verify script execution was attempted
                assert result is not None

    @pytest.mark.asyncio
    async def test_git_script_with_predefined_info(self, mock_resolver):
        """Test git-script execution when git/script_path are already provided"""
        # Mock validation only (no resolution needed)
        mock_resolver.validate_script_info.return_value = (True, "Valid")

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

                result, _ = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True,
                    git_script_resolver=mock_resolver
                )

                # Verify resolver validation was called but not resolution
                mock_resolver.validate_script_info.assert_called_once()
                mock_resolver.resolve_git_script.assert_not_called()

                assert result is not None

    @pytest.mark.asyncio
    async def test_git_script_resolution_failure(self, mock_resolver):
        """Test handling when git-script resolution fails"""
        # Mock the resolver's resolve_git_script method to return None
        mock_resolver.resolve_git_script.return_value = None

        script_info = {
            'type': 'git-script',
            'name': 'non-existent-script'
        }

        # The exception is caught and returned as error message
        result, script_path = await run_script(
            script_info=script_info,
            params={},
            headless=True,
            git_script_resolver=mock_resolver
        )
        
        # Verify error is returned
        assert "Could not resolve git-script" in result
        assert script_path is None

    @pytest.mark.asyncio
    async def test_git_script_validation_failure(self, mock_resolver):
        """Test handling when git-script validation fails"""
        # Mock resolver to pass resolution but fail validation
        mock_resolver.resolve_git_script.return_value = {
            'type': 'git-script',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'scripts/test.py'
        }

        mock_resolver.validate_script_info.return_value = (False, "Invalid configuration")

        script_info = {
            'type': 'git-script',
            'name': 'test-script'
        }

        # Exception is caught and returned as error message
        result, script_path = await run_script(
            script_info=script_info,
            params={},
            headless=True,
            git_script_resolver=mock_resolver
        )
        
        # Verify error is returned
        assert "Invalid git-script configuration" in result
        assert script_path is None

    @pytest.mark.asyncio
    async def test_git_script_new_method_execution(self, mock_resolver):
        """Test git-script execution using NEW METHOD (2024+)"""
        # Mock resolver methods
        mock_resolver.validate_script_info.return_value = (True, "Valid")

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

                result, _ = await run_script(
                    script_info=script_info,
                    params={'query': 'test'},
                    headless=True,
                    git_script_resolver=mock_resolver
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

    @pytest.mark.asyncio
    async def test_git_script_legacy_method_execution(self, mock_resolver):
        """Test git-script execution using LEGACY METHOD"""
        # Mock resolver methods
        mock_resolver.validate_script_info.return_value = (True, "Valid")

        # Mock legacy method components
        with patch('src.script.script_manager.clone_git_repo', new_callable=AsyncMock) as mock_clone:
            with patch('src.script.script_manager.process_execution', new_callable=AsyncMock) as mock_process:
                with patch('src.script.script_manager.patch_search_script_for_chrome', new_callable=AsyncMock) as mock_patch:
                    with patch('os.path.exists') as mock_exists:
                        mock_clone.return_value = '/tmp/test_repo'
                        mock_process.return_value = (MagicMock(returncode=0, communicate=AsyncMock(return_value=(b'', b''))), ['Legacy method executed'])
                        mock_patch.return_value = None
                        mock_exists.return_value = True

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

                            result, _ = await run_script(
                                script_info=script_info,
                                params={'query': 'test'},
                                headless=True,
                                git_script_resolver=mock_resolver
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

    @pytest.mark.asyncio
    async def test_git_script_resolution_order(self, mock_resolver):
        """Test that git-script resolution follows correct priority order"""
        # Test that resolver is called with the script name
        mock_resolver.resolve_git_script.return_value = {
            'type': 'script', 
            'resolved_from': 'absolute_path',
            'git': 'https://github.com/test/repo.git',
            'script_path': 'test.py'
        }
        mock_resolver.validate_script_info.return_value = (True, "Valid")

        with patch('src.script.script_manager.execute_git_script_new_method', new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = ("Success", "/path/to/script")

            script_info = {
                'type': 'git-script',
                'name': '/absolute/path/to/script.py'
            }

            await run_script(
                script_info=script_info,
                params={},
                headless=True,
                git_script_resolver=mock_resolver
            )

            # Verify resolver was called with the absolute path
            mock_resolver.resolve_git_script.assert_called_once_with('/absolute/path/to/script.py', {})

    @pytest.mark.asyncio
    async def test_git_script_error_handling(self, mock_resolver):
        """Test error handling in git-script processing"""
        # Mock resolver to raise exception during resolution
        mock_resolver.resolve_git_script.side_effect = Exception("Resolution failed")

        script_info = {
            'type': 'git-script',
            'name': 'failing-script'
        }

        # Exception is caught and returned as error message
        result, script_path = await run_script(
            script_info=script_info,
            params={},
            headless=True,
            git_script_resolver=mock_resolver
        )
        
        # Verify error is returned
        assert "Resolution failed" in result
        assert script_path is None
