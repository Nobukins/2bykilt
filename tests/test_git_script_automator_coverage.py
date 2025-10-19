"""
Additional unit tests for GitScriptAutomator to improve test coverage
"""
import pytest
import asyncio
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock, MagicMock
import subprocess
import shutil

# Add src to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)

from src.utils.git_script_automator import GitScriptAutomator, EdgeAutomator, ChromeAutomator


@pytest.mark.local_only
class TestGitScriptAutomatorCoverage:
    """Additional tests to improve coverage for GitScriptAutomator"""

    @pytest.fixture
    def temp_workspace(self):
        """テスト用の作業ディレクトリを作成"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

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

    def test_validate_source_profile_exception_handling(self, mock_edge_profile):
        """validate_source_profile の例外ハンドリングをテスト (lines 47-52)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # ProfileManager.get_profile_info() が例外を投げるようにモック
        with patch.object(automator.profile_manager, 'get_profile_info', side_effect=Exception("Test exception")):
            result = automator.validate_source_profile()
            assert result is False

    def test_prepare_selenium_profile_exception_handling(self, mock_edge_profile, temp_workspace):
        """prepare_selenium_profile の例外ハンドリングをテスト (lines 64-89)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # create_selenium_profile_with_stats が例外を投げるようにモック
        with patch.object(automator.profile_manager, 'create_selenium_profile_with_stats', side_effect=Exception("Profile creation failed")):
            with pytest.raises(Exception, match="Profile creation failed"):
                automator.prepare_selenium_profile(temp_workspace)

    @pytest.mark.asyncio
    async def test_launch_browser_with_profile_logging(self, mock_edge_profile, temp_workspace):
        """launch_browser_with_profile のログ出力をテスト (lines 112-114)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # ブラウザ起動をモック
        mock_context = AsyncMock()
        mock_context.pages = []

        with patch.object(automator.browser_launcher, 'launch_with_profile', return_value=mock_context):
            with patch.object(automator, 'prepare_selenium_profile', return_value="/mock/profile"):
                context = await automator.launch_browser_with_profile(temp_workspace, headless=False)
                assert context == mock_context

    @pytest.mark.asyncio
    async def test_browser_context_cleanup(self, mock_edge_profile, temp_workspace):
        """browser_context のクリーンアップをテスト (lines 127-151)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        mock_context = AsyncMock()
        mock_playwright = AsyncMock()

        with patch.object(automator, 'launch_browser_with_profile', return_value=mock_context):
            # コンテキストにplaywrightインスタンスを設定
            mock_context._playwright_instance = mock_playwright

            async with automator.browser_context(temp_workspace, headless=False):
                pass  # コンテキストマネージャーが正常に動作することを確認

            # close と stop が呼ばれたことを確認
            mock_context.close.assert_called_once()
            mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_browser_context_cleanup_with_exceptions(self, mock_edge_profile, temp_workspace):
        """browser_context の例外発生時のクリーンアップをテスト"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        mock_context = AsyncMock()
        mock_context.close.side_effect = Exception("Close failed")
        mock_playwright = AsyncMock()
        mock_playwright.stop.side_effect = Exception("Stop failed")

        with patch.object(automator, 'launch_browser_with_profile', return_value=mock_context):
            mock_context._playwright_instance = mock_playwright

            # 例外が発生してもクリーンアップが試行されることを確認
            async with automator.browser_context(temp_workspace, headless=False):
                pass

            # 例外が発生してもメソッドが呼ばれたことを確認
            mock_context.close.assert_called_once()
            mock_playwright.stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_git_script_workflow_error_handling(self, mock_edge_profile, temp_workspace):
        """execute_git_script_workflow のエラーハンドリングをテスト (lines 165-185)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # validate_source_profile が False を返すようにモック
        with patch.object(automator, 'validate_source_profile', return_value=False):
            result = await automator.execute_git_script_workflow(
                workspace_dir=temp_workspace,
                script_path="/test/script.py",
                command="python ${script_path}",
                params={}
            )

            assert result["success"] is False
            assert "Source profile validation failed" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_git_script_workflow_general_exception(self, mock_edge_profile, temp_workspace):
        """execute_git_script_workflow の一般的な例外ハンドリングをテスト"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # prepare_selenium_profile が例外を投げるようにモック
        with patch.object(automator, 'validate_source_profile', return_value=True):
            with patch.object(automator, 'prepare_selenium_profile', side_effect=Exception("Preparation failed")):
                result = await automator.execute_git_script_workflow(
                    workspace_dir=temp_workspace,
                    script_path="/test/script.py",
                    command="python ${script_path}",
                    params={}
                )

                assert result["success"] is False
                assert "Preparation failed" in result["error"]

    def test_cleanup_selenium_profile_no_profile(self):
        """cleanup_selenium_profile がプロファイルなしの場合のテスト (lines 269-271)"""
        automator = GitScriptAutomator(browser_type="edge")

        # current_selenium_profile が None の場合
        automator.current_selenium_profile = None
        result = automator.cleanup_selenium_profile()
        assert result is True

    def test_cleanup_selenium_profile_with_exception(self, mock_edge_profile):
        """cleanup_selenium_profile の例外ハンドリングをテスト"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # プロファイルを設定
        automator.current_selenium_profile = "/mock/profile"

        # cleanup_selenium_profile が例外を投げるようにモック
        with patch.object(automator.profile_manager, 'cleanup_selenium_profile', side_effect=Exception("Cleanup failed")):
            result = automator.cleanup_selenium_profile()
            assert result is False

    def test_get_automation_info(self, mock_edge_profile):
        """get_automation_info のテスト (lines 296-299)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # プロファイルを設定
        automator.current_selenium_profile = "/mock/profile"

        info = automator.get_automation_info()

        assert info["browser_type"] == "edge"
        assert "Microsoft Edge" in info["source_profile_dir"]
        assert info["current_selenium_profile"] == "/mock/profile"
        assert "profile_manager" in info
        assert "browser_launcher" in info

    @pytest.mark.asyncio
    async def test_test_automation_setup(self, mock_edge_profile):
        """test_automation_setup のテスト (lines 305-321, 325, 335-363)"""
        automator = GitScriptAutomator(
            browser_type="edge",
            source_profile_dir=mock_edge_profile
        )

        # execute_git_script_workflow をモック
        mock_result = {
            "success": True,
            "browser_type": "edge",
            "workspace_dir": "/mock/workspace",
            "script_path": "/test_script.py",
            "command": "python ${script_path} --test",
            "params": {"test": "value"},
            "error": None
        }

        with patch.object(automator, 'execute_git_script_workflow', return_value=mock_result):
            result = await automator.test_automation_setup()

            assert result["success"] is True
            assert result["browser_type"] == "edge"

    def test_edge_automator_initialization(self):
        """EdgeAutomator の初期化テスト (line 370)"""
        automator = EdgeAutomator()
        assert automator.browser_type == "edge"
        assert automator.source_profile_dir is not None

    def test_chrome_automator_initialization(self):
        """ChromeAutomator の初期化テスト (line 377)"""
        automator = ChromeAutomator()
        assert automator.browser_type == "chrome"
        assert automator.source_profile_dir is not None

    def test_unsupported_browser_type(self):
        """サポートされていないブラウザタイプのテスト"""
        with pytest.raises(ValueError, match="Unsupported browser type"):
            GitScriptAutomator(browser_type="firefox")
