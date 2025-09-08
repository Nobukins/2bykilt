"""
Directory Migration Tool for 2bykilt

Handles migration from tmp/myscript to myscript directory structure.
Provides backward compatibility and migration logging.
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

class DirectoryMigrationTool:
    """Tool for migrating user scripts from tmp/myscript to myscript directory"""

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize migration tool

        Args:
            base_dir: Base directory for migration (defaults to current working directory)
        """
        self.base_dir = Path(base_dir) if base_dir else Path.cwd()
        self.old_dir = self.base_dir / 'tmp' / 'myscript'
        self.new_dir = self.base_dir / 'myscript'
        self.backup_dir = self.base_dir / 'tmp' / 'myscript_backup'

    def needs_migration(self) -> bool:
        """
        Check if migration is needed

        Returns:
            True if old directory exists and new directory doesn't, or old has content
        """
        old_exists = self.old_dir.exists()
        new_exists = self.new_dir.exists()

        if not old_exists:
            return False

        if not new_exists:
            return True

        # Check if old directory has files that new directory doesn't
        old_files = set(self._get_file_list(self.old_dir))
        new_files = set(self._get_file_list(self.new_dir))

        return bool(old_files - new_files)

    def _get_file_list(self, directory: Path) -> List[str]:
        """Get list of relative file paths in directory"""
        if not directory.exists():
            return []

        files = []
        for file_path in directory.rglob('*'):
            if file_path.is_file():
                files.append(str(file_path.relative_to(directory)))

        return files

    def create_backup(self) -> bool:
        """
        Create backup of old directory before migration

        Returns:
            True if backup created successfully
        """
        if not self.old_dir.exists():
            logger.info("Old directory doesn't exist, no backup needed")
            return True

        try:
            if self.backup_dir.exists():
                logger.info(f"Backup already exists at {self.backup_dir}")
                return True

            logger.info(f"Creating backup: {self.old_dir} -> {self.backup_dir}")
            shutil.copytree(self.old_dir, self.backup_dir)
            logger.info("✅ Backup created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            return False

    def migrate_files(self) -> Tuple[bool, List[str]]:
        """
        Migrate files from old directory to new directory

        Returns:
            Tuple of (success, list of migrated files)
        """
        migrated_files = []

        try:
            # Ensure new directory exists
            self.new_dir.mkdir(parents=True, exist_ok=True)

            if not self.old_dir.exists():
                logger.info("Old directory doesn't exist, nothing to migrate")
                return True, []

            # Get all files in old directory
            for old_file in self.old_dir.rglob('*'):
                if not old_file.is_file():
                    continue

                # Calculate relative path
                relative_path = old_file.relative_to(self.old_dir)
                new_file = self.new_dir / relative_path

                # Create parent directories if needed
                new_file.parent.mkdir(parents=True, exist_ok=True)

                # Skip if file already exists in new location
                if new_file.exists():
                    logger.info(f"File already exists, skipping: {relative_path}")
                    continue

                # Copy file
                logger.info(f"Migrating: {relative_path}")
                shutil.copy2(old_file, new_file)
                migrated_files.append(str(relative_path))

            logger.info(f"✅ Migration completed: {len(migrated_files)} files migrated")
            return True, migrated_files

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            return False, migrated_files

    def create_symlink(self) -> bool:
        """
        Create symlink from old directory to new directory for backward compatibility

        Returns:
            True if symlink created successfully
        """
        try:
            # Remove old directory if it exists
            if self.old_dir.exists():
                if self.old_dir.is_symlink():
                    self.old_dir.unlink()
                elif self.old_dir.is_dir():
                    # Only remove if it's empty (files should have been migrated)
                    if not any(self.old_dir.iterdir()):
                        self.old_dir.rmdir()
                    else:
                        logger.warning(f"Old directory not empty, keeping for safety: {self.old_dir}")
                        return False

            # Create parent directory if needed
            self.old_dir.parent.mkdir(parents=True, exist_ok=True)

            # Create symlink
            logger.info(f"Creating symlink: {self.old_dir} -> {self.new_dir}")
            self.old_dir.symlink_to(self.new_dir, target_is_directory=True)
            logger.info("✅ Symlink created successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to create symlink: {e}")
            return False

    def log_migration(self, migrated_files: List[str], run_id: Optional[str] = None) -> None:
        """
        Log migration details to artifacts

        Args:
            migrated_files: List of migrated file paths
            run_id: Run ID for logging context
        """
        try:
            # Create artifacts directory structure
            artifacts_dir = self.base_dir / 'artifacts'
            if run_id:
                artifacts_dir = artifacts_dir / 'runs' / run_id

            artifacts_dir.mkdir(parents=True, exist_ok=True)
            log_file = artifacts_dir / 'migration.log'

            # Prepare log content
            timestamp = datetime.now().isoformat()
            log_content = f"""Migration Log - {timestamp}
=====================================

Migration Details:
- From: {self.old_dir}
- To: {self.new_dir}
- Backup: {self.backup_dir}
- Files Migrated: {len(migrated_files)}

Migrated Files:
{chr(10).join(f"- {file}" for file in migrated_files) if migrated_files else "None"}

Status: Migration completed successfully
"""

            # Write log
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(log_content)

            logger.info(f"✅ Migration log written to: {log_file}")

        except Exception as e:
            logger.error(f"Failed to write migration log: {e}")

    def perform_migration(self, run_id: Optional[str] = None) -> Dict[str, any]:
        """
        Perform complete migration process

        Args:
            run_id: Run ID for logging context

        Returns:
            Migration result dictionary
        """
        result = {
            'success': False,
            'needs_migration': self.needs_migration(),
            'migrated_files': [],
            'backup_created': False,
            'symlink_created': False,
            'error': None
        }

        if not result['needs_migration']:
            logger.info("✅ No migration needed")
            result['success'] = True
            return result

        logger.info("🔄 Starting directory migration process...")

        # Step 1: Create backup
        if not self.create_backup():
            result['error'] = "Failed to create backup"
            return result

        result['backup_created'] = True

        # Step 2: Migrate files
        success, migrated_files = self.migrate_files()
        if not success:
            result['error'] = "Failed to migrate files"
            return result

        result['migrated_files'] = migrated_files

        # Step 3: Create symlink for backward compatibility
        if self.create_symlink():
            result['symlink_created'] = True

        # Step 4: Log migration
        self.log_migration(migrated_files, run_id)

        result['success'] = True
        logger.info("✅ Directory migration completed successfully")
        return result

    def get_migration_status(self) -> Dict[str, any]:
        """
        Get current migration status

        Returns:
            Status dictionary
        """
        return {
            'old_dir_exists': self.old_dir.exists(),
            'new_dir_exists': self.new_dir.exists(),
            'backup_exists': self.backup_dir.exists(),
            'old_dir_is_symlink': self.old_dir.is_symlink() if self.old_dir.exists() else False,
            'needs_migration': self.needs_migration(),
            'old_dir_files': self._get_file_list(self.old_dir),
            'new_dir_files': self._get_file_list(self.new_dir)
        }


def migrate_user_scripts(base_dir: Optional[str] = None, run_id: Optional[str] = None) -> Dict[str, any]:
    """
    Convenience function to migrate user scripts directory

    Args:
        base_dir: Base directory for migration
        run_id: Run ID for logging

    Returns:
        Migration result
    """
    tool = DirectoryMigrationTool(base_dir)
    return tool.perform_migration(run_id)


def get_migration_status(base_dir: Optional[str] = None) -> Dict[str, any]:
    """
    Convenience function to get migration status

    Args:
        base_dir: Base directory to check

    Returns:
        Status dictionary
    """
    tool = DirectoryMigrationTool(base_dir)
    return tool.get_migration_status()
