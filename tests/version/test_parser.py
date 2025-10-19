"""Tests for semantic version parsing and comparison."""

import pytest
from src.version.parser import SemanticVersion, parse_version, validate_version


@pytest.mark.ci_safe
def test_semantic_version_basic():
    """Test basic SemanticVersion creation."""
    version = SemanticVersion(1, 2, 3)
    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3
    assert version.prerelease is None
    assert version.metadata is None


@pytest.mark.ci_safe
def test_semantic_version_with_prerelease():
    """Test SemanticVersion with prerelease."""
    version = SemanticVersion(1, 2, 3, prerelease="alpha")
    assert str(version) == "1.2.3-alpha"


@pytest.mark.ci_safe
def test_semantic_version_with_metadata():
    """Test SemanticVersion with metadata."""
    version = SemanticVersion(1, 2, 3, metadata="build.1")
    assert str(version) == "1.2.3+build.1"


@pytest.mark.ci_safe
def test_semantic_version_full():
    """Test SemanticVersion with prerelease and metadata."""
    version = SemanticVersion(1, 2, 3, prerelease="beta", metadata="build.5")
    assert str(version) == "1.2.3-beta+build.5"


@pytest.mark.ci_safe
def test_parse_version_basic():
    """Test parsing basic version string."""
    version = parse_version("1.2.3")
    assert version.major == 1
    assert version.minor == 2
    assert version.patch == 3


@pytest.mark.ci_safe
def test_parse_version_with_prerelease():
    """Test parsing version with prerelease."""
    version = parse_version("1.2.3-alpha.1")
    assert version.major == 1
    assert version.prerelease == "alpha.1"


@pytest.mark.ci_safe
def test_parse_version_with_metadata():
    """Test parsing version with metadata."""
    version = parse_version("1.2.3+build.123")
    assert version.metadata == "build.123"


@pytest.mark.ci_safe
def test_parse_version_full():
    """Test parsing complete version string."""
    version = parse_version("2.0.0-rc.1+build.456")
    assert version.major == 2
    assert version.minor == 0
    assert version.patch == 0
    assert version.prerelease == "rc.1"
    assert version.metadata == "build.456"


@pytest.mark.ci_safe
def test_parse_version_invalid():
    """Test parsing invalid version strings."""
    invalid_versions = [
        "1.2",  # Missing patch
        "1.2.3.4",  # Too many parts
        "a.b.c",  # Non-numeric
        "1.2.3-",  # Invalid prerelease
        "1.2.3+",  # Invalid metadata
        "",  # Empty
    ]
    for version_str in invalid_versions:
        with pytest.raises(ValueError):
            parse_version(version_str)


@pytest.mark.ci_safe
def test_validate_version_valid():
    """Test validating valid versions."""
    valid_versions = ["1.0.0", "0.0.1", "10.20.30", "1.0.0-alpha", "1.0.0+build"]
    for version_str in valid_versions:
        assert validate_version(version_str)


@pytest.mark.ci_safe
def test_validate_version_invalid():
    """Test validating invalid versions."""
    invalid_versions = ["1.2", "a.b.c", "1.2.3.4"]
    for version_str in invalid_versions:
        assert not validate_version(version_str)


@pytest.mark.ci_safe
def test_version_comparison_equal():
    """Test version equality comparison."""
    v1 = parse_version("1.2.3")
    v2 = parse_version("1.2.3")
    assert v1 == v2
    assert v1 >= v2
    assert v1 <= v2


@pytest.mark.ci_safe
def test_version_comparison_less_than():
    """Test version less than comparison."""
    v1 = parse_version("1.2.2")
    v2 = parse_version("1.2.3")
    assert v1 < v2
    assert v1 <= v2
    assert v1 <= v2
    assert v1 < v2


@pytest.mark.ci_safe
def test_version_comparison_greater_than():
    """Test version greater than comparison."""
    v1 = parse_version("2.0.0")
    v2 = parse_version("1.9.9")
    assert v1 > v2
    assert v1 >= v2
    assert v1 > v2
    assert v1 > v2


@pytest.mark.ci_safe
def test_version_comparison_prerelease():
    """Test prerelease versions are less than release versions."""
    release = parse_version("1.0.0")
    prerelease = parse_version("1.0.0-alpha")
    assert prerelease < release
    assert prerelease <= release


@pytest.mark.ci_safe
def test_version_major_bump():
    """Test major version increment."""
    v1 = parse_version("1.2.3")
    v2 = SemanticVersion(v1.major + 1, 0, 0)
    assert str(v2) == "2.0.0"


@pytest.mark.ci_safe
def test_version_minor_bump():
    """Test minor version increment."""
    v1 = parse_version("1.2.3")
    v2 = SemanticVersion(v1.major, v1.minor + 1, 0)
    assert str(v2) == "1.3.0"


@pytest.mark.ci_safe
def test_version_patch_bump():
    """Test patch version increment."""
    v1 = parse_version("1.2.3")
    v2 = SemanticVersion(v1.major, v1.minor, v1.patch + 1)
    assert str(v2) == "1.2.4"
