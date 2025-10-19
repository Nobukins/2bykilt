"""
Tests for direct_browser_control module (Issue #340 Phase 2)

Coverage targets:
- Normalize functions (_normalize_from_list, _normalize_from_dict, _normalize_extract_entries)
- Build functions (_build_extract_entry)
- Helper functions (_cancelled, _register_video_artifact)

Target: Phase 2 Browser & Script Testing completion
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from pathlib import Path
from typing import Dict, Any, List

from src.modules.direct_browser_control import (
    _build_extract_entry,
    _normalize_from_list,
    _normalize_from_dict,
    _normalize_extract_entries,
    _register_video_artifact,
    _cancelled,
)
from src.utils.timeout_manager import TimeoutManager


@pytest.mark.ci_safe
class TestBuildExtractEntry:
    """Test _build_extract_entry function"""
    
    def test_build_entry_selector_only(self):
        """Test building extract entry with selector only"""
        result = _build_extract_entry("div.content")
        
        assert result == {
            "selector": "div.content",
            "label": "div.content",  # label defaults to selector
            "fields": None
        }
    
    def test_build_entry_with_label(self):
        """Test building extract entry with label"""
        result = _build_extract_entry("h1", label="title")
        
        assert result == {
            "selector": "h1",
            "label": "title",
            "fields": None
        }
    
    def test_build_entry_with_fields(self):
        """Test building extract entry with fields"""
        result = _build_extract_entry("a", fields=["href", "text"])
        
        assert result == {
            "selector": "a",
            "label": "a",  # label defaults to selector
            "fields": ["href", "text"]
        }
    
    def test_build_entry_complete(self):
        """Test building extract entry with all parameters"""
        result = _build_extract_entry("img", label="image", fields=["src", "alt"])
        
        assert result == {
            "selector": "img",
            "label": "image",
            "fields": ["src", "alt"]
        }


@pytest.mark.ci_safe
class TestNormalizeFromList:
    """Test _normalize_from_list function"""
    
    def test_normalize_string_selectors(self):
        """Test normalizing list of string selectors"""
        selectors = ["div.content", "h1.title", "p.text"]
        result = _normalize_from_list(selectors)
        
        assert len(result) == 3
        assert result[0] == {"selector": "div.content", "label": "div.content", "fields": None}
        assert result[1] == {"selector": "h1.title", "label": "h1.title", "fields": None}
        assert result[2] == {"selector": "p.text", "label": "p.text", "fields": None}
    
    def test_normalize_dict_entries(self):
        """Test normalizing list of dict entries"""
        selectors = [
            {"selector": "h1", "label": "title"},
            {"selector": "p", "fields": ["text"]}
        ]
        result = _normalize_from_list(selectors)
        
        assert len(result) == 2
        assert result[0]["selector"] == "h1"
        assert result[0]["label"] == "title"
        assert result[1]["selector"] == "p"
        assert result[1]["fields"] == ["text"]
    
    def test_normalize_empty_list(self):
        """Test normalizing empty list"""
        result = _normalize_from_list([])
        assert result == []
    
    def test_normalize_mixed_list(self):
        """Test normalizing mixed list of strings and dicts"""
        selectors = [
            "div.content",
            {"selector": "h1", "label": "title"},
            "p.text"
        ]
        result = _normalize_from_list(selectors)
        
        assert len(result) == 3
        assert result[0] == {"selector": "div.content", "label": "div.content", "fields": None}
        assert result[1]["label"] == "title"
        assert result[2]["selector"] == "p.text"


@pytest.mark.ci_safe
class TestNormalizeFromDict:
    """Test _normalize_from_dict function"""
    
    def test_normalize_simple_dict(self):
        """Test normalizing dict with simple selectors"""
        selectors = {
            "title": "h1",
            "content": "div.content"
        }
        result = _normalize_from_dict(selectors)
        
        assert len(result) == 2
        # Check if both entries exist (order may vary)
        labels = [r["label"] for r in result]
        assert "title" in labels
        assert "content" in labels
    
    def test_normalize_dict_with_fields(self):
        """Test normalizing dict with fields"""
        selectors = {
            "links": {"selector": "a", "fields": ["href", "text"]},
            "images": {"selector": "img", "fields": ["src"]}
        }
        result = _normalize_from_dict(selectors)
        
        assert len(result) == 2
        # Find the links entry
        links_entry = next(r for r in result if r["label"] == "links")
        assert links_entry["selector"] == "a"
        assert links_entry["fields"] == ["href", "text"]
    
    def test_normalize_empty_dict(self):
        """Test normalizing empty dict"""
        result = _normalize_from_dict({})
        assert result == []


@pytest.mark.ci_safe
class TestNormalizeExtractEntries:
    """Test _normalize_extract_entries function"""
    
    def test_normalize_with_selectors_list(self):
        """Test normalizing options with selectors list"""
        options = {
            "selectors": ["h1", "p.content"]
        }
        result = _normalize_extract_entries(options)
        
        assert len(result) == 2
        assert result[0]["selector"] == "h1"
        assert result[1]["selector"] == "p.content"
    
    def test_normalize_with_selectors_dict(self):
        """Test normalizing options with selectors dict"""
        options = {
            "selectors": {
                "title": "h1",
                "content": "div"
            }
        }
        result = _normalize_extract_entries(options)
        
        assert len(result) == 2
        labels = [r["label"] for r in result]
        assert "title" in labels
        assert "content" in labels
    
    def test_normalize_without_selectors(self):
        """Test normalizing options without selectors key"""
        options = {"timeout": 5000}
        result = _normalize_extract_entries(options)
        
        # Falls back to "h1" when no selectors provided
        assert len(result) == 1
        assert result[0]["selector"] == "h1"
    
    def test_normalize_with_none_selectors(self):
        """Test normalizing options with None selectors"""
        options = {"selectors": None}
        result = _normalize_extract_entries(options)
        
        # Falls back to "h1" when selectors is None
        assert len(result) == 1
        assert result[0]["selector"] == "h1"


@pytest.mark.ci_safe
class TestRegisterVideoArtifact:
    """Test _register_video_artifact function"""
    
    def test_register_with_valid_path(self):
        """Test registering video artifact with valid path"""
        mock_video_path = MagicMock(spec=Path)
        mock_video_path.exists.return_value = True
        
        mock_manager = MagicMock()
        mock_manager.register_video_file.return_value = mock_video_path
        
        with patch('src.modules.direct_browser_control.get_artifact_manager', return_value=mock_manager):
            _register_video_artifact(mock_video_path, attempted=True)
        
        mock_manager.register_video_file.assert_called_once_with(mock_video_path)
    
    def test_register_with_none_path_attempted(self):
        """Test registering video artifact with None path but attempted"""
        mock_manager = MagicMock()
        
        with patch('src.modules.direct_browser_control.get_artifact_manager', return_value=mock_manager), \
             patch('src.modules.direct_browser_control.logger') as mock_logger:
            _register_video_artifact(None, attempted=True)
        
        # Should log warning about video not found
        assert mock_logger.warning.called
        mock_manager.register_video_file.assert_not_called()
    
    def test_register_with_none_path_not_attempted(self):
        """Test registering video artifact with None path and not attempted"""
        mock_manager = MagicMock()
        
        with patch('src.modules.direct_browser_control.get_artifact_manager', return_value=mock_manager):
            _register_video_artifact(None, attempted=False)
        
        # Should return early without calling manager
        mock_manager.register_video_file.assert_not_called()


@pytest.mark.ci_safe
class TestCancelled:
    """Test _cancelled function"""
    
    def test_not_cancelled(self):
        """Test when timeout not cancelled"""
        timeout_manager = MagicMock(spec=TimeoutManager)
        timeout_manager.is_cancelled.return_value = False
        
        result = _cancelled(timeout_manager, "test_context")
        
        assert result is False
        timeout_manager.is_cancelled.assert_called_once()
    
    def test_cancelled(self):
        """Test when timeout is cancelled"""
        timeout_manager = MagicMock(spec=TimeoutManager)
        timeout_manager.is_cancelled.return_value = True
        
        with patch('src.modules.direct_browser_control.logger') as mock_logger:
            result = _cancelled(timeout_manager, "navigation")
        
        assert result is True
        timeout_manager.is_cancelled.assert_called_once()
        mock_logger.warning.assert_called_once()
        # Check that the context was passed to the warning
        assert "navigation" in str(mock_logger.warning.call_args)


@pytest.mark.ci_safe
class TestMaybeSlowMoIntegration:
    """Test _maybe_sleep_with_cancel integration"""
    
    @pytest.mark.asyncio
    async def test_sleep_not_cancelled(self):
        """Test sleep when not cancelled"""
        timeout_manager = MagicMock(spec=TimeoutManager)
        timeout_manager.is_cancelled.return_value = False
        
        # Patch asyncio.sleep at the source where it's used (direct_browser_control module)
        with patch('src.modules.direct_browser_control.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            from src.modules.direct_browser_control import _maybe_sleep_with_cancel
            result = await _maybe_sleep_with_cancel(timeout_manager, 100)
        
        assert result is False
        mock_sleep.assert_awaited_once_with(0.1)  # 100ms -> 0.1s
    
    @pytest.mark.asyncio
    async def test_sleep_cancelled(self):
        """Test sleep when cancelled"""
        timeout_manager = MagicMock(spec=TimeoutManager)
        timeout_manager.is_cancelled.return_value = True
        
        from src.modules.direct_browser_control import _maybe_sleep_with_cancel
        result = await _maybe_sleep_with_cancel(timeout_manager, 100)
        
        assert result is True
