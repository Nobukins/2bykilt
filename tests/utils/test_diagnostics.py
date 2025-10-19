"""
Tests for src/utils/diagnostics.py

This module tests browser diagnostics collection functionality.
"""

import os
import json
import platform
import sys
from datetime import datetime
from unittest.mock import patch, MagicMock

import pytest
import psutil

from src.utils.diagnostics import BrowserDiagnostics


@pytest.mark.local_only
class TestBrowserDiagnosticsCollectBrowserInfo:
    """Tests for BrowserDiagnostics.collect_browser_info method."""
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_browser_info_success(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test successful browser info collection."""
        # Mock BrowserConfig
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {"chrome": {"path": "/usr/bin/chrome"}}
        }
        mock_browser_config.return_value = mock_config_instance
        
        # Mock running processes
        mock_chrome_proc = MagicMock()
        mock_chrome_proc.info = {
            'pid': 1234,
            'name': 'chrome',
            'cmdline': ['/usr/bin/chrome', '--flag']
        }
        mock_process_iter.return_value = [mock_chrome_proc]
        
        # Mock file operations
        mock_file = MagicMock()
        mock_file_open.return_value.__enter__.return_value = mock_file
        
        result = BrowserDiagnostics.collect_browser_info()
        
        assert isinstance(result, str)
        assert result.startswith('logs/browser_diagnostics_')
        assert result.endswith('.json')
        mock_makedirs.assert_called_once_with('logs', exist_ok=True)
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_chrome_and_edge_processes(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test collection of Chrome and Edge processes."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        
        # Mock Chrome and Edge processes
        mock_chrome = MagicMock()
        mock_chrome.info = {
            'pid': 1234,
            'name': 'chrome',
            'cmdline': ['/usr/bin/chrome']
        }
        
        mock_edge = MagicMock()
        mock_edge.info = {
            'pid': 5678,
            'name': 'msedge',
            'cmdline': ['/usr/bin/msedge']
        }
        
        mock_process_iter.return_value = [mock_chrome, mock_edge]
        
        mock_file = MagicMock()
        mock_file_open.return_value.__enter__.return_value = mock_file
        
        BrowserDiagnostics.collect_browser_info()
        
        # Verify json.dump was called with diagnostics data
        mock_file.write.assert_called()
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_handles_process_errors(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test handling of process access errors."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        
        # Mock empty process list (errors would be caught and ignored)
        mock_process_iter.return_value = []
        
        mock_file = MagicMock()
        mock_file_open.return_value.__enter__.return_value = mock_file
        
        # Should not raise, should handle error gracefully
        result = BrowserDiagnostics.collect_browser_info()
        assert isinstance(result, str)
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch.dict(os.environ, {
        'CHROME_PATH': '/custom/chrome',
        'CHROME_USER_DATA': '/custom/userdata',
        'CHROME_DEBUGGING_PORT': '9222',
        'EDGE_PATH': '/custom/edge',
        'EDGE_USER_DATA': '/custom/edge_data',
        'EDGE_DEBUGGING_PORT': '9223'
    })
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_environment_variables(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test collection of environment variables."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        mock_process_iter.return_value = []
        
        mock_file = MagicMock()
        mock_file_open.return_value.__enter__.return_value = mock_file
        
        BrowserDiagnostics.collect_browser_info()
        
        # Verify json.dump was called
        assert mock_file.write.called
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_system_info(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test collection of system information."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "edge",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        mock_process_iter.return_value = []
        
        captured_data = {}
        
        def capture_json_dump(data, file, **kwargs):
            captured_data.update(data)
        
        with patch('json.dump', side_effect=capture_json_dump):
            BrowserDiagnostics.collect_browser_info()
        
        assert 'system_info' in captured_data
        assert 'os' in captured_data['system_info']
        assert 'python_version' in captured_data['system_info']
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_collect_timestamp_format(self, mock_makedirs, mock_file_open, mock_process_iter, mock_browser_config):
        """Test that timestamp is in correct format."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        mock_process_iter.return_value = []
        
        captured_data = {}
        
        def capture_json_dump(data, file, **kwargs):
            captured_data.update(data)
        
        with patch('src.utils.diagnostics.json.dump', side_effect=capture_json_dump):
            BrowserDiagnostics.collect_browser_info()
        
        assert 'timestamp' in captured_data
        # Verify ISO format
        datetime.fromisoformat(captured_data['timestamp'])


@pytest.mark.local_only
class TestBrowserDiagnosticsDiagnoseOnError:
    """Tests for BrowserDiagnostics.diagnose_on_error method."""
    
    @patch.object(BrowserDiagnostics, 'collect_browser_info')
    def test_diagnose_on_error_success(self, mock_collect):
        """Test successful error diagnostics."""
        mock_collect.return_value = "logs/diagnostics_20231015_120000.json"
        
        result = BrowserDiagnostics.diagnose_on_error()
        
        assert result == "logs/diagnostics_20231015_120000.json"
        mock_collect.assert_called_once()
    
    @patch.object(BrowserDiagnostics, 'collect_browser_info')
    def test_diagnose_on_error_failure(self, mock_collect):
        """Test error handling when diagnostics collection fails."""
        mock_collect.side_effect = Exception("Collection failed")
        
        result = BrowserDiagnostics.diagnose_on_error()
        
        assert result is None
    
    @patch.object(BrowserDiagnostics, 'collect_browser_info')
    def test_diagnose_on_error_logs_error(self, mock_collect):
        """Test that errors are logged properly."""
        mock_collect.side_effect = RuntimeError("Test error")
        
        with patch('src.utils.diagnostics.logger') as mock_logger:
            result = BrowserDiagnostics.diagnose_on_error()
            
            assert result is None
            mock_logger.error.assert_called()


@pytest.mark.local_only
class TestBrowserDiagnosticsIntegration:
    """Integration tests for BrowserDiagnostics."""
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    def test_full_diagnostics_workflow(self, mock_process_iter, mock_browser_config, tmp_path):
        """Test full diagnostics collection workflow."""
        # Setup mocks
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {"chrome": {"path": "/usr/bin/chrome"}}
        }
        mock_browser_config.return_value = mock_config_instance
        
        mock_proc = MagicMock()
        mock_proc.info = {
            'pid': 9999,
            'name': 'chrome.exe',
            'cmdline': ['C:\\Program Files\\Google\\Chrome\\chrome.exe']
        }
        mock_process_iter.return_value = [mock_proc]
        
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', create=True) as mock_open:
                mock_file = MagicMock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                result = BrowserDiagnostics.collect_browser_info()
                
                assert 'logs/browser_diagnostics_' in result
                mock_makedirs.assert_called_with('logs', exist_ok=True)
    
    @patch('src.browser.browser_config.BrowserConfig')
    @patch('psutil.process_iter')
    @patch('builtins.open', create=True)
    @patch('os.makedirs')
    def test_no_browser_processes_running(self, mock_makedirs, mock_open, mock_process_iter, mock_browser_config):
        """Test diagnostics when no browser processes are running."""
        mock_config_instance = MagicMock()
        mock_config_instance.config = {
            "current_browser": "chrome",
            "browsers": {}
        }
        mock_browser_config.return_value = mock_config_instance
        
        # No browser processes
        mock_other_proc = MagicMock()
        mock_other_proc.info = {
            'pid': 1111,
            'name': 'python',
            'cmdline': ['python', 'script.py']
        }
        mock_process_iter.return_value = [mock_other_proc]
        
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        result = BrowserDiagnostics.collect_browser_info()
        
        assert isinstance(result, str)
        assert 'browser_diagnostics_' in result
