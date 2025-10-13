"""Tests for llms.txt Merger (Issue #320 Phase 2)

Test coverage:
  * Merge operations (add, skip, overwrite, rename)
  * Conflict detection and resolution
  * Backup creation
  * Preview functionality
  * Error handling and edge cases
"""
import pytest
import tempfile
import yaml
from pathlib import Path

from src.modules.llmstxt_merger import (
    LlmsTxtMerger,
    MergeError,
    MergeResult,
    MergePreview,
    merge_remote_actions,
)


@pytest.fixture
def temp_llms_txt(tmp_path):
    """Create temporary llms.txt file for testing."""
    llms_path = tmp_path / "llms.txt"
    initial_data = {
        'actions': [
            {
                'name': 'existing-action-1',
                'type': 'browser-control',
                'flow': [{'action': 'navigate', 'url': 'https://example.com'}]
            },
            {
                'name': 'existing-action-2',
                'type': 'script',
                'command': 'echo test'
            }
        ]
    }
    with open(llms_path, 'w') as f:
        yaml.dump(initial_data, f, default_flow_style=False)
    return llms_path


@pytest.fixture
def empty_llms_txt(tmp_path):
    """Create empty llms.txt file for testing."""
    llms_path = tmp_path / "llms.txt"
    llms_path.touch()
    with open(llms_path, 'w') as f:
        f.write("actions: []\n")
    return llms_path


@pytest.fixture
def new_actions():
    """Sample new actions to merge."""
    return [
        {
            'name': 'new-action-1',
            'type': 'browser-control',
            'flow': [{'action': 'click', 'selector': '#button'}]
        },
        {
            'name': 'new-action-2',
            'type': 'git-script',
            'git': 'https://github.com/user/repo',
            'script_path': 'script.sh'
        }
    ]


@pytest.fixture
def conflicting_actions():
    """Sample actions with name conflicts."""
    return [
        {
            'name': 'existing-action-1',  # Conflicts with existing
            'type': 'browser-control',
            'flow': [{'action': 'click', 'selector': '#new-button'}]
        },
        {
            'name': 'new-action',  # No conflict
            'type': 'script',
            'command': 'ls -la'
        }
    ]


class TestLlmsTxtMergerInit:
    """Test LlmsTxtMerger initialization."""

    def test_init_with_existing_file(self, temp_llms_txt):
        """Test initialization with existing llms.txt file."""
        merger = LlmsTxtMerger(temp_llms_txt)
        assert merger.llms_txt_path == temp_llms_txt
        assert merger.strategy == 'skip'
        assert merger.backup_dir == temp_llms_txt.parent

    def test_init_with_custom_backup_dir(self, temp_llms_txt, tmp_path):
        """Test initialization with custom backup directory."""
        backup_dir = tmp_path / "backups"
        merger = LlmsTxtMerger(temp_llms_txt, backup_dir=backup_dir)
        assert merger.backup_dir == backup_dir

    def test_init_with_strategy(self, temp_llms_txt):
        """Test initialization with different strategies."""
        for strategy in ['skip', 'overwrite', 'rename']:
            merger = LlmsTxtMerger(temp_llms_txt, strategy=strategy)
            assert merger.strategy == strategy

    def test_init_with_nonexistent_file(self, tmp_path):
        """Test initialization with non-existent file (will be created)."""
        llms_path = tmp_path / "new_llms.txt"
        merger = LlmsTxtMerger(llms_path)
        assert merger.llms_txt_path == llms_path


