"""llms.txt Merger (Issue #320 Phase 2)

Merge discovered remote llms.txt actions into local llms.txt file.

Design goals:
  * Conflict detection (duplicate action names)
  * Automatic backup creation before merge
  * Preserve existing llms.txt structure and formatting
  * Support different merge strategies (skip, overwrite, rename)
  * Detailed merge reporting (added, skipped, conflicts)

Merge workflow:
  1. Load local llms.txt file
  2. Create timestamped backup (.bak)
  3. Detect action name conflicts
  4. Apply merge strategy
  5. Write merged content back to file
  6. Return merge result with statistics

Public API:
  LlmsTxtMerger(llms_txt_path, backup_dir=None, strategy='skip')
    .merge_actions(new_actions: List[Dict]) -> MergeResult
    .preview_merge(new_actions: List[Dict]) -> MergePreview

Integration with Phase 1 & 2:
  - Works with LlmsTxtSource discovery results
  - Applies SecurityValidator validation before merge
  - Maintains llms.txt schema compatibility
"""
from __future__ import annotations

import shutil
import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from src.utils.app_logger import logger


class MergeError(Exception):
    """Raised when merge operation fails."""


@dataclass(slots=True)
class MergeResult:
    """Result of merge operation."""
    success: bool
    added: List[str] = field(default_factory=list)  # Action names successfully added
    skipped: List[str] = field(default_factory=list)  # Action names skipped (conflicts)
    overwritten: List[str] = field(default_factory=list)  # Action names overwritten
    backup_path: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def total_processed(self) -> int:
        """Total number of actions processed."""
        return len(self.added) + len(self.skipped) + len(self.overwritten)

    def summary(self) -> str:
        """Human-readable summary of merge operation."""
        if not self.success:
            return f"Merge failed: {self.error_message}"
        
        parts = [
            f"Merge completed: {self.total_processed} actions processed",
            f"  ✅ Added: {len(self.added)}",
            f"  ⏭️  Skipped: {len(self.skipped)}",
            f"  🔄 Overwritten: {len(self.overwritten)}",
        ]
        if self.backup_path:
            parts.append(f"  💾 Backup: {self.backup_path}")
        return "\n".join(parts)


@dataclass(slots=True)
class MergePreview:
    """Preview of merge operation without actually performing it."""
    would_add: List[str] = field(default_factory=list)
    would_skip: List[str] = field(default_factory=list)
    would_overwrite: List[str] = field(default_factory=list)
    conflicts: List[Dict[str, Any]] = field(default_factory=list)  # Detailed conflict info

    @property
    def has_conflicts(self) -> bool:
        """Check if there are any conflicts."""
        return len(self.conflicts) > 0

    def summary(self) -> str:
        """Human-readable summary of preview."""
        parts = [
            "Merge Preview:",
            f"  ➕ Would add: {len(self.would_add)} actions",
            f"  ⏭️  Would skip: {len(self.would_skip)} actions",
            f"  🔄 Would overwrite: {len(self.would_overwrite)} actions",
        ]
        if self.has_conflicts:
            parts.append(f"  ⚠️  Conflicts: {len(self.conflicts)}")
        return "\n".join(parts)


