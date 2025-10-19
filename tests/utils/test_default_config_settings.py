"""
Tests for src/utils/default_config_settings.py

This module tests configuration loading, validation, and saving functionality.
"""

import os
import json
import pickle
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest
import jsonschema
import gradio as gr

from src.utils.default_config_settings import (
    default_config,
    load_config_from_file,
    load_config_from_json,
    save_config_to_file,
    save_config_to_json,
    save_current_config,
    update_ui_from_config,
    CONFIG_SCHEMA
)


@pytest.mark.ci_safe
class TestDefaultConfig:
    """Tests for default_config function."""
    
    @patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False)
    def test_default_config_legacy(self):
        """Test legacy default configuration."""
        config = default_config()
        
        assert isinstance(config, dict)
        assert config["agent_type"] == "custom"
        assert config["max_steps"] == 100
        assert config["max_actions_per_step"] == 10
        assert config["use_vision"] is True
        assert config["llm_provider"] == "openai"
        assert config["llm_model_name"] == "gpt-4o"
        assert config["headless"] is False
        assert config["dev_mode"] is False
    
    @patch('src.utils.default_config_settings.get_config_for_environment')
    def test_default_config_multi_env(self, mock_get_config):
        """Test multi-environment configuration."""
        # Mock should return a complete config matching default_config structure
        mock_config = {
            "agent_type": "multi-env",
            "max_steps": 50,
            "max_actions_per_step": 10,
            "use_vision": True,
            "tool_calling_method": "auto",
            "llm_provider": "openai",
            "llm_model_name": "gpt-4o",
            "llm_num_ctx": 32000,
            "llm_temperature": 1.0,
            "llm_base_url": "",
            "llm_api_key": "",
            "use_own_browser": False,
            "keep_browser_open": False,
            "headless": False,
            "disable_security": True,
            "enable_recording": True,
            "window_w": 1280,
            "window_h": 1100,
            "save_recording_path": "./tmp/videos",
            "save_trace_path": "./tmp/traces",
            "save_agent_history_path": "./tmp/agent_history",
            "task": "test task",
            "dev_mode": False,
        }
        mock_get_config.return_value = mock_config
        
        # Patch MULTI_ENV_AVAILABLE within the function's module namespace
        with patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', True):
            config = default_config()
        
            assert config == mock_config
            assert config["agent_type"] == "multi-env"
            assert config["max_steps"] == 50
            mock_get_config.assert_called_once()
    
    @patch('src.utils.default_config_settings.get_config_for_environment')
    def test_default_config_multi_env_fallback(self, mock_get_config):
        """Test fallback when multi-env config fails."""
        mock_get_config.side_effect = Exception("Config error")
        
        # Patch MULTI_ENV_AVAILABLE within the function's module namespace
        with patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', True):
            config = default_config()
        
            # Should fallback to legacy config
            assert config["agent_type"] == "custom"
            assert config["max_steps"] == 100
    
    @patch.dict(os.environ, {'CHROME_PERSISTENT_SESSION': 'true'})
    @patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False)
    def test_default_config_use_own_browser(self):
        """Test use_own_browser from environment variable."""
        config = default_config()
        
        assert config["use_own_browser"] is True
    
    @patch('src.utils.default_config_settings.create_or_get_recording_dir')
    @patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False)
    def test_default_config_recording_path(self, mock_recording_dir):
        """Test recording path configuration."""
        mock_recording_dir.return_value = Path("/custom/recording/path")
        
        config = default_config()
        
        assert config["save_recording_path"] == "/custom/recording/path"


@pytest.mark.ci_safe
class TestLoadConfigFromFile:
    """Tests for load_config_from_file function."""
    
    def test_load_valid_pickle(self, tmp_path):
        """Test loading valid pickle configuration."""
        config_data = {"agent_type": "test", "max_steps": 50}
        config_file = tmp_path / "test.pkl"
        
        with open(config_file, 'wb') as f:
            pickle.dump(config_data, f)
        
        result = load_config_from_file(str(config_file))
        
        assert result == config_data
    
    def test_load_invalid_pickle(self, tmp_path):
        """Test loading invalid pickle file."""
        config_file = tmp_path / "invalid.pkl"
        config_file.write_text("invalid pickle data")
        
        result = load_config_from_file(str(config_file))
        
        assert isinstance(result, str)
        assert "Error loading configuration" in result
    
    def test_load_missing_file(self):
        """Test loading non-existent file."""
        result = load_config_from_file("/nonexistent/file.pkl")
        
        assert isinstance(result, str)
        assert "Error loading configuration" in result


