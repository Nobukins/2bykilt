# Git Script Path Resolution and Security

This document describes the git_script path resolution, normalization, and security validation system implemented for Issue #25.

## Overview

The git_script functionality allows users to specify Python scripts from git repositories that will be executed as part of automation workflows. To ensure security and proper operation, all script paths undergo rigorous validation and normalization.

## Feature Flag: GIT_SCRIPT_V2

The enhanced path validation is controlled by the `GIT_SCRIPT_V2` environment variable:

- `GIT_SCRIPT_V2=true`: Use enhanced path validation (recommended)
- `GIT_SCRIPT_V2=false` or unset: Use legacy path handling (for rollback)

```bash
# Enable enhanced validation
export GIT_SCRIPT_V2=true

# Disable enhanced validation (legacy mode)
export GIT_SCRIPT_V2=false
```

## Path Resolution Rules

### Basic Resolution Process

1. **Input Sanitization**: Remove leading/trailing whitespace
2. **Windows Security Check**: Reject Windows-specific dangerous patterns
3. **Home Directory Expansion**: Expand `~` only if result stays within repository
4. **Path Normalization**: Convert to canonical absolute path via `pathlib.Path.resolve()`
5. **Security Validation**: Ensure final path is within repository root
6. **Extension Validation**: Enforce allowed file extensions (default: `.py`)
7. **Existence Check**: Verify file exists and is readable

### Path Resolution Rules Table

| Input Path Type | Example | Behavior | Security Notes |
|-----------------|---------|----------|----------------|
| Simple relative | `script.py` | ✅ Resolved to `{repo_root}/script.py` | Safe |
| Nested relative | `dir/script.py` | ✅ Resolved to `{repo_root}/dir/script.py` | Safe |
| Current dir | `./script.py` | ✅ Resolved to `{repo_root}/script.py` | Safe |
| Parent traversal | `../script.py` | ❌ **DENIED** | Security risk |
| Deep traversal | `../../etc/passwd` | ❌ **DENIED** | Security risk |
| Home expansion (safe) | `~/repo_script.py` | ✅ If resolves within repo | Conditional |
| Home expansion (unsafe) | `~/outside.py` | ❌ **DENIED** | Security risk |
| Absolute within repo | `/tmp/repo/script.py` | ✅ If within repo root | Conditional |
| Absolute outside repo | `/etc/passwd` | ❌ **DENIED** | Security risk |
| Windows drive letter | `C:\script.py` | ❌ **DENIED** | Security risk |
| Windows UNC | `\\server\share\script.py` | ❌ **DENIED** | Security risk |
| Windows extended | `\\?\C:\script.py` | ❌ **DENIED** | Security risk |

## Security Policies

### Path Traversal Prevention

All attempts to escape the repository root directory are blocked:
- `..` path components are rejected
- Symbolic links that point outside the repository are rejected
- Absolute paths that resolve outside the repository are rejected

### Windows Path Security

To prevent host system access, all Windows-specific path patterns are denied:

- **Drive Letters**: `C:\`, `D:\`, etc.
- **UNC Paths**: `\\server\share\`, `//server/share/`
- **Extended Syntax**: `\\?\`, `\\.\`

**Rationale**: These paths could potentially access host system files outside the sandboxed repository environment.

### Home Directory Policy

Home directory expansion (`~`) is conditionally allowed:
- ✅ **Allowed**: If `~` expands to a path within the repository root
- ❌ **Denied**: If `~` would expand to any path outside the repository root

This prevents access to user home directories while allowing legitimate use cases.

### File Extension Enforcement

By default, only `.py` files are allowed. This can be customized via the `allowed_extensions` parameter.

- **Default**: `['.py']`
- **Security Note**: Restricting extensions prevents execution of unexpected file types

## Usage Examples

### Basic Usage

```python
from src.runner.git_script_path import validate_git_script_path

# Validate a script path
try:
    script_path, context = validate_git_script_path(
        repo_root="/tmp/my_repo",
        user_path="automation/script.py"
    )
    print(f"Validated path: {script_path}")
    print(f"Context: {context}")
except GitScriptPathError as e:
    print(f"Validation failed: {e} (code: {e.error_code})")
```

### With Custom Extensions

```python
from src.runner.git_script_path import GitScriptPathValidator

validator = GitScriptPathValidator(
    repo_root="/tmp/my_repo",
    allowed_extensions=['.py', '.sh']
)

