"""Tests for version CLI functionality."""

import argparse
from unittest.mock import MagicMock, patch

import pytest

from src.version.cli import (
    _handle_version_bump,
    _handle_version_set,
    _handle_version_show,
    _handle_version_tag,
    _handle_version_tags,
    create_version_parser,
    version_command,
)


@pytest.mark.ci_safe
def test_create_version_parser():
    """Test version parser creation."""
    main_parser = argparse.ArgumentParser()
    subparsers = main_parser.add_subparsers()
    parser = create_version_parser(subparsers)
    assert parser is not None


@pytest.mark.ci_safe
def test_handle_version_show():
    """Test show version command handler."""
    mock_manager = MagicMock()
    mock_version = MagicMock()
    mock_version.__str__ = MagicMock(return_value="1.2.3")
    mock_manager.get_current_version.return_value = mock_version
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_show(mock_manager)
        assert result == 0
        mock_print.assert_called_once()
        call_arg = mock_print.call_args[0][0]
        assert "1.2.3" in call_arg


@pytest.mark.ci_safe
def test_handle_version_set_success():
    """Test set version command handler with success."""
    mock_manager = MagicMock()
    args = argparse.Namespace(version="2.0.0", version_arg=None)
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_set(mock_manager, args)
        assert result == 0
        mock_manager.set_version.assert_called_once_with("2.0.0")
        mock_print.assert_called_once()


@pytest.mark.ci_safe
def test_handle_version_set_no_version_arg():
    """Test set version with no version argument."""
    mock_manager = MagicMock()
    args = argparse.Namespace(version=None, version_arg=None)
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_set(mock_manager, args)
        assert result == 1
        mock_print.assert_called_once()
        assert "Error" in mock_print.call_args[0][0]


@pytest.mark.ci_safe
def test_handle_version_bump_major():
    """Test bump major version command handler."""
    mock_manager = MagicMock()
    mock_new_version = MagicMock()
    mock_new_version.__str__ = MagicMock(return_value="2.0.0")
    mock_manager.bump_version.return_value = mock_new_version
    args = argparse.Namespace(bump_type="major")
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_bump(mock_manager, args)
        assert result == 0
        mock_manager.bump_version.assert_called_once_with("major")
        mock_print.assert_called_once()


@pytest.mark.ci_safe
def test_handle_version_bump_no_type():
    """Test bump with no type argument."""
    mock_manager = MagicMock()
    args = argparse.Namespace(bump_type=None)
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_bump(mock_manager, args)
        assert result == 1
        mock_print.assert_called_once()
        assert "Error" in mock_print.call_args[0][0]


@pytest.mark.ci_safe
def test_handle_version_tag():
    """Test create tag command handler."""
    mock_manager = MagicMock()
    mock_manager.create_git_tag.return_value = "v1.0.0"
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_tag(mock_manager)
        assert result == 0
        mock_manager.create_git_tag.assert_called_once()
        mock_print.assert_called_once()
        assert "v1.0.0" in mock_print.call_args[0][0]


@pytest.mark.ci_safe
def test_handle_version_tags_with_results():
    """Test list tags command handler with results."""
    mock_manager = MagicMock()
    mock_manager.get_git_tags.return_value = ["v1.0.0", "v0.9.0"]
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_tags(mock_manager)
        assert result == 0
        assert mock_print.call_count >= 2


@pytest.mark.ci_safe
def test_handle_version_tags_empty():
    """Test list tags with no tags found."""
    mock_manager = MagicMock()
    mock_manager.get_git_tags.return_value = []
    
    with patch("builtins.print") as mock_print:
        result = _handle_version_tags(mock_manager)
        assert result == 0
        mock_print.assert_called_once()
        assert "No version tags" in mock_print.call_args[0][0]


@pytest.mark.ci_safe
def test_version_command_show():
    """Test version command dispatcher with show action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        mock_version = MagicMock()
        mock_version.__str__ = MagicMock(return_value="1.2.3")
        mock_manager.get_current_version.return_value = mock_version
        
        args = argparse.Namespace(version_subcommand="show")
        
        with patch("builtins.print") as mock_print:
            result = version_command(args)
            assert result == 0
            mock_print.assert_called_once()


@pytest.mark.ci_safe
def test_version_command_set():
    """Test version command dispatcher with set action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        
        args = argparse.Namespace(
            version_subcommand="set",
            version="2.0.0",
            version_arg=None
        )
        
        with patch("builtins.print"):
            result = version_command(args)
            assert result == 0
            mock_manager.set_version.assert_called_once_with("2.0.0")


@pytest.mark.ci_safe
def test_version_command_bump():
    """Test version command dispatcher with bump action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        mock_new_version = MagicMock()
        mock_new_version.__str__ = MagicMock(return_value="2.0.0")
        mock_manager.bump_version.return_value = mock_new_version
        
        args = argparse.Namespace(
            version_subcommand="bump",
            bump_type="major"
        )
        
        with patch("builtins.print"):
            result = version_command(args)
            assert result == 0
            mock_manager.bump_version.assert_called_once_with("major")


@pytest.mark.ci_safe
def test_version_command_tag():
    """Test version command dispatcher with tag action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        mock_manager.create_git_tag.return_value = "v1.0.0"
        
        args = argparse.Namespace(version_subcommand="tag")
        
        with patch("builtins.print"):
            result = version_command(args)
            assert result == 0
            mock_manager.create_git_tag.assert_called_once()


@pytest.mark.ci_safe
def test_version_command_tags():
    """Test version command dispatcher with tags action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        mock_manager.get_git_tags.return_value = ["v1.0.0"]
        
        args = argparse.Namespace(version_subcommand="tags")
        
        with patch("builtins.print"):
            result = version_command(args)
            assert result == 0
            mock_manager.get_git_tags.assert_called_once()


@pytest.mark.ci_safe
def test_version_command_unknown_action():
    """Test version command with unknown action."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        
        args = argparse.Namespace(version_subcommand="unknown")
        
        with patch("builtins.print") as mock_print:
            result = version_command(args)
            assert result == 1
            mock_print.assert_called_once()
            assert "Unknown" in mock_print.call_args[0][0]


@pytest.mark.ci_safe
def test_version_command_exception_handling():
    """Test version command exception handling."""
    with patch("src.version.cli.VersionManager") as mock_vm_class:
        mock_manager = MagicMock()
        mock_vm_class.return_value = mock_manager
        mock_manager.get_current_version.side_effect = RuntimeError("Test error")
        
        args = argparse.Namespace(version_subcommand="show")
        
        with patch("builtins.print") as mock_print:
            result = version_command(args)
            assert result == 1
            call_text = mock_print.call_args[0][0]
            assert "Error" in call_text
