"""
Tests for src/config/config_cli.py

This module tests the configuration CLI utilities for showing, diffing,
and versioning configurations across environments.
"""

import argparse
import json
import sys
from io import StringIO
from unittest.mock import patch, MagicMock, call

import pytest

from src.config.config_cli import (
    _safe_write_json,
    _cmd_show,
    _cmd_diff,
    _cmd_version,
    build_parser,
    main
)


@pytest.mark.ci_safe
class TestSafeWriteJson:
    """Tests for _safe_write_json function."""
    
    def test_safe_write_json_success(self, capsys):
        """Test successful JSON writing to stdout."""
        data = {"test": "value", "number": 42}
        
        result = _safe_write_json(data)
        
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output == data
    
    def test_safe_write_json_with_non_ascii(self, capsys):
        """Test JSON writing with non-ASCII characters."""
        data = {"message": "こんにちは", "emoji": "🎉"}
        
        result = _safe_write_json(data)
        
        assert result == 0
        captured = capsys.readouterr()
        output = json.loads(captured.out)
        assert output["message"] == "こんにちは"
        assert output["emoji"] == "🎉"
    
    @patch('sys.stdout')
    def test_safe_write_json_broken_pipe(self, mock_stdout):
        """Test handling of BrokenPipeError."""
        mock_stdout.write.side_effect = BrokenPipeError()
        
        data = {"test": "value"}
        result = _safe_write_json(data)
        
        # Should return 0 (success) despite broken pipe
        assert result == 0


