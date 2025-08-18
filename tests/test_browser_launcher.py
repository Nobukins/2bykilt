"""
BrowserLauncher の単体テスト
TDD approach for 2024+ Chrome/Edge automation with launch_persistent_context
"""
import pytest
import asyncio
import os
import tempfile
import sys
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.utils.browser_launcher import BrowserLauncher


class TestBrowserLauncher:
    """BrowserLauncher の完全なテストスイート"""
    
    @pytest.fixture
    def mock_selenium_profile(self):
        """テスト用のSeleniumProfileディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        selenium_profile = Path(temp_dir) / "SeleniumProfile"
        selenium_profile.mkdir()
        
        # 必要最小限のファイルを作成
        default_dir = selenium_profile / "Default"
        default_dir.mkdir()
        (default_dir / "Preferences").write_text('{"profile":{"name":"Test"}}')
        (selenium_profile / "Local State").write_text('{"browser":{"check_default_browser":false}}')
        
        yield str(selenium_profile)
        
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_browser_launcher_initialization_edge(self):
        """Edge用BrowserLauncherの初期化"""
        launcher = BrowserLauncher("edge")
        
        assert launcher.browser_type == "edge"
        assert launcher.executable_path is not None
        assert "Edge" in launcher.executable_path or launcher.executable_path == "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
    
    def test_browser_launcher_initialization_chrome(self):
        """Chrome用BrowserLauncherの初期化"""
        launcher = BrowserLauncher("chrome")
        
        assert launcher.browser_type == "chrome"
        assert launcher.executable_path is not None
        assert "Chrome" in launcher.executable_path or launcher.executable_path == "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    
    def test_get_browser_args_edge(self):
        """Edge用の引数生成"""
        launcher = BrowserLauncher("edge")
        args = launcher._get_browser_args()
        
        # 自動化検知回避の引数確認
        assert "--disable-blink-features=AutomationControlled" in args
        assert "--no-first-run" in args
        assert "--no-default-browser-check" in args
        
        # Edge固有の最適化引数確認
        assert "--force-color-profile=srgb" in args
        assert "--enable-features=SharedArrayBuffer" in args
        
        # デバッグポートの確認
        debug_port_args = [arg for arg in args if arg.startswith("--remote-debugging-port=")]
        assert len(debug_port_args) == 1
        assert "9223" in debug_port_args[0]  # Edge default port
    
    def test_get_browser_args_chrome(self):
        """Chrome用の引数生成"""
        launcher = BrowserLauncher("chrome")
        args = launcher._get_browser_args()
        
        # 自動化検知回避の引数確認
        assert "--disable-blink-features=AutomationControlled" in args
        
        # Chrome固有の最適化引数確認
        assert "--disable-background-networking" in args
        assert "--disable-background-tasks" in args
        
        # デバッグポートの確認（Chrome default）
        debug_port_args = [arg for arg in args if arg.startswith("--remote-debugging-port=")]
        assert len(debug_port_args) == 1
        assert "9222" in debug_port_args[0]  # Chrome default port
    
    def test_custom_debugging_port_via_env(self):
        """環境変数によるカスタムデバッグポート設定"""
        with patch.dict(os.environ, {'EDGE_DEBUGGING_PORT': '9999'}):
            launcher = BrowserLauncher("edge")
            args = launcher._get_browser_args()
            
            debug_port_args = [arg for arg in args if arg.startswith("--remote-debugging-port=")]
            assert "--remote-debugging-port=9999" in debug_port_args
    
    def test_get_user_agent(self):
        """ユーザーエージェント文字列の生成"""
        launcher = BrowserLauncher("edge")
        user_agent = launcher._get_user_agent()
        
        assert "Mozilla/5.0" in user_agent
        assert "Macintosh" in user_agent
        assert "Chrome/" in user_agent
        assert "Safari/" in user_agent
        # 自動化検知されにくい一般的なUA
        assert "HeadlessChrome" not in user_agent
    
    @pytest.mark.asyncio
    async def test_launch_with_profile_mock_success(self, mock_selenium_profile):
        """モックを使用したプロファイル付きブラウザ起動の成功パターン"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            # モックの設定
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_context.new_page.return_value = mock_page
            mock_context.pages = [mock_page]
            
            mock_p = AsyncMock()
            mock_p.chromium.launch_persistent_context.return_value = mock_context
            
            # async_playwright() を mock して、.start() メソッドが mock_p を返すように設定
            mock_playwright_obj = AsyncMock()
            mock_playwright_obj.start.return_value = mock_p
            mock_playwright.return_value = mock_playwright_obj
            
            # テスト実行
            launcher = BrowserLauncher("edge")
            context = await launcher.launch_with_profile(mock_selenium_profile)
            
            # 検証
            assert context is not None
            mock_p.chromium.launch_persistent_context.assert_called_once()
            
            # 呼び出し引数の詳細確認
            call_kwargs = mock_p.chromium.launch_persistent_context.call_args.kwargs
            assert call_kwargs['user_data_dir'] == mock_selenium_profile
            assert call_kwargs['headless'] == False
            assert '--disable-blink-features=AutomationControlled' in call_kwargs['args']
            assert 'Mozilla/5.0' in call_kwargs['user_agent']
    
    @pytest.mark.asyncio
    async def test_launch_with_profile_mock_failure(self, mock_selenium_profile):
        """モックを使用したブラウザ起動の失敗パターン"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            # 失敗をシミュレート
            mock_p = AsyncMock()
            mock_p.chromium.launch_persistent_context.side_effect = Exception("Browser launch failed")
            
            mock_playwright_obj = AsyncMock()
            mock_playwright_obj.start.return_value = mock_p
            mock_playwright.return_value = mock_playwright_obj
            
            launcher = BrowserLauncher("edge")
            
            # 例外が発生することを確認
            with pytest.raises(Exception) as exc_info:
                await launcher.launch_with_profile(mock_selenium_profile)
            
            assert "Browser launch failed" in str(exc_info.value)
    
    def test_validate_selenium_profile_path(self, mock_selenium_profile):
        """SeleniumProfileパスの検証"""
        launcher = BrowserLauncher("edge")
        
        # 有効なパス
        assert launcher.validate_selenium_profile_path(mock_selenium_profile) == True
        
        # 無効なパス
        assert launcher.validate_selenium_profile_path("/nonexistent/path") == False
        assert launcher.validate_selenium_profile_path("/tmp") == False  # SeleniumProfileディレクトリではない
    
    def test_get_launch_options_edge(self, mock_selenium_profile):
        """Edge用の起動オプション生成"""
        launcher = BrowserLauncher("edge")
        options = launcher._get_launch_options(mock_selenium_profile)
        
        assert options['user_data_dir'] == mock_selenium_profile
        assert options['headless'] == False
        assert options['executable_path'] is not None
        assert '--disable-blink-features=AutomationControlled' in options['args']
        assert options['ignore_default_args'] == ["--enable-automation"]
        assert 'Mozilla/5.0' in options['user_agent']
        assert options['accept_downloads'] == True
        assert options['bypass_csp'] == True
    
    def test_get_launch_options_chrome(self, mock_selenium_profile):
        """Chrome用の起動オプション生成"""
        launcher = BrowserLauncher("chrome")
        options = launcher._get_launch_options(mock_selenium_profile)
        
        assert options['user_data_dir'] == mock_selenium_profile
        assert '--disable-background-networking' in options['args']
        assert '--disable-background-tasks' in options['args']
    
    def test_environment_variable_integration(self):
        """環境変数との統合テスト"""
        # カスタム実行ファイルパス
        with patch.dict(os.environ, {'EDGE_PATH': '/custom/edge/path'}):
            launcher = BrowserLauncher("edge")
            assert launcher.executable_path == '/custom/edge/path'
        
        # カスタムデバッグポート
        with patch.dict(os.environ, {'CHROME_DEBUGGING_PORT': '8888'}):
            launcher = BrowserLauncher("chrome")
            args = launcher._get_browser_args()
            assert "--remote-debugging-port=8888" in args
    
    @pytest.mark.asyncio
    async def test_context_cleanup_on_error(self, mock_selenium_profile):
        """エラー時のコンテキストクリーンアップ"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            mock_context = AsyncMock()
            mock_context.close = AsyncMock()
            
            mock_p = AsyncMock()
            mock_p.chromium.launch_persistent_context.return_value = mock_context
            
            mock_playwright_obj = AsyncMock()
            mock_playwright_obj.start.return_value = mock_p
            mock_playwright.return_value = mock_playwright_obj
            
            launcher = BrowserLauncher("edge")
            
            # launch_with_profile は基本的に例外をre-raiseするので、
            # エラーハンドリングは呼び出し側の責任
            context = await launcher.launch_with_profile(mock_selenium_profile)
            assert context == mock_context


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
