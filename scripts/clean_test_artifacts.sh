#!/bin/bash
#
# Clean test artifacts before running pytest
#
# This script removes test-generated artifacts that can interfere with test execution
# when tests use tmp_path but ArtifactManager still references the original directory.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

echo "Cleaning test artifacts..."

# Remove test-specific artifact directories
rm -rf artifacts/runs/SCRDUPON-art
rm -rf artifacts/runs/SCRDUPOFF-art
rm -rf artifacts/runs/TESTRUN*-art
rm -rf artifacts/runs/TESTVIDEO*-art
rm -rf artifacts/runs/test-art
rm -rf artifacts/runs/phrase-search-art
rm -rf artifacts/runs/test_search-art
rm -rf artifacts/runs/test_with_recording-art
rm -rf artifacts/runs/test_error_handling-art
rm -rf artifacts/runs/simple_test-art

# Clean pytest cache
rm -rf .pytest_cache

echo "✅ Test artifacts cleaned successfully"
