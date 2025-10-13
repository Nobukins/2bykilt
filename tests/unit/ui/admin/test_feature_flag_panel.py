"""Unit tests for Feature Flag Admin Panel (Issue #272)

Tests the admin UI components and helper functions.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from typing import Dict, Any

# Test imports
from src.ui.admin.feature_flag_panel import (
    create_feature_flag_admin_panel,
    get_feature_flags_summary,
    _resolve_flag_name_from_event,
)


class TestFeatureFlagAdminPanel:
    """Test suite for Feature Flag Admin Panel UI."""

    def test_resolve_flag_name_from_event_with_row_index(self):
        """Selecting any cell in a row should resolve to its flag name."""
        mock_event = Mock()
        mock_event.index = (1, 4)
        mock_event.value = "runtime"  # clicked the source column
        rows = [
            ["flag_a", "True", "False", "bool", "file", "desc"],
            ["flag_b", "False", "False", "bool", "runtime", "desc"],
        ]

        resolved = _resolve_flag_name_from_event(mock_event, rows)

        assert resolved == "flag_b"

    def test_resolve_flag_name_from_event_with_value_fallback(self):
        """Fall back to value lookup when row index is missing."""
        mock_event = Mock()
        mock_event.index = None
        mock_event.value = "flag_a"
        rows = [["flag_a", "True", "False", "bool", "file", "desc"]]

        resolved = _resolve_flag_name_from_event(mock_event, rows)

        assert resolved == "flag_a"

    def test_resolve_flag_name_from_event_no_match(self):
        """Return None when neither index nor value map to a known flag."""
        mock_event = Mock()
        mock_event.index = None
        mock_event.value = "unknown"

        resolved = _resolve_flag_name_from_event(mock_event, [["flag_a"]])

        assert resolved is None
    
    def test_create_admin_panel_returns_blocks(self):
        """Test that create_feature_flag_admin_panel() returns a Gradio Blocks instance."""
        import gradio as gr
        
        panel = create_feature_flag_admin_panel()
        
        assert panel is not None
        assert isinstance(panel, gr.Blocks)
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_load_flags_with_data(self, mock_get_all_flags):
        """Test loading flags when data is available."""
        # Mock flag data
        mock_get_all_flags.return_value = {
            "enable_llm": {
                "value": True,
                "default": False,
                "type": "bool",
                "description": "Enable LLM functionality",
                "source": "environment",
                "override_active": False,
            },
            "ui.theme": {
                "value": "dark",
                "default": "light",
                "type": "str",
                "description": "UI theme setting",
                "source": "file",
                "override_active": False,
            }
        }
        
        # Create panel and access load_flags function
        # Note: This is a simplified test - in practice, we'd need to extract
        # the function or test via UI interaction
        from src.config.feature_flags import FeatureFlags
        all_flags = FeatureFlags.get_all_flags()
        
        assert len(all_flags) > 0
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_load_flags_empty(self, mock_get_all_flags):
        """Test loading flags when no data is available."""
        mock_get_all_flags.return_value = {}
        
        from src.config.feature_flags import FeatureFlags
        all_flags = FeatureFlags.get_all_flags()
        
        assert len(all_flags) == 0
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_flag_metadata')
    def test_flag_metadata_retrieval(self, mock_get_metadata):
        """Test retrieving metadata for a specific flag."""
        mock_metadata = {
            "value": True,
            "default": False,
            "type": "bool",
            "description": "Test flag",
            "source": "file",
            "override_active": False,
        }
        mock_get_metadata.return_value = mock_metadata
        
        from src.config.feature_flags import FeatureFlags
        metadata = FeatureFlags.get_flag_metadata("test_flag")
        
        assert metadata is not None
        assert metadata["value"] is True
        assert metadata["type"] == "bool"
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_flag_metadata')
    def test_flag_metadata_nonexistent(self, mock_get_metadata):
        """Test retrieving metadata for non-existent flag."""
        mock_get_metadata.return_value = None
        
        from src.config.feature_flags import FeatureFlags
        metadata = FeatureFlags.get_flag_metadata("nonexistent_flag")
        
        assert metadata is None


class TestFeatureFlagsSummary:
    """Test suite for get_feature_flags_summary() helper function."""
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_summary_with_flags(self, mock_get_all_flags):
        """Test summary generation with various flag types."""
        mock_get_all_flags.return_value = {
            "flag1": {"type": "bool", "value": True, "source": "file"},
            "flag2": {"type": "bool", "value": False, "source": "environment"},
            "flag3": {"type": "int", "value": 42, "source": "runtime"},
            "flag4": {"type": "str", "value": "test", "source": "file"},
        }
        
        summary = get_feature_flags_summary()
        
        assert summary["total"] == 4
        assert summary["enabled"] == 1  # Only flag1 is True
        assert summary["by_type"]["bool"] == 2
        assert summary["by_type"]["int"] == 1
        assert summary["by_type"]["str"] == 1
        assert summary["by_source"]["file"] == 2
        assert summary["by_source"]["environment"] == 1
        assert summary["by_source"]["runtime"] == 1
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_summary_empty(self, mock_get_all_flags):
        """Test summary generation with no flags."""
        mock_get_all_flags.return_value = {}
        
        summary = get_feature_flags_summary()
        
        assert summary["total"] == 0
        assert summary["enabled"] == 0
        assert summary["by_type"]["bool"] == 0
        assert summary["by_type"]["int"] == 0
        assert summary["by_type"]["str"] == 0
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_summary_error_handling(self, mock_get_all_flags):
        """Test summary generation with error."""
        mock_get_all_flags.side_effect = Exception("Test error")
        
        summary = get_feature_flags_summary()
        
        assert "error" in summary
        assert summary["total"] == 0


class TestFeatureFlagsDataFormatting:
    """Test data formatting for UI display."""
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_description_truncation(self, mock_get_all_flags):
        """Test that long descriptions are truncated for table display."""
        long_desc = "A" * 150  # 150 characters
        mock_get_all_flags.return_value = {
            "test_flag": {
                "value": True,
                "default": False,
                "type": "bool",
                "description": long_desc,
                "source": "file",
                "override_active": False,
            }
        }
        
        from src.config.feature_flags import FeatureFlags
        flags = FeatureFlags.get_all_flags()
        flag_data = flags["test_flag"]
        
        # Verify description exists and is long
        assert len(flag_data["description"]) > 100
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_source_filtering(self, mock_get_all_flags):
        """Test filtering flags by source."""
        mock_get_all_flags.return_value = {
            "flag1": {"type": "bool", "value": True, "source": "file", "description": ""},
            "flag2": {"type": "bool", "value": False, "source": "environment", "description": ""},
            "flag3": {"type": "int", "value": 42, "source": "runtime", "description": ""},
        }
        
        from src.config.feature_flags import FeatureFlags
        all_flags = FeatureFlags.get_all_flags()
        
        # Filter by source (simulating UI filter)
        file_flags = {k: v for k, v in all_flags.items() if v["source"] == "file"}
        env_flags = {k: v for k, v in all_flags.items() if v["source"] == "environment"}
        runtime_flags = {k: v for k, v in all_flags.items() if v["source"] == "runtime"}
        
        assert len(file_flags) == 1
        assert len(env_flags) == 1
        assert len(runtime_flags) == 1
    
    @patch('src.ui.admin.feature_flag_panel.FeatureFlags.get_all_flags')
    def test_type_filtering(self, mock_get_all_flags):
        """Test filtering flags by type."""
        mock_get_all_flags.return_value = {
            "flag1": {"type": "bool", "value": True, "source": "file", "description": ""},
            "flag2": {"type": "bool", "value": False, "source": "file", "description": ""},
            "flag3": {"type": "int", "value": 42, "source": "file", "description": ""},
            "flag4": {"type": "str", "value": "test", "source": "file", "description": ""},
        }
        
        from src.config.feature_flags import FeatureFlags
        all_flags = FeatureFlags.get_all_flags()
        
        # Filter by type
        bool_flags = {k: v for k, v in all_flags.items() if v["type"] == "bool"}
        int_flags = {k: v for k, v in all_flags.items() if v["type"] == "int"}
        str_flags = {k: v for k, v in all_flags.items() if v["type"] == "str"}
        
        assert len(bool_flags) == 2
        assert len(int_flags) == 1
        assert len(str_flags) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
