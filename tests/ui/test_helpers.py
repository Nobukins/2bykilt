import pytest

from src.ui import helpers


@pytest.fixture
def temp_llms_path(tmp_path, monkeypatch):
    target = tmp_path / "llms.txt"
    monkeypatch.setattr(helpers, "get_llms_txt_path", lambda: target)
    return target


def test_load_actions_config_missing_file_returns_empty_dict(temp_llms_path):
    assert helpers.load_actions_config() == {}


def test_load_actions_config_parses_valid_yaml(temp_llms_path):
    temp_llms_path.write_text("actions:\n  test: value\n", encoding="utf-8")
    config = helpers.load_actions_config()
    assert "actions" in config
    assert config["actions"]["test"] == "value"


def test_load_actions_config_handles_yaml_error(temp_llms_path, caplog):
    """Test that YAML parsing errors are logged and return empty dict."""
    temp_llms_path.write_text("invalid: yaml: content: [[[", encoding="utf-8")
    config = helpers.load_actions_config()
    assert config == {}
    assert any("YAML parsing error" in record.message for record in caplog.records)


def test_load_actions_config_handles_invalid_structure(temp_llms_path, caplog):
    """Test that invalid config structure is logged and returns empty dict."""
    temp_llms_path.write_text("not_actions: value\n", encoding="utf-8")
    config = helpers.load_actions_config()
    assert config == {}
    assert any("Invalid actions config structure" in record.message for record in caplog.records)


def test_load_llms_file_returns_contents(temp_llms_path):
    expected = "sample content"
    temp_llms_path.write_text(expected, encoding="utf-8")
    assert helpers.load_llms_file() == expected


def test_load_llms_file_returns_empty_on_missing_file(temp_llms_path):
    assert helpers.load_llms_file() == ""


def test_save_llms_file_writes_content(temp_llms_path):
    result = helpers.save_llms_file("new content")
    assert temp_llms_path.read_text(encoding="utf-8") == "new content"
    assert "保存しました" in result


def test_discover_and_preview_llmstxt_success(monkeypatch):
    """Test successful llms.txt discovery."""
    mock_discover = {
        'success': True,
        'browser_control': [{'name': 'action1', 'type': 'browser_control'}],
        'git_scripts': [],
        'raw_content': 'actions:\n  - name: action1'
    }
    
    mock_validation = type('ValidationResult', (), {
        'valid': True,
        'errors': [],
        'warnings': []
    })()
    
    monkeypatch.setattr('src.modules.llmstxt_discovery.discover_and_parse', lambda *args, **kwargs: mock_discover)
    monkeypatch.setattr('src.security.llmstxt_validator.validate_remote_llmstxt', lambda *args, **kwargs: mock_validation)
    
    _, status, actions_json = helpers.discover_and_preview_llmstxt('https://example.com/llms.txt')
    
    assert "✅ Discovery successful" in status
    assert "action1" in status
    assert actions_json


def test_discover_and_preview_llmstxt_discovery_failure(monkeypatch):
    """Test llms.txt discovery failure."""
    mock_discover = {
        'success': False,
        'error': 'Network error'
    }
    
    monkeypatch.setattr('src.modules.llmstxt_discovery.discover_and_parse', lambda *args, **kwargs: mock_discover)
    
    _, status, actions_json = helpers.discover_and_preview_llmstxt('https://example.com/llms.txt')
    
    assert "❌ Discovery failed" in status
    assert "Network error" in status
    assert not actions_json


def test_discover_and_preview_llmstxt_no_actions(monkeypatch):
    """Test discovery when no actions found."""
    mock_discover = {
        'success': True,
        'browser_control': [],
        'git_scripts': [],
        'raw_content': ''
    }
    
    monkeypatch.setattr('src.modules.llmstxt_discovery.discover_and_parse', lambda *args, **kwargs: mock_discover)
    
    _, status, actions_json = helpers.discover_and_preview_llmstxt('https://example.com/llms.txt')
    
    assert "No 2bykilt actions found" in status
    assert not actions_json


def test_discover_and_preview_llmstxt_security_validation_failure(monkeypatch):
    """Test security validation failure."""
    mock_discover = {
        'success': True,
        'browser_control': [{'name': 'bad_action', 'type': 'browser_control'}],
        'git_scripts': [],
        'raw_content': 'malicious content'
    }
    
    mock_validation = type('ValidationResult', (), {
        'valid': False,
        'errors': ['Malicious pattern detected'],
        'warnings': []
    })()
    
    monkeypatch.setattr('src.modules.llmstxt_discovery.discover_and_parse', lambda *args, **kwargs: mock_discover)
    monkeypatch.setattr('src.security.llmstxt_validator.validate_remote_llmstxt', lambda *args, **kwargs: mock_validation)
    
    _, status, _ = helpers.discover_and_preview_llmstxt('https://example.com/llms.txt')
    
    assert "⚠️ Security validation failed" in status
    assert "Malicious pattern detected" in status


