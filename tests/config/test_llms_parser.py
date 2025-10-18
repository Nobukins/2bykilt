"""
Tests for src/config/llms_parser.py

This module tests the LLMs.txt parsing and action extraction functionality.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import requests

from src.config.llms_parser import (
    fetch_llms_txt,
    parse_llms_txt,
    pre_evaluate_prompt,
    extract_params,
    resolve_sensitive_env_variables,
    load_actions_config
)
from src.config.llms_schema_validator import LLMSSchemaValidationError


class TestFetchLlmsTxt:
    """Tests for fetch_llms_txt function."""
    
    @patch('src.config.llms_parser.requests.get')
    def test_fetch_from_url(self, mock_get):
        """Test fetching llms.txt from URL."""
        mock_response = MagicMock()
        mock_response.text = "actions:\n  - name: test"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        prompt = "Please use https://example.com/llms.txt for actions"
        
        result = fetch_llms_txt(prompt)
        
        assert result == "actions:\n  - name: test"
        mock_get.assert_called_once_with("https://example.com/llms.txt")
    
    @patch('src.config.llms_parser.requests.get')
    def test_fetch_from_url_http_error(self, mock_get):
        """Test handling of HTTP errors when fetching from URL."""
        mock_get.side_effect = requests.HTTPError("404 Not Found")
        
        prompt = "Use https://example.com/llms.txt"
        
        with pytest.raises(requests.HTTPError):
            fetch_llms_txt(prompt)
    
    @patch('os.path.exists')
    @patch('builtins.open', new_callable=mock_open, read_data="local content")
    def test_fetch_from_local_file(self, mock_file, mock_exists):
        """Test fetching llms.txt from local file."""
        mock_exists.return_value = True
        
        prompt = "Run the action"
        
        result = fetch_llms_txt(prompt)
        
        assert result == "local content"
        mock_file.assert_called_once_with('llms.txt', 'r', encoding='utf-8')
    
    @patch('os.path.exists')
    def test_fetch_file_not_found(self, mock_exists):
        """Test error when llms.txt is not found."""
        mock_exists.return_value = False
        
        prompt = "Run the action"
        
        with pytest.raises(FileNotFoundError) as exc_info:
            fetch_llms_txt(prompt)
        
        assert "llms.txt not found" in str(exc_info.value)
    
    @patch('src.config.llms_parser.requests.get')
    def test_fetch_url_with_https(self, mock_get):
        """Test fetching from HTTPS URL."""
        mock_response = MagicMock()
        mock_response.text = "content"
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response
        
        prompt = "Use https://secure.example.com/llms.txt"
        
        result = fetch_llms_txt(prompt)
        
        assert result == "content"


class TestParseLlmsTxt:
    """Tests for parse_llms_txt function."""
    
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_valid_content(self, mock_validate):
        """Test parsing valid llms.txt content."""
        mock_validate.return_value = {
            "actions": [
                {"name": "action1", "type": "browser-control"},
                {"name": "action2", "type": "browser-control"}
            ]
        }
        
        content = "actions:\n  - name: action1"
        
        result = parse_llms_txt(content)
        
        assert len(result) == 2
        assert result[0]["name"] == "action1"
        assert result[1]["name"] == "action2"
    
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_missing_actions_key(self, mock_validate):
        """Test parsing when actions key is missing."""
        mock_validate.return_value = {}
        
        content = "invalid: content"
        
        result = parse_llms_txt(content)
        
        assert result == []
    
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_actions_not_list(self, mock_validate):
        """Test parsing when actions is not a list."""
        mock_validate.return_value = {"actions": "not a list"}
        
        content = "actions: invalid"
        
        result = parse_llms_txt(content)
        
        assert result == []
    
    @patch.dict(os.environ, {'BYKILT_LLMS_STRICT': '1'})
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_strict_mode_validation_error(self, mock_validate):
        """Test strict mode raises validation errors."""
        mock_validate.side_effect = LLMSSchemaValidationError("Validation failed")
        
        content = "invalid content"
        
        with pytest.raises(LLMSSchemaValidationError):
            parse_llms_txt(content)
    
    @patch.dict(os.environ, {'BYKILT_LLMS_STRICT': 'true'})
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_strict_mode_variations(self, mock_validate):
        """Test strict mode environment variable variations."""
        mock_validate.side_effect = LLMSSchemaValidationError("Error")
        
        for value in ['1', 'true', 'TRUE', 'yes', 'YES', 'on', 'ON']:
            with patch.dict(os.environ, {'BYKILT_LLMS_STRICT': value}):
                with pytest.raises(LLMSSchemaValidationError):
                    parse_llms_txt("content")
    
    @patch.dict(os.environ, {'BYKILT_LLMS_STRICT': '0'})
    @patch('src.config.llms_parser.validate_llms_content')
    def test_parse_non_strict_mode(self, mock_validate):
        """Test non-strict mode doesn't raise on validation errors."""
        mock_validate.return_value = {"actions": []}
        
        content = "content"
        result = parse_llms_txt(content)
        
        assert result == []


