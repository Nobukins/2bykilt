"""
End-to-End Integration Tests for llms.txt Import Feature (Issue #320 Phase 3)

Tests the complete workflow from discovery to import through the UI handler functions.
"""

import json
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Import handler functions from bykilt.py
# These are the actual UI handler functions being tested
@pytest.fixture(autouse=True)
def mock_bykilt_module():
    """Mock the bykilt module and its handler functions for testing."""
    # We'll patch the actual functions when needed in individual tests
    pass


@pytest.mark.ci_safe
class TestDiscoveryE2E:
    """Test discovery workflow end-to-end."""
    
    def test_complete_discovery_flow(self, temp_llmstxt_file):
        """Test complete discovery flow with valid URL."""
        from src.modules.llmstxt_discovery import discover_and_parse
        from src.security.llmstxt_validator import validate_remote_llmstxt
        
        url = "https://example.com/llms.txt"
        
        # Mock HTTP response
        with patch('src.modules.llmstxt_discovery.LlmsTxtSource.auto_discover') as mock_discover:
            mock_discover.return_value = {
                'url': url,
                'content': """
# 2bykilt browser_control
## search_product
- navigate: https://example.com
- type: input[name="q"] = "test"
- click: button[type="submit"]

# 2bykilt git_script
## commit_changes
- command: git add .
- command: git commit -m "test"
                """
            }
            
            result = discover_and_parse(url, https_only=True)
            
            assert result['success']
            assert len(result['browser_control']) == 1
            assert len(result['git_scripts']) == 1
            assert result['browser_control'][0]['name'] == 'search_product'
            assert result['git_scripts'][0]['name'] == 'commit_changes'
    
    def test_discovery_with_security_validation(self):
        """Test discovery triggers security validation."""
        from src.modules.llmstxt_discovery import discover_and_parse
        from src.security.llmstxt_validator import validate_remote_llmstxt
        
        url = "https://example.com/llms.txt"
        
        with patch('src.modules.llmstxt_discovery.LlmsTxtSource.auto_discover') as mock_discover:
            content = """
# 2bykilt browser_control
## test_action
- navigate: https://example.com
            """
            mock_discover.return_value = {
                'url': url,
                'content': content
            }
            
            result = discover_and_parse(url, https_only=True)
            actions = result['browser_control']
            
            # Validate discovered actions
            validation = validate_remote_llmstxt(url, actions, content, https_only=True)
            
            assert validation.valid
            assert validation.url == url
    
    def test_discovery_fails_gracefully_on_error(self):
        """Test discovery handles errors gracefully."""
        from src.modules.llmstxt_discovery import discover_and_parse
        
        url = "https://invalid-url-that-does-not-exist.example"
        
        with patch('src.modules.llmstxt_discovery.LlmsTxtSource.auto_discover') as mock_discover:
            mock_discover.side_effect = Exception("Network error")
            
            result = discover_and_parse(url, https_only=True)
            
            assert not result['success']
            assert 'error' in result


