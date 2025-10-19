"""Unit tests for src/cli/main.py."""
import sys
from pathlib import Path
from unittest import mock

import pytest

from src.cli import main


@pytest.fixture
def mock_gradio_deps(monkeypatch):
    """Mock Gradio and UI dependencies to avoid import errors."""
    # Mock the bykilt module imports
    mock_bykilt = mock.MagicMock()
    mock_bykilt.theme_map = {"Ocean": mock.MagicMock(), "Soft": mock.MagicMock()}
    mock_bykilt.create_ui = mock.MagicMock(return_value=mock.MagicMock())
    
    sys.modules['bykilt'] = mock_bykilt
    
    # Mock FastAPI app creation
    mock_app_module = mock.MagicMock()
    mock_app_module.create_fastapi_app = mock.MagicMock(return_value=mock.MagicMock())
    mock_app_module.run_app = mock.MagicMock()
    sys.modules['src.api.app'] = mock_app_module
    
    # Mock default_config
    mock_config_module = mock.MagicMock()
    mock_config_module.default_config = mock.MagicMock(return_value={})
    sys.modules['src.utils.default_config_settings'] = mock_config_module
    
    yield mock_bykilt, mock_app_module


@pytest.mark.ci_safe
def test_ensure_asset_directories_creates_structure(tmp_path, monkeypatch):
    """Test that _ensure_asset_directories creates required folders."""
    monkeypatch.setattr('src.cli.main.get_assets_dir', lambda: tmp_path)
    
    main._ensure_asset_directories()
    
    assert (tmp_path / "css").exists()
    assert (tmp_path / "js").exists()
    assert (tmp_path / "fonts").exists()
    assert (tmp_path / "fonts" / "ui-sans-serif").exists()
    assert (tmp_path / "fonts" / "system-ui").exists()
    
    # Check font files are created
    assert (tmp_path / "fonts" / "ui-sans-serif" / "ui-sans-serif-Regular.woff2").exists()
    assert (tmp_path / "fonts" / "ui-sans-serif" / "ui-sans-serif-Bold.woff2").exists()
    assert (tmp_path / "fonts" / "system-ui" / "system-ui-Regular.woff2").exists()
    assert (tmp_path / "fonts" / "system-ui" / "system-ui-Bold.woff2").exists()


@pytest.mark.ci_safe
def test_ensure_asset_directories_idempotent(tmp_path, monkeypatch):
    """Test that _ensure_asset_directories can be called multiple times safely."""
    monkeypatch.setattr('src.cli.main.get_assets_dir', lambda: tmp_path)
    
    main._ensure_asset_directories()
    main._ensure_asset_directories()  # Should not raise
    
    assert (tmp_path / "css").exists()


@pytest.mark.ci_safe
def test_main_preview_llms_exits_successfully(monkeypatch, mock_gradio_deps, capsys):
    """Test --preview-llms flag exits without launching UI."""
    monkeypatch.setattr('sys.argv', ['main.py', '--preview-llms', 'https://example.com/llms.txt'])
    
    mock_discover = mock.MagicMock(return_value=("", "✅ Discovery successful", '{"actions": []}'))
    mock_preview = mock.MagicMock(return_value="Preview result")
    monkeypatch.setattr('src.cli.main.discover_and_preview_llmstxt', mock_discover)
    monkeypatch.setattr('src.cli.main.preview_merge_llmstxt', mock_preview)
    
    # Mock metrics and timeout manager initialization
    mock_initialize_metrics = mock.MagicMock()
    monkeypatch.setattr('src.metrics.initialize_metrics', mock_initialize_metrics, raising=False)
    mock_get_timeout_manager = mock.MagicMock()
    monkeypatch.setattr('src.utils.timeout_manager.get_timeout_manager', mock_get_timeout_manager, raising=False)
    monkeypatch.setattr('src.utils.timeout_manager.reset_timeout_manager', mock.MagicMock(), raising=False)
    
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    
    assert exc_info.value.code == 0
    mock_discover.assert_called_once()


