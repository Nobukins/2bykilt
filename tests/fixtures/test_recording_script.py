"""
Fixture script for testing script type recording functionality.
This script is used by tests/test_script_type_recording.py

NOTE: This is NOT a pytest test file. It's a fixture script used by other tests.
The function name matches pytest's pattern but it's intentional - it's meant to be
executed as a standalone script, not by pytest.
"""
import os
import pytest

@pytest.mark.ci_safe
def test_recording_verification():
    """Simple test that verifies recording path is set"""
    recording_path = os.environ.get('RECORDING_PATH')
    print(f"Recording path: {recording_path}")
    
    # Verify recording path is set
    assert recording_path is not None, "RECORDING_PATH environment variable must be set"
    assert "artifacts" in recording_path or "videos" in recording_path, \
        f"Recording path should contain 'artifacts' or 'videos': {recording_path}"
    
    print("Recording path verification successful")

if __name__ == "__main__":
    test_recording_verification()