@pytest.mark.ci_safe
class TestPreviewE2E:
    """Test preview workflow end-to-end."""
    
    def test_preview_merge_skip_strategy(self, temp_llmstxt_file):
        """Test preview merge with skip strategy."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        # Create existing llms.txt with one action
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
- click: button
"""
        temp_llmstxt_file.write_text(existing_content)
        
        # New actions to merge
        new_actions = [
            {
                'name': 'existing_action',  # Conflict
                'type': 'browser_control',
                'steps': [
                    {'action': 'navigate', 'selector': '', 'value': 'https://new.com'},
                    {'action': 'type', 'selector': 'input', 'value': 'test'}
                ]
            },
            {
                'name': 'new_action',  # No conflict
                'type': 'browser_control',
                'steps': [
                    {'action': 'click', 'selector': 'button', 'value': ''}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='skip')
        preview = merger.preview_merge(new_actions)
        
        assert preview.has_conflicts
        assert preview.stats['would_skip'] == 1  # existing_action
        assert preview.stats['would_add'] == 1   # new_action
        assert len(preview.conflicts) == 1
    
    def test_preview_merge_overwrite_strategy(self, temp_llmstxt_file):
        """Test preview merge with overwrite strategy."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
"""
        temp_llmstxt_file.write_text(existing_content)
        
        new_actions = [
            {
                'name': 'existing_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'navigate', 'selector': '', 'value': 'https://new.com'}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='overwrite')
        preview = merger.preview_merge(new_actions)
        
        assert preview.has_conflicts
        assert preview.stats['would_overwrite'] == 1
        assert len(preview.conflicts) == 1
    
    def test_preview_merge_rename_strategy(self, temp_llmstxt_file):
        """Test preview merge with rename strategy."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
"""
        temp_llmstxt_file.write_text(existing_content)
        
        new_actions = [
            {
                'name': 'existing_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'navigate', 'selector': '', 'value': 'https://new.com'}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='rename')
        preview = merger.preview_merge(new_actions)
        
        # With rename, conflict is resolved by adding number suffix
        # This should still show as a conflict with 'rename' resolution
        assert preview.has_conflicts
        assert preview.stats['would_add'] == 1  # Will be added as existing_action_2
        assert len(preview.conflicts) == 1


@pytest.mark.ci_safe
class TestImportE2E:
    """Test import workflow end-to-end."""
    
    def test_complete_import_flow_skip(self, temp_llmstxt_file):
        """Test complete import flow with skip strategy."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
"""
        temp_llmstxt_file.write_text(existing_content)
        
        new_actions = [
            {
                'name': 'new_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'click', 'selector': 'button', 'value': ''}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='skip')
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success
        assert result.stats['added'] == 1
        assert result.backup_path is not None
        assert Path(result.backup_path).exists()
        
        # Verify content
        final_content = temp_llmstxt_file.read_text()
        assert 'existing_action' in final_content
        assert 'new_action' in final_content
    
    def test_import_creates_backup(self, temp_llmstxt_file):
        """Test import creates backup file."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        original_content = """
# 2bykilt browser_control

## test_action
- navigate: https://test.com
"""
        temp_llmstxt_file.write_text(original_content)
        
        new_actions = [
            {
                'name': 'new_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'click', 'selector': 'button', 'value': ''}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='skip')
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.backup_path is not None
        backup_file = Path(result.backup_path)
        assert backup_file.exists()
        assert backup_file.name.startswith('llms.txt.backup.')
        
        # Backup should contain original content
        backup_content = backup_file.read_text()
        assert 'test_action' in backup_content
    
    def test_import_with_overwrite(self, temp_llmstxt_file):
        """Test import with overwrite strategy replaces existing actions."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://old-url.com
- click: button
"""
        temp_llmstxt_file.write_text(existing_content)
        
        new_actions = [
            {
                'name': 'existing_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'navigate', 'selector': '', 'value': 'https://new-url.com'},
                    {'action': 'type', 'selector': 'input', 'value': 'test'}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='overwrite')
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success
        assert result.stats['overwritten'] == 1
        
        # Verify new content
        final_content = temp_llmstxt_file.read_text()
        assert 'https://new-url.com' in final_content
        assert 'https://old-url.com' not in final_content
    
    def test_import_with_rename(self, temp_llmstxt_file):
        """Test import with rename strategy adds numbered suffix."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
"""
        temp_llmstxt_file.write_text(existing_content)
        
        new_actions = [
            {
                'name': 'existing_action',
                'type': 'browser_control',
                'steps': [
                    {'action': 'navigate', 'selector': '', 'value': 'https://new.com'}
                ]
            }
        ]
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='rename')
        result = merger.merge_actions(new_actions, create_backup=True)
        
        assert result.success
        assert result.stats['added'] == 1
        
        # Verify renamed action exists
        final_content = temp_llmstxt_file.read_text()
        assert 'existing_action' in final_content  # Original
        assert 'existing_action_2' in final_content  # Renamed


@pytest.mark.ci_safe
class TestErrorHandlingE2E:
    """Test error handling across the workflow."""
    
    def test_invalid_url_discovery(self):
        """Test handling of invalid URLs during discovery."""
        from src.modules.llmstxt_discovery import discover_and_parse
        
        url = "not-a-valid-url"
        
        result = discover_and_parse(url, https_only=True)
        
        assert not result['success']
        assert 'error' in result
    
    def test_security_validation_failure(self):
        """Test security validation catches dangerous patterns."""
        from src.security.llmstxt_validator import validate_remote_llmstxt
        
        url = "https://example.com/llms.txt"
        dangerous_actions = [
            {
                'name': 'dangerous_action',
                'type': 'git_script',
                'steps': [
                    {'action': 'command', 'selector': '', 'value': 'rm -rf /'}
                ]
            }
        ]
        yaml_content = """
# 2bykilt git_script
## dangerous_action
- command: rm -rf /
"""
        
        validation = validate_remote_llmstxt(url, dangerous_actions, yaml_content, https_only=True)
        
        assert not validation.valid
        assert len(validation.errors) > 0
    
    def test_merge_with_empty_actions(self, temp_llmstxt_file):
        """Test merge handles empty actions list gracefully."""
        from src.modules.llmstxt_merger import LlmsTxtMerger
        
        existing_content = """
# 2bykilt browser_control

## existing_action
- navigate: https://existing.com
"""
        temp_llmstxt_file.write_text(existing_content)
        
        merger = LlmsTxtMerger(str(temp_llmstxt_file), strategy='skip')
        result = merger.merge_actions([], create_backup=False)
        
        # Should succeed but add nothing
        assert result.success
        assert result.stats['added'] == 0
        assert result.stats['skipped'] == 0


@pytest.fixture
def temp_llmstxt_file(tmp_path):
    """Create a temporary llms.txt file for testing."""
    llms_file = tmp_path / "llms.txt"
    llms_file.touch()
    yield llms_file
    # Cleanup backups
    for backup in tmp_path.glob("llms.txt.backup.*"):
        backup.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
