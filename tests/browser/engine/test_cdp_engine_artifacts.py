"""
Tests for CDPEngine artifacts and shutdown (Issue #340 Phase 2)

Coverage targets:
- CDPEngine.capture_artifacts
- CDPEngine.shutdown

Target: 49% → 60% coverage for cdp_engine.py
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path

from src.browser.engine.cdp_engine import CDPEngine
from src.browser.engine.browser_engine import (
    LaunchContext,
    ArtifactCaptureError,
)


class TestCDPEngineCaptureArtifacts:
    """Test CDPEngine artifact capture"""
    
    @pytest.mark.asyncio
    async def test_capture_screenshot(self):
        """Test screenshot artifact capture"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        # Mock Page.captureScreenshot
        engine._cdp_client.send_command = AsyncMock(return_value={
            "data": "aVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FBQUFFQUFBQUIuLi4="  # base64 placeholder
        })
        
        with patch.object(Path, 'write_bytes'):
            artifacts = await engine.capture_artifacts(["screenshot"])
        
        assert "screenshot" in artifacts
        assert artifacts["screenshot"].endswith(".png")
        engine._cdp_client.send_command.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_capture_trace_with_data(self):
        """Test trace artifact capture with event data"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        engine._trace_data = [
            {"method": "Page.navigate", "timestamp": 1234567890, "url": "https://example.com"},
            {"method": "Page.loadEventFired", "timestamp": 1234567891}
        ]
        
        with patch.object(Path, 'parent') as mock_parent, \
             patch.object(Path, 'write_text'):
            mock_parent.mkdir = MagicMock()
            artifacts = await engine.capture_artifacts(["trace"])
        
        assert "trace" in artifacts
        assert artifacts["trace"].endswith(".json")
        assert "cdp_trace_" in artifacts["trace"]
    
    @pytest.mark.asyncio
    async def test_capture_trace(self):
        """Test trace artifact capture"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        engine._trace_data = [
            {"method": "Page.navigate", "timestamp": 1234567890},
            {"method": "Page.loadEventFired", "timestamp": 1234567891}
        ]
        
        with patch('builtins.open', create=True):
            with patch('json.dump'):
                artifacts = await engine.capture_artifacts(["trace"])
        
        assert "trace" in artifacts
        assert artifacts["trace"].endswith(".json")
    
    @pytest.mark.asyncio
    async def test_capture_multiple_artifacts(self):
        """Test capturing multiple artifact types"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        engine._trace_data = []
        
        engine._cdp_client.send_command = AsyncMock(side_effect=[
            {"data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAAB..."},
            {"result": {"value": "<html></html>"}}
        ])
        
        with patch.object(Path, 'write_bytes'), \
             patch.object(Path, 'write_text'), \
             patch.object(Path, 'parent'):
            artifacts = await engine.capture_artifacts(["screenshot", "trace"])
        
        assert "screenshot" in artifacts
        assert "trace" in artifacts
    
    @pytest.mark.asyncio
    async def test_capture_artifacts_not_launched(self):
        """Test capture_artifacts when engine not launched"""
        engine = CDPEngine()
        
        # When engine not launched, returns empty dict (no screenshot, but trace might be available)
        artifacts = await engine.capture_artifacts(["screenshot"])
        
        # Screenshot requires cdp_client and page_id, so it won't be captured
        assert "screenshot" not in artifacts
    
    @pytest.mark.asyncio
    async def test_capture_artifacts_command_failure(self):
        """Test capture_artifacts with command failure"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        engine._cdp_client.send_command = AsyncMock(side_effect=RuntimeError("CDP command failed"))
        
        with pytest.raises(ArtifactCaptureError):
            await engine.capture_artifacts(["screenshot"])


class TestCDPEngineShutdown:
    """Test CDPEngine shutdown"""
    
    @pytest.mark.asyncio
    async def test_shutdown_with_capture(self):
        """Test shutdown with final state capture"""
        engine = CDPEngine()
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        engine._cdp_client = mock_client
        engine._page_id = "page-123"
        engine._trace_data = []
        
        with patch.object(engine, 'capture_artifacts', new_callable=AsyncMock) as mock_capture:
            await engine.shutdown(capture_final_state=True)
        
        mock_capture.assert_awaited_once()
        mock_client.disconnect.assert_awaited_once()
        assert engine._cdp_client is None
    
    @pytest.mark.asyncio
    async def test_shutdown_without_capture(self):
        """Test shutdown without final state capture"""
        engine = CDPEngine()
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock()
        engine._cdp_client = mock_client
        engine._page_id = "page-123"
        
        with patch.object(engine, 'capture_artifacts', new_callable=AsyncMock) as mock_capture:
            await engine.shutdown(capture_final_state=False)
        
        mock_capture.assert_not_awaited()
        mock_client.disconnect.assert_awaited_once()
        assert engine._cdp_client is None
    
    @pytest.mark.asyncio
    async def test_shutdown_not_launched(self):
        """Test shutdown when engine not launched"""
        engine = CDPEngine()
        
        # Should not raise exception
        await engine.shutdown()
    
    @pytest.mark.asyncio
    async def test_shutdown_disconnect_failure(self):
        """Test shutdown with disconnect failure"""
        engine = CDPEngine()
        mock_client = MagicMock()
        mock_client.disconnect = AsyncMock(side_effect=RuntimeError("Disconnect failed"))
        engine._cdp_client = mock_client
        engine._page_id = "page-123"
        
        # Should not raise exception - shutdown should be resilient
        await engine.shutdown(capture_final_state=False)
        
        # Disconnect was attempted
        mock_client.disconnect.assert_awaited_once()
