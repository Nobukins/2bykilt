# Contributing to 2bykilt

## Welcome Contributors! 🎉

Thank you for your interest in contributing to 2bykilt! This document provides guidelines and information for contributors.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [myscript Directory Policy](#myscript-directory-policy)
- [Development Workflow](#development-workflow)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Documentation](#documentation)

## 🤝 Code of Conduct

This project follows a code of conduct to ensure a welcoming environment for all contributors. Please be respectful and constructive in all interactions.

## 🚀 Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/your-username/2bykilt.git`
3. Create a feature branch: `git checkout -b feature/your-feature-name`
4. Set up the development environment (see below)

## 🛠️ Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- Playwright

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
playwright install

# Set up pre-commit hooks (recommended)
pip install pre-commit
pre-commit install
```

### Environment Variables

Set the following environment variables for development:

```bash
export RECORDING_PATH="./artifacts"
export BASE_DIR="$(pwd)"
```

## 🗂️ myscript Directory Policy

### Directory Structure

The `myscript/` directory follows a specific structure for organized script management:

```
myscript/
  bin/              # Executable scripts (entry points)
  templates/        # Script templates and samples
  helpers/          # Reusable helper modules
  README.md         # Usage guide and conventions
```

### Key Principles

1. **Separation of Concerns**: Keep execution scripts separate from generated artifacts
2. **Consistent Path Handling**: Use `RECORDING_PATH` for all output destinations
3. **Pathlib Usage**: Always use `pathlib.Path` instead of string concatenation
4. **Environment Validation**: Validate `RECORDING_PATH` exists before execution

### Output Conventions

All generated artifacts must follow these conventions:

- **Videos**: `artifacts/<task>/Tab-XX-<name>.webm` (XX is zero-padded)
- **Manifests**: `artifacts/<task>/tab_index_manifest.json`
- **Logs**: `artifacts/<task>/logs/` or `tmp/<task>/logs/`
- **Temporary Files**: `tmp/<task>/` (not in myscript/)

### RECORDING_PATH Usage

```python
import os
from pathlib import Path

# Always validate RECORDING_PATH
recording_path = os.environ.get("RECORDING_PATH")
if not recording_path:
    raise ValueError("RECORDING_PATH environment variable is required")

recording_dir = Path(recording_path)
recording_dir.mkdir(parents=True, exist_ok=True)

# Use pathlib for path operations
video_path = recording_dir / "Tab-01-recording.webm"
manifest_path = recording_dir / "tab_index_manifest.json"
```

### Script Development Guidelines

#### File Organization

- Place executable scripts in `myscript/bin/`
- Put reusable utilities in `myscript/helpers/`
- Store templates in `myscript/templates/`
- Keep the main `myscript/` directory clean of generated files

#### Naming Conventions

- Use descriptive names: `verb_target_format.py`
- Examples: `search_linkedin_profiles.py`, `extract_product_data.py`

#### Error Handling

```python
def ensure_recording_path():
    """Validate RECORDING_PATH environment variable"""
    recording_path = os.environ.get("RECORDING_PATH")
    if not recording_path:
        raise ValueError("RECORDING_PATH environment variable is required")
    return Path(recording_path)
```

#### Logging

```python
from datetime import datetime

def log_message(message):
    """Log messages with timestamps"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")
```

## 🔄 Development Workflow

### 1. Choose an Issue

- Check [Issues](../../issues) for tasks labeled `good first issue` or `help wanted`
- Comment on the issue to indicate you're working on it
- Wait for maintainer approval before starting work

### 2. Create a Feature Branch

```bash
git checkout -b feature/issue-number-description
# Example: git checkout -b feature/203-myscript-documentation
```

### 3. Make Changes

- Follow the myscript directory policy
- Write tests for new functionality
- Update documentation as needed
- Ensure all tests pass

### 4. Test Your Changes

```bash
# Run unit tests
pytest tests/

# Run integration tests
pytest tests/integration/

# Test myscript functionality
cd myscript
pytest --browser-type chrome
```

### 5. Commit Your Changes

```bash
git add .
git commit -m "feat: add myscript documentation and examples

- Add myscript directory policy to CONTRIBUTING.md
- Update README.md with myscript usage examples
- Add RECORDING_PATH validation examples

Closes #203"
```

## 🧪 Testing

### Running Tests

```bash
# All tests
pytest

# Specific test file
pytest tests/test_specific_feature.py

# With coverage
pytest --cov=src --cov-report=html
```

### Feature Flags Testing

#### Using Feature Flags Artifacts in Tests

For tests that need to ensure feature flags artifacts are created, use the provided fixtures and helpers:

```python
import pytest
from src.config.feature_flags import FeatureFlags
from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact

def test_with_flags_artifact(ensure_flags_artifact):
    """Test that automatically ensures flags artifact exists."""
    # ensure_flags_artifact fixture creates artifact if needed
    assert (ensure_flags_artifact / "feature_flags_resolved.json").exists()

    # Your test logic here
    flag_value = FeatureFlags.is_enabled("test.flag")
    assert isinstance(flag_value, bool)

def test_with_custom_overrides(tmp_path):
    """Test with custom flag overrides and artifact creation."""
    from tests.fixtures.feature_flags_fixtures import ensure_flags_artifact_with_overrides_helper

    overrides = {
        "test.enabled": True,
        "test.value": "custom_value",
        "test.number": 42
    }

    artifact_dir = ensure_flags_artifact_with_overrides_helper(overrides, tmp_path)
    assert (artifact_dir / "feature_flags_resolved.json").exists()

    # Verify overrides are applied
    assert FeatureFlags.is_enabled("test.enabled") is True
    assert FeatureFlags.get("test.value") == "custom_value"
    assert FeatureFlags.get("test.number") == 42
```

#### Controlling Lazy Artifact Creation

By default, accessing undefined feature flags will automatically create artifacts. You can control this behavior:

```python
# Disable lazy artifact creation
FeatureFlags.set_lazy_artifact_enabled(False)

# Check current setting
is_enabled = FeatureFlags.is_lazy_artifact_enabled()

# Re-enable (default behavior)
FeatureFlags.set_lazy_artifact_enabled(True)
```

#### Environment Variable Control

You can also control lazy artifact creation via environment variable:

```bash
# Disable lazy artifacts
export BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED=false

# Enable lazy artifacts (default)
export BYKILT_FLAGS_LAZY_ARTIFACT_ENABLED=true
```

#### Manual Artifact Creation

For tests that need explicit control over artifact creation:

```python
def test_manual_artifact_creation(tmp_path):
    """Test with manual artifact creation."""
    import os
    os.chdir(tmp_path)

    # Manually create artifact
    artifact_dir = FeatureFlags.dump_snapshot()
    assert (artifact_dir / "feature_flags_resolved.json").exists()

    # Your test logic here
    # ...
```

### Browser Testing

```bash
# Test with specific browser
pytest --browser-type chrome
pytest --browser-type firefox

# Test with profile
pytest --use-profile --browser-type chrome
```

### myscript Testing

```bash
cd myscript

# Test search functionality
pytest search_script.py --query "test query"

# Test with recording
export RECORDING_PATH="./artifacts/test"
pytest search_script.py --query "test"
```

## 📝 Submitting Changes

### Pull Request Process

1. **Update Documentation**: Ensure README.md and docs are updated
2. **Add Tests**: Include tests for new functionality
3. **Update CHANGELOG**: Add entry for user-facing changes
4. **Squash Commits**: Combine related commits into logical units

### PR Template

Please use the following template for pull requests:

```markdown
## Description
Brief description of the changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring
- [ ] Test addition

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed

## Screenshots (if applicable)
Add screenshots for UI changes

## Related Issues
Closes #123
```

### Code Review Process

- All PRs require review from at least one maintainer
- Address review comments promptly
- Keep PRs focused on a single feature or fix
- Rebase on main branch before merging

## 📚 Documentation

### Updating Documentation

- Keep README.md current with new features
- Update inline code comments
- Add examples for complex functionality
- Update CHANGELOG.md for releases

### Documentation Standards

- Use clear, concise language
- Include code examples where helpful
- Keep screenshots up to date
- Test all documentation examples

## 🎯 Areas for Contribution

### High Priority
- Bug fixes and performance improvements
- Documentation improvements
- Test coverage expansion

### Medium Priority
- New browser automation features
- UI/UX enhancements
- Integration with other tools

### Future Considerations
- Mobile browser support
- Cloud deployment options
- Advanced reporting features

## 📞 Getting Help

- **Issues**: Use GitHub issues for bugs and feature requests
- **Discussions**: Use GitHub discussions for questions and ideas
- **Discord**: Join our community Discord for real-time help

## 🙏 Recognition

Contributors are recognized in:
- CHANGELOG.md for releases
- GitHub contributors list
- Project documentation

Thank you for contributing to 2bykilt! 🚀