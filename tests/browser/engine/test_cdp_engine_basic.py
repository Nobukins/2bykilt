"""
Tests for CDPEngine basic actions (Issue #340 Phase 2)

Coverage targets:
- CDPEngine.__init__
- CDPEngine.launch
- CDPEngine.navigate
- CDPEngine.dispatch
- CDPEngine.supports_action

Target: 10% → 40% coverage for cdp_engine.py
"""

import sys
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

from src.browser.engine.cdp_engine import CDPEngine
from src.browser.engine.browser_engine import (
    EngineType,
    LaunchContext,
    ActionResult,
    EngineLaunchError,
    ActionExecutionError,
)


@pytest.mark.ci_safe
class TestCDPEngineInit:
    """Test CDPEngine initialization"""
    
    def test_init_default(self):
        """Test default initialization"""
        engine = CDPEngine()
        assert engine.engine_type == EngineType.CDP
        assert engine._cdp_client is None
        assert engine._browser_process is None
        assert engine._page_id is None
        assert engine._trace_data == []
        assert engine._network_interception_enabled is False
    
    def test_init_with_explicit_type(self):
        """Test initialization with explicit engine type"""
        engine = CDPEngine(engine_type=EngineType.CDP)
        assert engine.engine_type == EngineType.CDP


@pytest.mark.ci_safe
class TestCDPEngineLaunch:
    """Test CDPEngine launch functionality"""
    
    @pytest.mark.asyncio
    async def test_launch_success(self):
        """Test successful browser launch"""
        engine = CDPEngine()
        context = LaunchContext(headless=True, timeout_ms=30000)
        
        # Mock CDPClient
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.create_page = AsyncMock(return_value="page-123")
        mock_client.send_command = AsyncMock()
        
        # Create a fake cdp_use module with CDPClient
        mock_cdp_module = MagicMock()
        mock_cdp_module.CDPClient = MagicMock(return_value=mock_client)
        
        with patch.dict('sys.modules', {'cdp_use': mock_cdp_module}):
            await engine.launch(context)
        
        assert engine._cdp_client is not None
        assert engine._page_id == "page-123"
        mock_client.connect.assert_awaited_once()
        mock_client.create_page.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_launch_with_sandbox_config(self):
        """Test launch with sandbox configuration"""
        engine = CDPEngine()
        context = LaunchContext(headless=True, timeout_ms=30000)
        context.sandbox_network_mode = "none"
        
        mock_client = MagicMock()
        mock_client.connect = AsyncMock()
        mock_client.create_page = AsyncMock(return_value="page-456")
        mock_client.send_command = AsyncMock()
        
        mock_cdp_module = MagicMock()
        mock_cdp_module.CDPClient = MagicMock(return_value=mock_client)
        
        with patch.dict('sys.modules', {'cdp_use': mock_cdp_module}):
            await engine.launch(context)
        
        # Verify sandbox config was passed to connect
        call_kwargs = mock_client.connect.call_args.kwargs
        assert 'sandbox' in call_kwargs
        assert call_kwargs['sandbox']['network_mode'] == "none"
    
    @pytest.mark.asyncio
    async def test_launch_import_error(self):
        """Test launch failure when cdp-use is not installed"""
        engine = CDPEngine()
        context = LaunchContext(headless=True, timeout_ms=30000)
        
        # Patch the import itself to raise ImportError
        with patch.dict('sys.modules', {'cdp_use': None}):
            with pytest.raises(EngineLaunchError, match="cdp-use library not installed"):
                await engine.launch(context)
    
    @pytest.mark.asyncio
    async def test_launch_connection_failure(self):
        """Test launch failure due to connection error"""
        engine = CDPEngine()
        context = LaunchContext(headless=True, timeout_ms=30000)
        
        mock_client = MagicMock()
        mock_client.connect = AsyncMock(side_effect=RuntimeError("Connection refused"))
        mock_client.disconnect = AsyncMock()
        
        mock_cdp_module = MagicMock()
        mock_cdp_module.CDPClient = MagicMock(return_value=mock_client)
        
        with patch.dict('sys.modules', {'cdp_use': mock_cdp_module}):
            with pytest.raises(EngineLaunchError, match="CDP launch failed"):
                await engine.launch(context)


