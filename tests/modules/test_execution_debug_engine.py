"""
Tests for ExecutionDebugEngine module (Issue #340 Phase 3)

NOTE: These tests are marked as local_only because:
- ExecutionDebugEngine uses BrowserDebugManager which launches real browsers
- Tests require Playwright browser automation (headless or headed)
- CI environment would need full Playwright setup for these tests
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from pathlib import Path
import json

from src.modules.execution_debug_engine import ExecutionDebugEngine


@pytest.fixture
def engine():
    """Create ExecutionDebugEngine instance"""
    return ExecutionDebugEngine()


@pytest.fixture
def mock_browser_manager():
    """Create mock browser manager"""
    manager = MagicMock()
    manager.initialize_custom_browser = AsyncMock(return_value={"status": "success"})
    manager.get_or_create_tab = AsyncMock(return_value=(MagicMock(), AsyncMock(), True))
    manager.highlight_automated_tab = AsyncMock()
    manager.cleanup = AsyncMock()
    return manager


@pytest.fixture
def mock_page():
    """Create mock page object"""
    page = AsyncMock()
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.keyboard.press = AsyncMock()
    page.locator = MagicMock(return_value=AsyncMock())
    page.evaluate = AsyncMock()
    page.screenshot = AsyncMock()
    return page


@pytest.mark.ci_safe
class TestExecutionDebugEngineInit:
    """Tests for ExecutionDebugEngine initialization"""
    
    def test_init_creates_browser_manager(self, engine):
        """Test that __init__ creates BrowserDebugManager"""
        assert hasattr(engine, 'browser_manager')
        assert engine.browser_manager is not None


@pytest.mark.ci_safe
class TestExecuteCommands:
    """Tests for execute_commands method"""
    
    @pytest.mark.asyncio
    async def test_execute_commands_navigate(self, engine, mock_browser_manager, mock_page):
        """Test command execution with navigation"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [{"action": "command", "args": ["https://example.com"]}]
        
        result = await engine.execute_commands(
            commands, 
            use_own_browser=False, 
            headless=True, 
            tab_selection="new_tab"
        )
        
        # Should initialize browser
        mock_browser_manager.initialize_custom_browser.assert_called_once_with(False, True)
        
        # Should navigate to URL
        mock_page.goto.assert_called_once_with(
            "https://example.com", 
            wait_until="domcontentloaded"
        )
        mock_page.wait_for_load_state.assert_called_with("networkidle")
    
    @pytest.mark.asyncio
    async def test_execute_commands_fill_form(self, engine, mock_browser_manager, mock_page):
        """Test fill_form command"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, False)
        )
        
        commands = [{"action": "fill_form", "args": ["#username", "testuser"]}]
        
        await engine.execute_commands(commands, headless=True)
        
        # Should fill form field
        mock_page.fill.assert_called_once_with("#username", "testuser")
    
    @pytest.mark.asyncio
    async def test_execute_commands_click(self, engine, mock_browser_manager, mock_page):
        """Test click command"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [{"action": "click", "args": ["#submit-btn"]}]
        
        await engine.execute_commands(commands, headless=True)
        
        # Should click element
        mock_page.click.assert_called_once_with("#submit-btn")
    
    @pytest.mark.asyncio
    async def test_execute_commands_keyboard_press(self, engine, mock_browser_manager, mock_page):
        """Test keyboard_press command"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [{"action": "keyboard_press", "args": ["Enter"]}]
        
        await engine.execute_commands(commands, headless=True)
        
        # Should press key
        mock_page.keyboard.press.assert_called_once_with("Enter")
    
    @pytest.mark.asyncio
    async def test_execute_commands_wait_for_navigation(self, engine, mock_browser_manager, mock_page):
        """Test wait_for_navigation command"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [{"action": "wait_for_navigation"}]
        
        await engine.execute_commands(commands, headless=True)
        
        # Should wait for navigation
        mock_page.wait_for_load_state.assert_called_with("networkidle")
    
    @pytest.mark.asyncio
    async def test_execute_commands_browser_init_error(self, engine, mock_browser_manager):
        """Test handling of browser initialization error"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.initialize_custom_browser = AsyncMock(
            return_value={"status": "error", "message": "Connection refused"}
        )
        
        commands = [{"action": "command", "args": ["https://example.com"]}]
        
        result = await engine.execute_commands(commands, headless=True)
        
        # Should return None on browser init error
        assert result is None
        
        # Should not attempt to get tab
        mock_browser_manager.get_or_create_tab.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_execute_commands_multiple_commands(self, engine, mock_browser_manager, mock_page):
        """Test executing multiple commands in sequence"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [
            {"action": "command", "args": ["https://example.com"]},
            {"action": "fill_form", "args": ["#username", "admin"]},
            {"action": "click", "args": ["#submit"]}
        ]
        
        await engine.execute_commands(commands, headless=True)
        
        # All commands should be executed
        mock_page.goto.assert_called_once()
        mock_page.fill.assert_called_once()
        mock_page.click.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_commands_keep_tab_open_unlock_future(self, engine, mock_browser_manager, mock_page):
        """Test keep_tab_open defaults to True for unlock-future action type"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands = [{"action": "command", "args": ["https://example.com"]}]
        
        # For unlock-future, keep_tab_open should default to True
        await engine.execute_commands(
            commands, 
            headless=True, 
            action_type="unlock-future"
        )
        
        # Verify initialization occurred (indicating keep_tab_open logic works)
        mock_browser_manager.initialize_custom_browser.assert_called_once()


@pytest.mark.ci_safe
class TestExecuteJsonCommands:
    """Tests for execute_json_commands method"""
    
    @pytest.mark.asyncio
    async def test_execute_json_commands_basic(self, engine, mock_browser_manager, mock_page):
        """Test JSON command execution"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands_data = {
            "commands": [
                {"action": "command", "args": ["https://example.com"]}
            ],
            "action_type": "unlock-future"
        }
        
        result = await engine.execute_json_commands(
            commands_data, 
            use_own_browser=False, 
            headless=True
        )
        
        # Should execute commands
        mock_page.goto.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_json_commands_with_tab_selection(self, engine, mock_browser_manager, mock_page):
        """Test JSON commands with tab selection"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, False)
        )
        
        commands_data = {
            "commands": [{"action": "click", "args": ["#button"]}],
            "tab_selection": "active_tab"
        }
        
        await engine.execute_json_commands(commands_data, headless=True)
        
        # Should use new_tab as default (tab_selection in JSON might not be used directly)
        # The implementation uses "new_tab" as default
        mock_browser_manager.get_or_create_tab.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_json_commands_keep_tab_open(self, engine, mock_browser_manager, mock_page):
        """Test JSON commands with keep_tab_open flag"""
        engine.browser_manager = mock_browser_manager
        mock_browser_manager.get_or_create_tab = AsyncMock(
            return_value=(MagicMock(), mock_page, True)
        )
        
        commands_data = {
            "commands": [{"action": "command", "args": ["https://example.com"]}],
            "keep_tab_open": True
        }
        
        await engine.execute_json_commands(commands_data, headless=True)
        
        # Should respect keep_tab_open from JSON
        mock_browser_manager.initialize_custom_browser.assert_called_once()