class TestMergeActionsSkipStrategy:
    """Test merge operations with 'skip' strategy."""

    def test_merge_new_actions_no_conflicts(self, temp_llms_txt, new_actions):
        """Test merging new actions with no conflicts."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        result = merger.merge_actions(new_actions)
        
        assert result.success is True
        assert len(result.added) == 2
        assert 'new-action-1' in result.added
        assert 'new-action-2' in result.added
        assert len(result.skipped) == 0
        assert len(result.overwritten) == 0

    def test_merge_conflicting_actions_skip(self, temp_llms_txt, conflicting_actions):
        """Test merging with conflicts using skip strategy."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        result = merger.merge_actions(conflicting_actions)
        
        assert result.success is True
        assert 'existing-action-1' in result.skipped  # Conflict, skipped
        assert 'new-action' in result.added  # No conflict, added
        assert len(result.overwritten) == 0

    def test_merge_creates_backup(self, temp_llms_txt, new_actions):
        """Test that backup is created during merge."""
        merger = LlmsTxtMerger(temp_llms_txt)
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success is True
        assert result.backup_path is not None
        backup_file = Path(result.backup_path)
        assert backup_file.exists()
        assert backup_file.suffix == '.bak'

    def test_merge_without_backup(self, temp_llms_txt, new_actions):
        """Test merge without creating backup."""
        merger = LlmsTxtMerger(temp_llms_txt)
        result = merger.merge_actions(new_actions, create_backup=False)
        
        assert result.success is True
        assert result.backup_path is None

    def test_merged_file_contains_all_actions(self, temp_llms_txt, new_actions):
        """Test that merged file contains both old and new actions."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        _ = merger.merge_actions(new_actions)  # Merge actions
        
        # Load merged file
        with open(temp_llms_txt, 'r') as f:
            data = yaml.safe_load(f)
        
        actions = data['actions']
        action_names = {a['name'] for a in actions}
        
        # Should have 2 existing + 2 new = 4 total
        assert len(actions) == 4
        assert 'existing-action-1' in action_names
        assert 'existing-action-2' in action_names
        assert 'new-action-1' in action_names
        assert 'new-action-2' in action_names


class TestMergeActionsOverwriteStrategy:
    """Test merge operations with 'overwrite' strategy."""

    def test_merge_overwrite_conflicting_action(self, temp_llms_txt, conflicting_actions):
        """Test overwriting conflicting action."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='overwrite')
        result = merger.merge_actions(conflicting_actions)
        
        assert result.success is True
        assert 'existing-action-1' in result.overwritten
        assert 'new-action' in result.added
        assert len(result.skipped) == 0

    def test_overwritten_action_has_new_content(self, temp_llms_txt, conflicting_actions):
        """Test that overwritten action has new content."""
        # Get original action
        with open(temp_llms_txt, 'r') as f:
            original_data = yaml.safe_load(f)
        original_action = next(a for a in original_data['actions'] if a['name'] == 'existing-action-1')
        
        # Merge with overwrite
        merger = LlmsTxtMerger(temp_llms_txt, strategy='overwrite')
        merger.merge_actions(conflicting_actions)
        
        # Load merged file
        with open(temp_llms_txt, 'r') as f:
            data = yaml.safe_load(f)
        
        merged_action = next(a for a in data['actions'] if a['name'] == 'existing-action-1')
        
        # Content should be different
        assert merged_action['flow'] != original_action['flow']
        assert merged_action['flow'] == conflicting_actions[0]['flow']


