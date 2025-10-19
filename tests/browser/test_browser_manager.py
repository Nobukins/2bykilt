"""
Tests for src/browser/browser_manager.py

This module tests browser initialization, configuration, and fallback mechanisms.
"""

import os
import platform
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock
import pytest

from src.browser.browser_manager import (
    close_global_browser,
    get_browser_configs,
    _find_browser_path_windows,
    initialize_browser,
    prepare_recording_path
)


@pytest.mark.ci_safe
class TestCloseGlobalBrowser:
    """Tests for close_global_browser function."""
    
    @pytest.mark.asyncio
    async def test_close_both_browser_and_context(self):
        """Test closing both browser and browser context."""
        mock_context = AsyncMock()
        mock_browser = AsyncMock()
        
        with patch('src.browser.browser_manager.get_globals') as mock_get_globals:
            mock_get_globals.return_value = {
                "browser_context": mock_context,
                "browser": mock_browser
            }
            
            await close_global_browser()
            
            mock_context.close.assert_called_once()
            mock_browser.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_none_browser(self):
        """Test closing when browser is None."""
        with patch('src.browser.browser_manager.get_globals') as mock_get_globals:
            mock_get_globals.return_value = {
                "browser_context": None,
                "browser": None
            }
            
            # Should not raise an error
            await close_global_browser()
    
    @pytest.mark.asyncio
    async def test_close_only_context(self):
        """Test closing when only context exists."""
        mock_context = AsyncMock()
        
        with patch('src.browser.browser_manager.get_globals') as mock_get_globals:
            mock_get_globals.return_value = {
                "browser_context": mock_context,
                "browser": None
            }
            
            await close_global_browser()
            
            mock_context.close.assert_called_once()


