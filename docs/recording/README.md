# Recording Functionality Documentation

## Overview

This documentation provides comprehensive information about the recording functionality in the 2bykilt automation framework. The recording system captures browser interactions as video files (`.webm` and `.mp4`) across all script types, providing visual evidence of automation execution for debugging, verification, and compliance purposes.

## Recording Architecture

### Unified Recording Path System

All script types now use a unified recording path resolution system through `recording_dir_resolver` and `recording_factory` utilities:

- **Centralized Path Resolution**: `src/utils/recording_dir_resolver.py`
- **Recording Initialization**: `src/utils/recording_factory.py`
- **Path Utilities**: `src/utils/recording_path_utils.py`

### Supported Script Types

| Script Type | Status | Recording Location | Implementation |
|-------------|--------|--------------------|----------------|
| `script` | ✅ Working | `artifacts/runs/{run-id}/videos/` | Direct path setup with RECORDING_PATH env |
| `browser-control` | ✅ Working | `artifacts/runs/{run-id}/videos/` | Native recording integration |
| `git-script` | ✅ Working | `artifacts/runs/{run-id}/videos/` | Post-execution file copying from temp dirs |
| `action_runner_template` | ✅ Working | `artifacts/runs/{run-id}/videos/` | Template-based recording setup |

## Test Documentation

### Test File Overview

| Test File | Purpose | Coverage |
|-----------|---------|----------|
| `test_script_type_recording.py` | Script type recording validation | Path resolution, environment setup |
| `test_browser_control_type_recording.py` | Browser-control recording validation | Native recording, custom paths |
| `test_git_script_type_recording.py` | Git-script recording validation | Temp directory handling, file copying |
| `test_action_runner_template_type_recording.py` | Action runner recording validation | Template recording integration |
| `test_all_script_types_recording_integration.py` | Cross-type integration tests | Unified behavior validation |
| `test_recording_dir_resolver.py` | Recording directory resolver tests | Path resolution logic |
| `test_recording_path_env_precedence.py` | Environment variable precedence | Configuration priority |
| `test_unified_recording_path_rollout.py` | Unified path system tests | Migration and compatibility |
| `tests/artifacts/test_recording_all_run_types.py` | All run types recording tests | End-to-end recording validation |

### Test Categories

#### 1. Unit Tests (Individual Script Types)

##### test_script_type_recording.py

- **Purpose**: Validates that `type:script` generates recordings correctly
- **Key Test Cases**:
  - `test_script_type_recording_path`: Verifies correct RECORDING_PATH environment variable setup
  - `test_recording_dir_resolver_integration`: Tests path resolution logic
- **Expected Response**: RECORDING_PATH env variable set to `artifacts/runs/{run-id}/videos/`
- **Malfunction Indicators**: Missing RECORDING_PATH env, incorrect path format, non-existent directories

**test_browser_control_type_recording.py**
- **Purpose**: Validates that `type:browser-control` maintains native recording functionality
- **Key Test Cases**:
  - `test_browser_control_type_recording_path`: Tests recording path setup
  - `test_browser_control_with_custom_recording_path`: Validates custom path handling
  - `test_recording_path_unified_behavior`: Ensures unified behavior
- **Expected Response**: Recording files generated in specified `artifacts/runs/{run-id}/videos/`
- **Malfunction Indicators**: Missing recording files, incorrect file location, broken custom path handling

**test_git_script_type_recording.py**
- **Purpose**: Validates that `type:git-script` copies recordings from temp directories
- **Key Test Cases**:
  - `test_git_script_type_recording_path`: Tests NEW METHOD recording setup
  - `test_git_script_with_custom_recording_path`: Validates custom path copying
  - `test_git_script_recording_path_resolution`: Tests path resolution
- **Expected Response**: Files copied from `/tmp/bykilt_gitscripts/.../tmp/record_videos/` to `artifacts/runs/{run-id}/videos/`
- **Malfunction Indicators**: Missing copied files, failed file operations, temp directory access issues

**test_action_runner_template_type_recording.py**
- **Purpose**: Validates recording functionality for action runner templates
- **Key Test Cases**:
  - `test_action_runner_template_type_recording_path`: Tests recording path setup
  - `test_action_runner_template_with_custom_recording_path`: Custom path validation
  - `test_recording_path_unified_behavior_action_runner`: Unified behavior testing
- **Expected Response**: Template-based recording with proper path resolution
- **Malfunction Indicators**: Template generation failures, incorrect path resolution

#### 2. Integration Tests

**test_all_script_types_recording_integration.py**
- **Purpose**: Ensures consistent recording behavior across all script types
- **Key Test Cases**:
  - `test_all_script_types_recording_integration`: Cross-type consistency validation
  - `test_recording_path_unification_across_types`: Unified path behavior
  - `test_recording_path_consistency_across_types`: Path consistency validation
  - `test_recording_path_with_environment_variable`: Environment precedence
- **Expected Response**: All script types use identical path resolution and generate recordings in correct locations
- **Malfunction Indicators**: Inconsistent behavior between types, path resolution differences

#### 3. System Tests

**tests/artifacts/test_recording_all_run_types.py**
- **Purpose**: End-to-end validation of recording functionality across all run types
- **Key Test Cases**:
  - Recording generation for all supported types
  - Artifact management integration
  - Video retention and cleanup
- **Expected Response**: Complete recording lifecycle management
- **Malfunction Indicators**: Failed artifact registration, missing retention policies

#### 4. Utility Tests

**test_recording_dir_resolver.py**
- **Purpose**: Tests the core recording directory resolution logic
- **Key Test Cases**:
  - Path creation and validation
  - Default path handling
  - Custom path resolution
- **Expected Response**: Correct directory creation and path resolution
- **Malfunction Indicators**: Directory creation failures, incorrect path resolution

