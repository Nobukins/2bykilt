"""
Test fixtures for feature flags and artifacts.

This module provides pytest fixtures and helper functions to ensure
feature flags artifacts are properly generated during testing.
"""

import pytest
from pathlib import Path
from typing import Generator, Optional

from src.config.feature_flags import FeatureFlags
from src.runtime.run_context import RunContext


@pytest.fixture
def ensure_flags_artifact(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture that ensures a flags artifact exists before the test runs.

    This fixture:
    1. Changes to the temp directory to isolate artifacts
    2. Calls FeatureFlags.dump_snapshot() to ensure artifact creation
    3. Yields the path to the created artifact directory
    4. Cleans up by clearing overrides after the test

    Usage:
        def test_something(ensure_flags_artifact):
            # flags artifact is guaranteed to exist at ensure_flags_artifact path
            assert (ensure_flags_artifact / "feature_flags_resolved.json").exists()
    """
    # Change to temp directory to isolate artifacts
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)

        # Ensure clean state
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

        # Create the artifact
        artifact_dir = FeatureFlags.dump_snapshot()

        yield artifact_dir

    finally:
        # Restore original directory and clean up
        os.chdir(original_cwd)
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()


@pytest.fixture
def flags_artifact_with_overrides(tmp_path: Path) -> Generator[Path, None, None]:
    """Fixture that creates a flags artifact with some test overrides.

    This is useful for testing scenarios where specific flag values are needed.
    """
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)

        # Set up test overrides
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()
        FeatureFlags.set_override("test.enabled", True)
        FeatureFlags.set_override("test.value", "test_string")
        FeatureFlags.set_override("test.number", 42)

        # Create artifact with overrides
        artifact_dir = FeatureFlags.dump_snapshot()

        yield artifact_dir

    finally:
        os.chdir(original_cwd)
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()


def ensure_flags_artifact_helper(tmp_path: Optional[Path] = None) -> Path:
    """Helper function to ensure flags artifact exists.

    This can be called directly in test functions when you don't want
    to use the fixture approach.

    Args:
        tmp_path: Optional temp directory path. If None, uses current directory.

    Returns:
        Path to the artifact directory containing feature_flags_resolved.json
    """
    if tmp_path:
        original_cwd = Path.cwd()
        import os
        os.chdir(tmp_path)

    try:
        # Ensure clean state
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

        # Create artifact
        return FeatureFlags.dump_snapshot()

    finally:
        if tmp_path:
            os.chdir(original_cwd)


def ensure_flags_artifact_with_overrides_helper(
    overrides: dict,
    tmp_path: Optional[Path] = None
) -> Path:
    """Helper function to create flags artifact with specific overrides.

    Args:
        overrides: Dict of flag names to values to override
        tmp_path: Optional temp directory path

    Returns:
        Path to the artifact directory
    """
    if tmp_path:
        original_cwd = Path.cwd()
        import os
        os.chdir(tmp_path)

    try:
        FeatureFlags.clear_all_overrides()
        FeatureFlags.reload()

        # Apply overrides
        for flag_name, value in overrides.items():
            FeatureFlags.set_override(flag_name, value)

        return FeatureFlags.dump_snapshot()

    finally:
        if tmp_path:
            os.chdir(original_cwd)


@pytest.fixture
def ensure_flags_artifact_for_run_context_tests(tmp_path: Path):
    """Fixture that ensures flags artifacts for run_context related tests.

    This fixture should be explicitly requested by tests that need to ensure
    they have access to flags artifacts for 'run_context' or 'artifact' scenarios.
    """
    original_cwd = Path.cwd()
    try:
        import os
        os.chdir(tmp_path)

        # Only create if no artifact exists
        try:
            run_context = RunContext.get()
            flags_dir = run_context.artifact_dir("flags", ensure=False)
            if not flags_dir.exists():
                FeatureFlags.dump_snapshot()
        except Exception:
            # Fallback: create artifact anyway
            FeatureFlags.dump_snapshot()

    finally:
        os.chdir(original_cwd)