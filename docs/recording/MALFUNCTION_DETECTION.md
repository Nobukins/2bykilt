# Recording Malfunction Detection Guide

This document provides specific guidance for detecting and diagnosing recording functionality malfunctions in the 2bykilt automation framework.

## Quick Malfunction Detection

### 1-Minute Health Check

```bash
#!/bin/bash
# Quick recording health check
echo "=== Recording Health Check ==="

# Check if recordings directory exists
if [ ! -d "artifacts/runs" ]; then
    echo "❌ FAIL: artifacts/runs directory not found"
    exit 1
fi

# Run minimal test
python -c "
import asyncio
from src.script.script_manager import run_script

async def health_check():
    try:
        result = await run_script({
            'type': 'browser-control',
            'commands': [{'command': 'navigate', 'url': 'https://example.com'}]
        }, {}, headless=True, save_recording_path='./artifacts/runs/health-check/videos')
        return 'PASS' if result else 'FAIL'
    except Exception as e:
        return f'ERROR: {e}'

result = asyncio.run(health_check())
print(f'Recording test: {result}')
"

# Check for generated files
RECORDING_COUNT=$(find artifacts/runs/health-check -name "*.webm" 2>/dev/null | wc -l)
if [ "$RECORDING_COUNT" -gt 0 ]; then
    echo "✅ PASS: Recording files generated ($RECORDING_COUNT files)"
else
    echo "❌ FAIL: No recording files generated"
fi
```

## Malfunction Categories

### Category A: Critical Failures (System Broken)

#### A1: No Recording Files Generated

**Symptoms:**
- Empty `artifacts/runs` directory after test execution
- No `.webm` or `.mp4` files found
- Tests pass but no visual output

**Diagnostic Commands:**

```bash
# Check recording initialization
python -c "
from src.utils.recording_dir_resolver import create_or_get_recording_dir
path = create_or_get_recording_dir('./artifacts/runs/diagnostic/videos')
print(f'Recording path: {path}')
print(f'Path exists: {path.exists()}')
"

# Check environment variables
env | grep -E "(RECORDING|PLAYWRIGHT)"

# Test minimal recording
playwright codegen --target python-async --output test_minimal.py https://example.com
```

**Root Causes:**
1. Playwright not installed or configured
2. Recording environment variables not set
3. Browser automation disabled
4. Permission issues

**Quick Fix:**

```bash
# Install/reinstall playwright
pip install playwright
playwright install chromium

# Verify installation
playwright --version
```

#### A2: Script Execution Failures

**Symptoms:**
- Tests fail with import errors
- `ModuleNotFoundError` exceptions
- Script manager errors

**Diagnostic Commands:**

```bash
# Check Python environment
python --version
which python
pip list | grep -E "(playwright|pytest)"

# Test imports
python -c "
try:
    from src.script.script_manager import run_script
    print('✅ Script manager import OK')
except ImportError as e:
    print(f'❌ Import error: {e}')
"
```

**Quick Fix:**

```bash
# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Category B: Partial Failures (Inconsistent Behavior)

#### B1: Git-Script Recording Location Issues

**Symptoms:**
- Files generated in `/tmp` directories
- Recordings not accessible after test completion
- Temporary directory cleanup removes files

**Diagnostic Commands:**

```bash
# Check NEW METHOD configuration
echo "BYKILT_USE_NEW_METHOD: ${BYKILT_USE_NEW_METHOD:-not set}"

# Monitor file operations during git-script execution
inotifywait -m -r /tmp --include ".*\.webm" &
MONITOR_PID=$!

# Run git-script test
python -c "
import asyncio
from src.script.script_manager import run_script

async def test_git_script():
    result = await run_script({
        'type': 'git-script',
        'git': 'https://github.com/Nobukins/sample-tests.git',
        'script_path': 'search_script.py',
        'command': 'python -m pytest search_script.py::test_text_search --no-cov'
    }, {}, headless=True, save_recording_path='./artifacts/runs/git-diagnostic/videos')
    print('Git-script result:', result)