@pytest.mark.ci_safe
def test_main_import_llms_success(monkeypatch, mock_gradio_deps, capsys):
    """Test --import-llms flag with successful import."""
    monkeypatch.setattr('sys.argv', ['main.py', '--import-llms', 'https://example.com/llms.txt'])
    
    actions_json = '[{"name": "test_action", "type": "browser_control"}]'
    mock_discover = mock.MagicMock(return_value=("", "✅ Discovery successful", actions_json))
    mock_preview = mock.MagicMock(return_value="Preview result")
    mock_import = mock.MagicMock(return_value="✅ Import completed!")
    
    monkeypatch.setattr('src.cli.main.discover_and_preview_llmstxt', mock_discover)
    monkeypatch.setattr('src.cli.main.preview_merge_llmstxt', mock_preview)
    monkeypatch.setattr('src.cli.main.import_llmstxt_actions', mock_import)
    
    # Mock metrics and timeout manager initialization
    mock_initialize_metrics = mock.MagicMock()
    monkeypatch.setattr('src.metrics.initialize_metrics', mock_initialize_metrics, raising=False)
    mock_get_timeout_manager = mock.MagicMock()
    monkeypatch.setattr('src.utils.timeout_manager.get_timeout_manager', mock_get_timeout_manager, raising=False)
    monkeypatch.setattr('src.utils.timeout_manager.reset_timeout_manager', mock.MagicMock(), raising=False)
    
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    
    assert exc_info.value.code == 0
    mock_import.assert_called_once()


@pytest.mark.ci_safe
def test_main_import_llms_fails_on_discovery_error(monkeypatch, mock_gradio_deps):
    """Test --import-llms aborts when discovery fails."""
    monkeypatch.setattr('sys.argv', ['main.py', '--import-llms', 'https://example.com/llms.txt'])
    
    mock_discover = mock.MagicMock(return_value=("", "❌ Discovery failed", ""))
    monkeypatch.setattr('src.cli.main.discover_and_preview_llmstxt', mock_discover)
    
    # Mock metrics and timeout manager initialization
    mock_initialize_metrics = mock.MagicMock()
    monkeypatch.setattr('src.metrics.initialize_metrics', mock_initialize_metrics, raising=False)
    mock_get_timeout_manager = mock.MagicMock()
    monkeypatch.setattr('src.utils.timeout_manager.get_timeout_manager', mock_get_timeout_manager, raising=False)
    monkeypatch.setattr('src.utils.timeout_manager.reset_timeout_manager', mock.MagicMock(), raising=False)
    
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    
    assert exc_info.value.code == 1


@pytest.mark.ci_safe
def test_main_import_llms_fails_on_security_validation(monkeypatch, mock_gradio_deps):
    """Test --import-llms aborts when security validation fails."""
    monkeypatch.setattr('sys.argv', ['main.py', '--import-llms', 'https://example.com/llms.txt'])
    
    actions_json = '[{"name": "test"}]'
    mock_discover = mock.MagicMock(return_value=("", "Security validation failed", actions_json))
    monkeypatch.setattr('src.cli.main.discover_and_preview_llmstxt', mock_discover)
    
    # Mock metrics and timeout manager initialization
    mock_initialize_metrics = mock.MagicMock()
    monkeypatch.setattr('src.metrics.initialize_metrics', mock_initialize_metrics, raising=False)
    mock_get_timeout_manager = mock.MagicMock()
    monkeypatch.setattr('src.utils.timeout_manager.get_timeout_manager', mock_get_timeout_manager, raising=False)
    monkeypatch.setattr('src.utils.timeout_manager.reset_timeout_manager', mock.MagicMock(), raising=False)
    
    with pytest.raises(SystemExit) as exc_info:
        main.main()
    
    assert exc_info.value.code == 1
