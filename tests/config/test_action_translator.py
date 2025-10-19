"""
Tests for src/config/action_translator.py

This module tests the ActionTranslator class which converts llms.txt actions
into JSON command format for browser automation.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.config.action_translator import ActionTranslator


@pytest.mark.local_only
class TestActionTranslatorInitialization:
    """Tests for ActionTranslator initialization."""
    
    def test_init_creates_temp_directory(self, tmp_path):
        """Test that initialization creates the temporary directory."""
        temp_dir = tmp_path / "json_commands"
        translator = ActionTranslator(temp_dir=str(temp_dir))
        
        assert translator.temp_dir == str(temp_dir)
        assert temp_dir.exists()
        assert temp_dir.is_dir()
    
    def test_init_with_existing_directory(self, tmp_path):
        """Test initialization with an already existing directory."""
        temp_dir = tmp_path / "existing_dir"
        temp_dir.mkdir()
        
        translator = ActionTranslator(temp_dir=str(temp_dir))
        
        assert translator.temp_dir == str(temp_dir)
        assert temp_dir.exists()
    
    def test_init_with_default_directory(self):
        """Test initialization with default directory."""
        with patch('os.makedirs') as mock_makedirs:
            translator = ActionTranslator()
            
            assert translator.temp_dir == "./tmp/json_commands"
            mock_makedirs.assert_called_once_with("./tmp/json_commands", exist_ok=True)


@pytest.mark.local_only
class TestActionTranslatorTranslateToJson:
    """Tests for translate_to_json method."""
    
    @pytest.fixture
    def translator(self, tmp_path):
        """Create a translator instance with temp directory."""
        return ActionTranslator(temp_dir=str(tmp_path))
    
    @pytest.fixture
    def sample_action_dict(self):
        """Sample action configuration as dictionary."""
        return {
            "actions": [
                {
                    "name": "login",
                    "type": "browser-control",
                    "keep_tab_open": True,
                    "slowmo": 500,
                    "flow": [
                        {
                            "action": "command",
                            "url": "https://example.com/login"
                        },
                        {
                            "action": "fill_form",
                            "selector": "#username",
                            "value": "${params.username}"
                        },
                        {
                            "action": "fill_form",
                            "selector": "#password",
                            "value": "${params.password}"
                        },
                        {
                            "action": "click",
                            "selector": "#login-button"
                        },
                        {
                            "action": "keyboard_press",
                            "key": "Enter"
                        }
                    ]
                }
            ]
        }
    
    @pytest.fixture
    def sample_action_list(self):
        """Sample action configuration as list."""
        return [
            {
                "name": "search",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "command",
                        "url": "https://google.com"
                    },
                    {
                        "action": "fill_form",
                        "selector": "input[name='q']",
                        "value": "${params.query}"
                    }
                ]
            }
        ]
    
    def test_translate_action_dict_format(self, translator, sample_action_dict, tmp_path):
        """Test translation with action config as dictionary."""
        params = {"username": "testuser", "password": "testpass"}
        
        result_path = translator.translate_to_json(
            "login", params, sample_action_dict
        )
        
        # Verify file was created
        assert Path(result_path).exists()
        assert Path(result_path).parent == tmp_path
        
        # Verify JSON content
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert result["maintain_session"] is False
        assert result["tab_selection_strategy"] == "new_tab"
        assert result["keep_tab_open"] is True
        assert result["slowmo"] == 500
        assert len(result["commands"]) == 5
        
        # Verify command URL
        assert result["commands"][0]["action"] == "command"
        assert result["commands"][0]["args"] == ["https://example.com/login"]
        
        # Verify parameter substitution
        assert result["commands"][1]["action"] == "fill_form"
        assert result["commands"][1]["args"] == ["#username", "testuser"]
        
        assert result["commands"][2]["action"] == "fill_form"
        assert result["commands"][2]["args"] == ["#password", "testpass"]
        
        # Verify click action
        assert result["commands"][3]["action"] == "click"
        assert result["commands"][3]["args"] == ["#login-button"]
        
        # Verify keyboard press
        assert result["commands"][4]["action"] == "keyboard_press"
        assert result["commands"][4]["args"] == ["Enter"]
    
    def test_translate_action_list_format(self, translator, sample_action_list, tmp_path):
        """Test translation with action config as list."""
        params = {"query": "Python testing"}
        
        result_path = translator.translate_to_json(
            "search", params, sample_action_list
        )
        
        assert Path(result_path).exists()
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert len(result["commands"]) == 2
        assert result["commands"][1]["args"] == ["input[name='q']", "Python testing"]
    
    def test_translate_with_maintain_session(self, translator, sample_action_list):
        """Test translation with maintain_session option."""
        params = {"query": "test"}
        
        result_path = translator.translate_to_json(
            "search", params, sample_action_list, maintain_session=True
        )
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert result["maintain_session"] is True
    
    def test_translate_with_tab_selection_strategy(self, translator, sample_action_list):
        """Test translation with custom tab selection strategy."""
        params = {"query": "test"}
        
        result_path = translator.translate_to_json(
            "search", params, sample_action_list,
            tab_selection_strategy="active_tab"
        )
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert result["tab_selection_strategy"] == "active_tab"
    
    def test_translate_action_not_found(self, translator, sample_action_dict):
        """Test translation with non-existent action name."""
        params = {}
        
        with pytest.raises(ValueError) as exc_info:
            translator.translate_to_json("nonexistent", params, sample_action_dict)
        
        assert "Action 'nonexistent' is not defined" in str(exc_info.value)
    
    def test_translate_command_without_url(self, translator, tmp_path):
        """Test translation of command action without URL."""
        actions = [
            {
                "name": "current_page",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "command"
                        # No URL specified
                    }
                ]
            }
        ]
        
        result_path = translator.translate_to_json("current_page", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        # Should use "current" as default
        assert result["commands"][0]["args"] == ["current"]
    
    def test_translate_command_with_wait_parameters(self, translator, tmp_path):
        """Test translation of command with wait_for and wait_until."""
        actions = [
            {
                "name": "wait_test",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "command",
                        "url": "https://example.com",
                        "wait_for": "networkidle",
                        "wait_until": "domcontentloaded"
                    }
                ]
            }
        ]
        
        result_path = translator.translate_to_json("wait_test", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        cmd = result["commands"][0]
        assert cmd["wait_for"] == "networkidle"
        assert cmd["wait_until"] == "domcontentloaded"
    
    def test_translate_keyboard_press_default_key(self, translator, tmp_path):
        """Test keyboard_press action with default key."""
        actions = [
            {
                "name": "press_test",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "keyboard_press"
                        # No key specified, should default to Enter
                    }
                ]
            }
        ]
        
        result_path = translator.translate_to_json("press_test", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert result["commands"][0]["args"] == ["Enter"]
    
    def test_translate_default_options(self, translator, sample_action_list):
        """Test default values for keep_tab_open and slowmo."""
        params = {"query": "test"}
        
        result_path = translator.translate_to_json("search", params, sample_action_list)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        # Defaults should be applied
        assert result["keep_tab_open"] is False
        assert result["slowmo"] == 1000
    
    def test_translate_unlock_future_type(self, translator, tmp_path):
        """Test translation of unlock-future type action."""
        actions = [
            {
                "name": "future_action",
                "type": "unlock-future",
                "flow": [
                    {
                        "action": "click",
                        "selector": "#button"
                    }
                ]
            }
        ]
        
        result_path = translator.translate_to_json("future_action", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert len(result["commands"]) == 1
        assert result["commands"][0]["action"] == "click"
    
    def test_translate_file_naming(self, translator, sample_action_list, tmp_path):
        """Test that generated file names are unique based on params."""
        params1 = {"query": "test1"}
        params2 = {"query": "test2"}
        
        path1 = translator.translate_to_json("search", params1, sample_action_list)
        path2 = translator.translate_to_json("search", params2, sample_action_list)
        
        # Files should have different names (different hash)
        assert path1 != path2
        assert Path(path1).exists()
        assert Path(path2).exists()
    
    def test_translate_json_formatting(self, translator, sample_action_list):
        """Test that JSON is properly formatted with indentation."""
        params = {"query": "test"}
        
        result_path = translator.translate_to_json("search", params, sample_action_list)
        
        # Read raw file content
        with open(result_path, 'r') as f:
            content = f.read()
        
        # Should be indented (contains newlines and spaces)
        assert '\n' in content
        assert '  ' in content  # 2-space indent
    
    def test_translate_non_ascii_characters(self, translator, sample_action_list):
        """Test handling of non-ASCII characters in parameters."""
        params = {"query": "日本語テスト"}
        
        result_path = translator.translate_to_json("search", params, sample_action_list)
        
        with open(result_path, 'r', encoding='utf-8') as f:
            result = json.load(f)
        
        # Non-ASCII should be preserved
        assert result["commands"][1]["args"][1] == "日本語テスト"


@pytest.mark.local_only
class TestActionTranslatorEdgeCases:
    """Tests for edge cases and error handling."""
    
    @pytest.fixture
    def translator(self, tmp_path):
        """Create a translator instance with temp directory."""
        return ActionTranslator(temp_dir=str(tmp_path))
    
    def test_empty_actions_config(self, translator):
        """Test with empty actions configuration."""
        with pytest.raises(ValueError):
            translator.translate_to_json("test", {}, [])
    
    def test_action_without_flow(self, translator):
        """Test action without flow definition."""
        actions = [
            {
                "name": "no_flow",
                "type": "browser-control"
                # No flow key
            }
        ]
        
        result_path = translator.translate_to_json("no_flow", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        # Should have empty commands list
        assert result["commands"] == []
    
    def test_fill_form_without_selector(self, translator):
        """Test fill_form action without selector."""
        actions = [
            {
                "name": "test",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "fill_form",
                        "value": "test"
                        # No selector
                    }
                ]
            }
        ]
        
        result_path = translator.translate_to_json("test", {}, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        # Should have empty args initially, then value
        assert result["commands"][0]["args"] == ["test"]
    
    def test_multiple_param_substitutions(self, translator):
        """Test multiple parameter substitutions in one value."""
        actions = [
            {
                "name": "multi_param",
                "type": "browser-control",
                "flow": [
                    {
                        "action": "fill_form",
                        "selector": "#input",
                        "value": "${params.first} ${params.second}"
                    }
                ]
            }
        ]
        
        params = {"first": "Hello", "second": "World"}
        result_path = translator.translate_to_json("multi_param", params, actions)
        
        with open(result_path, 'r') as f:
            result = json.load(f)
        
        assert result["commands"][0]["args"][1] == "Hello World"