class TestMergeActionsRenameStrategy:
    """Test merge operations with 'rename' strategy."""

    def test_merge_rename_conflicting_action(self, temp_llms_txt, conflicting_actions):
        """Test renaming conflicting action."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='rename')
        result = merger.merge_actions(conflicting_actions)
        
        assert result.success is True
        assert 'existing-action-1_1' in result.added  # Renamed
        assert 'new-action' in result.added
        assert len(result.skipped) == 0
        assert len(result.overwritten) == 0

    def test_renamed_action_in_file(self, temp_llms_txt, conflicting_actions):
        """Test that renamed action exists in file."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='rename')
        merger.merge_actions(conflicting_actions)
        
        # Load merged file
        with open(temp_llms_txt, 'r') as f:
            data = yaml.safe_load(f)
        
        action_names = {a['name'] for a in data['actions']}
        
        # Should have both original and renamed
        assert 'existing-action-1' in action_names  # Original kept
        assert 'existing-action-1_1' in action_names  # Renamed version added
        assert 'new-action' in action_names

    def test_multiple_renames_increment_suffix(self, temp_llms_txt):
        """Test that multiple renames increment suffix correctly."""
        actions_with_same_name = [
            {'name': 'existing-action-1', 'type': 'script', 'command': 'echo 1'},
            {'name': 'existing-action-1', 'type': 'script', 'command': 'echo 2'},
            {'name': 'existing-action-1', 'type': 'script', 'command': 'echo 3'},
        ]
        
        merger = LlmsTxtMerger(temp_llms_txt, strategy='rename')
        result = merger.merge_actions(actions_with_same_name)
        
        assert result.success is True
        assert 'existing-action-1_1' in result.added
        assert 'existing-action-1_2' in result.added
        assert 'existing-action-1_3' in result.added


class TestPreviewMerge:
    """Test merge preview functionality."""

    def test_preview_no_conflicts(self, temp_llms_txt, new_actions):
        """Test preview with no conflicts."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        preview = merger.preview_merge(new_actions)
        
        assert len(preview.would_add) == 2
        assert 'new-action-1' in preview.would_add
        assert 'new-action-2' in preview.would_add
        assert len(preview.would_skip) == 0
        assert len(preview.would_overwrite) == 0
        assert preview.has_conflicts is False

    def test_preview_with_conflicts_skip(self, temp_llms_txt, conflicting_actions):
        """Test preview with conflicts using skip strategy."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        preview = merger.preview_merge(conflicting_actions)
        
        assert 'existing-action-1' in preview.would_skip
        assert 'new-action' in preview.would_add
        assert preview.has_conflicts is True
        assert len(preview.conflicts) == 1

    def test_preview_with_conflicts_overwrite(self, temp_llms_txt, conflicting_actions):
        """Test preview with conflicts using overwrite strategy."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='overwrite')
        preview = merger.preview_merge(conflicting_actions)
        
        assert 'existing-action-1' in preview.would_overwrite
        assert 'new-action' in preview.would_add
        assert preview.has_conflicts is True

    def test_preview_with_conflicts_rename(self, temp_llms_txt, conflicting_actions):
        """Test preview with conflicts using rename strategy."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='rename')
        preview = merger.preview_merge(conflicting_actions)
        
        assert 'existing-action-1_1' in preview.would_add  # Renamed
        assert 'new-action' in preview.would_add
        assert preview.has_conflicts is True

    def test_preview_does_not_modify_file(self, temp_llms_txt, new_actions):
        """Test that preview does not modify the file."""
        # Get original content
        with open(temp_llms_txt, 'r') as f:
            original_content = f.read()
        
        merger = LlmsTxtMerger(temp_llms_txt)
        _ = merger.preview_merge(new_actions)  # Preview should not modify file
        
        # Content should be unchanged
        with open(temp_llms_txt, 'r') as f:
            current_content = f.read()
        
        assert current_content == original_content

    def test_conflict_details(self, temp_llms_txt, conflicting_actions):
        """Test that conflict details are provided in preview."""
        merger = LlmsTxtMerger(temp_llms_txt, strategy='skip')
        preview = merger.preview_merge(conflicting_actions)
        
        assert len(preview.conflicts) == 1
        conflict = preview.conflicts[0]
        assert conflict['name'] == 'existing-action-1'
        assert conflict['existing_type'] == 'browser-control'
        assert conflict['new_type'] == 'browser-control'
        assert conflict['resolution'] == 'skip'


