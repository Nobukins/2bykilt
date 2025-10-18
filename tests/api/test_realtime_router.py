"""
Tests for src/api/realtime_router.py

This module tests WebSocket realtime endpoints for UI updates.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
from fastapi import WebSocket
from fastapi.testclient import TestClient

from src.api.realtime_router import (
    _build_run_history_payload,
    _load_history_entries,
    _compute_stats,
    router
)


class TestLoadHistoryEntries:
    """Tests for _load_history_entries function."""
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_load_entries_file_not_exists(self, mock_file):
        """Test loading when file doesn't exist."""
        mock_file.exists.return_value = False
        
        result = _load_history_entries()
        
        assert result == []
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_load_entries_valid_json(self, mock_file):
        """Test loading valid JSON entries."""
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps([
            {"id": "run1", "status": "success"},
            {"id": "run2", "status": "failed"}
        ])
        
        result = _load_history_entries()
        
        assert len(result) == 2
        assert result[0]["id"] == "run1"
        assert result[1]["status"] == "failed"
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_load_entries_invalid_json(self, mock_file):
        """Test handling of invalid JSON."""
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "{invalid json"
        
        result = _load_history_entries()
        
        assert result == []
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_load_entries_read_error(self, mock_file):
        """Test handling of file read errors."""
        mock_file.exists.return_value = True
        mock_file.read_text.side_effect = IOError("Cannot read file")
        
        result = _load_history_entries()
        
        assert result == []
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_load_entries_empty_json(self, mock_file):
        """Test loading empty JSON array."""
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = "[]"
        
        result = _load_history_entries()
        
        assert result == []


class TestComputeStats:
    """Tests for _compute_stats function."""
    
    def test_compute_stats_empty_list(self):
        """Test stats computation with empty entries."""
        result = _compute_stats([])
        
        assert result["total"] == 0
        assert result["success"] == 0
        assert result["success_rate"] == pytest.approx(0.0)
        assert result["avg_duration"] == pytest.approx(0.0)
    
    def test_compute_stats_all_success(self):
        """Test stats with all successful entries."""
        entries = [
            {"status": "success", "duration_sec": 10.0},
            {"status": "success", "duration_sec": 20.0},
            {"status": "success", "duration_sec": 30.0}
        ]
        
        result = _compute_stats(entries)
        
        assert result["total"] == 3
        assert result["success"] == 3
        assert result["success_rate"] == pytest.approx(100.0)
        assert result["avg_duration"] == pytest.approx(20.0)
    
    def test_compute_stats_mixed_status(self):
        """Test stats with mixed success/failure."""
        entries = [
            {"status": "success", "duration_sec": 10.0},
            {"status": "failed", "duration_sec": 5.0},
            {"status": "success", "duration_sec": 15.0}
        ]
        
        result = _compute_stats(entries)
        
        assert result["total"] == 3
        assert result["success"] == 2
        assert result["success_rate"] == pytest.approx(66.666, rel=0.01)
        assert result["avg_duration"] == pytest.approx(10.0)
    
    def test_compute_stats_no_duration(self):
        """Test stats when duration is missing."""
        entries = [
            {"status": "success"},
            {"status": "success"}
        ]
        
        result = _compute_stats(entries)
        
        assert result["total"] == 2
        assert result["success"] == 2
        assert result["avg_duration"] == pytest.approx(0.0)
    
    def test_compute_stats_partial_duration(self):
        """Test stats with partial duration data."""
        entries = [
            {"status": "success", "duration_sec": 10.0},
            {"status": "failed"},
            {"status": "success", "duration_sec": 20.0}
        ]
        
        result = _compute_stats(entries)
        
        assert result["total"] == 3
        assert result["avg_duration"] == pytest.approx(10.0)  # (10 + 0 + 20) / 3


class TestBuildRunHistoryPayload:
    """Tests for _build_run_history_payload function."""
    
    @patch('src.api.realtime_router._load_history_entries')
    def test_build_payload_empty(self, mock_load):
        """Test building payload with no entries."""
        mock_load.return_value = []
        
        result = _build_run_history_payload()
        
        payload = json.loads(result)
        assert payload["type"] == "run_history"
        assert payload["entries"] == []
        assert payload["stats"]["total"] == 0
    
    @patch('src.api.realtime_router._load_history_entries')
    def test_build_payload_with_entries(self, mock_load):
        """Test building payload with entries."""
        mock_load.return_value = [
            {"id": "run1", "status": "success", "duration_sec": 10.0}
        ]
        
        result = _build_run_history_payload()
        
        payload = json.loads(result)
        assert payload["type"] == "run_history"
        assert len(payload["entries"]) == 1
        assert payload["stats"]["total"] == 1
        assert payload["stats"]["success"] == 1
    
    @patch('src.api.realtime_router._load_history_entries')
    def test_build_payload_json_format(self, mock_load):
        """Test payload is valid JSON."""
        mock_load.return_value = [
            {"name": "テスト", "status": "success"}  # Non-ASCII
        ]
        
        result = _build_run_history_payload()
        
        # Should be valid JSON
        payload = json.loads(result)
        assert "テスト" in json.dumps(payload, ensure_ascii=False)