class TestPreEvaluatePrompt:
    """Tests for pre_evaluate_prompt function."""
    
    @patch('src.config.llms_parser.fetch_llms_txt')
    @patch('src.config.llms_parser.parse_llms_txt')
    def test_pre_evaluate_matching_action(self, mock_parse, mock_fetch):
        """Test finding a matching action in prompt."""
        mock_fetch.return_value = "content"
        mock_parse.return_value = [
            {"name": "login", "type": "browser-control"},
            {"name": "search", "type": "browser-control"}
        ]
        
        prompt = "Please run login action"
        
        result = pre_evaluate_prompt(prompt)
        
        assert result is not None
        assert result["name"] == "login"
    
    @patch('src.config.llms_parser.fetch_llms_txt')
    @patch('src.config.llms_parser.parse_llms_txt')
    def test_pre_evaluate_no_matching_action(self, mock_parse, mock_fetch):
        """Test when no action matches the prompt."""
        mock_fetch.return_value = "content"
        mock_parse.return_value = [
            {"name": "login", "type": "browser-control"}
        ]
        
        prompt = "Please run logout action"
        
        result = pre_evaluate_prompt(prompt)
        
        assert result is None
    
    @patch('src.config.llms_parser.fetch_llms_txt')
    @patch('src.config.llms_parser.parse_llms_txt')
    def test_pre_evaluate_invalid_action_format(self, mock_parse, mock_fetch):
        """Test handling of invalid action format."""
        mock_fetch.return_value = "content"
        mock_parse.return_value = [
            "invalid string action",
            {"no_name_key": "value"}
        ]
        
        prompt = "Run action"
        
        result = pre_evaluate_prompt(prompt)
        
        assert result is None
    
    @patch('src.config.llms_parser.fetch_llms_txt')
    def test_pre_evaluate_fetch_error(self, mock_fetch):
        """Test handling of fetch errors."""
        mock_fetch.side_effect = FileNotFoundError("File not found")
        
        prompt = "Run action"
        
        result = pre_evaluate_prompt(prompt)
        
        assert result is None
    
    @patch('src.config.llms_parser.fetch_llms_txt')
    @patch('src.config.llms_parser.parse_llms_txt')
    def test_pre_evaluate_first_match_wins(self, mock_parse, mock_fetch):
        """Test that first matching action is returned."""
        mock_fetch.return_value = "content"
        mock_parse.return_value = [
            {"name": "test", "priority": 1},
            {"name": "test", "priority": 2}
        ]
        
        prompt = "Run test action"
        
        result = pre_evaluate_prompt(prompt)
        
        assert result["priority"] == 1


class TestExtractParams:
    """Tests for extract_params function."""
    
    def test_extract_params_from_string(self):
        """Test extracting parameters when param_names is a string."""
        prompt = "username=john password=secret123"
        param_names = "username, password"
        
        result = extract_params(prompt, param_names)
        
        assert result == {"username": "john", "password": "secret123"}
    
    def test_extract_params_from_list(self):
        """Test extracting parameters when param_names is a list of dicts."""
        prompt = "query=Python language=en"
        param_names = [
            {"name": "query", "required": True},
            {"name": "language", "required": False}
        ]
        
        result = extract_params(prompt, param_names)
        
        assert result == {"query": "Python", "language": "en"}
    
    def test_extract_params_none(self):
        """Test with None param_names."""
        prompt = "test=value"
        
        result = extract_params(prompt, None)
        
        assert result == {}
    
    def test_extract_params_empty_string(self):
        """Test with empty string param_names."""
        prompt = "test=value"
        
        result = extract_params(prompt, "")
        
        assert result == {}
    
    def test_extract_params_partial_match(self):
        """Test when only some parameters are found."""
        prompt = "user=alice"
        param_names = "user, password, email"
        
        result = extract_params(prompt, param_names)
        
        assert result == {"user": "alice"}
        assert "password" not in result
        assert "email" not in result
    
    def test_extract_params_no_match(self):
        """Test when no parameters match."""
        prompt = "some text without params"
        param_names = "user, password"
        
        result = extract_params(prompt, param_names)
        
        assert result == {}
    
    def test_extract_params_list_without_name_key(self):
        """Test list of dicts without 'name' key."""
        prompt = "test=value"
        param_names = [
            {"invalid": "dict"},
            {"name": "test"}
        ]
        
        result = extract_params(prompt, param_names)
        
        assert result == {"test": "value"}
    
    def test_extract_params_with_special_characters(self):
        """Test parameter values with special characters."""
        prompt = "url=https://example.com/path?q=test"
        param_names = "url"
        
        result = extract_params(prompt, param_names)
        
        # Only captures until first whitespace
        assert "url" in result


