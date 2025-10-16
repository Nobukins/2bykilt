"""
Script module for bykilt.

This module provides functionality for browser automation script generation and execution.
Phase 4 Refactoring: Functions have been organized into focused modules while maintaining
backward compatibility through this __init__.py.

Phase 2 Refactoring (Issue #329): Further split browser control and process helpers.

Modules:
    - git_operations: Git repository cloning and script execution
    - artifact_management: Artifact collection and metadata management
    - browser_control_executor: Browser control script generation and execution (Phase 2)
    - process_helpers: Subprocess execution helpers (Phase 2)
    - script_manager: Main script orchestration and remaining functions
"""

# Re-export all functions for backward compatibility
from .git_operations import (
    execute_git_script,
    clone_git_repo,
    execute_git_script_new_method,
)

from .artifact_management import (
    move_script_files_to_artifacts,
)

from .browser_control_executor import (
    generate_browser_script,
    execute_browser_control,
)

from .process_helpers import (
    log_subprocess_output,
    process_execution,
)

# Export all public functions
__all__ = [
    # Git operations
    'execute_git_script',
    'clone_git_repo',
    'execute_git_script_new_method',
    # Artifact management
    'move_script_files_to_artifacts',
    # Browser control (Phase 2)
    'generate_browser_script',
    'execute_browser_control',
    # Process helpers (Phase 2)
    'log_subprocess_output',
    'process_execution',
]
