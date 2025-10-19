"""Tests for version manager functionality."""

import json
import os
import subprocess
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.version.version_manager import VersionManager, get_current_version, set_version


@pytest.mark.ci_safe
def test_version_manager_creation():
    """Test VersionManager instance creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        assert manager.version_file == version_file


@pytest.mark.ci_safe
def test_get_current_version_basic():
    """Test getting current version from file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("2.3.4\n")
        
        manager = VersionManager(version_file)
        version = manager.get_current_version()
        
        assert version.major == 2
        assert version.minor == 3
        assert version.patch == 4


@pytest.mark.ci_safe
def test_get_current_version_with_prerelease():
    """Test getting version with prerelease."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0-beta\n")
        
        manager = VersionManager(version_file)
        version = manager.get_current_version()
        
        assert str(version) == "1.0.0-beta"


@pytest.mark.ci_safe
def test_set_version():
    """Test setting new version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        manager.set_version("2.0.0")
        
        assert version_file.read_text().strip() == "2.0.0"


@pytest.mark.ci_safe
def test_bump_version_major():
    """Test bumping major version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.2.3\n")
        
        manager = VersionManager(version_file)
        manager.bump_version("major")
        
        new_version = manager.get_current_version()
        assert str(new_version) == "2.0.0"


@pytest.mark.ci_safe
def test_bump_version_minor():
    """Test bumping minor version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.2.3\n")
        
        manager = VersionManager(version_file)
        manager.bump_version("minor")
        
        new_version = manager.get_current_version()
        assert str(new_version) == "1.3.0"


@pytest.mark.ci_safe
def test_bump_version_patch():
    """Test bumping patch version."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.2.3\n")
        
        manager = VersionManager(version_file)
        manager.bump_version("patch")
        
        new_version = manager.get_current_version()
        assert str(new_version) == "1.2.4"


@pytest.mark.ci_safe
def test_bump_version_invalid():
    """Test bumping with invalid type."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        with pytest.raises(ValueError):
            manager.bump_version("invalid")


@pytest.mark.ci_safe
def test_bump_version_clears_prerelease():
    """Test bumping version clears prerelease."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0-alpha\n")
        
        manager = VersionManager(version_file)
        manager.bump_version("patch")
        
        new_version = manager.get_current_version()
        assert str(new_version) == "1.0.1"
        assert new_version.prerelease is None


@pytest.mark.ci_safe
def test_create_git_tag():
    """Test creating git tag."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_git_tag()
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "tag" in args
            assert "v1.0.0" in args


@pytest.mark.ci_safe
def test_create_git_tag_with_prefix():
    """Test creating git tag with custom prefix."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("2.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            manager.create_git_tag(tag_prefix="release-")
            
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "git" in args
            assert "tag" in args
            assert "release-2.0.0" in args


@pytest.mark.ci_safe
def test_create_git_tag_failure():
    """Test git tag creation failure."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git tag', stderr="error")
            
            with pytest.raises(subprocess.CalledProcessError):
                manager.create_git_tag()


@pytest.mark.ci_safe
def test_get_git_tags():
    """Test getting list of git tags."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="v1.0.0\nv0.9.0\nv0.8.0"
            )
            tags = manager.get_git_tags()
            
            assert "v1.0.0" in tags
            assert "v0.9.0" in tags
            assert "v0.8.0" in tags


@pytest.mark.ci_safe
def test_get_git_tags_empty():
    """Test getting git tags when none exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="")
            tags = manager.get_git_tags()
            
            assert tags == []


@pytest.mark.ci_safe
def test_get_git_tags_failure():
    """Test git tag listing failure returns empty list."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        manager = VersionManager(version_file)
        
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, 'git tag -l')
            
            tags = manager.get_git_tags()
            assert tags == []


@pytest.mark.ci_safe
def test_module_convenience_get_current_version():
    """Test module-level get_current_version convenience function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("3.2.1\n")
        
        with patch("src.version.version_manager.DEFAULT_VERSION_FILE", version_file):
            version = get_current_version()
            assert str(version) == "3.2.1"


@pytest.mark.ci_safe
def test_module_convenience_set_version():
    """Test module-level set_version convenience function."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("1.0.0\n")
        
        with patch("src.version.version_manager.DEFAULT_VERSION_FILE", version_file):
            set_version("2.0.0")
            assert version_file.read_text().strip() == "2.0.0"


@pytest.mark.ci_safe
def test_version_manager_file_not_found():
    """Test VersionManager with missing file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "MISSING_VERSION"
        
        manager = VersionManager(version_file)
        
        with pytest.raises(FileNotFoundError):
            manager.get_current_version()


@pytest.mark.ci_safe
def test_version_manager_invalid_version_in_file():
    """Test VersionManager with invalid version string in file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        version_file = Path(tmpdir) / "VERSION"
        version_file.write_text("invalid-version\n")
        
        manager = VersionManager(version_file)
        
        with pytest.raises(ValueError):
            manager.get_current_version()
