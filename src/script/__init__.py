"""
Script module for bykilt.

This module provides functionality for browser automation script generation and execution.
Phase 4 Refactoring: Functions have been organized into focused modules while maintaining
backward compatibility through this __init__.py.

Modules:
    - git_operations: Git repository cloning and script execution
    - artifact_management: Artifact collection and metadata management
    - script_manager: Main script generation and management (remaining functions)
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

# Export all public functions
__all__ = [
    # Git operations
    'execute_git_script',
    'clone_git_repo',
    'execute_git_script_new_method',
    # Artifact management
    'move_script_files_to_artifacts',
]