@pytest.mark.ci_safe
class TestGetBrowserConfigs:
    """Tests for get_browser_configs function."""
    
    def test_default_config(self):
        """Test default browser configuration."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.get_current_browser.return_value = "chrome"
            mock_config.is_browser_available.return_value = True
            
            config = get_browser_configs(
                use_own_browser=False,
                window_w=1920,
                window_h=1080
            )
            
            assert config["browser_path"] is None
            assert config["browser_type"] == "chrome"
            assert "--window-size=1920,1080" in config["extra_chromium_args"]
    
    def test_explicit_browser_type(self):
        """Test configuration with explicit browser type."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.is_browser_available.return_value = True
            
            config = get_browser_configs(
                use_own_browser=False,
                window_w=800,
                window_h=600,
                browser_type="edge"
            )
            
            assert config["browser_type"] == "edge"
            assert "--window-size=800,600" in config["extra_chromium_args"]
    
    def test_fallback_to_available_browser(self):
        """Test fallback when requested browser unavailable."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.is_browser_available.return_value = False
            mock_config.get_available_browsers.return_value = ["chrome"]
            
            config = get_browser_configs(
                use_own_browser=False,
                window_w=1024,
                window_h=768,
                browser_type="edge"
            )
            
            assert config["browser_type"] == "chrome"
    
    def test_use_own_browser_with_path(self):
        """Test configuration with custom browser path."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.get_current_browser.return_value = "chrome"
            mock_config.is_browser_available.return_value = True
            mock_config.get_browser_settings.return_value = {
                "path": "/usr/bin/google-chrome",
                "user_data": None
            }
            
            config = get_browser_configs(
                use_own_browser=True,
                window_w=1920,
                window_h=1080
            )
            
            assert config["browser_path"] == "/usr/bin/google-chrome"
    
    def test_use_own_browser_with_user_data(self):
        """Test configuration with custom user data directory."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.get_current_browser.return_value = "chrome"
            mock_config.is_browser_available.return_value = True
            mock_config.get_browser_settings.return_value = {
                "path": "/usr/bin/chrome",
                "user_data": "/home/user/.config/chrome"
            }
            
            config = get_browser_configs(
                use_own_browser=True,
                window_w=1920,
                window_h=1080
            )
            
            assert any("--user-data-dir=" in arg for arg in config["extra_chromium_args"])
    
    @patch('src.browser.browser_manager.platform.system', return_value="Windows")
    def test_windows_extra_args(self, mock_platform):
        """Test Windows-specific browser arguments."""
        with patch('src.browser.browser_manager.browser_config') as mock_config:
            mock_config.get_current_browser.return_value = "chrome"
            mock_config.is_browser_available.return_value = True
            
            config = get_browser_configs(
                use_own_browser=False,
                window_w=1920,
                window_h=1080
            )
            
            assert "--disable-background-timer-throttling" in config["extra_chromium_args"]
            assert "--no-first-run" in config["extra_chromium_args"]


@pytest.mark.ci_safe
class TestFindBrowserPathWindows:
    """Tests for _find_browser_path_windows function."""
    
    @patch('src.browser.browser_manager.os.path.exists')
    def test_find_chrome_standard_location(self, mock_exists):
        """Test finding Chrome in standard location."""
        def exists_side_effect(path):
            return "Google\\Chrome" in path
        
        mock_exists.side_effect = exists_side_effect
        
        path = _find_browser_path_windows("chrome")
        
        assert path is not None
        assert "chrome.exe" in path.lower()
    
    @patch('src.browser.browser_manager.os.path.exists')
    def test_find_edge_standard_location(self, mock_exists):
        """Test finding Edge in standard location."""
        def exists_side_effect(path):
            return "Microsoft\\Edge" in path
        
        mock_exists.side_effect = exists_side_effect
        
        path = _find_browser_path_windows("edge")
        
        assert path is not None
        assert "msedge.exe" in path.lower()
    
    @patch('src.browser.browser_manager.os.path.exists', return_value=False)
    def test_browser_not_found(self, mock_exists):
        """Test when browser is not found."""
        path = _find_browser_path_windows("chrome")
        
        assert path is None


@pytest.mark.ci_safe
class TestInitializeBrowser:
    """Tests for initialize_browser function."""
    
    @pytest.mark.asyncio
    async def test_successful_initialization(self):
        """Test successful browser initialization."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            mock_debug_instance.initialize_custom_browser.return_value = {
                "status": "success"
            }
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                mock_config.get.return_value = "chrome"
                
                result = await initialize_browser()
                
                assert result["status"] == "success"
                mock_debug_instance.initialize_custom_browser.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_initialization_with_explicit_browser(self):
        """Test initialization with explicit browser type."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            mock_debug_instance.initialize_custom_browser.return_value = {
                "status": "success"
            }
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                
                result = await initialize_browser(browser_type="edge")
                
                assert result["status"] == "success"
                mock_config.set_current_browser.assert_called_with("edge")
    
    @pytest.mark.asyncio
    async def test_fallback_on_failure(self):
        """Test fallback to alternative browser on failure."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            # First call fails, second succeeds
            mock_debug_instance.initialize_custom_browser.side_effect = [
                {"status": "error", "message": "Chrome failed"},
                {"status": "success"}
            ]
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                mock_config.get.return_value = "chrome"
                mock_config.get_browser_settings.return_value = {"debugging_port": 9222}
                
                with patch('src.browser.browser_diagnostic.BrowserDiagnostic') as MockDiagnostic:
                    result = await initialize_browser(
                        browser_type="chrome",
                        auto_fallback=True
                    )
                    
                    assert "fallback_used" in result or result["status"] == "success"
                    MockDiagnostic.diagnose_browser_startup_issues.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_no_fallback_when_disabled(self):
        """Test no fallback when auto_fallback=False."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            mock_debug_instance.initialize_custom_browser.return_value = {
                "status": "error",
                "message": "Failed"
            }
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                mock_config.get.return_value = "chrome"
                mock_config.get_browser_settings.return_value = {"debugging_port": 9222}
                
                result = await initialize_browser(
                    browser_type="chrome",
                    auto_fallback=False
                )
                
                # Should not have fallback keys
                assert "fallback_used" not in result
    
    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test exception handling during initialization."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            mock_debug_instance.initialize_custom_browser.side_effect = Exception("Unexpected error")
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                
                # Should handle exception and attempt fallback
                result = await initialize_browser(
                    browser_type="chrome",
                    auto_fallback=True
                )
                
                # Should attempt fallback or return error
                assert isinstance(result, dict)


@pytest.mark.ci_safe
class TestPrepareRecordingPath:
    """Tests for prepare_recording_path function."""
    
    def test_recording_disabled(self):
        """Test when recording is disabled."""
        path = prepare_recording_path(enable_recording=False, save_recording_path=None)
        
        assert path is None
    
    def test_recording_with_explicit_path(self):
        """Test recording with explicit path."""
        test_path = "/tmp/recordings"
        
        with patch('src.utils.recording_dir_resolver.create_or_get_recording_dir') as mock_create:
            mock_create.return_value = Path(test_path)
            
            path = prepare_recording_path(
                enable_recording=True,
                save_recording_path=test_path
            )
            
            assert path == test_path
            mock_create.assert_called_with(test_path)
    
    def test_recording_with_default_path(self):
        """Test recording with default path."""
        default_path = "/tmp/default_recordings"
        
        with patch('src.utils.recording_dir_resolver.create_or_get_recording_dir') as mock_create:
            mock_create.return_value = Path(default_path)
            
            path = prepare_recording_path(
                enable_recording=True,
                save_recording_path=None
            )
            
            assert path == default_path
            # Called without arguments (None becomes no argument)
            assert mock_create.called
    
    def test_recording_fallback_on_error(self):
        """Test fallback when recording path creation fails."""
        with patch('src.utils.recording_dir_resolver.create_or_get_recording_dir') as mock_create:
            # First call fails, second succeeds (fallback within same module)
            mock_create.side_effect = [
                Exception("Path creation failed"),
                "/tmp/fallback"
            ]
            
            path = prepare_recording_path(
                enable_recording=True,
                save_recording_path="/tmp/fail"
            )
            
            # Should return some valid path (fallback or temp)
            assert path is not None
    
    def test_recording_final_tempdir_fallback(self):
        """Test final tempdir fallback when all else fails."""
        with patch('src.utils.recording_dir_resolver.create_or_get_recording_dir') as mock_create:
            mock_create.side_effect = Exception("All failed")
            
            with patch('tempfile.gettempdir', return_value="/tmp"):
                path = prepare_recording_path(
                    enable_recording=True,
                    save_recording_path="/tmp/fail"
                )
                
                assert path == "/tmp"


@pytest.mark.ci_safe
class TestBrowserManagerIntegration:
    """Integration tests for browser manager functions."""
    
    def test_config_with_windows_path(self):
        """Test configuration with Windows path handling."""
        with patch('src.browser.browser_manager.platform.system', return_value="Windows"):
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.get_current_browser.return_value = "chrome"
                mock_config.is_browser_available.return_value = True
                mock_config.get_browser_settings.return_value = {
                    "path": r"C:\Program Files\Chrome\chrome.exe",
                    "user_data": r"C:\Users\Test\AppData\Chrome"
                }
                
                config = get_browser_configs(
                    use_own_browser=True,
                    window_w=1920,
                    window_h=1080
                )
                
                assert config["browser_path"] == r"C:\Program Files\Chrome\chrome.exe"
                assert any("--user-data-dir=" in arg for arg in config["extra_chromium_args"])
    
    @pytest.mark.asyncio
    async def test_initialize_and_close_workflow(self):
        """Test complete initialize and close workflow."""
        with patch('src.browser.browser_manager.BrowserDebugManager') as MockDebugManager:
            mock_debug_instance = AsyncMock()
            mock_debug_instance.initialize_custom_browser.return_value = {
                "status": "success"
            }
            MockDebugManager.return_value = mock_debug_instance
            
            with patch('src.browser.browser_manager.browser_config') as mock_config:
                mock_config.config = {"current_browser": "chrome"}
                
                # Initialize
                result = await initialize_browser()
                assert result["status"] == "success"
                
                # Close
                mock_context = AsyncMock()
                mock_browser = AsyncMock()
                
                with patch('src.browser.browser_manager.get_globals') as mock_get_globals:
                    mock_get_globals.return_value = {
                        "browser_context": mock_context,
                        "browser": mock_browser
                    }
                    
                    await close_global_browser()
                    
                    mock_context.close.assert_called_once()
                    mock_browser.close.assert_called_once()
