# Git Script Resolver Implementation

## Overview
This implementation addresses **Issue #44: git_script bug fix** by providing a comprehensive git-script resolution system for the 2bykilt project.

## Features Implemented

### 1. Git Script Resolution Logic
- **Resolution Order**: Absolute path → Relative path → llms.txt lookup
- **Automatic Detection**: Detects git-script candidates from various sources
- **GitHub Integration**: Fetches scripts from GitHub repositories with caching

### 2. Core Components

#### `GitScriptResolver` Class
- `resolve_git_script()`: Main resolution method following priority order
- `fetch_script_from_github()`: Downloads scripts from GitHub repositories
- `validate_script_info()`: Validates git-script configuration
- `get_script_candidates()`: Finds matching git-script actions

#### `GitScriptCandidate` Class
- Represents git-script metadata (name, git URL, script path, version)
- Provides string representation for debugging

### 3. Integration Points

#### Script Manager Integration
- Modified `script_manager.py` to use `GitScriptResolver` for git-script processing
- Automatic resolution when `git`/`script_path` fields are missing
- Validation of resolved script information

#### llms.txt Support
- Resolves git-scripts defined in `llms.txt` configuration
- Supports all git-script parameters (command, params, timeout, slowmo)

## Usage Examples

### Basic Resolution
```python
from src.script.git_script_resolver import get_git_script_resolver

resolver = get_git_script_resolver()
result = await resolver.resolve_git_script('site-defined-script')
```

### With Script Manager
```python
from src.script.script_manager import run_script

# Script info without git/script_path - will be resolved automatically
script_info = {
    'type': 'git-script',
    'name': 'site-defined-script'
}

result, script_path = await run_script(script_info, params={'query': 'test'})
```

## Resolution Priority

1. **Absolute Path**: If script name is a full path, resolve from filesystem
2. **Relative Path**: If script name contains path separators, search common directories
3. **llms.txt Lookup**: Search for matching git-script action in configuration

## Security Features

- GitHub URL validation (must be github.com)
- Script path security checks (no `..` or absolute paths)
- Safe subprocess execution with timeouts
- Repository caching to prevent repeated downloads

## Testing

### Unit Tests
- `tests/test_git_script_resolver.py`: Comprehensive unit tests for resolver functionality
- Tests resolution logic, validation, and error handling

### Integration Tests
- `tests/test_git_script_integration.py`: Tests integration with script_manager
- Verifies end-to-end git-script resolution and execution

## Files Modified/Created

### New Files
- `src/script/git_script_resolver.py`: Main resolver implementation
- `tests/test_git_script_resolver.py`: Unit tests
- `tests/test_git_script_integration.py`: Integration tests

### Modified Files
- `src/script/script_manager.py`: Integrated git_script_resolver

## Validation Results

✅ **Resolution Test Passed**: Successfully resolved `site-defined-script` from llms.txt
```
Type: git-script
Git: https://github.com/Nobukins/sample-tests.git
Script Path: search_script.py
Version: main
Resolved From: llms.txt
```

✅ **Unit Tests Passed**: All resolver functionality tests pass
✅ **Integration Tests Passed**: Script manager integration works correctly

## Benefits

1. **Robust Resolution**: Handles various script reference formats
2. **GitHub Integration**: Seamless fetching from remote repositories
3. **Security**: Validates URLs and paths to prevent malicious access
4. **Caching**: Efficient repository management with local caching
5. **Extensible**: Easy to add new resolution sources or validation rules

## Future Enhancements

- Support for private GitHub repositories (authentication)
- Additional resolution sources (database, API endpoints)
- Advanced caching strategies (LRU, size limits)
- Script dependency resolution and validation
