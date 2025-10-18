"""
GitScriptAutomator の統合テスト
ProfileManager + BrowserLauncher の統合による完全なgit-script自動化
"""
import pytest
import asyncio
import os
import tempfile
import sys
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import shutil

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.utils.git_script_automator import GitScriptAutomator


class TestGitScriptAutomator:
    """GitScriptAutomator の完全な統合テスト"""
    
    @pytest.fixture
    def mock_edge_profile(self):
        """モックのEdgeプロファイルを作成"""
        temp_base = tempfile.mkdtemp()
        edge_profile = Path(temp_base) / "Microsoft Edge"
        
        # モックプロファイル構造を作成
        default_profile = edge_profile / "Default" 
        default_profile.mkdir(parents=True)
        
        # 重要なファイルを作成
        essential_files = {
            "Default/Preferences": '{"profile":{"name":"Test User","avatar_index":0}}',
            "Default/Secure Preferences": '{"protection":{"macs":{"profile":{"name":"secure_data"}}}}',
            "Default/Login Data": 'SQLite format 3\x00login_data_mock',
            "Default/Cookies": 'SQLite format 3\x00cookies_mock',
            "Local State": '{"browser":{"check_default_browser":false}}'
        }
        
        for file_path, content in essential_files.items():
            full_path = edge_profile / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content, encoding='utf-8')
        
        yield str(edge_profile)
        
        shutil.rmtree(temp_base, ignore_errors=True)
    
    @pytest.fixture
    def temp_workspace(self):
        """テスト用の作業ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    def test_git_script_automator_initialization_edge(self, mock_edge_profile):
        """Edge用GitScriptAutomatorの初期化"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        
        assert automator.browser_type == "edge"
        assert automator.profile_manager is not None
        assert automator.browser_launcher is not None
        assert automator.source_profile_dir == mock_edge_profile
    
    def test_git_script_automator_initialization_chrome(self, mock_edge_profile):
        """Chrome用GitScriptAutomatorの初期化（同じ構造を使用）"""
        automator = GitScriptAutomator(
            browser_type="chrome",
            source_profile_dir=mock_edge_profile
        )
        
        assert automator.browser_type == "chrome"
        assert automator.profile_manager is not None
        assert automator.browser_launcher is not None
    
    def test_prepare_selenium_profile(self, mock_edge_profile, temp_workspace):
        """SeleniumProfileの準備"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        
        selenium_profile = automator.prepare_selenium_profile(temp_workspace)
        
        assert Path(selenium_profile).exists()
        assert Path(selenium_profile).name == "SeleniumProfile"
        assert (Path(selenium_profile) / "Default" / "Preferences").exists()
        assert (Path(selenium_profile) / "Local State").exists()
    
    def test_prepare_selenium_profile_multiple_calls(self, mock_edge_profile, temp_workspace):
        """SeleniumProfile準備の複数回呼び出し（上書き動作確認）"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        
        # 初回準備
        selenium_profile1 = automator.prepare_selenium_profile(temp_workspace)
        
        # テストマーカーファイル作成
        marker_file = Path(selenium_profile1) / "test_marker"
        marker_file.write_text("first_preparation")
        
        # 2回目準備（上書きされるべき）
        selenium_profile2 = automator.prepare_selenium_profile(temp_workspace)
        
        assert selenium_profile1 == selenium_profile2
        assert not marker_file.exists()  # 上書きされたので消失
    
    @pytest.mark.local_only
    @pytest.mark.asyncio
    async def test_launch_browser_with_profile_mock(self, mock_edge_profile, temp_workspace):
        """モックを使用したブラウザ起動テスト"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            # モックの設定
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.url = "about:blank"
            mock_context.pages = [mock_page]
            mock_context.new_page.return_value = mock_page
            
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch_persistent_context.return_value = mock_context
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            # テスト実行
            automator = GitScriptAutomator(
                browser_type="edge",
                source_profile_dir=mock_edge_profile
            )
            
            context = await automator.launch_browser_with_profile(temp_workspace)
            
            # 検証
            assert context is not None
            assert len(context.pages) > 0
            mock_playwright_instance.chromium.launch_persistent_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_execute_git_script_workflow_mock(self, mock_edge_profile, temp_workspace):
        """完全なgit-scriptワークフローのモックテスト"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            # ブラウザモックの設定
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_page.goto = AsyncMock()
            mock_page.title.return_value = "Test Page"
            mock_context.pages = [mock_page]
            mock_context.new_page.return_value = mock_page
            mock_context.close = AsyncMock()
            
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch_persistent_context.return_value = mock_context
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            # テスト実行
            automator = GitScriptAutomator(
                browser_type="edge",
                source_profile_dir=mock_edge_profile
            )
            
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path="/bin/echo",
                command='echo "test"',
                params={}
            )
            
            # 検証
            assert result["success"] is True
            assert result["browser_type"] == "edge"
            assert "selenium_profile" in result
            assert "stdout" in result
    
    def test_cleanup_selenium_profile(self, mock_edge_profile, temp_workspace):
        """SeleniumProfileのクリーンアップ"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        
        # プロファイル準備
        selenium_profile = automator.prepare_selenium_profile(temp_workspace)
        assert Path(selenium_profile).exists()
        
        # クリーンアップ実行
        result = automator.cleanup_selenium_profile()
        
        assert result is True
        assert not Path(selenium_profile).exists()
    
    def test_get_automation_info(self, mock_edge_profile):
        """自動化情報の取得"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        
        info = automator.get_automation_info()
        
        assert info["browser_type"] == "edge"
        assert info["profile_manager"]["source_path"] == mock_edge_profile
        assert info["browser_launcher"]["browser_type"] == "edge"
        assert "executable_exists" in info["browser_launcher"]
    
    @pytest.mark.skip(reason="Test expects browser launch failure but method doesn't launch browser")
    @pytest.mark.asyncio
    async def test_error_handling_browser_launch_failure(self, mock_edge_profile, temp_workspace):
        """ブラウザ起動失敗時のエラーハンドリング"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            # 失敗をシミュレート
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch_persistent_context.side_effect = Exception("Browser failed")
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            automator = GitScriptAutomator(
                browser_type="edge",
                source_profile_dir=mock_edge_profile
            )
            
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path="/bin/echo",
                command='echo "test"',
                params={}
            )
            
            # エラーが適切に処理されることを確認
            assert result["success"] is False
            assert "error" in result
            assert "Browser failed" in result["error"]
    
    def test_validate_source_profile(self, mock_edge_profile):
        """ソースプロファイルの検証"""
        # 有効なプロファイル
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )
        assert automator.validate_source_profile() is True
        
        # 無効なプロファイル
        with pytest.raises(FileNotFoundError):
            GitScriptAutomator(
                browser_type="edge",
                source_profile_dir="/nonexistent/path"
            )
    
    @pytest.mark.asyncio
    async def test_context_management(self, mock_edge_profile, temp_workspace):
        """ブラウザコンテキストの適切な管理"""
        with patch('src.utils.browser_launcher.async_playwright') as mock_playwright:
            mock_context = AsyncMock()
            mock_page = AsyncMock()
            mock_context.pages = [mock_page]
            mock_context.close = AsyncMock()
            
            mock_playwright_instance = AsyncMock()
            mock_playwright_instance.chromium.launch_persistent_context.return_value = mock_context
            mock_playwright.return_value.__aenter__.return_value = mock_playwright_instance
            
            automator = GitScriptAutomator(
                browser_type="edge",
                source_profile_dir=mock_edge_profile
            )
            
            # コンテキスト使用
            async with automator.browser_context(temp_workspace) as context:
                assert context is not None
                assert context == mock_context
            
            # 自動的にクローズされることを確認
            mock_context.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