@pytest.mark.ci_safe
class TestLoadConfigFromJson:
    """Tests for load_config_from_json function."""
    
    def test_load_valid_json(self, tmp_path):
        """Test loading valid JSON configuration."""
        config_data = default_config()
        config_file = tmp_path / "config.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = load_config_from_json(str(config_file))
        
        assert result == config_data
    
    def test_load_invalid_json_syntax(self, tmp_path):
        """Test loading JSON with syntax error."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json")
        
        result = load_config_from_json(str(config_file))
        
        assert isinstance(result, str)
        assert "Error loading configuration" in result
    
    def test_load_invalid_schema(self, tmp_path):
        """Test loading JSON with invalid schema."""
        config_data = {"invalid_key": "value"}
        config_file = tmp_path / "invalid_schema.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = load_config_from_json(str(config_file))
        
        assert isinstance(result, str)
        assert "Error validating configuration" in result
    
    def test_load_json_missing_required_fields(self, tmp_path):
        """Test loading JSON missing required fields."""
        config_data = {"agent_type": "test"}  # Missing many required fields
        config_file = tmp_path / "incomplete.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        result = load_config_from_json(str(config_file))
        
        assert isinstance(result, str)
        assert "Error validating configuration" in result


@pytest.mark.ci_safe
class TestSaveConfigToFile:
    """Tests for save_config_to_file function."""
    
    def test_save_config_pickle(self, tmp_path):
        """Test saving configuration to pickle file."""
        config_data = {"agent_type": "test", "max_steps": 50}
        
        result = save_config_to_file(config_data, save_dir=str(tmp_path))
        
        assert "Configuration saved to" in result
        assert tmp_path.exists()
        
        # Verify file was created
        pkl_files = list(tmp_path.glob("*.pkl"))
        assert len(pkl_files) == 1
        
        # Verify content
        with open(pkl_files[0], 'rb') as f:
            loaded = pickle.load(f)
        assert loaded == config_data
    
    def test_save_config_creates_directory(self):
        """Test that save creates directory if it doesn't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = os.path.join(tmpdir, "new_dir")
            config_data = {"test": "data"}
            
            result = save_config_to_file(config_data, save_dir=save_dir)
            
            assert os.path.exists(save_dir)
            assert "Configuration saved to" in result


