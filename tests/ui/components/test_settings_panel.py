"""
Test suite for src/ui/components/settings_panel.py

Tests SettingsPanel class initialization, rendering, and interactions.
Focuses on FeatureFlagService integration, LLM status, and Gradio mocking.

Coverage Target: 26% → 70%+
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestSettingsPanelInitialization:
    """Test SettingsPanel class initialization."""

    def test_settings_panel_init_success(self):
        """Test successful SettingsPanel initialization."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            assert panel.flag_service is not None
            assert panel.llm_gateway is not None
            mock_flag_service.assert_called_once()
            mock_llm_gateway.assert_called_once()


class TestSettingsPanelRender:
    """Test SettingsPanel rendering."""

    def test_render_creates_panel(self):
        """Test that render creates a Gradio panel."""
        with patch("src.ui.components.settings_panel.gr") as mock_gr, \
             patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            # Mock flag service state
            mock_state = Mock()
            mock_state.runner_engine = "playwright"
            mock_state.enable_llm = False
            mock_state.ui_modern_layout = True
            mock_state.ui_trace_viewer = True
            mock_state.ui_run_history = True
            mock_state.ui_realtime_updates = False
            
            mock_service = Mock()
            mock_service.get_current_state.return_value = mock_state
            mock_flag_service.return_value = mock_service
            mock_llm_gateway.return_value = Mock()
            
            # Mock Gradio components
            mock_column = MagicMock()
            mock_gr.Column.return_value.__enter__.return_value = mock_column
            mock_gr.Accordion.return_value.__enter__.return_value = Mock()
            mock_gr.Row.return_value.__enter__.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            result = panel.render()
            
            # Verify render was called
            assert result is not None
            mock_gr.Column.assert_called_once()
            mock_service.get_current_state.assert_called_once_with(force_refresh=True)

    def test_render_raises_when_gradio_not_available(self):
        """Test render raises RuntimeError when Gradio is not installed."""
        with patch("src.ui.components.settings_panel.gr", None), \
             patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            with pytest.raises(RuntimeError, match="Gradio is required"):
                panel.render()

    def test_render_creates_all_accordions(self):
        """Test that render creates all expected accordion sections."""
        with patch("src.ui.components.settings_panel.gr") as mock_gr, \
             patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            # Mock state
            mock_state = Mock()
            mock_state.runner_engine = "playwright"
            mock_state.enable_llm = True
            mock_state.ui_modern_layout = True
            mock_state.ui_trace_viewer = True
            mock_state.ui_run_history = True
            mock_state.ui_realtime_updates = True
            
            mock_service = Mock()
            mock_service.get_current_state.return_value = mock_state
            mock_flag_service.return_value = mock_service
            mock_llm_gateway.return_value = Mock()
            
            # Track Accordion calls
            accordion_labels = []
            def mock_accordion(label=None, open=True):
                if label:
                    accordion_labels.append(label)
                return MagicMock()
            
            mock_gr.Accordion.side_effect = mock_accordion
            mock_gr.Column.return_value.__enter__.return_value = Mock()
            mock_gr.Row.return_value.__enter__.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            panel.render()
            
            # Verify all accordions were created
            assert "ブラウザエンジン" in accordion_labels
            assert "LLM 機能" in accordion_labels
            assert "UI オプション" in accordion_labels


class TestSettingsPanelFormatMethods:
    """Test internal formatting methods."""

    def test_format_engine_info(self):
        """Test _format_engine_info method."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Create mock state
            mock_state = Mock()
            mock_state.runner_engine = "playwright"
            mock_state.runner_isolation = "process"
            
            result = panel._format_engine_info(mock_state)
            
            assert isinstance(result, str)
            assert "playwright" in result.lower()

    def test_format_llm_info(self):
        """Test _format_llm_info method."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Test with LLM enabled
            mock_state_enabled = Mock()
            mock_state_enabled.enable_llm = True
            
            result_enabled = panel._format_llm_info(mock_state_enabled)
            assert isinstance(result_enabled, str)
            assert "有効" in result_enabled or "Enabled" in result_enabled
            
            # Test with LLM disabled
            mock_state_disabled = Mock()
            mock_state_disabled.enable_llm = False
            
            result_disabled = panel._format_llm_info(mock_state_disabled)
            assert isinstance(result_disabled, str)
            assert "無効" in result_disabled or "Disabled" in result_disabled

    def test_format_ui_info(self):
        """Test _format_ui_info method."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Create mock state with various UI flags
            mock_state = Mock()
            mock_state.ui_modern_layout = True
            mock_state.ui_trace_viewer = True
            mock_state.ui_run_history = False
            mock_state.ui_realtime_updates = False
            
            result = panel._format_ui_info(mock_state)
            
            assert isinstance(result, str)


class TestSettingsPanelEventHandlers:
    """Test event handler methods."""

    def test_on_engine_change(self):
        """Test _on_engine_change handler."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway, \
             patch("src.ui.components.settings_panel.FeatureFlags") as mock_flags, \
             patch("src.ui.components.settings_panel.gr") as mock_gr:
            
            mock_service = Mock()
            mock_state = Mock()
            mock_state.runner_engine = "cdp"
            mock_service.get_current_state.return_value = mock_state
            mock_flag_service.return_value = mock_service
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Call handler
            result = panel._on_engine_change("cdp")
            
            # Verify it returns tuple (for Gradio outputs)
            assert isinstance(result, tuple)
            assert len(result) == 2  # Should return (dropdown, info_markdown)

    def test_on_llm_toggle(self):
        """Test _on_llm_toggle handler."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway, \
             patch("src.ui.components.settings_panel.FeatureFlags") as mock_flags, \
             patch("src.ui.components.settings_panel.gr") as mock_gr:
            
            mock_service = Mock()
            mock_state = Mock()
            mock_state.enable_llm = True
            mock_service.get_current_state.return_value = mock_state
            mock_flag_service.return_value = mock_service
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Call handler with True
            result = panel._on_llm_toggle(True)
            
            # Verify it returns tuple (for Gradio outputs)
            assert isinstance(result, tuple)
            assert len(result) == 2  # Should return (checkbox, info_markdown)

    def test_on_bool_flag_toggle(self):
        """Test _on_bool_flag_toggle handler."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway, \
             patch("src.ui.components.settings_panel.FeatureFlags") as mock_flags, \
             patch("src.ui.components.settings_panel.gr") as mock_gr:
            
            mock_service = Mock()
            mock_state = Mock()
            mock_state.ui_modern_layout = True
            mock_service.get_current_state.return_value = mock_state
            mock_flag_service.return_value = mock_service
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import SettingsPanel
            
            panel = SettingsPanel()
            
            # Call handler
            result = panel._on_bool_flag_toggle("ui.modern_layout", True)
            
            # Verify it returns tuple (for Gradio outputs)
            assert isinstance(result, tuple)


class TestCreateSettingsPanel:
    """Test create_settings_panel factory function."""

    def test_create_settings_panel(self):
        """Test factory function creates SettingsPanel instance."""
        with patch("src.ui.components.settings_panel.get_feature_flag_service") as mock_flag_service, \
             patch("src.ui.components.settings_panel.get_llm_gateway") as mock_llm_gateway:
            
            mock_flag_service.return_value = Mock()
            mock_llm_gateway.return_value = Mock()
            
            from src.ui.components.settings_panel import create_settings_panel, SettingsPanel
            
            panel = create_settings_panel()
            
            assert isinstance(panel, SettingsPanel)