class TestResolveSensitiveEnvVariables:
    """Tests for resolve_sensitive_env_variables function."""
    
    @patch.dict(os.environ, {'SENSITIVE_API_KEY': 'secret123'})
    def test_resolve_single_variable(self):
        """Test resolving a single environment variable."""
        text = "API key is $SENSITIVE_API_KEY"
        
        result = resolve_sensitive_env_variables(text)
        
        assert result == "API key is secret123"
    
    @patch.dict(os.environ, {
        'SENSITIVE_USER': 'admin',
        'SENSITIVE_PASS': 'password123'
    })
    def test_resolve_multiple_variables(self):
        """Test resolving multiple environment variables."""
        text = "User: $SENSITIVE_USER, Pass: $SENSITIVE_PASS"
        
        result = resolve_sensitive_env_variables(text)
        
        assert result == "User: admin, Pass: password123"
    
    def test_resolve_none_text(self):
        """Test with None input."""
        result = resolve_sensitive_env_variables(None)
        
        assert result is None
    
    def test_resolve_empty_string(self):
        """Test with empty string."""
        result = resolve_sensitive_env_variables("")
        
        assert result == ""
    
    @patch.dict(os.environ, {}, clear=True)
    def test_resolve_undefined_variable(self):
        """Test when environment variable is not defined."""
        text = "Key: $SENSITIVE_UNDEFINED"
        
        result = resolve_sensitive_env_variables(text)
        
        # Should remain unchanged
        assert result == "Key: $SENSITIVE_UNDEFINED"
    
    @patch.dict(os.environ, {'SENSITIVE_KEY': 'value'})
    def test_resolve_no_variables(self):
        """Test text without any variables."""
        text = "This is plain text"
        
        result = resolve_sensitive_env_variables(text)
        
        assert result == "This is plain text"
    
    @patch.dict(os.environ, {'SENSITIVE_TOKEN_123': 'token_value'})
    def test_resolve_with_numbers(self):
        """Test variable names with numbers."""
        text = "Token: $SENSITIVE_TOKEN_123"
        
        result = resolve_sensitive_env_variables(text)
        
        assert result == "Token: token_value"


class TestLoadActionsConfig:
    """Tests for load_actions_config function."""
    
    def test_load_valid_config(self, tmp_path):
        """Test loading valid actions configuration."""
        # Create a temporary llms.txt file
        config_content = """
actions:
  - name: test_action
    type: browser-control
  - name: another_action
    type: browser-control
"""
        llms_file = tmp_path / "llms.txt"
        llms_file.write_text(config_content)
        
        # Patch the config path to use our temp file
        with patch('os.path.join', return_value=str(llms_file)):
            with patch('os.path.exists', return_value=True):
                result = load_actions_config()
        
        assert isinstance(result, dict)
        assert "actions" in result
        assert len(result["actions"]) == 2
    
    @patch('os.path.exists')
    def test_load_config_file_not_found(self, mock_exists):
        """Test when config file doesn't exist."""
        mock_exists.return_value = False
        
        result = load_actions_config()
        
        assert result == {}
    
    def test_load_invalid_yaml(self, tmp_path):
        """Test loading invalid YAML content."""
        invalid_content = "invalid: [yaml: content"
        llms_file = tmp_path / "llms.txt"
        llms_file.write_text(invalid_content)
        
        with patch('os.path.join', return_value=str(llms_file)):
            with patch('os.path.exists', return_value=True):
                result = load_actions_config()
        
        assert result == {}
    
    def test_load_config_missing_actions_key(self, tmp_path):
        """Test loading config without 'actions' key."""
        config_content = """
other_key:
  - value1
  - value2
"""
        llms_file = tmp_path / "llms.txt"
        llms_file.write_text(config_content)
        
        with patch('os.path.join', return_value=str(llms_file)):
            with patch('os.path.exists', return_value=True):
                result = load_actions_config()
        
        assert result == {}
    
    @patch('builtins.open')
    @patch('os.path.exists')
    def test_load_config_read_error(self, mock_exists, mock_open_func):
        """Test handling of file read errors."""
        mock_exists.return_value = True
        mock_open_func.side_effect = IOError("Cannot read file")
        
        result = load_actions_config()
        
        assert result == {}