asyncio.run(test_git_script())
"

# Stop monitoring
kill $MONITOR_PID

# Check results
find artifacts/runs/git-diagnostic -name "*.webm"
find /tmp -name "*bykilt*" -type d 2>/dev/null
```

**Quick Fix:**

```bash
# Enable NEW METHOD
export BYKILT_USE_NEW_METHOD=true

# Re-run test
```

#### B2: Path Resolution Inconsistencies

**Symptoms:**
- Different recording paths for different script types
- Inconsistent directory structure
- Path resolution errors

**Diagnostic Commands:**

```bash
# Test path resolution for all types
python -c "
from src.utils.recording_dir_resolver import create_or_get_recording_dir

test_paths = [
    './artifacts/runs/script-test/videos',
    './artifacts/runs/browser-test/videos',
    './artifacts/runs/git-test/videos'
]

for path in test_paths:
    resolved = create_or_get_recording_dir(path)
    print(f'{path} -> {resolved}')
"
```

**Quick Fix:**

```bash
# Clean and recreate directory structure
rm -rf artifacts/runs/*
mkdir -p artifacts/runs
```

### Category C: Performance Issues

#### C1: Slow Recording Initialization

**Symptoms:**
- Long delays before test execution
- Timeout errors during recording setup
- Slow directory creation

**Diagnostic Commands:**

```bash
# Benchmark directory creation
time python -c "
from src.utils.recording_dir_resolver import create_or_get_recording_dir
create_or_get_recording_dir('./artifacts/runs/benchmark/videos')
"

# Check disk space
df -h artifacts/

# Check I/O performance
dd if=/dev/zero of=artifacts/test_io bs=1M count=10
rm artifacts/test_io
```

#### C2: Large Recording Files

**Symptoms:**
- Extremely large `.webm` files (>100MB)
- Disk space issues
- Slow file operations

**Diagnostic Commands:**

```bash
# Check file sizes
find artifacts/runs -name "*.webm" -exec ls -lh {} \;

# Check total recording size
du -sh artifacts/runs/

# Monitor disk usage during test
df -h . && \
python -c "
import asyncio
from src.script.script_manager import run_script

async def size_test():
    await run_script({
        'type': 'browser-control',
        'commands': [{'command': 'navigate', 'url': 'https://example.com'}]
    }, {}, headless=True, save_recording_path='./artifacts/runs/size-test/videos')

asyncio.run(size_test())
" && \
df -h .
```

## Automated Malfunction Detection

### Monitoring Script

```python
#!/usr/bin/env python3
"""
Recording malfunction monitoring script
"""
import os
import time
import subprocess
from pathlib import Path

def check_recording_health():
    """Comprehensive recording health check"""
    issues = []
    
    # Check 1: Directory structure
    artifacts_dir = Path("artifacts/runs")
    if not artifacts_dir.exists():
        issues.append("CRITICAL: artifacts/runs directory missing")
    
    # Check 2: Recent recording activity
    recent_files = list(artifacts_dir.glob("**/*.webm"))
    if not recent_files:
        issues.append("WARNING: No recent recording files found")
    
    # Check 3: File sizes
    for file_path in recent_files:
        if file_path.stat().st_size == 0:
            issues.append(f"ERROR: Zero-byte recording file {file_path}")
        elif file_path.stat().st_size > 100 * 1024 * 1024:  # 100MB
            issues.append(f"WARNING: Large recording file {file_path} ({file_path.stat().st_size} bytes)")
    
    # Check 4: Environment
    required_env = ["RECORDING_PATH", "PLAYWRIGHT_BROWSERS_PATH"]
    for env_var in required_env:
        if env_var not in os.environ:
            issues.append(f"INFO: {env_var} not set")
    
    # Check 5: Dependencies
    try:
        import playwright
        issues.append("OK: Playwright available")
    except ImportError:
        issues.append("CRITICAL: Playwright not available")
    
    return issues

if __name__ == "__main__":
    issues = check_recording_health()
    for issue in issues:
        print(issue)
    
    # Return exit code based on severity
    critical_issues = [i for i in issues if "CRITICAL" in i]
    exit(1 if critical_issues else 0)
