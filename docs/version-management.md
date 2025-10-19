# Version Management System (Issue #342)

The Version Management System provides a comprehensive solution for managing and tracking project versions according to [Semantic Versioning 2.0.0](https://semver.org/) standards.

## Overview

The version management system is built on three core components:

1. **Semantic Version Parser** (`src/version/parser.py`): Parses and validates semantic version strings
2. **Version Manager** (`src/version/version_manager.py`): Handles version file I/O and Git operations
3. **CLI Interface** (`src/version/cli.py`): Provides command-line access to version management operations

## Features

### Semantic Versioning Support

- **Format**: `MAJOR.MINOR.PATCH[-PRERELEASE][+METADATA]`
- **Examples**:
  - `1.0.0` - Release version
  - `1.0.0-alpha` - Prerelease version
  - `1.0.0-beta.1` - Prerelease with identifier
  - `1.0.0+build.1` - Version with metadata
  - `1.0.0-rc.1+build.456` - Full specification

### Version Comparison

The system supports full semantic version comparison operators:

- Equal: `1.0.0 == 1.0.0`
- Less than: `0.9.0 < 1.0.0`
- Greater than: `2.0.0 > 1.0.0`
- Prerelease handling: `1.0.0-alpha < 1.0.0`

### Version Bumping

Automatically increment version numbers:

- **Major bump**: `1.2.3` → `2.0.0` (breaking changes)
- **Minor bump**: `1.2.3` → `1.3.0` (feature additions)
- **Patch bump**: `1.2.3` → `1.2.4` (bug fixes)

Prerelease tags are automatically cleared during version bumping.

### Git Integration

- Create annotated tags for versions: `git tag v1.0.0`
- List all version tags: `git tag -l 'v*'`
- Automatic tag naming with configurable prefix (default: `v`)

## CLI Usage

### Display Current Version

```bash
python bykilt.py version show
# Output: 2bykilt version: 0.0.1
```

### Set Specific Version

```bash
python bykilt.py version set 1.5.0
# Output: Version set to 1.5.0

# Set with prerelease
python bykilt.py version set 2.0.0-beta.1
```

### Bump Version

```bash
# Bump major version (1.2.3 → 2.0.0)
python bykilt.py version bump --type major

# Bump minor version (1.2.3 → 1.3.0)
python bykilt.py version bump --type minor

# Bump patch version (1.2.3 → 1.2.4)
python bykilt.py version bump --type patch
```

### Create Git Tag

```bash
# Create tag with default prefix 'v' (v1.2.3)
python bykilt.py version tag

# Create tag with custom prefix
python bykilt.py version tag --prefix release-
```

### List Version Tags

```bash
python bykilt.py version tags
# Output:
# Version tags:
#   v1.0.0
#   v0.9.0
#   v0.8.0
```

## Version File Location

The version is stored in the `VERSION` file at the project root:

```text
PROJECT_ROOT/
├── VERSION          # Contains current version string (e.g., "0.0.1\n")
├── bykilt.py
├── src/
│   └── version/
│       ├── __init__.py
│       ├── parser.py
│       ├── version_manager.py
│       └── cli.py
└── ...
```

## Python API Usage

### Import Version Management

```python
from src.version import SemanticVersion, parse_version
from src.version.version_manager import VersionManager, get_current_version, set_version

# Get current version as string
version_str = get_current_version()
print(f"Current version: {version_str}")

# Set new version
set_version("1.5.0")

# Parse version for comparison
v1 = parse_version("1.0.0")
v2 = parse_version("1.1.0")
if v1 < v2:
    print("v1 is earlier than v2")
```

### Using VersionManager Directly

```python
from pathlib import Path
from src.version.version_manager import VersionManager

# Initialize manager with custom version file path
version_file = Path("/path/to/VERSION")
manager = VersionManager(version_file)

# Get current version
version = manager.get_current_version()
print(f"Current: {version}")

# Bump version
new_version = manager.bump_version("minor")
print(f"Bumped to: {new_version}")

# Create Git tag
tag_name = manager.create_git_tag()
print(f"Created tag: {tag_name}")

# List tags
tags = manager.get_git_tags()
print(f"Tags: {tags}")
```

## Release Workflow

See [Release Process Guide](./release-process.md) for recommended version management workflow during releases.

## Error Handling

The version management system includes comprehensive error handling:

### Invalid Version Strings

```python
from src.version.parser import parse_version

try:
    version = parse_version("invalid")  # Raises ValueError
except ValueError as e:
    print(f"Invalid version: {e}")
```

### Git Operations

```python
from src.version.version_manager import VersionManager

try:
    manager.create_git_tag()
except subprocess.CalledProcessError as e:
    print(f"Git operation failed: {e}")
```

### File Not Found

```python
try:
    version = manager.get_current_version()
except FileNotFoundError:
    print("VERSION file not found")
```

## Testing

Comprehensive test suite is included with 94%+ coverage:

```bash
# Run all version tests
pytest tests/version/ -v

# Run with coverage report
pytest tests/version/ --cov=src/version --cov-report=term

# Run specific test file
pytest tests/version/test_parser.py -v
```

## Related Issues

- **Issue #342**: Release Version Management System (this feature)
- **Issue #344**: Client UI Packaging (depends on Issue #342)
- **Issue #346**: Artifact Auto-backup (depends on Issue #342)

## Architecture

The version management system follows a layered architecture:

```text
CLI Layer (cli.py)
    ↓
Version Manager Layer (version_manager.py)
    ↓
Parser Layer (parser.py)
    ↓
Git/File I/O
```

This separation allows:

- Easy CLI integration and extension
- Reusable version manager for programmatic use
- Testable parsing and comparison logic
- Clear separation of concerns

## Future Enhancements

Potential future improvements:

- [ ] Automatic changelog generation
- [ ] Version constraint matching (e.g., `>=1.0.0 <2.0.0`)
- [ ] Release branch management
- [ ] Semantic commit parsing for auto-versioning
- [ ] Version history tracking

## Troubleshooting

### VERSION file not found

**Error**: `FileNotFoundError: VERSION file not found`

**Solution**: Ensure `VERSION` file exists in project root with valid semantic version string.

```bash
echo "1.0.0" > VERSION
```

### Git tag already exists

**Error**: `fatal: tag 'v1.0.0' already exists`

**Solution**: Delete existing tag or use different prefix:

```bash
git tag -d v1.0.0
python bykilt.py version tag
```

### Invalid version format

**Error**: `ValueError: Invalid semantic version`

**Solution**: Ensure version string matches semantic versioning format:

```bash
# Valid formats
1.0.0
1.0.0-alpha
1.0.0-beta.1
1.0.0+build.1

# Invalid formats
1.0
1.0.0.0
v1.0.0
```

## References

- [Semantic Versioning 2.0.0](https://semver.org/)
- [Python argparse documentation](https://docs.python.org/3/library/argparse.html)
- [Git Tags documentation](https://git-scm.com/book/en/v2/Git-Basics-Tagging)
