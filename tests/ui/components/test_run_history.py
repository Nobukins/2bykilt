"""
Tests for src/ui/components/run_history.py

This module tests Gradio UI component for execution history display.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.ui.components.run_history import RunHistory


class TestRunHistoryInit:
    """Tests for RunHistory initialization."""
    
    def test_init_with_defaults(self, tmp_path):
        """Test initialization with default parameters."""
        history_file = tmp_path / "run_history.json"
        history_file.write_text("[]")
        
        with patch('src.ui.components.run_history.Path', return_value=history_file):
            run_history = RunHistory()
            
            assert run_history._history_file == history_file
            assert run_history._history_data == []
    
    def test_init_with_custom_file(self, tmp_path):
        """Test initialization with custom history file."""
        custom_file = tmp_path / "custom_history.json"
        custom_file.write_text('[{"id": "test-1"}]')
        
        run_history = RunHistory(history_file=custom_file)
        
        assert run_history._history_file == custom_file
        assert len(run_history._history_data) == 1


class TestRunHistoryLoadHistory:
    """Tests for _load_history method."""
    
    def test_load_history_success(self, tmp_path):
        """Test loading history from valid JSON file."""
        history_file = tmp_path / "history.json"
        history_data = [
            {"id": "run-1", "status": "success"},
            {"id": "run-2", "status": "failure"}
        ]
        history_file.write_text(json.dumps(history_data))
        
        run_history = RunHistory(history_file=history_file)
        
        assert len(run_history._history_data) == 2
        assert run_history._history_data[0]["id"] == "run-1"
        assert run_history._history_data[1]["status"] == "failure"
    
    def test_load_history_file_not_found(self, tmp_path):
        """Test loading history when file doesn't exist."""
        nonexistent = tmp_path / "nonexistent.json"
        
        run_history = RunHistory(history_file=nonexistent)
        
        assert run_history._history_data == []
    
    def test_load_history_invalid_json(self, tmp_path):
        """Test loading history with invalid JSON."""
        history_file = tmp_path / "invalid.json"
        history_file.write_text("not valid json")
        
        run_history = RunHistory(history_file=history_file)
        
        assert run_history._history_data == []
    
    def test_load_history_empty_file(self, tmp_path):
        """Test loading history from empty file."""
        history_file = tmp_path / "empty.json"
        history_file.write_text("")
        
        run_history = RunHistory(history_file=history_file)
        
        assert run_history._history_data == []