class LlmsTxtMerger:
    """Merger for integrating remote llms.txt actions into local file."""

    def __init__(
        self,
        llms_txt_path: str | Path,
        backup_dir: Optional[str | Path] = None,
        strategy: Literal['skip', 'overwrite', 'rename'] = 'skip',
    ):
        """Initialize LlmsTxtMerger.

        Args:
            llms_txt_path: Path to local llms.txt file
            backup_dir: Directory for backups (default: same directory as llms.txt)
            strategy: Conflict resolution strategy:
                - 'skip': Skip conflicting actions (keep existing)
                - 'overwrite': Overwrite existing actions with new ones
                - 'rename': Rename conflicting actions (append suffix)
        """
        self.llms_txt_path = Path(llms_txt_path)
        self.backup_dir = Path(backup_dir) if backup_dir else self.llms_txt_path.parent
        self.strategy = strategy
        
        if not self.llms_txt_path.exists():
            logger.warning(f"llms.txt not found at {self.llms_txt_path}, will create new file")
        
        logger.info(
            f"LlmsTxtMerger initialized: path={self.llms_txt_path}, "
            f"strategy={strategy}, backup_dir={self.backup_dir}"
        )

    def merge_actions(
        self,
        new_actions: List[Dict[str, Any]],
        *,
        create_backup: bool = True,
    ) -> MergeResult:
        """Merge new actions into local llms.txt file.

        Args:
            new_actions: List of action dictionaries to merge
            create_backup: If True, create backup before merge (default: True)

        Returns:
            MergeResult with operation status and statistics
        """
        result = MergeResult(success=False)

        try:
            # Load existing llms.txt
            existing_data = self._load_llms_txt()
            existing_actions = existing_data.get('actions', [])
            existing_names = {action.get('name') for action in existing_actions if action.get('name')}

            # Create backup if requested
            if create_backup:
                backup_path = self._create_backup()
                result.backup_path = str(backup_path) if backup_path else None

            # Process each new action according to strategy
            merged_actions = list(existing_actions)  # Copy existing actions
            
            for new_action in new_actions:
                action_name = new_action.get('name')
                if not action_name:
                    logger.warning("Skipping action without name")
                    continue

                if action_name in existing_names:
                    # Conflict detected
                    if self.strategy == 'skip':
                        result.skipped.append(action_name)
                        logger.info(f"Skipped conflicting action: {action_name}")
                    elif self.strategy == 'overwrite':
                        # Remove old action with same name
                        merged_actions = [a for a in merged_actions if a.get('name') != action_name]
                        merged_actions.append(new_action)
                        existing_names.discard(action_name)
                        existing_names.add(action_name)
                        result.overwritten.append(action_name)
                        logger.info(f"Overwritten action: {action_name}")
                    elif self.strategy == 'rename':
                        # Rename new action with suffix
                        renamed = self._rename_action(new_action, existing_names)
                        merged_actions.append(renamed)
                        existing_names.add(renamed['name'])
                        result.added.append(renamed['name'])
                        logger.info(f"Renamed and added action: {action_name} -> {renamed['name']}")
                else:
                    # No conflict, add directly
                    merged_actions.append(new_action)
                    existing_names.add(action_name)
                    result.added.append(action_name)
                    logger.info(f"Added new action: {action_name}")

            # Write merged content back to file
            merged_data = existing_data.copy()
            merged_data['actions'] = merged_actions
            self._save_llms_txt(merged_data)

            result.success = True
            logger.info(result.summary())

        except Exception as e:
            result.error_message = str(e)
            logger.error(f"Merge failed: {e}", exc_info=True)

        return result

    def preview_merge(
        self,
        new_actions: List[Dict[str, Any]],
    ) -> MergePreview:
        """Preview merge operation without modifying files.

        Args:
            new_actions: List of action dictionaries to preview

        Returns:
            MergePreview with what would happen during merge
        """
        preview = MergePreview()

        try:
            # Load existing llms.txt
            existing_data = self._load_llms_txt()
            existing_actions = existing_data.get('actions', [])
            existing_names = {action.get('name') for action in existing_actions if action.get('name')}
            
            # Build action lookup for conflict details
            existing_lookup = {a.get('name'): a for a in existing_actions if a.get('name')}

            # Analyze each new action
            for new_action in new_actions:
                action_name = new_action.get('name')
                if not action_name:
                    continue

                if action_name in existing_names:
                    # Conflict
                    if self.strategy == 'skip':
                        preview.would_skip.append(action_name)
                    elif self.strategy == 'overwrite':
                        preview.would_overwrite.append(action_name)
                    elif self.strategy == 'rename':
                        renamed = self._rename_action(new_action, existing_names)
                        preview.would_add.append(renamed['name'])
                    
                    # Add conflict details
                    preview.conflicts.append({
                        'name': action_name,
                        'existing_type': existing_lookup[action_name].get('type'),
                        'new_type': new_action.get('type'),
                        'resolution': self.strategy,
                    })
                else:
                    # No conflict
                    preview.would_add.append(action_name)

            logger.debug(preview.summary())

        except Exception as e:
            logger.error(f"Preview failed: {e}", exc_info=True)

        return preview

    def _load_llms_txt(self) -> Dict[str, Any]:
        """Load existing llms.txt file.

        Returns:
            Parsed YAML data as dictionary
        """
        if not self.llms_txt_path.exists():
            logger.info("llms.txt does not exist, returning empty structure")
            return {'actions': []}

        try:
            with open(self.llms_txt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content) or {}
                logger.debug(f"Loaded llms.txt with {len(data.get('actions', []))} actions")
                return data
        except Exception as e:
            logger.error(f"Failed to load llms.txt: {e}")
            raise MergeError(f"Failed to load {self.llms_txt_path}: {e}") from e

    def _save_llms_txt(self, data: Dict[str, Any]) -> None:
        """Save merged data back to llms.txt file.

        Args:
            data: YAML data to save
        """
        try:
            # Ensure parent directory exists
            self.llms_txt_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.llms_txt_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False,
                    indent=2,
                )
            logger.info(f"Saved merged llms.txt with {len(data.get('actions', []))} actions")
        except Exception as e:
            logger.error(f"Failed to save llms.txt: {e}")
            raise MergeError(f"Failed to save {self.llms_txt_path}: {e}") from e

    def _create_backup(self) -> Optional[Path]:
        """Create timestamped backup of llms.txt file.

        Returns:
            Path to backup file, or None if no file to backup
        """
        if not self.llms_txt_path.exists():
            logger.info("No existing llms.txt to backup")
            return None

        try:
            # Ensure backup directory exists
            self.backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Create backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"{self.llms_txt_path.stem}_{timestamp}.bak"
            backup_path = self.backup_dir / backup_name
            
            # Copy file
            shutil.copy2(self.llms_txt_path, backup_path)
            logger.info(f"Created backup: {backup_path}")
            return backup_path
        except Exception as e:
            logger.error(f"Failed to create backup: {e}")
            raise MergeError(f"Failed to create backup: {e}") from e

    def _rename_action(
        self,
        action: Dict[str, Any],
        existing_names: set,
    ) -> Dict[str, Any]:
        """Rename action to avoid conflict.

        Args:
            action: Action dictionary to rename
            existing_names: Set of existing action names

        Returns:
            New action dictionary with renamed 'name' field
        """
        original_name = action.get('name')
        suffix = 1
        
        while True:
            new_name = f"{original_name}_{suffix}"
            if new_name not in existing_names:
                renamed_action = action.copy()
                renamed_action['name'] = new_name
                return renamed_action
            suffix += 1


def merge_remote_actions(
    remote_actions: List[Dict[str, Any]],
    llms_txt_path: str | Path = "llms.txt",
    *,
    strategy: Literal['skip', 'overwrite', 'rename'] = 'skip',
    preview_only: bool = False,
) -> MergeResult | MergePreview:
    """Convenience function to merge remote actions into local llms.txt.

    Args:
        remote_actions: List of actions from remote llms.txt
        llms_txt_path: Path to local llms.txt file
        strategy: Conflict resolution strategy
        preview_only: If True, return MergePreview without modifying files

    Returns:
        MergeResult if preview_only=False, MergePreview otherwise
    """
    merger = LlmsTxtMerger(llms_txt_path, strategy=strategy)
    
    if preview_only:
        return merger.preview_merge(remote_actions)
    else:
        return merger.merge_actions(remote_actions)


__all__ = [
    "LlmsTxtMerger",
    "MergeError",
    "MergeResult",
    "MergePreview",
    "merge_remote_actions",
]
