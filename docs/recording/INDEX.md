# Recording Functionality Index

This directory contains comprehensive documentation for the recording functionality in the 2bykilt automation framework.

## Documents Overview

### 📖 Core Documentation

- **[README.md](README.md)** - Main recording functionality documentation
  - Architecture overview
  - Supported script types and their status
  - Test file descriptions and purposes
  - Configuration and troubleshooting

### 🧪 Testing & Validation

- **[TEST_MATRIX.md](TEST_MATRIX.md)** - Comprehensive test execution guide
  - Test commands for all script types
  - Manual validation procedures
  - Performance benchmarks
  - CI/CD integration examples

- **[validate_recording.py](validate_recording.py)** - Automated validation script
  - Comprehensive recording functionality validator
  - Quick and full validation modes
  - Integration scenario testing
  - Automated malfunction detection

### 🚨 Malfunction Detection

- **[MALFUNCTION_DETECTION.md](MALFUNCTION_DETECTION.md)** - Malfunction detection and recovery
  - Quick health checks
  - Common failure patterns and solutions
  - Automated monitoring scripts
  - Recovery procedures

## Quick Start

### 1-Minute Health Check

```bash
cd /path/to/2bykilt
python docs/recording/validate_recording.py --quick
```

### Full Validation

```bash
cd /path/to/2bykilt
python docs/recording/validate_recording.py
```

### Run Specific Tests

```bash
# Test all recording functionality
pytest tests/test_*recording*.py -v

# Test specific script type
pytest tests/test_script_type_recording.py -v
pytest tests/test_git_script_type_recording.py -v
pytest tests/test_browser_control_type_recording.py -v
```

## Current Status (Issue #237 Resolution)

### ✅ Fixed Issues

1. **Script Type Recording** - Now generates recordings in `artifacts/runs/{run-id}/videos/`
2. **Git-Script Recording Location** - Files now copied from temp directories to accessible locations
3. **Unified Recording System** - All script types use consistent path resolution
4. **Browser-Control Headless Mode** - Fixed headless mode control via environment variables
5. **PYTEST_HEADLESS Environment Variable** - Implemented proper headless control for pytest-playwright

### 🎯 Validation Results

| Script Type | Status | Recording Location | File Copying | Headless Control |
|-------------|--------|--------------------|--------------|------------------|
| `script` | ✅ Working | `artifacts/runs/` | Direct | Environment-based |
| `browser-control` | ✅ Working | `artifacts/runs/` | Direct | PYTEST_HEADLESS env |
| `git-script` | ✅ Working | `artifacts/runs/` | Post-execution copy | Command-line args |
| `action_runner_template` | ✅ Working | `artifacts/runs/` | Direct | Environment-based |

### 🔧 Recent Changes (2025-09-20)

#### Browser-Control Type Improvements

- **Environment Variable Control**: Implemented `PYTEST_HEADLESS` environment variable for headless mode
- **Fixture-Based Configuration**: Updated `browser_type_launch_args` fixture to read headless setting from environment
- **Command Line Cleanup**: Removed duplicate `--headless` arguments to prevent pytest errors

#### Script Manager Enhancements

- **Unified Headless Control**: Standardized headless mode handling across all script types
- **Environment Variable Priority**: Environment variables now take precedence over command-line arguments
- **Error Prevention**: Added logic to prevent conflicting headless/headful arguments

#### Documentation Updates

- **Test Matrix**: Added comprehensive test execution commands and validation procedures
- **Malfunction Detection**: Enhanced troubleshooting guides with specific error patterns
- **Configuration Guide**: Added recording path configuration documentation

## Architecture Summary

### Recording Path Flow

```mermaid
User Request
    ↓
Script Manager
    ↓
Recording Directory Resolver
    ↓
artifacts/runs/{run-id}/videos/
    ↓
Generated Recording Files
```

### Key Components

- **recording_dir_resolver.py** - Unified path resolution
- **recording_factory.py** - Recording initialization
- **recording_path_utils.py** - Path utilities
- **script_manager.py** - Execution orchestration

## Troubleshooting Quick Reference

### Common Issues

1. **No recording files generated**

   ```bash
   # Check playwright installation
   playwright --version
   playwright install chromium
   ```

2. **Files in wrong location**

   ```bash
   # Check environment variables
   env | grep RECORDING
   
   # Run validation
   python docs/recording/validate_recording.py --quick
   ```

3. **Git-script specific issues**

   ```bash
   # Enable NEW METHOD
   export BYKILT_USE_NEW_METHOD=true
   
   # Test git-script
   python -c "
   import asyncio
   from src.script.script_manager import run_script
   
   async def test():
       result = await run_script({
           'type': 'git-script',
           'git': 'https://github.com/Nobukins/sample-tests.git',
           'script_path': 'search_script.py',
           'command': 'python -m pytest search_script.py::test_text_search --no-cov'
       }, {}, headless=True, save_recording_path='./artifacts/runs/test-git/videos')
       print('Result:', result)
   
   asyncio.run(test())
   "
   ```

## Maintenance

### Regular Validation

```bash
# Weekly full validation
python docs/recording/validate_recording.py

# Daily quick check
python docs/recording/validate_recording.py --quick

# After code changes
pytest tests/test_all_script_types_recording_integration.py -v
```

### Performance Monitoring

```bash
# Check recording file sizes
find artifacts/runs -name "*.webm" -exec ls -lh {} \;

# Monitor disk usage
du -sh artifacts/runs/

# Benchmark recording creation
time python docs/recording/validate_recording.py --quick
```

## Contributing

When modifying recording functionality:

1. Run full validation suite before and after changes
2. Update test cases if behavior changes
3. Update documentation for new features
4. Verify all script types maintain consistent behavior

### Adding New Tests

1. Create test file in `tests/` directory
2. Follow naming convention: `test_*_recording.py`
3. Include in integration test suite
4. Document test purpose and expected responses
5. Add to validation script if needed

## Support

For recording functionality issues:

1. **Check documentation** - Start with this index and README.md
2. **Run validation** - Use `validate_recording.py` for diagnosis
3. **Review tests** - Check relevant test files for expected behavior
4. **Check logs** - Review execution logs for error patterns
5. **Escalate** - Contact development team with validation results

---

**Last Updated**: 2025-09-20  
**Issue Reference**: #237 - Recording file generation bug  
**Status**: ✅ Resolved and documented
