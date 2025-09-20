# Recording Functionality Test Matrix

This document provides a comprehensive test matrix for validating recording functionality across all script types in the 2bykilt automation framework.

## Test Execution Commands

### Quick Validation Suite

```bash
# Run all recording-related tests
pytest tests/test_*recording*.py -v

# Run specific script type tests
pytest tests/test_script_type_recording.py -v
pytest tests/test_browser_control_type_recording.py -v
pytest tests/test_git_script_type_recording.py -v
pytest tests/test_action_runner_template_type_recording.py -v

# Run integration tests
pytest tests/test_all_script_types_recording_integration.py -v
pytest tests/artifacts/test_recording_all_run_types.py -v
```

### Manual Validation Commands

```bash
# Test script type recording
python -c "
import asyncio
from src.script.script_manager import run_script

async def test_script():
    result = await run_script({
        'type': 'script',
        'script_path': 'myscript/search_script.py',
        'command': 'python -m pytest \${script_path}::test_nogtips_simple --no-cov'
    }, {}, headless=False, save_recording_path='./artifacts/runs/test-script/videos')
    print('Script result:', result)

asyncio.run(test_script())
"

# Test browser-control type recording
python -c "
import asyncio
from src.script.script_manager import run_script

async def test_browser():
    result = await run_script({
        'type': 'browser-control',
        'commands': [{'command': 'navigate', 'url': 'https://example.com'}]
    }, {}, headless=False, save_recording_path='./artifacts/runs/test-browser/videos')
    print('Browser result:', result)

asyncio.run(test_browser())
"

# Test git-script type recording
python -c "
import asyncio
from src.script.script_manager import run_script

async def test_git():
    result = await run_script({
        'type': 'git-script',
        'git': 'https://github.com/Nobukins/sample-tests.git',
        'script_path': 'search_script.py',
        'command': 'python -m pytest \${script_path}::test_text_search --no-cov'
    }, {}, headless=False, save_recording_path='./artifacts/runs/test-git/videos')
    print('Git result:', result)

asyncio.run(test_git())
"
```

## Test Validation Checklist

### Pre-Test Setup

- [ ] Virtual environment activated (`source venv/bin/activate`)
- [ ] All dependencies installed
- [ ] Clean artifacts directory
- [ ] Browser binaries available

### Post-Test Validation

#### File System Checks

```bash
# Check for recording files
find artifacts/runs -name "*.webm" -o -name "*.mp4"

# Verify directory structure
ls -la artifacts/runs/*/videos/

# Check file sizes (should be > 1KB)
find artifacts/runs -name "*.webm" -exec ls -lh {} \;
```

#### Expected Outcomes

| Test Type | Expected Files | Expected Location | File Size |
|-----------|----------------|-------------------|-----------|
| script | `*.webm` | `artifacts/runs/test-script/videos/` | > 1KB |
| browser-control | `*.webm` | `artifacts/runs/test-browser/videos/` | > 1KB |
| git-script | `*.webm` | `artifacts/runs/test-git/videos/` | > 1KB |

### Malfunction Detection

#### Critical Indicators

1. **No recording files**: Empty videos directory
2. **Zero-byte files**: Recording started but failed
3. **Wrong location**: Files in `/tmp` instead of `artifacts/runs`
4. **Permission errors**: Files exist but not accessible

#### Debug Commands

```bash
# Check environment variables during test
env | grep RECORDING

# Check directory permissions
ls -la artifacts/runs/

# Check for temporary files
find /tmp -name "*bykilt*" -type d

# Monitor file system during test
inotifywait -m -r artifacts/runs/
```

## Regression Testing Scenarios

### Scenario 1: Clean System Test

```bash
# Fresh environment test
rm -rf artifacts/runs/*
pytest tests/test_all_script_types_recording_integration.py::TestAllScriptTypesRecordingIntegration::test_all_script_types_recording_integration -v
```

### Scenario 2: Environment Variable Precedence

```bash
# Test with custom RECORDING_PATH
RECORDING_PATH=/tmp/custom-recording pytest tests/test_recording_path_env_precedence.py -v
```

### Scenario 3: Permission Boundaries

```bash
# Test with restricted permissions
chmod 555 artifacts/runs
pytest tests/test_script_type_recording.py::TestScriptTypeRecording::test_script_type_recording_path -v
chmod 755 artifacts/runs  # restore
```

### Scenario 4: Concurrent Execution

