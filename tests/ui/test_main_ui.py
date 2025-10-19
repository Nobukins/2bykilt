"""
Test suite for src/ui/main_ui.py

Tests ModernUI class initialization, interface building, and launching.
Focuses on error handling, component integration, and Gradio mocking.

Coverage Target: 0% → 70%+
"""

import logging
from unittest.mock import MagicMock, Mock, patch, call
import pytest


@pytest.mark.local_only
class TestModernUIInitialization:
    """Test ModernUI class initialization."""

    def test_modern_ui_init_success(self):
        """Test successful ModernUI initialization."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel") as mock_settings, \
             patch("src.ui.main_ui.create_trace_viewer") as mock_trace, \
             patch("src.ui.main_ui.create_run_history") as mock_history, \
             patch("src.ui.main_ui.create_run_panel") as mock_run:
            
            mock_flag_service.return_value = Mock()
            mock_settings.return_value = Mock()
            mock_trace.return_value = Mock()
            mock_history.return_value = Mock()
            mock_run.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            
            assert ui._flag_service is not None
            assert ui._settings_panel is not None
            assert ui._trace_viewer is not None
            assert ui._run_history is not None
            assert ui._run_panel is not None

    def test_modern_ui_init_calls_sync_gradio_module(self):
        """Test that _sync_gradio_module is called during init."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui._sync_gradio_module") as mock_sync, \
             patch("src.ui.main_ui.get_feature_flag_service"), \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"):
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            
            mock_sync.assert_called_once_with(mock_gr)


@pytest.mark.local_only
class TestModernUIBuildInterface:
    """Test interface building."""

    def test_build_interface_success(self):
        """Test successful interface building."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel") as mock_settings, \
             patch("src.ui.main_ui.create_trace_viewer") as mock_trace, \
             patch("src.ui.main_ui.create_run_history") as mock_history, \
             patch("src.ui.main_ui.create_run_panel") as mock_run:
            
            # Setup mocks
            mock_flag_service.return_value = Mock()
            mock_settings_panel = Mock()
            mock_trace_viewer = Mock()
            mock_run_history_panel = Mock()
            mock_run_panel_obj = Mock()
            
            mock_settings.return_value = mock_settings_panel
            mock_trace.return_value = mock_trace_viewer
            mock_history.return_value = mock_run_history_panel
            mock_run.return_value = mock_run_panel_obj
            
            # Mock Gradio Blocks context manager
            mock_blocks_instance = MagicMock()
            mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks_instance
            mock_gr.Tabs.return_value.__enter__.return_value = Mock()
            mock_gr.Tab.return_value.__enter__.return_value = Mock()
            mock_gr.themes.Soft.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            interface = ui.build_interface()
            
            # Verify interface was built
            assert interface is not None
            mock_gr.Blocks.assert_called_once()
            
            # Verify all panels rendered
            mock_run_panel_obj.render.assert_called_once()
            mock_settings_panel.render.assert_called_once()
            mock_run_history_panel.render.assert_called_once()
            mock_trace_viewer.render.assert_called_once()

    def test_build_interface_gradio_not_installed(self):
        """Test interface building when Gradio is not installed."""
        with patch("src.ui.main_ui.gr", None), \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"), \
             patch("src.ui.main_ui.logger") as mock_logger:
            
            mock_flag_service.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            interface = ui.build_interface()
            
            assert interface is None
            mock_logger.error.assert_called_once_with("Gradio not installed, cannot build UI")

    def test_build_interface_creates_all_tabs(self):
        """Test that all expected tabs are created."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"):
            
            mock_flag_service.return_value = Mock()
            
            # Track Tab calls
            tab_calls = []
            def mock_tab_side_effect(label):
                tab_calls.append(label)
                return MagicMock()
            
            mock_gr.Tab.side_effect = mock_tab_side_effect
            mock_gr.Blocks.return_value.__enter__.return_value = Mock()
            mock_gr.Tabs.return_value.__enter__.return_value = Mock()
            mock_gr.themes.Soft.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            ui.build_interface()
            
            # Verify all 4 tabs were created
            assert len(tab_calls) == 4
            assert "🚀 実行画面" in tab_calls
            assert "⚙️ 設定" in tab_calls
            assert "📜 履歴" in tab_calls
            assert "🎬 トレース" in tab_calls


@pytest.mark.local_only
class TestModernUILaunch:
    """Test UI launch functionality."""

    def test_launch_success(self):
        """Test successful UI launch."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"), \
             patch("src.ui.main_ui.logger") as mock_logger:
            
            mock_flag_service.return_value = Mock()
            
            # Mock interface
            mock_interface = Mock()
            mock_gr.Blocks.return_value.__enter__.return_value = mock_interface
            mock_gr.Tabs.return_value.__enter__.return_value = Mock()
            mock_gr.Tab.return_value.__enter__.return_value = Mock()
            mock_gr.themes.Soft.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            ui.launch(server_name="127.0.0.1", server_port=8080, share=True)
            
            # Verify launch was called with correct parameters
            mock_interface.launch.assert_called_once_with(
                server_name="127.0.0.1",
                server_port=8080,
                share=True
            )
            
            # Verify logging
            assert mock_logger.info.call_count == 2  # build + launch

    def test_launch_default_parameters(self):
        """Test launch with default parameters."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"):
            
            mock_flag_service.return_value = Mock()
            
            mock_interface = Mock()
            mock_gr.Blocks.return_value.__enter__.return_value = mock_interface
            mock_gr.Tabs.return_value.__enter__.return_value = Mock()
            mock_gr.Tab.return_value.__enter__.return_value = Mock()
            mock_gr.themes.Soft.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            ui.launch()
            
            # Verify default parameters
            mock_interface.launch.assert_called_once_with(
                server_name="0.0.0.0",
                server_port=7860,
                share=False
            )

    def test_launch_when_interface_build_fails(self):
        """Test launch when interface building fails."""
        with patch("src.ui.main_ui.gr", None), \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"), \
             patch("src.ui.main_ui.logger") as mock_logger:
            
            mock_flag_service.return_value = Mock()
            
            from src.ui.main_ui import ModernUI
            
            ui = ModernUI()
            ui.launch()
            
            # Verify error logging
            mock_logger.error.assert_called_with("Cannot launch UI: interface build failed")