class TestRunHistoryWebSocket:
    """Tests for run_history_stream WebSocket endpoint."""
    
    @pytest.mark.asyncio
    @patch('src.api.realtime_router.get_feature_flag_service')
    @patch('src.api.realtime_router._build_run_history_payload')
    async def test_websocket_sends_updates(self, mock_build, mock_flag_service):
        """Test WebSocket sends updates when enabled."""
        # Mock feature flag service
        mock_service = MagicMock()
        mock_state = MagicMock()
        mock_state.ui_realtime_updates = True
        mock_service.get_current_state.return_value = mock_state
        mock_flag_service.return_value = mock_service
        
        # Mock payload builder
        payload1 = json.dumps({"type": "run_history", "entries": []})
        payload2 = json.dumps({"type": "run_history", "entries": [{"id": "new"}]})
        mock_build.side_effect = [payload1, payload2, payload2]  # Third call same as second
        
        # Mock WebSocket
        mock_ws = AsyncMock(spec=WebSocket)
        
        # Run for limited time
        from src.api.realtime_router import run_history_stream
        
        async def limited_run():
            task = asyncio.create_task(run_history_stream(mock_ws))
            await asyncio.sleep(0.1)  # Let it run briefly
            task.cancel()
            await task
        
        with pytest.raises(asyncio.CancelledError):
            await limited_run()
        
        # Verify WebSocket was accepted
        mock_ws.accept.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.api.realtime_router.get_feature_flag_service')
    @patch('src.api.realtime_router._build_run_history_payload')
    @patch('src.api.realtime_router._POLL_INTERVAL', 0.01)
    async def test_websocket_disabled_feature_flag(self, mock_build, mock_flag_service):
        """Test WebSocket when feature flag is disabled."""
        # Mock feature flag service with disabled flag
        mock_service = MagicMock()
        mock_state = MagicMock()
        mock_state.ui_realtime_updates = False
        mock_service.get_current_state.return_value = mock_state
        mock_flag_service.return_value = mock_service
        
        mock_ws = AsyncMock(spec=WebSocket)
        
        from src.api.realtime_router import run_history_stream
        
        async def limited_run():
            task = asyncio.create_task(run_history_stream(mock_ws))
            await asyncio.sleep(0.05)
            task.cancel()
            await task
        
        with pytest.raises(asyncio.CancelledError):
            await limited_run()
        
        # Should not send any data when disabled
        mock_build.assert_not_called()
    
    @pytest.mark.asyncio
    @patch('src.api.realtime_router.get_feature_flag_service')
    async def test_websocket_disconnect(self, mock_flag_service):
        """Test WebSocket handles disconnect gracefully."""
        mock_service = MagicMock()
        mock_state = MagicMock()
        mock_state.ui_realtime_updates = True
        mock_service.get_current_state.return_value = mock_state
        mock_flag_service.return_value = mock_service
        
        mock_ws = AsyncMock(spec=WebSocket)
        from fastapi import WebSocketDisconnect
        mock_ws.send_text.side_effect = WebSocketDisconnect()
        
        from src.api.realtime_router import run_history_stream
        
        # Should handle disconnect without raising
        await run_history_stream(mock_ws)


class TestRealtimeRouterIntegration:
    """Integration tests for realtime router."""
    
    @patch('src.api.realtime_router._RUN_HISTORY_FILE')
    def test_full_payload_workflow(self, mock_file):
        """Test complete workflow from file to payload."""
        # Setup mock file with test data
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = json.dumps([
            {"id": "1", "status": "success", "duration_sec": 15.0},
            {"id": "2", "status": "failed", "duration_sec": 5.0},
            {"id": "3", "status": "success", "duration_sec": 25.0}
        ])
        
        # Build payload
        payload_str = _build_run_history_payload()
        payload = json.loads(payload_str)
        
        # Verify complete payload structure
        assert payload["type"] == "run_history"
        assert len(payload["entries"]) == 3
        assert payload["stats"]["total"] == 3
        assert payload["stats"]["success"] == 2
        assert payload["stats"]["success_rate"] == pytest.approx(66.666, rel=0.01)
        assert payload["stats"]["avg_duration"] == pytest.approx(15.0)