script_path, context = validator.validate_and_normalize_path("scripts/setup.sh")
```

### Integration with git-script

```python
# In llms.txt or script configuration
{
    "type": "git-script",
    "git": "https://github.com/user/repo.git",
    "script_path": "automation/browser_script.py",  # ← This gets validated
    "version": "main"
}
```

## Error Handling

### Exception Types

- **`GitScriptPathNotFound`**: File doesn't exist at resolved path
  - Error code: `git_script.path_not_found`
- **`GitScriptPathDenied`**: Path rejected for security reasons
  - Error code: `git_script.path.denied`

### Error Patterns

```python
try:
    path, context = validate_git_script_path(repo_root, user_path)
except GitScriptPathNotFound as e:
    # Handle missing file
    logger.error(f"Script not found: {e}")
except GitScriptPathDenied as e:
    # Handle security violation
    logger.error(f"Path denied: {e}")
```

## Logging and Metrics

### Structured Logging

The system emits structured log events for monitoring and debugging:

#### git_script.resolved Event

```json
{
  "event": "git_script.resolved",
  "original": "automation/script.py",
  "normalized": "/tmp/repo/automation/script.py",
  "execution_root": "/tmp/repo",
  "validation_mode": "v2",
  "home_expanded": false,
  "made_absolute": true,
  "validation_success": true
}
```

#### git_script.execution.started Event

```json
{
  "event": "git_script.execution.started",
  "git_url": "https://github.com/user/repo.git",
  "script_path": "automation/script.py",
  "validation_mode": "v2"
}
```

#### git_script.execution.failed Event

```json
{
  "event": "git_script.execution.failed",
  "error_code": "git_script.path.denied",
  "error_message": "Path traversal patterns not allowed",
  "original_path": "../escape.py",
  "repo_root": "/tmp/repo"
}
```

### Metrics Counters

The system tracks execution metrics:
- `git_script.execution.started`: Count of git-script executions initiated
- `git_script.execution.failed`: Count of git-script executions that failed

## Troubleshooting

### Common Issues

1. **Path not found**: Verify the script exists in the repository
2. **Path denied**: Check for path traversal attempts or Windows-specific paths
3. **Extension denied**: Ensure the file has a `.py` extension (or customize allowed extensions)
4. **Home expansion failed**: Check if `~` expansion would escape the repository

### Debug Mode

Enable debug logging to see detailed path resolution:

```python
import logging
logging.getLogger('src.runner.git_script_path').setLevel(logging.DEBUG)
```

### Validation Context

The validation context provides detailed information about the resolution process:

```python
script_path, context = validate_git_script_path(repo_root, user_path)
print(f"Original: {context['original']}")
print(f"Normalized: {context['normalized']}")
print(f"Execution root: {context['execution_root']}")
print(f"Made absolute: {context['made_absolute']}")
print(f"Home expanded: {context['home_expanded']}")
```

## Migration from Legacy

### Backward Compatibility

Legacy behavior is preserved when `GIT_SCRIPT_V2=false`. The enhanced validation is opt-in.

### Recommended Migration

1. Test with `GIT_SCRIPT_V2=true` in development
2. Verify all legitimate scripts still work
3. Update any scripts using discouraged patterns
4. Deploy with `GIT_SCRIPT_V2=true` in production

### Breaking Changes

The enhanced validation may reject previously accepted paths:
- Path traversal attempts (`../`)
- Windows absolute paths (`C:\`)
- Files outside repository root
- Non-Python files (by default)

## Security Considerations

This implementation follows defense-in-depth principles:

1. **Input Validation**: All user input is validated
2. **Path Normalization**: Canonical paths prevent bypass attempts
3. **Boundary Enforcement**: Repository root serves as security boundary
4. **Principle of Least Privilege**: Only necessary file access is granted
5. **Fail-Safe Defaults**: Unknown patterns are rejected
6. **Comprehensive Logging**: All security events are logged

## Testing

Run the comprehensive test suite:

```bash
# Run all git_script path tests
python -m pytest tests/test_git_script_path.py -v

# Run specific regression tests
python -m pytest tests/test_git_script_path.py::TestGitScriptRegression -v
```

The test suite covers:
- ✅ Path normalization for all forms
- ✅ Windows path handling with deny policy
- ✅ Security validation edge cases
- ✅ Regression tests for Issue #25 requirements
- ✅ Error handling and exception codes