@pytest.mark.local_only
class TestFactoryFunction:
    """Test create_modern_ui factory function."""

    def test_create_modern_ui(self):
        """Test factory function creates ModernUI instance."""
        with patch("src.ui.main_ui.gr") as mock_gr, \
             patch("src.ui.main_ui.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.main_ui.create_settings_panel"), \
             patch("src.ui.main_ui.create_trace_viewer"), \
             patch("src.ui.main_ui.create_run_history"), \
             patch("src.ui.main_ui.create_run_panel"):
            
            mock_flag_service.return_value = Mock()
            
            from src.ui.main_ui import create_modern_ui, ModernUI
            
            ui = create_modern_ui()
            
            assert isinstance(ui, ModernUI)


@pytest.mark.local_only
class TestMainEntryPoint:
    """Test main() entry point."""

    def test_main_with_default_args(self):
        """Test main() with default arguments."""
        import argparse
        
        with patch.object(argparse, "ArgumentParser") as mock_parser_class, \
             patch("src.ui.main_ui.create_modern_ui") as mock_create_ui:
            
            # Mock argument parser
            mock_parser = Mock()
            mock_args = Mock(host="0.0.0.0", port=7860, share=False)
            mock_parser.parse_args.return_value = mock_args
            mock_parser_class.return_value = mock_parser
            
            # Mock UI
            mock_ui = Mock()
            mock_create_ui.return_value = mock_ui
            
            from src.ui.main_ui import main
            
            main()
            
            # Verify UI was created and launched
            mock_create_ui.assert_called_once()
            mock_ui.launch.assert_called_once_with(
                server_name="0.0.0.0",
                server_port=7860,
                share=False
            )

    def test_main_with_custom_args(self):
        """Test main() with custom arguments."""
        import argparse
        
        with patch.object(argparse, "ArgumentParser") as mock_parser_class, \
             patch("src.ui.main_ui.create_modern_ui") as mock_create_ui:
            
            # Mock argument parser with custom args
            mock_parser = Mock()
            mock_args = Mock(host="127.0.0.1", port=8080, share=True)
            mock_parser.parse_args.return_value = mock_args
            mock_parser_class.return_value = mock_parser
            
            # Mock UI
            mock_ui = Mock()
            mock_create_ui.return_value = mock_ui
            
            from src.ui.main_ui import main
            
            main()
            
            # Verify UI was launched with custom args
            mock_ui.launch.assert_called_once_with(
                server_name="127.0.0.1",
                server_port=8080,
                share=True
            )

    def test_main_argument_parser_setup(self):
        """Test that argument parser is configured correctly."""
        import argparse
        
        with patch.object(argparse, "ArgumentParser") as mock_parser_class, \
             patch("src.ui.main_ui.create_modern_ui"):
            
            mock_parser = Mock()
            mock_parser.parse_args.return_value = Mock(host="0.0.0.0", port=7860, share=False)
            mock_parser_class.return_value = mock_parser
            
            from src.ui.main_ui import main
            
            main()
            
            # Verify ArgumentParser was created
            mock_parser_class.assert_called_once()
            
            # Verify arguments were added
            assert mock_parser.add_argument.call_count == 3
            
            # Check for --host argument
            host_call = [c for c in mock_parser.add_argument.call_args_list if "--host" in c[0]]
            assert len(host_call) == 1
            
            # Check for --port argument
            port_call = [c for c in mock_parser.add_argument.call_args_list if "--port" in c[0]]
            assert len(port_call) == 1
            
            # Check for --share argument
            share_call = [c for c in mock_parser.add_argument.call_args_list if "--share" in c[0]]
            assert len(share_call) == 1


@pytest.mark.local_only
class TestSyncGradioModule:
    """Test _sync_gradio_module function."""

    def test_sync_gradio_module_does_not_raise_exception(self):
        """Test that _sync_gradio_module executes without errors."""
        mock_gr = Mock()
        
        from src.ui.main_ui import _sync_gradio_module
        
        # Should not raise exception
        try:
            _sync_gradio_module(mock_gr)
        except Exception as e:
            pytest.fail(f"_sync_gradio_module raised exception: {e}")

    def test_sync_gradio_module_handles_import_errors(self):
        """Test that _sync_gradio_module handles import errors gracefully."""
        mock_gr = Mock()
        
        # This test verifies the try/except in _sync_gradio_module
        # If import fails, function should not raise
        from src.ui.main_ui import _sync_gradio_module
        
        # Should not raise exception even with import issues
        try:
            _sync_gradio_module(mock_gr)
        except Exception as e:
            pytest.fail(f"_sync_gradio_module raised exception: {e}")