class TestEmptyAndNewFiles:
    """Test merge with empty or non-existent files."""

    def test_merge_into_empty_file(self, empty_llms_txt, new_actions):
        """Test merging into empty llms.txt file."""
        merger = LlmsTxtMerger(empty_llms_txt)
        result = merger.merge_actions(new_actions)
        
        assert result.success is True
        assert len(result.added) == 2
        assert len(result.skipped) == 0

    def test_merge_creates_new_file(self, tmp_path, new_actions):
        """Test that merge creates new file if it doesn't exist."""
        llms_path = tmp_path / "new_llms.txt"
        merger = LlmsTxtMerger(llms_path)
        result = merger.merge_actions(new_actions)
        
        assert result.success is True
        assert llms_path.exists()
        assert len(result.added) == 2

    def test_no_backup_for_nonexistent_file(self, tmp_path, new_actions):
        """Test that no backup is created if file doesn't exist."""
        llms_path = tmp_path / "new_llms.txt"
        merger = LlmsTxtMerger(llms_path)
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success is True
        assert result.backup_path is None  # No file to backup


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_merge_empty_actions_list(self, temp_llms_txt):
        """Test merging empty actions list."""
        merger = LlmsTxtMerger(temp_llms_txt)
        result = merger.merge_actions([])
        
        assert result.success is True
        assert len(result.added) == 0

    def test_merge_action_without_name(self, temp_llms_txt):
        """Test merging action without name (should be skipped)."""
        actions = [
            {'type': 'script', 'command': 'echo test'},  # No name
            {'name': 'valid-action', 'type': 'script', 'command': 'ls'}
        ]
        
        merger = LlmsTxtMerger(temp_llms_txt)
        result = merger.merge_actions(actions)
        
        assert result.success is True
        assert len(result.added) == 1
        assert 'valid-action' in result.added

    def test_merge_result_summary(self, temp_llms_txt, new_actions):
        """Test MergeResult summary generation."""
        merger = LlmsTxtMerger(temp_llms_txt)
        result = merger.merge_actions(new_actions)
        
        summary = result.summary()
        assert "Merge completed" in summary
        assert "Added: 2" in summary
        assert result.total_processed == 2

    def test_preview_summary(self, temp_llms_txt, new_actions):
        """Test MergePreview summary generation."""
        merger = LlmsTxtMerger(temp_llms_txt)
        preview = merger.preview_merge(new_actions)
        
        summary = preview.summary()
        assert "Merge Preview" in summary
        assert "Would add: 2" in summary

    def test_backup_directory_created_if_not_exists(self, tmp_path, new_actions):
        """Test that backup directory is created if it doesn't exist."""
        llms_path = tmp_path / "llms.txt"
        llms_path.touch()
        with open(llms_path, 'w') as f:
            f.write("actions: []\n")
        
        backup_dir = tmp_path / "backups" / "nested"
        merger = LlmsTxtMerger(llms_path, backup_dir=backup_dir)
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success is True
        assert backup_dir.exists()
        if result.backup_path:
            assert Path(result.backup_path).parent == backup_dir


class TestConvenienceFunction:
    """Test convenience function merge_remote_actions."""

    def test_merge_remote_actions_default(self, temp_llms_txt, new_actions):
        """Test convenience function with default parameters."""
        result = merge_remote_actions(new_actions, temp_llms_txt)
        
        assert isinstance(result, MergeResult)
        assert result.success is True
        assert len(result.added) == 2

    def test_merge_remote_actions_preview_only(self, temp_llms_txt, new_actions):
        """Test convenience function with preview_only=True."""
        preview = merge_remote_actions(new_actions, temp_llms_txt, preview_only=True)
        
        assert isinstance(preview, MergePreview)
        assert len(preview.would_add) == 2

    def test_merge_remote_actions_with_strategy(self, temp_llms_txt, conflicting_actions):
        """Test convenience function with custom strategy."""
        result = merge_remote_actions(
            conflicting_actions,
            temp_llms_txt,
            strategy='overwrite'
        )
        
        assert result.success is True
        assert len(result.overwritten) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
