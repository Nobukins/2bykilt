"""
Semantic version parsing and validation.

Provides parsing, validation, and comparison utilities for semantic versioning.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class SemanticVersion:
    """Represents a semantic version following semver.org specification."""
    major: int
    minor: int
    patch: int
    prerelease: Optional[str] = None
    metadata: Optional[str] = None

    def __str__(self) -> str:
        """Return the version string representation."""
        version = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            version += f"-{self.prerelease}"
        if self.metadata:
            version += f"+{self.metadata}"
        return version

    def __lt__(self, other: 'SemanticVersion') -> bool:
        """Check if this version is less than another."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented

        # Compare major.minor.patch
        if (self.major, self.minor, self.patch) != (other.major, other.minor, other.patch):
            return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)

        # Versions with prerelease are less than release versions
        if bool(self.prerelease) != bool(other.prerelease):
            return bool(self.prerelease)

        # Both have prerelease or both don't
        if self.prerelease is not None and other.prerelease is not None:
            return self.prerelease < other.prerelease

        return False

    def __eq__(self, other: object) -> bool:
        """Check if this version equals another."""
        if not isinstance(other, SemanticVersion):
            return NotImplemented
        return (self.major, self.minor, self.patch, self.prerelease) == \
               (other.major, other.minor, other.patch, other.prerelease)

    def __le__(self, other: 'SemanticVersion') -> bool:
        """Check if this version is less than or equal to another."""
        return self < other or self == other

    def __gt__(self, other: 'SemanticVersion') -> bool:
        """Check if this version is greater than another."""
        return other < self

    def __ge__(self, other: 'SemanticVersion') -> bool:
        """Check if this version is greater than or equal to another."""
        return self > other or self == other


def parse_version(version_string: str) -> SemanticVersion:
    """
    Parse a semantic version string.

    Args:
        version_string: Version string (e.g., "1.2.3", "1.2.3-alpha", "1.2.3+build.1")

    Returns:
        SemanticVersion object

    Raises:
        ValueError: If version string is invalid
    """
    # Pattern: major.minor.patch[-prerelease][+metadata]
    pattern = r'^(\d+)\.(\d+)\.(\d+)(?:-([a-zA-Z0-9.-]+))?(?:\+([a-zA-Z0-9.-]+))?$'
    match = re.match(pattern, version_string.strip())

    if not match:
        raise ValueError(f"Invalid semantic version: {version_string}")

    major, minor, patch, prerelease, metadata = match.groups()
    return SemanticVersion(
        major=int(major),
        minor=int(minor),
        patch=int(patch),
        prerelease=prerelease,
        metadata=metadata
    )


def validate_version(version_string: str) -> bool:
    """
    Validate if a string is a valid semantic version.

    Args:
        version_string: Version string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        parse_version(version_string)
        return True
    except ValueError:
        return False