class TestRunHistoryFormatHistoryData:
    """Tests for _format_history_data method."""
    
    def test_format_empty_history(self, tmp_path):
        """Test formatting empty history."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        run_history = RunHistory(history_file=history_file)
        rows = run_history._format_history_data("all")
        
        assert isinstance(rows, list)
        assert len(rows) == 0
    
    def test_format_single_entry(self, tmp_path):
        """Test formatting single history entry."""
        history_file = tmp_path / "history.json"
        entry = {
            "id": "test-run-1",
            "timestamp": "2025-01-15 10:30:00",
            "status": "success",
            "duration_sec": 5.2,
            "command_summary": "test command"
        }
        history_file.write_text(json.dumps([entry]))
        
        run_history = RunHistory(history_file=history_file)
        rows = run_history._format_history_data("all")
        
        assert len(rows) == 1
        assert rows[0][0] == "2025-01-15 10:30:00"  # timestamp
        assert "成功" in rows[0][1]  # status
        assert rows[0][2] == "test command"  # summary
        assert rows[0][3] == pytest.approx(5.2)  # duration
    
    def test_format_multiple_entries(self, tmp_path):
        """Test formatting multiple history entries."""
        history_file = tmp_path / "history.json"
        entries = [
            {"id": "run-1", "status": "success", "duration_sec": 3.0, "timestamp": "2025-01-15 10:00:00", "command_summary": "cmd1"},
            {"id": "run-2", "status": "failure", "duration_sec": 1.5, "timestamp": "2025-01-15 11:00:00", "command_summary": "cmd2"},
            {"id": "run-3", "status": "success", "duration_sec": 4.2, "timestamp": "2025-01-15 12:00:00", "command_summary": "cmd3"}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        rows = run_history._format_history_data("all")
        
        assert len(rows) == 3
        assert rows[0][2] == "cmd1"
        assert rows[1][2] == "cmd2"
        assert rows[2][2] == "cmd3"


class TestRunHistoryApplyFilter:
    """Tests for _apply_filter method."""
    
    def test_filter_all(self, tmp_path):
        """Test applying 'all' filter."""
        history_file = tmp_path / "history.json"
        entries = [
            {"id": "run-1", "status": "success"},
            {"id": "run-2", "status": "failure"},
            {"id": "run-3", "status": "success"}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        filtered = run_history._apply_filter("all")
        
        assert len(filtered) == 3
    
    def test_filter_success(self, tmp_path):
        """Test applying 'success' filter."""
        history_file = tmp_path / "history.json"
        entries = [
            {"id": "run-1", "status": "success"},
            {"id": "run-2", "status": "failure"},
            {"id": "run-3", "status": "success"}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        filtered = run_history._apply_filter("success")
        
        assert len(filtered) == 2
        assert all(e["status"] == "success" for e in filtered)
    
    def test_filter_failure(self, tmp_path):
        """Test applying 'failure' filter."""
        history_file = tmp_path / "history.json"
        entries = [
            {"id": "run-1", "status": "success"},
            {"id": "run-2", "status": "failure"},
            {"id": "run-3", "status": "failure"}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        filtered = run_history._apply_filter("failure")
        
        assert len(filtered) == 2
        assert all(e["status"] != "success" for e in filtered)
    
    def test_filter_empty_data(self, tmp_path):
        """Test applying filter to empty data."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        run_history = RunHistory(history_file=history_file)
        filtered = run_history._apply_filter("success")
        
        assert filtered == []


