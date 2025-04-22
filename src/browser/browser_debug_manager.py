import asyncio
import os
import sys
import subprocess
import uuid
from datetime import datetime
from src.browser.session_manager import SessionManager
from src.browser.browser_config import BrowserConfig
from src.utils.logger import Logger
from src.utils.diagnostics import BrowserDiagnostics

logger = Logger.setup("browser_debug_manager")

browser_sessions = {}
browser_config = BrowserConfig()

class BrowserDebugManager:
    """ブラウザの初期化と管理のためのクラス"""
    
    def __init__(self):
        """ブラウザマネージャの初期化"""
        self.chrome_process = None
        self.global_browser = None
        self.global_playwright = None
        self.global_context = None
        self.global_page = None
        
        # psutilの利用可能性チェック
        self.have_psutil = False
        try:
            import psutil
            self.have_psutil = True
            self.psutil = psutil
        except ImportError:
            pass
        
        self.session_manager = SessionManager()
    
    async def initialize_browser(self, use_own_browser=False, headless=False, browser_type=None):
        """Initialize or reuse a browser instance with support for Chrome and Edge."""
        settings = browser_config.get_browser_settings(browser_type)
        browser_path = settings["path"]
        user_data_dir = settings["user_data"]
        debugging_port = settings["debugging_port"]

        if use_own_browser:
            cmd_args = [
                browser_path,
                f"--remote-debugging-port={debugging_port}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            if user_data_dir:
                cmd_args.append(f"--user-data-dir={user_data_dir}")
            chrome_process = subprocess.Popen(cmd_args)
            await asyncio.sleep(3)
            try:
                browser = await self.playwright.chromium.connect_over_cdp(
                    endpoint_url=f'http://localhost:{debugging_port}'
                )
                self.global_browser = browser
                return {"browser": browser, "status": "success"}
            except Exception as e:
                logger.error(f"Failed to connect to browser: {e}")
        else:
            browser = await self.playwright.chromium.launch(headless=headless)
            self.global_browser = browser
            return {"browser": browser, "status": "success"}

    @Logger.log_async_method_calls(logger)
    async def initialize_custom_browser(self, use_own_browser=False, headless=False, tab_selection_strategy="new_tab"):
        """カスタムプロファイル付きでブラウザインスタンスを初期化"""
        # 完全なブラウザ設定診断を実行
        from src.browser.browser_diagnostic import BrowserDiagnostic
        debug_file = BrowserDiagnostic.capture_browser_state("browser_init_debug")
        
        # BrowserConfigの参照関係とインスタンスIDを出力
        global browser_config
        logger.info(f"BrowserConfig instance ID: {id(browser_config)}")
        
        # 現在設定されているブラウザの確認
        current_browser = browser_config.config.get("current_browser", "chrome")
        logger.info(f"Current browser in config: {current_browser}")
        
        # ブラウザ設定の詳細ログ
        browser_settings = browser_config.get_browser_settings()
        logger.info(f"🔍 DEBUG: ブラウザ初期化開始 - 設定されたブラウザタイプ: {current_browser}")
        logger.info(f"🔍 DEBUG: BrowserConfig直接チェック: {browser_settings}")
        
        # すでにブラウザインスタンスが存在する場合はそれを返す
        if self.global_browser is not None:
            logger.info(f"✅ 既存のブラウザインスタンスを再利用します: {self.browser_type}")
            return {"browser": self.global_browser, "playwright": self.global_playwright, "status": "success"}
        
        try:
            # Playwrightインスタンスを先に初期化
            from playwright.async_api import async_playwright
            
            playwright = await async_playwright().start()
            self.global_playwright = playwright
            
            if use_own_browser:
                # ブラウザタイプに応じた設定
                if current_browser == "edge":
                    browser_path = browser_settings.get("path")
                    browser_user_data = browser_settings.get("user_data")
                    browser_debug_port = browser_settings.get("debugging_port", 9223)
                    logger.info(f"🔍 use_own_browser が有効です。Edge を探します...")
                    logger.info(f"📁 ユーザーデータディレクトリ: {browser_user_data}")
                    logger.info(f"🚀 Edge を起動します: {browser_path}")
                    logger.info(f"🔌 デバッグポート: {browser_debug_port}")
                    
                    # Edge接続テスト
                    import requests
                    try:
                        response = requests.get(f"http://localhost:{browser_debug_port}/json/version", timeout=5)
                        logger.info(f"✅ Edgeデバッグエンドポイント接続成功: {response.status_code}")
                    except Exception as e:
                        logger.warning(f"⚠️ デバッグエンドポイントへの接続確認に失敗: {e}")
                        
                        # Edgeが実行中でない場合は起動を試みる
                        if browser_path:
                            import subprocess
                            cmd = [
                                browser_path,
                                f"--remote-debugging-port={browser_debug_port}",
                                "--no-first-run",
                                "--no-default-browser-check"
                            ]
                            if browser_user_data:
                                cmd.append(f"--user-data-dir={browser_user_data}")
                            
                            logger.info(f"🚀 Edge起動コマンド: {' '.join(cmd)}")
                            subprocess.Popen(cmd)
                            # 接続のために少し待機
                            import asyncio
                            await asyncio.sleep(3)
                    
                    try:
                        # Playwrightインスタンスが正しく初期化されているか確認
                        if self.global_playwright is None:
                            logger.error("⚠️ Playwrightインスタンスが初期化されていません")
                            from playwright.async_api import async_playwright
                            self.global_playwright = await async_playwright().start()
                            logger.info("✅ Playwrightインスタンスを再初期化しました")
                        
                        # EdgeにはPlaywrightのchromiumドライバーを使用
                        if hasattr(self.global_playwright, 'chromium'):
                            browser = await self.global_playwright.chromium.connect_over_cdp(f"http://localhost:{browser_debug_port}")
                            self.global_browser = browser
                            self.browser_type = "edge"
                            logger.info("✅ 起動したEdgeインスタンスに接続しました")
                            return {"browser": browser, "playwright": self.global_playwright, "status": "success"}
                        else:
                            logger.error("⚠️ Playwrightインスタンスにchromiumドライバーが見つかりません")
                            return {"status": "error", "message": "Playwrightインスタンスにchromiumドライバーが見つかりません"}
                    except Exception as e:
                        logger.error(f"⚠️ Edge への接続に失敗しました: {e}")
                        # 詳細な診断を実行
                        diagnostic_file = BrowserDiagnostic.capture_browser_state(f"startup_issue_edge")
                        logger.error(f"ブラウザ起動診断情報: {diagnostic_file}")
                        return {"status": "error", "message": f"Edgeの初期化に失敗しました: {e}"}
                else:
                    # Chrome用の設定
                    browser_path = browser_settings.get("path")
                    browser_user_data = browser_settings.get("user_data")
                    browser_debug_port = browser_settings.get("debugging_port", 9222)
                    logger.info(f"🔍 use_own_browser が有効です。Chrome を探します...")
                    logger.info(f"📁 ユーザーデータディレクトリ: {browser_user_data}")
                    logger.info(f"🚀 Chrome を起動します: {browser_path}")
                    logger.info(f"🔌 デバッグポート: {browser_debug_port}")
                    
                    # Chrome接続テスト
                    import requests
                    try:
                        response = requests.get(f"http://localhost:{browser_debug_port}/json/version", timeout=5)
                        logger.info(f"✅ Chromeデバッグエンドポイント接続成功: {response.status_code}")
                    except Exception as e:
                        logger.warning(f"⚠️ デバッグエンドポイントへの接続確認に失敗: {e}")
                        
                        # Chromeが実行中でない場合は起動を試みる
                        if browser_path:
                            import subprocess
                            cmd = [
                                browser_path,
                                f"--remote-debugging-port={browser_debug_port}",
                                "--no-first-run",
                                "--no-default-browser-check"
                            ]
                            if browser_user_data:
                                cmd.append(f"--user-data-dir={browser_user_data}")
                            
                            logger.info(f"🚀 Chrome起動コマンド: {' '.join(cmd)}")
                            subprocess.Popen(cmd)
                            # 接続のために少し待機
                            import asyncio
                            await asyncio.sleep(3)
                    
                    try:
                        # ChromeにはPlaywrightのchromiumドライバーを使用
                        browser = await self.global_playwright.chromium.connect_over_cdp(f"http://localhost:{browser_debug_port}")
                        self.global_browser = browser
                        self.browser_type = "chrome"
                        logger.info("✅ 起動したChromeインスタンスに接続しました")
                        return {"browser": browser, "playwright": self.global_playwright, "status": "success"}
                    except Exception as e:
                        logger.error(f"⚠️ Chrome への接続に失敗しました: {e}")
                        # 詳細な診断を実行
                        diagnostic_file = BrowserDiagnostic.capture_browser_state(f"startup_issue_chrome")
                        logger.error(f"ブラウザ起動診断情報: {diagnostic_file}")
                        return {"status": "error", "message": f"Chromeの初期化に失敗しました: {e}"}
                    
            else:
                # Playwright管理ブラウザを使用 - ブラウザタイプに基づき選択
                if current_browser == "edge":
                    logger.info("✅ Playwright管理のEdgeブラウザを起動します")
                    browser = await self.global_playwright.chromium.launch(
                        headless=headless,
                        executable_path=browser_settings.get("path")
                    )
                else:
                    logger.info("✅ Playwright管理のChromeブラウザを起動します")
                    browser = await self.global_playwright.chromium.launch(headless=headless)
                    
                self.global_browser = browser
                self.browser_type = current_browser
                logger.info(f"✅ Playwright管理{current_browser}ブラウザを起動しました")
                return {"browser": browser, "playwright": playwright, "status": "success"}
                
        except Exception as e:
            logger.error(f"⚠️ ブラウザセッションの初期化中にエラーが発生しました: {e}")
            import traceback
            logger.error(f"スタックトレース: {traceback.format_exc()}")
            
            # 詳細な診断情報を保存
            diagnostic_file = BrowserDiagnostic.capture_browser_state(f"browser_init_error")
            logger.error(f"詳細診断情報: {diagnostic_file}")
            
            return {"status": "error", "message": f"ブラウザセッションの初期化中にエラーが発生しました: {e}"}

    async def initialize_with_session(self, session_id=None, use_own_browser=False, headless=False):
        """ブラウザセッションを初期化"""
        try:
            # グローバル設定を使用
            global browser_config
            direct_browser_type = browser_config.config.get("current_browser", "chrome")
            settings_browser_type = browser_config.get_browser_settings()["browser_type"]
            
            # 設定の不一致を検出
            if direct_browser_type != settings_browser_type:
                logger.error(f"⚠️ ブラウザ設定の不一致を検出: config={direct_browser_type}, settings={settings_browser_type}")
                # 不一致を解決
                browser_config.config["current_browser"] = settings_browser_type
                logger.info(f"✅ ブラウザ設定を修正: {settings_browser_type}")
            
            if use_own_browser:
                browser_settings = browser_config.get_browser_settings()
                port = browser_settings["debugging_port"]
                browser_path = browser_settings["path"]
                user_data_dir = browser_settings["user_data"]
                browser_name = "Edge" if settings_browser_type == "edge" else "Chrome"
                
                logger.info(f"🔍 use_own_browser が有効です。{browser_name} を探します...")
                logger.info(f"🚀 {browser_name} を起動します: {browser_path}")
                logger.info(f"📁 ユーザーデータディレクトリ: {user_data_dir}")
                logger.info(f"🔌 デバッグポート: {port}")
                
                cmd_args = [
                    browser_path,
                    f"--remote-debugging-port={port}",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
                if user_data_dir:
                    cmd_args.append(f"--user-data-dir={user_data_dir}")
                
                self.chrome_process = subprocess.Popen(cmd_args)
                await asyncio.sleep(3)
                
                try:
                    endpoint_url = f'http://localhost:{port}'
                    browser = await self.global_playwright.chromium.connect_over_cdp(endpoint_url=endpoint_url)
                    self.global_browser = browser
                    logger.info(f"✅ {browser_name} に接続しました (ポート {port})")
                    return {"browser": browser, "status": "success"}
                except Exception as e:
                    logger.error(f"⚠️ {browser_name} への接続に失敗しました: {e}")
                    return {"status": "error", "message": f"{browser_name} への接続に失敗しました: {e}"}
            else:
                # Playwright管理ブラウザを使用
                browser = await self.global_playwright.chromium.launch(headless=headless)
                self.global_browser = browser
                logger.info("✅ Playwright管理ブラウザを起動しました")
                return {"browser": browser, "status": "success"}
        except Exception as e:
            logger.error(f"⚠️ ブラウザセッションの初期化中にエラーが発生しました: {e}")
            return {"status": "error", "message": f"ブラウザセッションの初期化中にエラーが発生しました: {e}"}

    async def cleanup_resources(self, session_id=None, maintain_session=False):
        """リソースのクリーンアップ"""
        if not maintain_session:
            if self._global_browser:
                try:
                    await self._global_browser.close()
                    self._global_browser = None
                    
                    # セッションを削除
                    if session_id:
                        self.session_manager.remove_session(session_id)
                except Exception as e:
                    logger.error(f"ブラウザクリーンアップエラー: {e}")
        else:
            # セッションを維持する場合は最小限のクリーンアップのみ
            pass
    
    def _get_browser_info(self, browser):
        """ブラウザから識別情報を抽出"""
        try:
            import datetime
            return {
                "browser_id": str(id(browser)),
                "timestamp": datetime.datetime.now().isoformat(),
            }
        except Exception as e:
            logger.error(f"ブラウザ情報取得エラー: {e}")
            return {"error": str(e)}
    
    async def cleanup_resources(self, session_id=None, maintain_session=False):
        """
        Clean up browser resources.
        
        Args:
            session_id: Optional session ID to close.
            maintain_session: Whether to keep the session open.
        """
        if not maintain_session and session_id:
            # Close the session
            if session_id in browser_sessions:
                del browser_sessions[session_id]
            await self.browser.close()
        elif not maintain_session:
            # Close the browser only
            await self.browser.close()
        if self.global_browser:
            print("🧹 ブラウザインスタンスをクリーンアップしています...")
            try:
                # 明示的に接続を閉じないでリソースのみ解放
                # これによりChromeウィンドウは開いたままになる
                await self.global_playwright.stop()
            except Exception as e:
                print(f"クリーンアップ中にエラーが発生しました: {e}")
            
            self.global_browser = None
            self.global_playwright = None
            self.global_context = None
            self.global_page = None

    async def get_active_tab(self, browser):
        """
        Attempt to identify the currently active tab in Chrome using CDP.
        
        Args:
            browser: The browser instance.
        
        Returns:
            tuple: (page, is_new) where `page` is the active tab and `is_new` indicates if a new tab was created.
        """
        # Get the first context or create one
        context = browser.contexts[0] if browser.contexts else await browser.new_context()
        all_pages = context.pages

        if not all_pages:
            # No pages available, create a new one
            page = await context.new_page()
            return page, True

        try:
            # Use CDP to detect the active tab
            cdp_client = await browser.new_cdp_session(all_pages[0])
            targets = await cdp_client.send("Target.getTargets")

            # Look for attached targets of type "page"
            attached_tabs = [t for t in targets.get('targetInfos', []) 
                             if t.get('type') == 'page' and t.get('attached')]

            if attached_tabs:
                # Use the most recently active tab
                active_tab_id = attached_tabs[-1].get('targetId')
                for page in all_pages:
                    if hasattr(page, '_target_id') and page._target_id == active_tab_id:
                        return page, False
        except Exception as e:
            print(f"Active tab detection via CDP failed: {e}")

        # Fallback: Use the last tab as the active tab
        return all_pages[-1], False

    async def get_or_create_tab(self, tab_selection="active_tab"):
        """
        タブ選択戦略に基づいてタブを取得または作成します
        
        Args:
            tab_selection: タブの選択戦略：
                - "new_tab": 新しいタブを作成
                - "active_tab": 現在表示されているタブを使用
                - "last_tab": コンテキスト内の最後のタブを使用
        
        Returns:
            tuple: (context, page, is_new)
        """
        if not self.global_browser:
            raise ValueError("Browser must be initialized before creating or selecting tabs")

        context = self.global_browser.contexts[0] if self.global_browser.contexts else await self.global_browser.new_context()
        
        # 新しいタブを作成するケース
        if tab_selection == "new_tab" or not context.pages:
            print("✅ 新しいタブを作成します")
            print(f"🔍 タブ選択戦略: {tab_selection}")
            page = await context.new_page()
            return context, page, True
        
        # アクティブなタブを使用するケース
        elif tab_selection == "active_tab" and context.pages:
            try:
                # CDPでアクティブなタブを取得（可能な場合）
                if hasattr(self, 'cdp_session') and self.cdp_session:
                    targets = await self.cdp_session.send('Target.getTargets')
                    active_targets = [t for t in targets.get('targetInfos', []) if t.get('type') == 'page' and t.get('attached')]
                    if active_targets:
                        active_target_id = active_targets[0].get('targetId')
                        # アクティブなターゲットに対応するページを探す
                        for existing_page in context.pages:
                            if hasattr(existing_page, '_target_id') and existing_page._target_id == active_target_id:
                                print("✅ アクティブなタブを使用します")
                                print(f"🔍 タブ選択戦略: {tab_selection}")
                                return context, existing_page, False
                
                # フォールバック: 最初のページを使用
                if context.pages:
                    print("✅ 最初のタブを使用します (アクティブタブを特定できませんでした)")
                    print(f"🔍 タブ選択戦略: {tab_selection}")
                    return context, context.pages[0], False
                    
            except Exception as e:
                print(f"⚠️ アクティブタブの選択中にエラーが発生しました: {e}")
                print("✅ 新しいタブにフォールバックします")
            
            # エラーまたはアクティブなタブが見つからない場合、新しいタブを作成
            page = await context.new_page()
            return context, page, True
            
        # 最後のタブを使用するケース
        elif tab_selection == "last_tab" and context.pages:
            print("✅ 最後のタブを使用します")
            print(f"🔍 タブ選択戦略: {tab_selection}")
            return context, context.pages[-1], False
        
        # デフォルトケース - 新しいタブを作成
        print("✅ 新しいタブを作成します")
        print(f"🔍 タブ選択戦略: {tab_selection}")
        page = await context.new_page()
        return context, page, True

    async def highlight_automated_tab(self, page):
        """
        Add a visual indicator to the tab being automated.
        
        Args:
            page: The page to highlight.
        """
        await page.evaluate("""() => {
            const overlay = document.createElement('div');
            overlay.id = 'automation-indicator';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;'+
                'background:rgba(76,175,80,0.3);padding:5px;text-align:center;'+
                'font-weight:bold;color:white;';
            overlay.textContent = '🤖 タブ自動操作中...';
            document.body.appendChild(overlay);
            
            // Remove after 3 seconds
            setTimeout(() => {
                if (overlay && overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                }
            }, 3000);
        }""")
