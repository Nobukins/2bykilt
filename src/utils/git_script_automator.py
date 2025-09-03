"""
GitScriptAutomator - Complete Git-Script Automation Solution
Integrates ProfileManager + BrowserLauncher for stable 2024+ browser automation
"""
import os
import logging
import asyncio
from typing import Optional, Dict, Any
from pathlib import Path
from contextlib import asynccontextmanager
from playwright.async_api import BrowserContext

from .profile_manager import ProfileManager, EdgeProfileManager, ChromeProfileManager
from .browser_launcher import BrowserLauncher, EdgeLauncher, ChromeLauncher

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
                logger.error(f"❌ Insufficient essential files in source profile")
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
            
            logger.info(f"✅ Browser launched successfully")
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
    
    async def execute_git_script_workflow(self, workspace_dir: str, script_path: str, command: str, params: Dict[str, str], headless: bool = False) -> Dict[str, Any]:
        """
        完全なgit-scriptワークフローを実行
        
        Args:
            workspace_dir: 作業ディレクトリ
            script_path: 実行するスクリプトのパス
            command: 実行コマンドテンプレート
            params: スクリプトパラメータ
            headless: ヘッドレスモードで実行するか
            
        Returns:
            実行結果の辞書
        """
        result = {
            "success": False,
            "browser_type": self.browser_type,
            "workspace_dir": workspace_dir,
            "script_path": script_path,
            "selenium_profile": None,
            "error": None,
            "output": [],
            "exit_code": None
        }
        
        try:
            logger.info(f"🏁 Starting git-script workflow for {self.browser_type}")
            logger.info(f"git_script: start {script_path}")
            
            # Step 1: ソースプロファイルの検証
            if not self.validate_source_profile():
                raise ValueError("Source profile validation failed")
            
            # Step 2: SeleniumProfile の準備
            selenium_profile = self.prepare_selenium_profile(workspace_dir)
            result["selenium_profile"] = selenium_profile
            
            # Step 3: スクリプト実行
            # コマンドテンプレートの処理
            processed_command = command.replace('${script_path}', script_path)
            
            # パラメータ置換
            for param_name, param_value in params.items():
                placeholder = f"${{params.{param_name}}}"
                if placeholder in processed_command:
                    processed_command = processed_command.replace(placeholder, str(param_value))
            
            # コマンドを分割してリスト化
            import shlex
            try:
                command_parts = shlex.split(processed_command)
            except ValueError as e:
                logger.error(f"Failed to parse command: {e}")
                command_parts = processed_command.split()
            
            # Pythonの実行可能ファイルを現在のものに置換
            if command_parts and command_parts[0] == 'python':
                import sys
                command_parts[0] = sys.executable
            
            # 環境変数の設定
            env = os.environ.copy()
            env['BYKILT_BROWSER_TYPE'] = self.browser_type
            
            # ブラウザ設定の環境変数を設定
            try:
                from src.browser.browser_config import browser_config
                browser_settings = browser_config.get_browser_settings(self.browser_type)
                browser_path = browser_settings.get("path")
                if browser_path and os.path.exists(browser_path):
                    if self.browser_type == 'chrome':
                        env['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = browser_path
                    elif self.browser_type == 'edge':
                        env['PLAYWRIGHT_EDGE_EXECUTABLE_PATH'] = browser_path
                    logger.info(f"🎯 Browser executable path set to: {browser_path}")
            except Exception as e:
                logger.warning(f"⚠️ Could not load browser configuration: {e}")
            
            # headlessモードの設定
            if headless and '--headless' not in processed_command:
                command_parts.append('--headless')
            elif not headless and '--headed' not in processed_command:
                command_parts.append('--headed')
            
            logger.info(f"🚀 Executing command: {' '.join(command_parts)}")
            logger.info(f"📁 Working directory: {workspace_dir}")
            
            # スクリプト実行
            process = await asyncio.create_subprocess_exec(
                *command_parts,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
                cwd=workspace_dir
            )
            
            # 出力の収集
            output_lines = []
            
            async def read_stream(stream, is_error=False):
                while True:
                    line = await stream.readline()
                    if not line:
                        break
                    
                    # デコードとログ出力
                    try:
                        line_str = line.decode('utf-8').strip()
                    except UnicodeDecodeError:
                        line_str = line.decode('utf-8', errors='replace').strip()
                    
                    if line_str:
                        if is_error:
                            logger.error(f"SCRIPT ERROR: {line_str}")
                        else:
                            logger.info(f"SCRIPT: {line_str}")
                            output_lines.append(line_str)
            
            # 非同期で標準出力と標準エラーを読み取り
            stdout_task = asyncio.create_task(read_stream(process.stdout))
            stderr_task = asyncio.create_task(read_stream(process.stderr, is_error=True))
            
            # プロセスの完了を待つ
            await asyncio.gather(stdout_task, stderr_task)
            exit_code = await process.wait()
            
            result["output"] = output_lines
            result["exit_code"] = exit_code
            
            if exit_code == 0:
                result["success"] = True
                logger.info(f"✅ git_script: end {script_path} (exit_code: {exit_code})")
                logger.info(f"🎉 Git-script workflow completed successfully")
            else:
                result["success"] = False
                result["error"] = f"Script execution failed with exit code {exit_code}"
                logger.error(f"❌ git_script: end {script_path} (exit_code: {exit_code})")
            
        except Exception as e:
            error_msg = str(e)
            result["error"] = error_msg
            logger.error(f"❌ Git-script workflow failed: {error_msg}")
            logger.error(f"❌ git_script: end {script_path} (error: {error_msg})")
            
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
            # Create a simple test script
            test_script_path = os.path.join(test_workspace, "test_script.py")
            with open(test_script_path, 'w') as f:
                f.write('''#!/usr/bin/env python3
print("git_script: start test_script.py")
print("Test automation setup successful")
print("git_script: end test_script.py")
''')
            
            # Test with simple command
            test_command = "python ${script_path}"
            test_params = {}
            
            result = await self.execute_git_script_workflow(
                workspace_dir=test_workspace,
                script_path=test_script_path,
                command=test_command,
                params=test_params,
                headless=True  # テストはヘッドレスで実行
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