def test_import_llmstxt_actions_success(monkeypatch, tmp_path):
    """Test successful action import."""
    actions_json = '[{"name": "test_action", "type": "browser_control"}]'
    
    mock_result = type('MergeResult', (), {
        'success': True,
        'error_message': None,
        'summary': lambda self: "1 action added"
    })()
    
    mock_merger = type('MockMerger', (), {
        'merge_actions': lambda self, *args, **kwargs: mock_result
    })
    
    monkeypatch.setattr('src.modules.llmstxt_merger.LlmsTxtMerger', lambda *args, **kwargs: mock_merger())
    monkeypatch.setattr(helpers, "get_llms_txt_path", lambda: tmp_path / "llms.txt")
    
    result = helpers.import_llmstxt_actions(actions_json)
    
    assert "✅ Import completed" in result
    assert "1 action added" in result


def test_import_llmstxt_actions_no_actions():
    """Test import with no actions."""
    result = helpers.import_llmstxt_actions('[]')
    assert "❌ No actions to import" in result


def test_import_llmstxt_actions_merge_failure(monkeypatch, tmp_path):
    """Test import when merge fails."""
    actions_json = '[{"name": "test"}]'
    
    mock_result = type('MergeResult', (), {
        'success': False,
        'error_message': 'File permission denied'
    })()
    
    mock_merger = type('MockMerger', (), {
        'merge_actions': lambda self, *args, **kwargs: mock_result
    })
    
    monkeypatch.setattr('src.modules.llmstxt_merger.LlmsTxtMerger', lambda *args, **kwargs: mock_merger())
    monkeypatch.setattr(helpers, "get_llms_txt_path", lambda: tmp_path / "llms.txt")
    
    result = helpers.import_llmstxt_actions(actions_json)
    
    assert "❌ Import failed" in result
    assert "File permission denied" in result


def test_preview_merge_llmstxt_success(monkeypatch, tmp_path):
    """Test successful merge preview."""
    actions_json = '[{"name": "new_action", "type": "browser_control"}]'
    
    mock_preview = type('PreviewResult', (), {
        'has_conflicts': False,
        'conflicts': [],
        'summary': lambda self: "1 new action"
    })()
    
    mock_merger = type('MockMerger', (), {
        'preview_merge': lambda self, *args: mock_preview
    })
    
    monkeypatch.setattr('src.modules.llmstxt_merger.LlmsTxtMerger', lambda *args, **kwargs: mock_merger())
    monkeypatch.setattr(helpers, "get_llms_txt_path", lambda: tmp_path / "llms.txt")
    
    result = helpers.preview_merge_llmstxt(actions_json)
    
    assert "1 new action" in result


def test_preview_merge_llmstxt_with_conflicts(monkeypatch, tmp_path):
    """Test merge preview with conflicts."""
    actions_json = '[{"name": "action", "type": "git_script"}]'
    
    mock_preview = type('PreviewResult', (), {
        'has_conflicts': True,
        'conflicts': [{'name': 'action', 'existing_type': 'browser_control', 'new_type': 'git_script', 'resolution': 'skip'}],
        'summary': lambda self: "Conflicts detected"
    })()
    
    mock_merger = type('MockMerger', (), {
        'preview_merge': lambda self, *args: mock_preview
    })
    
    monkeypatch.setattr('src.modules.llmstxt_merger.LlmsTxtMerger', lambda *args, **kwargs: mock_merger())
    monkeypatch.setattr(helpers, "get_llms_txt_path", lambda: tmp_path / "llms.txt")
    
    result = helpers.preview_merge_llmstxt(actions_json)
    
    assert "Conflicts detected" in result
    assert "Conflict Details" in result
    assert "action" in result


def test_preview_merge_llmstxt_no_actions():
    """Test preview with no actions."""
    result = helpers.preview_merge_llmstxt('[]')
    assert "ℹ️ No actions to preview" in result


def test_load_env_browser_settings_file_success(monkeypatch, tmp_path):
    """Test loading browser settings from .env file."""
    env_file = tmp_path / ".env"
    env_file.write_text("CHROME_PATH=/usr/bin/chrome\nCHROME_USER_DATA=/home/user/.chrome\n")
    
    # Mock the env file object
    mock_env_file = type('MockFile', (), {'name': str(env_file)})()
    
    monkeypatch.setenv('CHROME_PATH', '/usr/bin/chrome')
    monkeypatch.setenv('CHROME_USER_DATA', '/home/user/.chrome')
    
    path_msg, user_data_msg, status = helpers.load_env_browser_settings_file(mock_env_file)
    
    assert "/usr/bin/chrome" in path_msg
    assert "/home/user/.chrome" in user_data_msg
    assert "✅ Env settings loaded" in status


def test_load_env_browser_settings_file_no_file():
    """Test loading browser settings with no file."""
    _, _, status = helpers.load_env_browser_settings_file(None)
    assert "❌ No env file selected" in status