class TestRunHistoryGetStatsummary:
    """Tests for _get_stats_summary method."""
    
    def test_stats_empty_data(self, tmp_path):
        """Test computing stats for empty data."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        run_history = RunHistory(history_file=history_file)
        stats = run_history._get_stats_summary()
        
        assert "履歴データなし" in stats
    
    def test_stats_all_success(self, tmp_path):
        """Test computing stats for all successful runs."""
        history_file = tmp_path / "history.json"
        entries = [
            {"status": "success", "duration_sec": 2.0},
            {"status": "success", "duration_sec": 4.0},
            {"status": "success", "duration_sec": 6.0}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        stats = run_history._get_stats_summary()
        
        assert "総実行回数: 3" in stats
        assert "成功率: 100.0%" in stats
        assert "平均実行時間: 4.00 秒" in stats
    
    def test_stats_mixed_results(self, tmp_path):
        """Test computing stats for mixed success/failure."""
        history_file = tmp_path / "history.json"
        entries = [
            {"status": "success", "duration_sec": 5.0},
            {"status": "failure", "duration_sec": 2.0},
            {"status": "success", "duration_sec": 3.0}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        stats = run_history._get_stats_summary()
        
        assert "総実行回数: 3" in stats
        assert "成功率: 66.7%" in stats
        assert "平均実行時間: 3.33 秒" in stats
    
    def test_stats_all_failure(self, tmp_path):
        """Test computing stats for all failed runs."""
        history_file = tmp_path / "history.json"
        entries = [
            {"status": "failure", "duration_sec": 1.0},
            {"status": "failure", "duration_sec": 2.0}
        ]
        history_file.write_text(json.dumps(entries))
        
        run_history = RunHistory(history_file=history_file)
        stats = run_history._get_stats_summary()
        
        assert "総実行回数: 2" in stats
        assert "成功率: 0.0%" in stats
        assert "平均実行時間: 1.50 秒" in stats


class TestRunHistoryAddEntry:
    """Tests for add_entry method."""
    
    def test_add_entry_to_empty_history(self, tmp_path):
        """Test adding entry to empty history."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        run_history = RunHistory(history_file=history_file)
        
        run_history.add_entry(
            status="success",
            command_summary="test command",
            duration_sec=3.5
        )
        
        assert len(run_history._history_data) == 1
        assert run_history._history_data[0]["status"] == "success"
        assert run_history._history_data[0]["command_summary"] == "test command"
    
    def test_add_entry_to_existing_history(self, tmp_path):
        """Test adding entry to existing history."""
        history_file = tmp_path / "history.json"
        existing = [{"timestamp": "2025-01-01", "status": "success", "command_summary": "existing", "duration_sec": 1.0}]
        history_file.write_text(json.dumps(existing))
        
        run_history = RunHistory(history_file=history_file)
        
        run_history.add_entry(
            status="failure",
            command_summary="new command",
            duration_sec=2.5
        )
        
        assert len(run_history._history_data) == 2
        assert run_history._history_data[1]["status"] == "failure"
    
    def test_add_entry_persists_to_file(self, tmp_path):
        """Test that adding entry persists to JSON file."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        run_history = RunHistory(history_file=history_file)
        
        run_history.add_entry(
            status="success",
            command_summary="persisted command",
            duration_sec=1.5
        )
        
        # Verify file was updated
        saved_data = json.loads(history_file.read_text())
        assert len(saved_data) == 1
        assert saved_data[0]["command_summary"] == "persisted command"


class TestRunHistoryRender:
    """Tests for render method."""
    
    @patch('src.ui.components.run_history.gr')
    @patch('src.ui.components.run_history.get_feature_flag_service')
    def test_render_creates_components(self, mock_get_feature_service, mock_gr, tmp_path):
        """Test that render creates Gradio components."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        mock_feature_service = MagicMock()
        mock_feature_service.is_enabled.return_value = True
        mock_get_feature_service.return_value = mock_feature_service
        
        # Mock Gradio components
        mock_column = MagicMock()
        mock_row = MagicMock()
        mock_gr.Column.return_value.__enter__.return_value = mock_column
        mock_gr.Row.return_value.__enter__.return_value = mock_row
        
        run_history = RunHistory(history_file=history_file)
        run_history.render()
        
        # Verify Gradio components were created
        assert mock_gr.Markdown.called
        assert mock_gr.Radio.called
        assert mock_gr.Dataframe.called
        assert mock_gr.Button.called
    
    @patch('src.ui.components.run_history.gr')
    @patch('src.ui.components.run_history.get_feature_flag_service')
    def test_render_without_realtime_updates(self, mock_get_feature_service, mock_gr, tmp_path):
        """Test render when realtime updates are disabled."""
        history_file = tmp_path / "history.json"
        history_file.write_text("[]")
        
        mock_feature_service = MagicMock()
        mock_feature_service.is_enabled.return_value = False
        mock_get_feature_service.return_value = mock_feature_service
        
        mock_column = MagicMock()
        mock_gr.Column.return_value.__enter__.return_value = mock_column
        
        run_history = RunHistory(history_file=history_file)
        run_history.render()
        
        # Should still create basic components
        assert mock_gr.Markdown.called
        assert mock_gr.Dataframe.called


class TestRunHistoryIntegration:
    """Integration tests for RunHistory component."""
    
    def test_full_workflow(self, tmp_path):
        """Test complete workflow from load to filter to add."""
        history_file = tmp_path / "workflow_history.json"
        initial_data = [
            {"timestamp": "2025-01-01", "status": "success", "command_summary": "cmd1", "duration_sec": 2.5},
            {"timestamp": "2025-01-02", "status": "failure", "command_summary": "cmd2", "duration_sec": 1.0},
        ]
        history_file.write_text(json.dumps(initial_data))
        
        run_history = RunHistory(history_file=history_file)
        
        # Load and format
        all_data = run_history._apply_filter("all")
        assert len(all_data) == 2
        
        # Filter success only
        success_only = run_history._apply_filter("success")
        assert len(success_only) == 1
        
        # Compute stats
        stats = run_history._get_stats_summary()
        assert "総実行回数: 2" in stats
        assert "成功率: 50.0%" in stats
        
        # Add new entry
        run_history.add_entry(
            status="success",
            command_summary="cmd3",
            duration_sec=3.0
        )
        
        # Verify updated stats
        updated_stats = run_history._get_stats_summary()
        assert "総実行回数: 3" in updated_stats
        assert "成功率: 66.7%" in updated_stats