```

### Continuous Monitoring

```bash
#!/bin/bash
# Continuous recording monitoring

MONITOR_INTERVAL=300  # 5 minutes
LOG_FILE="recording_health.log"

while true; do
    echo "$(date): Starting recording health check" >> $LOG_FILE
    
    # Run health check
    python monitor_recording.py >> $LOG_FILE 2>&1
    EXIT_CODE=$?
    
    if [ $EXIT_CODE -ne 0 ]; then
        echo "$(date): CRITICAL ISSUES DETECTED" >> $LOG_FILE
        # Send alert (email, slack, etc.)
        echo "Recording malfunction detected" | mail -s "2bykilt Recording Alert" admin@example.com
    fi
    
    sleep $MONITOR_INTERVAL
done
```

## Recovery Procedures

### Full System Recovery

```bash
#!/bin/bash
# Full recording system recovery

echo "=== Starting Full Recording System Recovery ==="

# Step 1: Clean environment
echo "Cleaning environment..."
rm -rf artifacts/runs/*
unset RECORDING_PATH
unset PLAYWRIGHT_BROWSERS_PATH

# Step 2: Reinstall dependencies
echo "Reinstalling dependencies..."
source venv/bin/activate
pip uninstall -y playwright
pip install playwright
playwright install chromium

# Step 3: Reset configuration
echo "Resetting configuration..."
export BYKILT_USE_NEW_METHOD=true

# Step 4: Test basic functionality
echo "Testing basic functionality..."
python -c "
import asyncio
from src.script.script_manager import run_script

async def recovery_test():
    try:
        result = await run_script({
            'type': 'browser-control',
            'commands': [{'command': 'navigate', 'url': 'https://example.com'}]
        }, {}, headless=True, save_recording_path='./artifacts/runs/recovery-test/videos')
        print('Recovery test result:', result)
        return True
    except Exception as e:
        print(f'Recovery test failed: {e}')
        return False

success = asyncio.run(recovery_test())
exit(0 if success else 1)
"

if [ $? -eq 0 ]; then
    echo "✅ Recovery completed successfully"
else
    echo "❌ Recovery failed - manual intervention required"
    exit 1
fi
```

### Partial Recovery (Git-Script Only)

```bash
#!/bin/bash
# Git-script specific recovery

echo "=== Git-Script Recording Recovery ==="

# Enable NEW METHOD
export BYKILT_USE_NEW_METHOD=true

# Test git-script recording
python -c "
import asyncio
from src.script.script_manager import run_script

async def git_recovery_test():
    result = await run_script({
        'type': 'git-script',
        'git': 'https://github.com/Nobukins/sample-tests.git',
        'script_path': 'search_script.py',
        'command': 'python -m pytest search_script.py::test_text_search --no-cov'
    }, {}, headless=True, save_recording_path='./artifacts/runs/git-recovery/videos')
    return result

result = asyncio.run(git_recovery_test())
print('Git-script recovery result:', result)
"

# Verify files were copied
if [ -n "$(find artifacts/runs/git-recovery -name '*.webm' 2>/dev/null)" ]; then
    echo "✅ Git-script recording recovery successful"
else
    echo "❌ Git-script recording recovery failed"
fi
```

## Escalation Procedures

### Level 1: Self-Recovery
- Run automated diagnostic scripts
- Apply standard recovery procedures
- Verify functionality with test suite

### Level 2: Manual Investigation
- Review logs for error patterns
- Check system resources and permissions
- Examine recent code changes

### Level 3: Expert Investigation
- Deep system analysis
- Code debugging and profiling
- Potential framework modifications

### Emergency Contact Information

```text
Recording System Emergency Contacts:
- Primary: Development Team Lead
- Secondary: DevOps Engineer
- Escalation: Technical Director

Critical Issue Indicators:
1. No recordings generated for >24 hours
2. >50% test failure rate
3. System resource exhaustion
4. Security-related recording exposure
```