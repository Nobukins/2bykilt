"""
Tests for src/ui/command_helper.py

This module tests command extraction and helper functionality for the UI.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.ui.command_helper import CommandHelper


class TestCommandHelperInit:
    """Tests for CommandHelper initialization."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_init_loads_commands(self, mock_load_config):
        """Test that initialization loads commands."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "search", "description": "Search the web"}
            ]
        }
        
        helper = CommandHelper()
        
        assert len(helper.commands) > 0
        mock_load_config.assert_called()
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_init_empty_config(self, mock_load_config):
        """Test initialization with empty config."""
        mock_load_config.return_value = {}
        
        helper = CommandHelper()
        
        # Should provide default commands
        assert len(helper.commands) >= 2
        assert any(cmd['name'] == 'search' for cmd in helper.commands)


class TestExtractCommandsFromConfig:
    """Tests for _extract_commands_from_config method."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_valid_actions(self, mock_load_config):
        """Test extracting valid actions from config."""
        mock_load_config.return_value = {
            "actions": [
                {
                    "name": "search",
                    "description": "Search query",
                    "params": [
                        {"name": "query", "required": True, "description": "Search term"}
                    ]
                },
                {
                    "name": "visit",
                    "description": "Visit URL"
                }
            ]
        }
        
        helper = CommandHelper()
        
        assert len(helper.commands) == 2
        assert helper.commands[0]['name'] == 'search'
        assert helper.commands[0]['description'] == 'Search query'
        assert len(helper.commands[0]['params']) == 1
        assert helper.commands[1]['name'] == 'visit'
        assert len(helper.commands[1]['params']) == 0
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_actions_without_params(self, mock_load_config):
        """Test extracting actions without parameters."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "help", "description": "Show help"}
            ]
        }
        
        helper = CommandHelper()
        
        assert len(helper.commands) == 1
        assert helper.commands[0]['params'] == []
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_actions_missing_name(self, mock_load_config):
        """Test that actions without 'name' are skipped."""
        mock_load_config.return_value = {
            "actions": [
                {"description": "No name"},
                {"name": "valid", "description": "Has name"}
            ]
        }
        
        helper = CommandHelper()
        
        assert len(helper.commands) == 1
        assert helper.commands[0]['name'] == 'valid'
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_actions_invalid_params(self, mock_load_config):
        """Test handling of invalid params structure."""
        mock_load_config.return_value = {
            "actions": [
                {
                    "name": "test",
                    "params": [
                        {"name": "valid"},
                        {"no_name": "invalid"},
                        "string_param"
                    ]
                }
            ]
        }
        
        helper = CommandHelper()
        
        assert len(helper.commands) == 1
        # Only valid param should be extracted
        assert len(helper.commands[0]['params']) == 1
        assert helper.commands[0]['params'][0]['name'] == 'valid'
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_no_actions_key(self, mock_load_config):
        """Test fallback when 'actions' key is missing."""
        mock_load_config.return_value = {"other_key": "value"}
        
        helper = CommandHelper()
        
        # Should fallback to default commands
        assert len(helper.commands) >= 2
        assert any(cmd['name'] == 'search' for cmd in helper.commands)
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_actions_not_list(self, mock_load_config):
        """Test when actions is not a list."""
        mock_load_config.return_value = {"actions": "not a list"}
        
        helper = CommandHelper()
        
        # Should fallback to defaults
        assert len(helper.commands) >= 2
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_extract_error_handling(self, mock_load_config):
        """Test error handling during extraction."""
        mock_load_config.side_effect = Exception("Config load error")
        
        helper = CommandHelper()
        
        # Should return default commands on error
        assert len(helper.commands) >= 2
        assert any(cmd['name'] == 'search' for cmd in helper.commands)


class TestGetCommandsForDisplay:
    """Tests for get_commands_for_display method."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_commands_for_display(self, mock_load_config):
        """Test getting commands formatted for display."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "search", "description": "Search web", "format": "search query=<q>"}
            ]
        }
        
        helper = CommandHelper()
        result = helper.get_commands_for_display()
        
        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0][0] == "search"
        assert result[0][1] == "Search web"
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_commands_for_display_no_format(self, mock_load_config):
        """Test display when 'format' key is missing."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "help", "description": "Show help"}
            ]
        }
        
        helper = CommandHelper()
        result = helper.get_commands_for_display()
        
        assert result[0][2] == "help"  # Uses name as fallback