@pytest.mark.ci_safe
class TestSaveConfigToJson:
    """Tests for save_config_to_json function."""
    
    def test_save_valid_json(self, tmp_path):
        """Test saving valid JSON configuration."""
        config_data = default_config()
        
        result = save_config_to_json(config_data, save_dir=str(tmp_path))
        
        assert "Configuration saved to" in result
        
        # Verify file exists and content
        config_file = tmp_path / "config.json"
        assert config_file.exists()
        
        with open(config_file, 'r') as f:
            loaded = json.load(f)
        assert loaded == config_data
    
    def test_save_invalid_json_schema(self, tmp_path):
        """Test saving JSON with invalid schema."""
        config_data = {"invalid_key": "value"}
        
        result = save_config_to_json(config_data, save_dir=str(tmp_path))
        
        assert "Error validating configuration" in result
    
    def test_save_json_creates_directory(self):
        """Test that JSON save creates directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            save_dir = os.path.join(tmpdir, "new_json_dir")
            config_data = default_config()
            
            result = save_config_to_json(config_data, save_dir=save_dir)
            
            assert os.path.exists(save_dir)
            assert "Configuration saved to" in result


@pytest.mark.ci_safe
class TestSaveCurrentConfig:
    """Tests for save_current_config function."""
    
    @patch('src.utils.default_config_settings.save_config_to_file')
    def test_save_current_config_all_args(self, mock_save):
        """Test saving current config with all arguments."""
        mock_save.return_value = "Success"
        
        # Prepare 23 arguments matching default_config keys
        args = [
            "custom",      # agent_type
            100,           # max_steps
            10,            # max_actions_per_step
            True,          # use_vision
            "auto",        # tool_calling_method
            "openai",      # llm_provider
            "gpt-4o",      # llm_model_name
            32000,         # llm_num_ctx
            1.0,           # llm_temperature
            "",            # llm_base_url
            "",            # llm_api_key
            False,         # use_own_browser
            False,         # keep_browser_open
            False,         # headless
            True,          # disable_security
            True,          # enable_recording
            1280,          # window_w
            1100,          # window_h
            "./tmp/videos",  # save_recording_path
            "./tmp/traces",  # save_trace_path
            "./tmp/history", # save_agent_history_path
            "test task",     # task
            False,           # dev_mode
        ]
        
        result = save_current_config(*args)
        
        assert result == "Success"
        mock_save.assert_called_once()
        
        # Verify the config dict structure
        saved_config = mock_save.call_args[0][0]
        assert saved_config["agent_type"] == "custom"
        assert saved_config["max_steps"] == 100
        assert saved_config["task"] == "test task"


@pytest.mark.ci_safe
class TestUpdateUIFromConfig:
    """Tests for update_ui_from_config function."""
    
    def test_update_ui_no_file(self):
        """Test update when no file is selected."""
        result = update_ui_from_config(None)
        
        # Should return tuple of gr.update() and message
        assert isinstance(result, tuple)
        assert len(result) == 23
        assert result[-1] == "No file selected."
    
    @patch('src.utils.default_config_settings.FEATURE_FLAGS_AVAILABLE', False)
    @patch.dict(os.environ, {'ALLOW_PICKLE_CONFIG': 'false'})
    def test_update_ui_pickle_not_allowed(self, tmp_path):
        """Test that pickle files are rejected by default."""
        config_file = tmp_path / "test.pkl"
        config_file.write_bytes(b"data")
        
        mock_file = MagicMock()
        mock_file.name = str(config_file)
        
        result = update_ui_from_config(mock_file)
        
        assert isinstance(result, tuple)
        assert "Error: .pkl files are not allowed" in result[-1]
    
    @patch('src.utils.default_config_settings.FEATURE_FLAGS_AVAILABLE', True)
    @patch('src.utils.default_config_settings.FeatureFlags')
    def test_update_ui_pickle_allowed_via_feature_flag(self, mock_flags, tmp_path):
        """Test pickle files allowed via feature flag."""
        mock_flags.is_enabled.return_value = True
        
        config_data = default_config()
        config_file = tmp_path / "test.pkl"
        with open(config_file, 'wb') as f:
            pickle.dump(config_data, f)
        
        mock_file = MagicMock()
        mock_file.name = str(config_file)
        
        result = update_ui_from_config(mock_file)
        
        assert isinstance(result, tuple)
        assert result[-1] == "Configuration loaded successfully."
    
    def test_update_ui_json_valid(self, tmp_path):
        """Test loading valid JSON file."""
        config_data = default_config()
        config_file = tmp_path / "config.json"
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        mock_file = MagicMock()
        mock_file.name = str(config_file)
        
        result = update_ui_from_config(mock_file)
        
        assert isinstance(result, tuple)
        assert len(result) == 24
        assert result[-1] == "Configuration loaded successfully."
    
    def test_update_ui_json_invalid(self, tmp_path):
        """Test loading invalid JSON file."""
        config_file = tmp_path / "invalid.json"
        config_file.write_text("{invalid json")
        
        mock_file = MagicMock()
        mock_file.name = str(config_file)
        
        result = update_ui_from_config(mock_file)
        
        assert isinstance(result, tuple)
        assert "Error: Invalid configuration file" in result[-1]
    
    def test_update_ui_unsupported_format(self):
        """Test unsupported file format."""
        mock_file = MagicMock()
        mock_file.name = "config.txt"
        
        result = update_ui_from_config(mock_file)
        
        assert isinstance(result, tuple)
        assert "Error: Only .json files are supported" in result[-1]


@pytest.mark.ci_safe
class TestConfigSchema:
    """Tests for CONFIG_SCHEMA validation."""
    
    def test_schema_validates_default_config(self):
        """Test that default config passes schema validation."""
        config = default_config()
        
        # Should not raise
        jsonschema.validate(instance=config, schema=CONFIG_SCHEMA)
    
    def test_schema_rejects_invalid_types(self):
        """Test schema rejects invalid types."""
        invalid_config = default_config()
        invalid_config["max_steps"] = "not a number"
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_config, schema=CONFIG_SCHEMA)
    
    def test_schema_rejects_out_of_range(self):
        """Test schema rejects out of range values."""
        invalid_config = default_config()
        invalid_config["llm_temperature"] = 5.0  # Max is 2
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=invalid_config, schema=CONFIG_SCHEMA)
    
    def test_schema_requires_all_fields(self):
        """Test schema requires all fields."""
        incomplete_config = {"agent_type": "test"}
        
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(instance=incomplete_config, schema=CONFIG_SCHEMA)
