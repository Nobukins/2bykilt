"""
GitScriptAutomator - Complete Git-Script Automation Solution
Integrates ProfileManager + BrowserLauncher for stable 2024+ browser automation
"""
import os
import sys
import logging
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from playwright.async_api import BrowserContext

from .profile_manager import ProfileManager, EdgeProfileManager, ChromeProfileManager
from .browser_launcher import BrowserLauncher, EdgeLauncher, ChromeLauncher
from .git_script_path import GitScriptPathValidator, validate_git_script_path, GitScriptPathNotFound, GitScriptPathDenied

logger = logging.getLogger(__name__)


class GitScriptAutomator:
    """
    Git-Script自動化のための統合クラス
    
    主な機能:
    - ProfileManager と BrowserLauncher の統合
    - 2024年5月以降の新作法への完全対応
    - セッション管理とクリーンアップ
    - エラーハンドリングと復旧
    """
    
    def __init__(self, browser_type: str, source_profile_dir: Optional[str] = None):
        """
        GitScriptAutomator を初期化
        
        Args:
            browser_type: 'chrome' または 'edge'
            source_profile_dir: 元のブラウザプロファイルディレクトリ（省略時はデフォルト）
        """
        self.browser_type = browser_type.lower()
        self.source_profile_dir = source_profile_dir
        self.current_selenium_profile = None
        
        # ProfileManager の初期化
        if source_profile_dir:
            self.profile_manager = ProfileManager(source_profile_dir)
        else:
            if self.browser_type == "edge":
                self.profile_manager = EdgeProfileManager()
            elif self.browser_type == "chrome":
                self.profile_manager = ChromeProfileManager()
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
        
        # BrowserLauncher の初期化
        self.browser_launcher = BrowserLauncher(self.browser_type)
        
        self.source_profile_dir = str(self.profile_manager.source_profile_dir)
        
        logger.info(f"🚀 GitScriptAutomator initialized for {self.browser_type}")
        logger.info(f"📁 Source profile: {self.source_profile_dir}")
    
    def validate_source_profile(self) -> bool:
        """ソースプロファイルの妥当性をチェック"""
        try:
            profile_info = self.profile_manager.get_profile_info()
            
            if not profile_info["exists"]:
                logger.error(f"❌ Source profile does not exist: {self.source_profile_dir}")
                return False
            
            if profile_info["is_locked"]:
                logger.warning(f"⚠️ Source profile is locked: {self.source_profile_dir}")
                # ロックされていても継続可能（警告のみ）
            
            essential_count = len(profile_info["essential_files_found"])
            missing_count = len(profile_info["missing_files"])
            
            logger.info(f"📊 Profile analysis: {essential_count} essential files found, {missing_count} missing")
            
            # 最低限のファイルがあれば継続可能
            if essential_count < 2:
                logger.error("❌ Insufficient essential files in source profile")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Source profile validation failed: {e}")
            return False
    
    def prepare_selenium_profile(self, workspace_dir: str) -> str:
        """
        SeleniumProfile を準備
        
        Args:
            workspace_dir: SeleniumProfileを作成する作業ディレクトリ
            
        Returns:
            作成されたSeleniumProfileディレクトリのパス
        """
        logger.info(f"🔧 Preparing SeleniumProfile in: {workspace_dir}")
        
        try:
            selenium_profile, copied_count = self.profile_manager.create_selenium_profile_with_stats(workspace_dir)
            self.current_selenium_profile = selenium_profile
            
            logger.info(f"✅ SeleniumProfile prepared: {selenium_profile}")
            logger.info(f"📋 Files copied: {copied_count}")
            
            return selenium_profile
            
        except Exception as e:
            logger.error(f"❌ Failed to prepare SeleniumProfile: {e}")
            raise
    
    async def launch_browser_with_profile(self, workspace_dir: str, headless: bool = False) -> BrowserContext:
        """
        プロファイル付きでブラウザを起動
        
        Args:
            workspace_dir: 作業ディレクトリ
            headless: ヘッドレスモードで起動するか
            
        Returns:
            BrowserContext インスタンス
        """
        logger.info(f"🚀 Launching {self.browser_type} with profile (headless: {headless})")
        
        # Chromium（Playwright内蔵）を使用する場合はプロファイルなしで起動
        if self.browser_launcher.is_using_builtin_chromium():
            logger.warning("⚠️ Using Playwright built-in Chromium - launching without profile to avoid API key warnings")
            return await self.browser_launcher.launch_chromium_without_profile()
        
        # SeleniumProfile の準備（Google Chrome/Edge用）
        if not self.current_selenium_profile:
            self.prepare_selenium_profile(workspace_dir)
        
        try:
            if headless:
                context = await self.browser_launcher.launch_headless_with_profile(self.current_selenium_profile)
            else:
                context = await self.browser_launcher.launch_with_profile(self.current_selenium_profile)
            
            logger.info("✅ Browser launched successfully")
            logger.info(f"📄 Initial pages: {len(context.pages)}")
            
            return context
            
        except Exception as e:
            logger.error(f"❌ Failed to launch browser with profile: {e}")
            raise
    
    @asynccontextmanager
    async def browser_context(self, workspace_dir: str, headless: bool = False):
        """
        ブラウザコンテキストのコンテキストマネージャー（新作法対応）
        
        Args:
            workspace_dir: 作業ディレクトリ
            headless: ヘッドレスモードで起動するか
            
        Yields:
            BrowserContext インスタンス
        """
        context = None
        playwright_instance = None
        try:
            context = await self.launch_browser_with_profile(workspace_dir, headless)
            playwright_instance = getattr(context, '_playwright_instance', None)
            yield context
        finally:
            if context:
                try:
                    await context.close()
                    logger.info("🔒 Browser context closed")
                except Exception as e:
                    logger.warning(f"⚠️ Error closing browser context: {e}")
            
            # Playwrightインスタンスもクリーンアップ
            if playwright_instance:
                try:
                    await playwright_instance.stop()
                    logger.info("🔒 Playwright instance stopped")
                except Exception as e:
                    logger.warning(f"⚠️ Error stopping playwright instance: {e}")
    
    async def execute_git_script_workflow(self, workspace_dir: str, script_path: str, command: str, params: Dict[str, str]) -> Dict[str, Any]:
        """
        完全なgit-scriptワークフローを実行（実際のスクリプト実行）
        
        Args:
            workspace_dir: 作業ディレクトリ
            script_path: 実行するスクリプトのパス
            command: 実行コマンドテンプレート
            params: パラメータ辞書
            headless: ヘッドレスモードで実行するか
            
        Returns:
            実行結果の辞書
        """
        result = {
            "success": False,
            "browser_type": self.browser_type,
            "workspace_dir": workspace_dir,
            "script_path": script_path,
            "command": command,
            "params": params,
            "error": None
        }
        
        try:
            logger.info(f"🏁 Starting git-script workflow for {self.browser_type}")
            logger.info(f"📄 Script: {script_path}")
            logger.info(f"📄 Command: {command}")
            logger.info(f"📄 Params: {params}")
            
            # Step 1: ソースプロファイルの検証
            if not self.validate_source_profile():
                raise ValueError("Source profile validation failed")
            
            # Step 2: SeleniumProfile の準備
            selenium_profile = self.prepare_selenium_profile(workspace_dir)
            result["selenium_profile"] = selenium_profile
            
            # Step 3: コマンドテンプレートの処理
            processed_command = command.replace('${script_path}', script_path)
            
            # パラメータの置換
            for param_name, param_value in params.items():
                placeholder = f"${{params.{param_name}}}"
                processed_command = processed_command.replace(placeholder, str(param_value))
            
            logger.info(f"🔧 Processed command: {processed_command}")
            
            # Step 4: スクリプトの実行（subprocessを使用）
            import shlex
            
            # コマンドを引数リストに分割
            command_parts = shlex.split(processed_command)

            # 先頭が 'python' の場合は現在のインタプリタに置き換え
            if command_parts and command_parts[0] == 'python':
                command_parts[0] = sys.executable or command_parts[0]
            
            # 作業ディレクトリを設定
            cwd = workspace_dir
            
            # 環境変数の設定
            env = os.environ.copy()
            env['PYTHONPATH'] = workspace_dir
            
            # 非同期でサブプロセスを実行
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                cwd=cwd,
                env=env,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # 出力の取得
            stdout, stderr = await process.communicate()
            
            # エンコーディングの処理
            def safe_decode(data):
                if not data:
                    return ""
                encodings = ['utf-8', 'cp932', 'shift_jis', 'latin1']
                for encoding in encodings:
                    try:
                        return data.decode(encoding)
                    except UnicodeDecodeError:
                        continue
                return data.decode('utf-8', errors='replace')
            
            stdout_text = safe_decode(stdout)
            stderr_text = safe_decode(stderr)
            
            result["exit_code"] = process.returncode
            result["stdout"] = stdout_text
            result["stderr"] = stderr_text
            
            # ログ出力
            logger.info("git_script: start")
            if stdout_text:
                logger.info(f"git_script stdout: {stdout_text}")
            if stderr_text:
                logger.error(f"git_script stderr: {stderr_text}")
            logger.info("git_script: end")
            
            # 成功判定
            if process.returncode == 0:
                result["success"] = True
                logger.info("🎉 Git-script workflow completed successfully")
            else:
                result["error"] = f"Script execution failed with exit code {process.returncode}"
                logger.error(f"❌ Git-script workflow failed: {result['error']}")
            
        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            logger.error(f"❌ Git-script workflow failed: {error_msg}")
            
        return result
    
    def cleanup_selenium_profile(self) -> bool:
        """現在のSeleniumProfileをクリーンアップ"""
        if not self.current_selenium_profile:
            logger.info("⏭️ No SeleniumProfile to cleanup")
            return True
        
        try:
            result = self.profile_manager.cleanup_selenium_profile(self.current_selenium_profile)
            if result:
                logger.info(f"🗑️ SeleniumProfile cleaned up: {self.current_selenium_profile}")
                self.current_selenium_profile = None
            else:
                logger.warning(f"⚠️ Failed to cleanup SeleniumProfile: {self.current_selenium_profile}")
            
            return result
            
        except Exception as e:
            logger.error(f"❌ Error during SeleniumProfile cleanup: {e}")
            return False
    
    def get_automation_info(self) -> Dict[str, Any]:
        """自動化システムの情報を取得"""
        return {
            "browser_type": self.browser_type,
            "source_profile_dir": self.source_profile_dir,
            "current_selenium_profile": self.current_selenium_profile,
            "profile_manager": self.profile_manager.get_profile_info(),
            "browser_launcher": self.browser_launcher.get_browser_info(),
        }
    
    async def test_automation_setup(self) -> Dict[str, Any]:
        """自動化セットアップのテスト実行"""
        import tempfile
        
        test_workspace = tempfile.mkdtemp()
        logger.info(f"🧪 Testing automation setup in: {test_workspace}")
        
        try:
            # テスト用のスクリプト情報
            test_script_path = "/test_script.py"
            test_command = "python ${script_path} --test"
            test_params = {"test": "value"}
            
            result = await self.execute_git_script_workflow(
                workspace_dir=test_workspace,
                script_path=test_script_path,
                command=test_command,
                params=test_params
            )
            
            return result
            
        finally:
            # テスト後のクリーンアップ
            self.cleanup_selenium_profile()
            try:
                import shutil
                shutil.rmtree(test_workspace, ignore_errors=True)
                logger.info(f"🗑️ Test workspace cleaned up: {test_workspace}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to cleanup test workspace: {e}")


class EdgeAutomator(GitScriptAutomator):
    """Edge専用の自動化クラス"""
    
    def __init__(self, source_profile_dir: Optional[str] = None):
        super().__init__("edge", source_profile_dir)


class ChromeAutomator(GitScriptAutomator):
    """Chrome専用の自動化クラス"""
    
    def __init__(self, source_profile_dir: Optional[str] = None):
        super().__init__("chrome", source_profile_dir)
