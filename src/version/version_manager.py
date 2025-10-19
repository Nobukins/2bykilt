"""
Version manager for 2bykilt.

Handles version file I/O, bumping, and Git tag management.
"""

import logging
import subprocess
from pathlib import Path
from typing import Optional

from .parser import SemanticVersion, parse_version, validate_version


logger = logging.getLogger(__name__)

# Default version file location
DEFAULT_VERSION_FILE = Path(__file__).parent.parent.parent / "VERSION"


class VersionManager:
    """Manages semantic versioning for the project."""

    def __init__(self, version_file: Optional[Path] = None):
        """
        Initialize VersionManager.

        Args:
            version_file: Path to VERSION file. Uses default if not provided.
        """
        self.version_file = version_file or DEFAULT_VERSION_FILE

    def get_current_version(self) -> SemanticVersion:
        """
        Get the current project version.

        Returns:
            SemanticVersion object

        Raises:
            FileNotFoundError: If VERSION file doesn't exist
            ValueError: If VERSION file contains invalid version
        """
        if not self.version_file.exists():
            raise FileNotFoundError(f"VERSION file not found at {self.version_file}")

        version_string = self.version_file.read_text(encoding='utf-8').strip()
        return parse_version(version_string)

    def set_version(self, version: str) -> None:
        """
        Set the project version.

        Args:
            version: Version string (e.g., "1.2.3")

        Raises:
            ValueError: If version string is invalid
        """
        if not validate_version(version):
            raise ValueError(f"Invalid semantic version: {version}")

        # Ensure parent directory exists
        self.version_file.parent.mkdir(parents=True, exist_ok=True)

        # Write version file
        self.version_file.write_text(f"{version}\n", encoding='utf-8')
        logger.info("Set version to %s", version)

    def bump_version(self, bump_type: str) -> SemanticVersion:
        """
        Bump version (major, minor, or patch).

        Args:
            bump_type: Type of bump ('major', 'minor', or 'patch')

        Returns:
            New SemanticVersion

        Raises:
            ValueError: If bump_type is invalid
        """
        if bump_type not in ('major', 'minor', 'patch'):
            raise ValueError(f"Invalid bump type: {bump_type}. Must be 'major', 'minor', or 'patch'")

        current = self.get_current_version()

        if bump_type == 'major':
            new_version = SemanticVersion(current.major + 1, 0, 0)
        elif bump_type == 'minor':
            new_version = SemanticVersion(current.major, current.minor + 1, 0)
        else:  # patch
            new_version = SemanticVersion(current.major, current.minor, current.patch + 1)

        self.set_version(str(new_version))
        logger.info("Bumped version from %s to %s", current, new_version)
        return new_version

    def create_git_tag(self, tag_prefix: str = "v") -> str:
        """
        Create a Git tag for the current version.

        Args:
            tag_prefix: Prefix for the tag (e.g., "v" for "v1.2.3")

        Returns:
            Tag name

        Raises:
            subprocess.CalledProcessError: If git command fails
        """
        version = self.get_current_version()
        tag_name = f"{tag_prefix}{version}"

        try:
            subprocess.run(
                ['git', 'tag', tag_name],
                check=True,
                capture_output=True,
                text=True
            )
            logger.info("Created Git tag: %s", tag_name)
            return tag_name
        except subprocess.CalledProcessError as e:
            logger.error("Failed to create Git tag: %s", e.stderr)
            raise

    def get_git_tags(self) -> list:
        """
        Get list of Git version tags.
        
        Returns:
            List of tag names
        """
        try:
            result = subprocess.run(
                ['git', 'tag', '-l', 'v*'],
                check=True,
                capture_output=True,
                text=True
            )
            return [tag.strip() for tag in result.stdout.strip().split('\n') if tag.strip()]
        except subprocess.CalledProcessError:
            logger.warning("Failed to retrieve Git tags")
            return []


def get_current_version() -> str:
    """Get current version as string."""
    manager = VersionManager()
    return str(manager.get_current_version())


def set_version(version: str) -> None:
    """Set project version."""
    manager = VersionManager()
    manager.set_version(version)
