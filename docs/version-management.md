# Version Management

## Overview

The version management system provides semantic versioning support with Git integration. It enables teams to manage releases consistently and automatically.

### Architecture

```text
┌─────────────────────────────────────────┐
│         CLI Layer                       │
│  (create_version_parser, version_cmd)  │
├─────────────────────────────────────────┤
│    Version Manager Layer                │
│  (VersionManager, command dispatch)     │
├─────────────────────────────────────────┤
│    Version Parser Layer                 │
│  (VersionParser, parsing & comparison)  │
├─────────────────────────────────────────┤
│      VERSION File & Git                 │
│  (Persistence & Tag Management)         │
└─────────────────────────────────────────┘
```

## Semantic Versioning

The system follows [Semantic Versioning 2.0.0](https://semver.org/) format:

```text
MAJOR.MINOR.PATCH[-PRERELEASE][+METADATA]
```

### Format Examples

- `1.0.0` - Release version
- `1.0.0-alpha.1` - Prerelease version (alpha stage, first iteration)
- `1.0.0-beta.2` - Prerelease version (beta stage, second iteration)
- `1.0.0-rc.1` - Release candidate
- `1.0.0+build.20231115` - Version with build metadata
- `1.0.0-rc.1+build.20231115` - Prerelease with metadata

### Versioning Rules

1. **MAJOR** - Breaking changes (incompatible API changes)
2. **MINOR** - Backward-compatible new features
3. **PATCH** - Backward-compatible bug fixes
4. **PRERELEASE** - Alpha, beta, rc versions (optional)
5. **METADATA** - Build information (optional, ignored in precedence)

## Version Comparison

The parser supports comparison operators for version matching:

- `==` - Exact match: `1.0.0 == 1.0.0`
- `!=` - Not equal: `1.0.0 != 1.1.0`
- `>` - Greater than: `1.1.0 > 1.0.0`
- `<` - Less than: `1.0.0 < 1.1.0`
- `>=` - Greater or equal: `1.0.0 >= 1.0.0`
- `<=` - Less or equal: `1.0.0 <= 1.1.0`
- `~` - Pessimistic constraint: `~1.0.0` matches `1.0.x` but not `1.1.0`
- `^` - Caret constraint: `^1.0.0` matches `1.x.x` but not `2.0.0`

## CLI Commands

### Show Current Version

```bash
python bykilt.py version show
```

Output:

```text
0.1.0
```

### Set Specific Version

```bash
python bykilt.py version set 2.0.0
```

After execution, the VERSION file is updated and version is confirmed.

### Version Bumping

Automatically increment version numbers for releases:

#### Bump Major (Breaking Changes)

```bash
python bykilt.py version bump --type major
```

- Before: `1.2.3`
- After: `2.0.0`

#### Bump Minor (Features)

```bash
python bykilt.py version bump --type minor
```

- Before: `1.2.3`
- After: `1.3.0`

#### Bump Patch (Bug Fixes)

```bash
python bykilt.py version bump --type patch
```

- Before: `1.2.3`
- After: `1.2.4`

### Create Git Tag

```bash
python bykilt.py version tag
```

Creates an annotated Git tag for the current version:

```text
v1.0.0
```

Tag is created with the format `v{version}` by default.

### List Version Tags

```bash
python bykilt.py version tags
```

Output:

```text
v0.0.1
v0.1.0
v1.0.0
```

Lists all version tags from the Git repository.

## Python API

### Import the Module

```python
from src.version.version_manager import VersionManager

# Initialize manager
manager = VersionManager()
```

### Get Current Version

```python
version = manager.get_version()
print(version)  # "1.0.0"
```

### Set Version

```python
manager.set_version("2.0.0")
```

### Bump Version

```python
# Bump major: 1.0.0 → 2.0.0
manager.bump_version("major")

# Bump minor: 1.0.0 → 1.1.0
manager.bump_version("minor")

# Bump patch: 1.0.0 → 1.0.1
manager.bump_version("patch")
```

### Parse Versions

```python
from src.version.parser import VersionParser

parser = VersionParser()

# Parse version string
v1 = parser.parse("1.0.0")
v2 = parser.parse("1.1.0")

# Compare versions
if v1 < v2:
    print("v1 is earlier than v2")

# Check constraints
if parser.matches("1.0.0", "^1.0.0"):
    print("Matches caret constraint")
```

## Prerelease Versions

Prerelease versions are used for alpha, beta, and release candidate versions:

### Naming Convention

```text
VERSION[-STAGE.NUMBER]
```

Common stages:

- `alpha` - Early testing phase
- `beta` - Feature complete, bug fixing
- `rc` (release candidate) - Final testing
- `dev` - Development version

### Examples

```bash
# Set prerelease version
python bykilt.py version set 1.0.0-alpha.1

# Set beta version
python bykilt.py version set 1.0.0-beta.1

# Set release candidate
python bykilt.py version set 1.0.0-rc.1
```

### Prerelease Comparison

Prerelease versions sort before release versions:

- `1.0.0-rc.1` < `1.0.0-beta.1` < `1.0.0-alpha.1`
- `1.0.0-rc.2` > `1.0.0-rc.1`

## Git Integration

### Automatic Tag Creation

```bash
# Create tag for current version
python bykilt.py version tag
```

Creates an annotated Git tag with the version as the message.

### Tag Configuration

Default tag prefix is `v` (e.g., `v1.0.0`). Tags are created with:

```bash
git tag -a v{version} -m "Version {version}"
```

### List Repository Tags

```bash
python bykilt.py version tags
```

Retrieves all tags from the current Git repository.

## Error Handling

### Invalid Version Format

```python
from src.version.parser import VersionParser, InvalidVersionError

parser = VersionParser()
try:
    v = parser.parse("not-a-version")
except InvalidVersionError as e:
    print(f"Error: {e}")
```

### File Not Found

If the VERSION file doesn't exist:

```python
from src.version.version_manager import VersionManager

manager = VersionManager()
# Automatically creates VERSION file if missing
version = manager.get_version()  # Creates VERSION if needed
```

### Git Not Available

If Git is not installed or not in PATH:

```python
from src.version.version_manager import VersionManager

manager = VersionManager()
try:
    manager.create_tag()
except RuntimeError as e:
    print(f"Git error: {e}")
```

## Testing

### Run All Version Tests

```bash
python -m pytest tests/version/ -v
```

### Run Specific Test File

```bash
python -m pytest tests/version/test_parser.py -v
```

### Run with Coverage

```bash
python -m pytest tests/version/ --cov=src.version --cov-report=term
```

### Test Markers

Tests are marked with `@pytest.mark.ci_safe` for CI environments:

```bash
python -m pytest -m ci_safe tests/version/ -v
```

## VERSION File

The project version is stored in a simple text file:

```text
PROJECT_ROOT/
└── VERSION              # Contains version string with newline
```

### File Format

```text
0.1.0
```

### File Location

The file is always in the project root directory.

### Automatic Handling

The VersionManager automatically:

1. Creates the file if missing
2. Reads the current version
3. Updates on version changes
4. Validates format

## Architecture Patterns

### Layered Design

1. **Parser Layer**: Parsing, validation, comparison logic
2. **Manager Layer**: Version operations and Git integration
3. **CLI Layer**: User interface and command routing

### Error Propagation

- Parser errors raise `InvalidVersionError`
- Manager errors raise `RuntimeError`
- CLI catches and formats errors for user display

### Subprocess Integration

Uses subprocess to interact with Git:

- `git tag` - Create annotated tags
- `git tag -l` - List tags
- Git must be installed and available in PATH

## Future Enhancements

- [ ] Automatic changelog generation from commits
- [ ] Version constraints validation (e.g., dependencies)
- [ ] Integration with CI/CD pipelines
- [ ] Version bump based on commit messages (conventional commits)
- [ ] Docker image tagging integration

## Troubleshooting

### Issue: "VERSION file not found"

**Solution**: The VersionManager creates it automatically on first use. If you need to manually create it:

```bash
echo "0.0.1" > VERSION
```

### Issue: Git tags not created

**Ensure**:

- Git is installed: `git --version`
- In a Git repository: `git status`
- Git has commit history (need at least one commit)

**Create repository if needed**:

```bash
git init
git config user.email "test@example.com"
git config user.name "Test User"
git add .
git commit -m "Initial commit"
```

### Issue: Version comparison not working as expected

**Check**:

- Version format is valid: `MAJOR.MINOR.PATCH`
- No extra whitespace: `parser.parse(version.strip())`
- For constraints, use correct operators: `^1.0.0` or `~1.0.0`

### Issue: Prerelease versions not sorting correctly

**Remember**:

- Prerelease versions sort BEFORE release versions
- `1.0.0-rc.1` < `1.0.0`
- Higher prerelease numbers are greater: `alpha.2` > `alpha.1`