```bash
# Test multiple script types simultaneously
python -c "
import asyncio
from src.script.script_manager import run_script

async def concurrent_test():
    tasks = [
        run_script({'type': 'script', 'script_path': 'myscript/search_script.py', 'command': 'python -m pytest search_script.py::test_nogtips_simple --no-cov'}, {}, headless=True, save_recording_path='./artifacts/runs/concurrent-script/videos'),
        run_script({'type': 'browser-control', 'commands': [{'command': 'navigate', 'url': 'https://example.com'}]}, {}, headless=True, save_recording_path='./artifacts/runs/concurrent-browser/videos')
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    print('Concurrent results:', results)

asyncio.run(concurrent_test())
"
```

## Performance Benchmarks

### Recording Performance Metrics

| Metric | Expected Range | Measurement Method |
|--------|----------------|-------------------|
| File Creation Time | < 5 seconds | `time` command |
| File Size | 100KB - 10MB | `ls -lh` |
| Directory Creation | < 1 second | `time mkdir` |
| Path Resolution | < 100ms | Python timing |

### Benchmark Commands

```bash
# Measure recording initialization time
time python -c "from src.utils.recording_dir_resolver import create_or_get_recording_dir; create_or_get_recording_dir('./artifacts/runs/benchmark/videos')"

# Measure script execution with recording
time python -c "
import asyncio
from src.script.script_manager import run_script

async def benchmark():
    await run_script({
        'type': 'script',
        'script_path': 'myscript/search_script.py',
        'command': 'python -m pytest search_script.py::test_nogtips_simple --no-cov'
    }, {}, headless=True, save_recording_path='./artifacts/runs/benchmark-script/videos')

asyncio.run(benchmark())
"
```

## Failure Analysis Guide

### Common Failure Patterns

#### Pattern 1: Import Errors

```
ModuleNotFoundError: No module named 'playwright'
```

**Solution**: Activate virtual environment and install dependencies

```bash
source venv/bin/activate
pip install -r requirements.txt
```

#### Pattern 2: Path Resolution Failures

```
FileNotFoundError: [Errno 2] No such file or directory: 'artifacts/runs'
```

**Solution**: Check directory permissions and creation logic

```bash
mkdir -p artifacts/runs
chmod 755 artifacts/runs
```

#### Pattern 3: Recording Not Generated

```
Recording path set but no files created
```

**Solution**: Check browser automation and playwright configuration

```bash
playwright install chromium
```

#### Pattern 4: Git-Script File Copying Issues

```
Files generated in /tmp but not copied to artifacts
```

**Solution**: Check NEW METHOD configuration and file permissions

```bash
export BYKILT_USE_NEW_METHOD=true
```

### Diagnostic Commands

```bash
# Full system diagnostic
echo "=== Environment Check ==="
python --version
which python
env | grep -E "(PATH|RECORDING|BYKILT)"

echo "=== Playwright Check ==="
playwright --version
playwright install --dry-run

echo "=== Directory Check ==="
ls -la artifacts/
find artifacts -type d -ls

echo "=== Recent Recording Files ==="
find artifacts/runs -name "*.webm" -o -name "*.mp4" -exec ls -lht {} \; | head -10
```

## Continuous Integration Integration

### CI Test Commands

```yaml
# Example GitHub Actions workflow snippet
- name: Test Recording Functionality
  run: |
    source venv/bin/activate
    pytest tests/test_*recording*.py --tb=short
    find artifacts/runs -name "*.webm" | wc -l
    
- name: Validate Recording Files
  run: |
    if [ $(find artifacts/runs -name "*.webm" | wc -l) -eq 0 ]; then
      echo "ERROR: No recording files generated"
      exit 1
    fi
```

### CI Validation Script

```bash
#!/bin/bash
# ci-recording-validation.sh

set -e

echo "Starting recording functionality validation..."

# Run core tests
pytest tests/test_script_type_recording.py -v
pytest tests/test_browser_control_type_recording.py -v
pytest tests/test_git_script_type_recording.py -v

# Run integration tests
pytest tests/test_all_script_types_recording_integration.py -v

# Validate file generation
RECORDING_COUNT=$(find artifacts/runs -name "*.webm" | wc -l)
if [ "$RECORDING_COUNT" -eq 0 ]; then
    echo "ERROR: No recording files generated during tests"
    exit 1
fi

echo "SUCCESS: $RECORDING_COUNT recording files generated"

# Clean up
rm -rf artifacts/runs/test-*

echo "Recording functionality validation completed successfully"
```