@pytest.mark.ci_safe
class TestCmdShow:
    """Tests for _cmd_show function."""
    
    @patch('src.config.config_cli.MultiEnvConfigLoader')
    @patch('src.config.config_cli._safe_write_json')
    def test_cmd_show_basic(self, mock_write_json, mock_loader_class):
        """Test basic show command."""
        # Setup mock loader
        mock_loader = MagicMock()
        mock_loader.load.return_value = {"key": "value"}
        mock_loader._mask_secrets.return_value = (
            {"key": "***"},
            {"key": "hash123"}
        )
        mock_loader.logical_env = "dev"
        mock_loader.files_loaded = ["/path/to/config.yaml"]
        mock_loader.warnings = []
        mock_loader_class.return_value = mock_loader
        
        mock_write_json.return_value = 0
        
        # Create namespace
        ns = argparse.Namespace(env="dev", debug=False)
        
        # Execute
        result = _cmd_show(ns)
        
        assert result == 0
        mock_loader.load.assert_called_once_with("dev")
        mock_write_json.assert_called_once()
        
        # Check payload structure
        call_args = mock_write_json.call_args[0][0]
        assert call_args["env"] == "dev"
        assert call_args["config"] == {"key": "***"}
        assert call_args["masked_hashes"] == {"key": "hash123"}
    
    @patch('src.config.config_cli.MultiEnvConfigLoader')
    @patch('src.config.config_cli._safe_write_json')
    @patch('sys.stderr', new_callable=StringIO)
    def test_cmd_show_with_debug(self, mock_stderr, mock_write_json, mock_loader_class):
        """Test show command with debug flag."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {}
        mock_loader._mask_secrets.return_value = ({}, {})
        mock_loader.logical_env = "staging"
        mock_loader.files_loaded = ["/path/config1.yaml", "/path/config2.yaml"]
        mock_loader.warnings = ["Warning: Missing key"]
        mock_loader_class.return_value = mock_loader
        
        mock_write_json.return_value = 0
        
        ns = argparse.Namespace(env="staging", debug=True)
        
        result = _cmd_show(ns)
        
        assert result == 0
        stderr_output = mock_stderr.getvalue()
        assert "DEBUG env=staging" in stderr_output
        assert "files=2" in stderr_output
        assert "warnings=1" in stderr_output
        assert "file_loaded: /path/config1.yaml" in stderr_output
        assert "file_loaded: /path/config2.yaml" in stderr_output
        assert "warning: Warning: Missing key" in stderr_output
    
    @patch('src.config.config_cli.MultiEnvConfigLoader')
    @patch('src.config.config_cli._safe_write_json')
    @patch('sys.stderr', new_callable=StringIO)
    def test_cmd_show_no_files_loaded(self, mock_stderr, mock_write_json, mock_loader_class):
        """Test show command when no config files are loaded."""
        mock_loader = MagicMock()
        mock_loader.load.return_value = {}
        mock_loader._mask_secrets.return_value = ({}, {})
        mock_loader.logical_env = "dev"
        mock_loader.files_loaded = []  # Empty list
        mock_loader.warnings = []
        mock_loader_class.return_value = mock_loader
        
        mock_write_json.return_value = 0
        
        ns = argparse.Namespace(env="dev", debug=False)
        
        result = _cmd_show(ns)
        
        assert result == 0
        stderr_output = mock_stderr.getvalue()
        assert "WARNING: no configuration files loaded" in stderr_output


@pytest.mark.ci_safe
class TestCmdDiff:
    """Tests for _cmd_diff function."""
    
    @patch('src.config.config_cli.diff_envs')
    @patch('src.config.config_cli._safe_write_json')
    def test_cmd_diff_json_output(self, mock_write_json, mock_diff_envs):
        """Test diff command with JSON output."""
        diff_result = {
            "from": "dev",
            "to": "prod",
            "added": ["new_key"],
            "removed": ["old_key"],
            "changed": {
                "modified_key": {"from": "value1", "to": "value2"}
            }
        }
        mock_diff_envs.return_value = diff_result
        mock_write_json.return_value = 0
        
        ns = argparse.Namespace(from_env="dev", to_env="prod", json=True)
        
        result = _cmd_diff(ns)
        
        assert result == 0
        mock_diff_envs.assert_called_once_with("dev", "prod")
        mock_write_json.assert_called_once_with(diff_result)
    
    @patch('src.config.config_cli.diff_envs')
    def test_cmd_diff_text_output_with_changes(self, mock_diff_envs, capsys):
        """Test diff command with text output showing all change types."""
        diff_result = {
            "from": "dev",
            "to": "prod",
            "added": ["new_key1", "new_key2"],
            "removed": ["removed_key"],
            "changed": {
                "changed_key": {"from": "old", "to": "new"}
            }
        }
        mock_diff_envs.return_value = diff_result
        
        ns = argparse.Namespace(from_env="dev", to_env="prod", json=False)
        
        result = _cmd_diff(ns)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "Added:" in captured.out
        assert "+ new_key1" in captured.out
        assert "+ new_key2" in captured.out
        assert "Removed:" in captured.out
        assert "- removed_key" in captured.out
        assert "Changed:" in captured.out
        assert "changed_key" in captured.out
    
    @patch('src.config.config_cli.diff_envs')
    def test_cmd_diff_no_differences(self, mock_diff_envs, capsys):
        """Test diff command when environments are identical."""
        diff_result = {
            "from": "dev",
            "to": "dev",
            "added": [],
            "removed": [],
            "changed": {}
        }
        mock_diff_envs.return_value = diff_result
        
        ns = argparse.Namespace(from_env="dev", to_env="dev", json=False)
        
        result = _cmd_diff(ns)
        
        assert result == 0
        captured = capsys.readouterr()
        assert "No differences." in captured.out
    
    @patch('src.config.config_cli.diff_envs')
    @patch('sys.stdout')
    def test_cmd_diff_broken_pipe(self, mock_stdout, mock_diff_envs):
        """Test diff command handling BrokenPipeError."""
        diff_result = {
            "from": "dev",
            "to": "prod",
            "added": ["key"],
            "removed": [],
            "changed": {}
        }
        mock_diff_envs.return_value = diff_result
        mock_stdout.write.side_effect = BrokenPipeError()
        
        ns = argparse.Namespace(from_env="dev", to_env="prod", json=False)
        
        result = _cmd_diff(ns)
        
        # Should return 0 despite broken pipe
        assert result == 0


@pytest.mark.ci_safe
class TestCmdVersion:
    """Tests for _cmd_version function."""
    
    @patch('src.config.config_cli.version')
    @patch('src.config.config_cli._safe_write_json')
    def test_cmd_version_success(self, mock_write_json, mock_version):
        """Test version command with package installed."""
        mock_version.return_value = "1.2.3"
        mock_write_json.return_value = 0
        
        ns = argparse.Namespace()
        
        result = _cmd_version(ns)
        
        assert result == 0
        mock_version.assert_called_once_with("2bykilt")
        
        call_args = mock_write_json.call_args[0][0]
        assert call_args["package"] == "2bykilt"
        assert call_args["version"] == "1.2.3"
    
    @patch('src.config.config_cli.version')
    @patch('src.config.config_cli._safe_write_json')
    def test_cmd_version_package_not_found(self, mock_write_json, mock_version):
        """Test version command when package is not installed."""
        from importlib.metadata import PackageNotFoundError
        mock_version.side_effect = PackageNotFoundError()
        mock_write_json.return_value = 0
        
        ns = argparse.Namespace()
        
        result = _cmd_version(ns)
        
        assert result == 0
        call_args = mock_write_json.call_args[0][0]
        assert call_args["version"] == "unknown"


@pytest.mark.ci_safe
class TestBuildParser:
    """Tests for build_parser function."""
    
    def test_build_parser_structure(self):
        """Test parser structure and subcommands."""
        parser = build_parser()
        
        assert parser.prog == "bykilt-config"
        assert parser.description == "2bykilt configuration utilities"
    
    def test_build_parser_show_command(self):
        """Test 'show' subcommand parsing."""
        parser = build_parser()
        
        args = parser.parse_args(["show", "--env", "dev", "--debug"])
        
        assert args.command == "show"
        assert args.env == "dev"
        assert args.debug is True
        assert callable(args.func)
    
    def test_build_parser_show_without_env(self):
        """Test 'show' subcommand without env argument."""
        parser = build_parser()
        
        args = parser.parse_args(["show"])
        
        assert args.command == "show"
        assert args.env is None
        assert args.debug is False
    
    def test_build_parser_diff_command(self):
        """Test 'diff' subcommand parsing."""
        parser = build_parser()
        
        args = parser.parse_args(["diff", "--from", "dev", "--to", "prod", "--json"])
        
        assert args.command == "diff"
        assert args.from_env == "dev"
        assert args.to_env == "prod"
        assert args.json is True
        assert callable(args.func)
    
    def test_build_parser_diff_without_json(self):
        """Test 'diff' subcommand without JSON flag."""
        parser = build_parser()
        
        args = parser.parse_args(["diff", "--from", "dev", "--to", "staging"])
        
        assert args.json is False
    
    def test_build_parser_version_command(self):
        """Test 'version' subcommand parsing."""
        parser = build_parser()
        
        args = parser.parse_args(["version"])
        
        assert args.command == "version"
        assert callable(args.func)
    
    def test_build_parser_no_command(self):
        """Test parser requires a command."""
        parser = build_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args([])


@pytest.mark.ci_safe
class TestMain:
    """Tests for main function."""
    
    @patch('src.config.config_cli._cmd_show')
    def test_main_show_command(self, mock_cmd_show):
        """Test main function with show command."""
        mock_cmd_show.return_value = 0
        
        result = main(["show", "--env", "dev"])
        
        assert result == 0
        mock_cmd_show.assert_called_once()
    
    @patch('src.config.config_cli._cmd_diff')
    def test_main_diff_command(self, mock_cmd_diff):
        """Test main function with diff command."""
        mock_cmd_diff.return_value = 0
        
        result = main(["diff", "--from", "dev", "--to", "prod"])
        
        assert result == 0
        mock_cmd_diff.assert_called_once()
    
    @patch('src.config.config_cli._cmd_version')
    def test_main_version_command(self, mock_cmd_version):
        """Test main function with version command."""
        mock_cmd_version.return_value = 0
        
        result = main(["version"])
        
        assert result == 0
        mock_cmd_version.assert_called_once()
    
    def test_main_keyboard_interrupt(self):
        """Test main function handling KeyboardInterrupt."""
        with patch('src.config.config_cli._cmd_show', side_effect=KeyboardInterrupt()):
            result = main(["show"])
            
            assert result == 1