@pytest.mark.ci_safe
class TestCDPEngineNavigate:
    """Test CDPEngine navigation"""
    
    @pytest.mark.asyncio
    async def test_navigate_success(self):
        """Test successful navigation"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        engine._cdp_client.send_command = AsyncMock(return_value={"frameId": "frame-456"})
        engine._cdp_client.wait_for_event = AsyncMock()
        
        result = await engine.navigate("https://example.com")
        
        assert result.success is True
        assert result.action_type == "navigate"
        assert result.duration_ms > 0
        assert result.metadata["url"] == "https://example.com"
        assert result.metadata["frame_id"] == "frame-456"
        
        engine._cdp_client.send_command.assert_awaited_once_with(
            "Page.navigate",
            page_id="page-123",
            params={"url": "https://example.com"}
        )
    
    @pytest.mark.asyncio
    async def test_navigate_not_launched(self):
        """Test navigation when engine not launched"""
        engine = CDPEngine()
        
        with pytest.raises(ActionExecutionError, match="Engine not launched"):
            await engine.navigate("https://example.com")
    
    @pytest.mark.asyncio
    async def test_navigate_timeout(self):
        """Test navigation timeout"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        engine._cdp_client.send_command = AsyncMock(return_value={"frameId": "frame-456"})
        engine._cdp_client.wait_for_event = AsyncMock(side_effect=TimeoutError("Page load timeout"))
        
        with pytest.raises(ActionExecutionError, match="Page load timeout"):
            await engine.navigate("https://example.com")


@pytest.mark.ci_safe
class TestCDPEngineDispatch:
    """Test CDPEngine action dispatch"""
    
    @pytest.mark.asyncio
    async def test_dispatch_click_action(self):
        """Test dispatching click action"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        # Mock Runtime.evaluate for element finding and clicking
        engine._cdp_client.send_command = AsyncMock(return_value={
            "result": {"type": "undefined"}
        })
        
        action = {
            "type": "click",
            "selector": "button#submit"
        }
        
        result = await engine.dispatch(action)
        
        assert result.success is True
        assert result.action_type == "click"
        assert result.metadata["selector"] == "button#submit"
    
    @pytest.mark.asyncio
    async def test_dispatch_fill_action(self):
        """Test dispatching fill action"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        engine._cdp_client.send_command = AsyncMock(return_value={
            "result": {"type": "undefined"}
        })
        
        action = {
            "type": "fill",
            "selector": "input#username",
            "text": "testuser"
        }
        
        result = await engine.dispatch(action)
        
        assert result.success is True
        assert result.action_type == "fill"
        assert result.metadata["selector"] == "input#username"
        assert result.metadata["text"] == "testuser"
    
    @pytest.mark.asyncio
    async def test_dispatch_unsupported_action(self):
        """Test dispatching unsupported action"""
        engine = CDPEngine()
        engine._cdp_client = MagicMock()
        engine._page_id = "page-123"
        
        action = {
            "type": "unsupported_action"
        }
        
        with pytest.raises(ActionExecutionError, match="Unsupported action"):
            await engine.dispatch(action)
    
    @pytest.mark.asyncio
    async def test_dispatch_not_launched(self):
        """Test dispatch when engine not launched"""
        engine = CDPEngine()
        
        action = {"type": "click", "selector": "button"}
        
        with pytest.raises(ActionExecutionError, match="Engine not launched"):
            await engine.dispatch(action)


@pytest.mark.ci_safe
class TestCDPEngineSupportsAction:
    """Test CDPEngine action support checks"""
    
    def test_supports_navigate(self):
        """Test supports_action for navigate"""
        engine = CDPEngine()
        assert engine.supports_action("navigate") is True
    
    def test_supports_click(self):
        """Test supports_action for click"""
        engine = CDPEngine()
        assert engine.supports_action("click") is True
    
    def test_supports_fill(self):
        """Test supports_action for fill"""
        engine = CDPEngine()
        assert engine.supports_action("fill") is True
    
    def test_supports_screenshot(self):
        """Test supports_action for screenshot"""
        engine = CDPEngine()
        assert engine.supports_action("screenshot") is True
    
    def test_not_supports_unsupported(self):
        """Test supports_action for unsupported action"""
        engine = CDPEngine()
        assert engine.supports_action("unsupported_action") is False