**test_recording_path_env_precedence.py**
- **Purpose**: Tests environment variable precedence and configuration
- **Key Test Cases**:
  - Environment variable override behavior
  - Configuration priority handling
- **Expected Response**: Correct precedence order for recording path configuration
- **Malfunction Indicators**: Incorrect precedence, configuration override failures

**test_unified_recording_path_rollout.py**
- **Purpose**: Tests the unified recording path system migration
- **Key Test Cases**:
  - Migration from legacy to unified system
  - Compatibility with existing configurations
- **Expected Response**: Seamless migration without breaking existing functionality
- **Malfunction Indicators**: Migration failures, compatibility issues

## Malfunction Detection Matrix

### Quick Validation Commands

```bash
# Test all recording types
python -c "
import asyncio
from src.script.script_manager import run_script

async def test_all_types():
    # Test type:script
    script_result = await run_script({
        'type': 'script',
        'script_path': 'myscript/search_script.py',
        'command': 'python -m pytest \${script_path}::test_nogtips_simple --no-cov'
    }, {}, headless=False, save_recording_path='./artifacts/runs/validation-script/videos')
    
    # Test type:browser-control
    browser_result = await run_script({
        'type': 'browser-control',
        'commands': [{'command': 'navigate', 'url': 'https://example.com'}]
    }, {}, headless=False, save_recording_path='./artifacts/runs/validation-browser/videos')
    
    # Test type:git-script
    git_result = await run_script({
        'type': 'git-script',
        'git': 'https://github.com/Nobukins/sample-tests.git',
        'script_path': 'search_script.py',
        'command': 'python -m pytest \${script_path}::test_text_search --no-cov'
    }, {}, headless=False, save_recording_path='./artifacts/runs/validation-git/videos')
    
    return script_result, browser_result, git_result

asyncio.run(test_all_types())
"
```

### Expected File Structure After Tests

```
artifacts/
└── runs/
    ├── validation-script/
    │   └── videos/
    │       └── *.webm
    ├── validation-browser/
    │   └── videos/
    │       └── *.webm
    └── validation-git/
        └── videos/
            └── *.webm
```

### Common Malfunction Patterns

#### 1. Missing Recording Files
- **Symptoms**: No `.webm` or `.mp4` files in expected directories
- **Investigation**: Check RECORDING_PATH environment variable, directory permissions
- **Tests to Run**: `test_script_type_recording_path`, `test_browser_control_type_recording_path`

#### 2. Incorrect Recording Locations
- **Symptoms**: Files generated in unexpected directories (e.g., `/tmp` instead of `artifacts/runs`)
- **Investigation**: Check recording path resolution logic, environment variable precedence
- **Tests to Run**: `test_recording_dir_resolver_integration`, `test_recording_path_env_precedence`

#### 3. Git-Script Specific Issues
- **Symptoms**: Recording files remain in temporary directories, not copied to accessible locations
- **Investigation**: Check file copying logic in `script_manager.py`, temp directory cleanup
- **Tests to Run**: `test_git_script_type_recording_path`, `test_git_script_with_custom_recording_path`

#### 4. Cross-Type Inconsistencies
- **Symptoms**: Different behavior between script types for similar operations
- **Investigation**: Check unified recording system implementation
- **Tests to Run**: `test_all_script_types_recording_integration`, `test_recording_path_consistency_across_types`

### Performance and Reliability Indicators

#### Recording File Validation
- **File Existence**: Verify `.webm`/`.mp4` files are created
- **File Size**: Ensure files are not empty (>1KB typically indicates successful recording)
- **File Accessibility**: Check read permissions and path accessibility
- **Timestamp Validation**: Ensure files are created during test execution timeframe

#### Path Resolution Validation
- **Directory Creation**: Verify directories are created with correct permissions
- **Path Consistency**: Ensure all script types use identical path patterns
- **Environment Variable Handling**: Validate RECORDING_PATH is set correctly

## Recent Fixes (Issue #237)

### Problem Identification
- `type:script` was not generating recording files
- `type:git-script` was generating recordings in inaccessible temporary directories
- Inconsistent recording behavior across script types

### Solution Implementation
1. **Script Type Fix**: Added recording directory setup and RECORDING_PATH environment variable in `search_script.py`
2. **Git-Script Type Fix**: Implemented post-execution file copying in `script_manager.py` to move recordings from temp directories to accessible `artifacts/runs` locations
3. **Unified System**: Ensured all script types use the same recording path resolution system

### Validation Results
- ✅ `type:script`: Recordings now generated in `artifacts/runs/{run-id}/videos/`
- ✅ `type:browser-control`: Maintained existing functionality
- ✅ `type:git-script`: Recordings now copied to accessible locations

## Configuration

### Environment Variables
- `RECORDING_PATH`: Override default recording directory
- `BYKILT_USE_NEW_METHOD`: Control git-script execution method (NEW METHOD enables file copying)

### Feature Flags
- `artifacts.unified_recording_path`: Enable unified recording path system
- `artifacts.video_retention_days`: Control video file retention period

## Troubleshooting

### Common Issues and Solutions

1. **No recording files generated**
   - Check RECORDING_PATH environment variable
   - Verify browser automation is enabled
   - Run relevant unit tests to isolate the issue

2. **Recording files in wrong location**
   - Verify unified recording system is enabled
   - Check custom path resolution logic
   - Run integration tests

3. **Git-script recordings missing**
   - Ensure NEW METHOD is enabled (`BYKILT_USE_NEW_METHOD=true`)
   - Check file copying logic and permissions
   - Verify temporary directory access

For detailed troubleshooting, refer to the test files in `/tests/` directory and run specific test cases to isolate issues.