class TestGetCommandByName:
    """Tests for get_command_by_name method."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_existing_command(self, mock_load_config):
        """Test retrieving an existing command."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "search", "description": "Search"},
                {"name": "visit", "description": "Visit"}
            ]
        }
        
        helper = CommandHelper()
        result = helper.get_command_by_name("search")
        
        assert result is not None
        assert result['name'] == "search"
        assert result['description'] == "Search"
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_nonexistent_command(self, mock_load_config):
        """Test retrieving a non-existent command."""
        mock_load_config.return_value = {
            "actions": [{"name": "search"}]
        }
        
        helper = CommandHelper()
        result = helper.get_command_by_name("nonexistent")
        
        assert result is None


class TestGenerateCommandTemplate:
    """Tests for generate_command_template method."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_generate_template_with_required_params(self, mock_load_config):
        """Test generating template with required parameters."""
        mock_load_config.return_value = {
            "actions": [
                {
                    "name": "search",
                    "params": [
                        {"name": "query", "required": True},
                        {"name": "lang", "required": True}
                    ]
                }
            ]
        }
        
        helper = CommandHelper()
        result = helper.generate_command_template("search")
        
        assert result == "search query= lang="
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_generate_template_no_params(self, mock_load_config):
        """Test generating template with no parameters."""
        mock_load_config.return_value = {
            "actions": [{"name": "help"}]
        }
        
        helper = CommandHelper()
        result = helper.generate_command_template("help")
        
        assert result == "help"
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_generate_template_optional_params_only(self, mock_load_config):
        """Test template with only optional parameters."""
        mock_load_config.return_value = {
            "actions": [
                {
                    "name": "visit",
                    "params": [
                        {"name": "url", "required": False}
                    ]
                }
            ]
        }
        
        helper = CommandHelper()
        result = helper.generate_command_template("visit")
        
        assert result == "visit"
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_generate_template_nonexistent_command(self, mock_load_config):
        """Test template for non-existent command."""
        mock_load_config.return_value = {
            "actions": [{"name": "search"}]
        }
        
        helper = CommandHelper()
        result = helper.generate_command_template("nonexistent")
        
        assert result == "nonexistent"


class TestGetAllCommands:
    """Tests for get_all_commands method."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_all_commands_success(self, mock_load_config):
        """Test getting all commands successfully."""
        mock_load_config.return_value = {
            "actions": [
                {"name": "search", "description": "Search"},
                {"name": "visit", "description": "Visit URL"}
            ]
        }
        
        helper = CommandHelper()
        result = helper.get_all_commands()
        
        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]['name'] == 'search'
        assert result[1]['name'] == 'visit'
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_all_commands_empty(self, mock_load_config):
        """Test get_all_commands when no commands available."""
        mock_load_config.return_value = {}
        
        helper = CommandHelper()
        result = helper.get_all_commands()
        
        # Should return default commands
        assert isinstance(result, list)
        assert len(result) >= 2
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_get_all_commands_error_handling(self, mock_load_config):
        """Test error handling in get_all_commands."""
        # Make load_actions_config raise an error
        mock_load_config.side_effect = Exception("Config load error")
        
        helper = CommandHelper()
        result = helper.get_all_commands()
        
        # Should return fallback data even on error
        assert isinstance(result, list)
        assert len(result) >= 2


class TestCommandHelperIntegration:
    """Integration tests for CommandHelper."""
    
    @patch('src.config.llms_parser.load_actions_config')
    def test_full_workflow(self, mock_load_config):
        """Test complete workflow of command helper."""
        mock_load_config.return_value = {
            "actions": [
                {
                    "name": "search",
                    "description": "Search the web",
                    "params": [
                        {"name": "query", "required": True, "description": "Search query"},
                        {"name": "lang", "required": False, "description": "Language"}
                    ]
                }
            ]
        }
        
        helper = CommandHelper()
        
        # Test various methods work together
        all_commands = helper.get_all_commands()
        assert len(all_commands) == 1
        
        cmd = helper.get_command_by_name("search")
        assert cmd is not None
        assert len(cmd['params']) == 2
        
        template = helper.generate_command_template("search")
        assert "query=" in template
        
        display = helper.get_commands_for_display()
        assert len(display) == 1
