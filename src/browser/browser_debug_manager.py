import asyncio
import os
import shlex
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
        self.playwright = None  # 追加
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

    async def _ensure_playwright_initialized(self):
        """Playwrightインスタンスの確実な初期化"""
        if self.playwright is None or self.global_playwright is None:
            try:
                from playwright.async_api import async_playwright
                self.playwright = await async_playwright().start()
                self.global_playwright = self.playwright
                logger.debug("✅ Playwrightインスタンスを初期化しました")
            except Exception as e:
                logger.error(f"❌ Playwright初期化エラー: {e}")
                raise e
        return self.playwright

    def _detect_browser_path(self, browser_type):
        """クロスプラットフォーム対応のブラウザパス自動検出"""
        import platform
        
        system = platform.system()
        logger.debug(f"🔍 OS検出: {system}")
        
        if browser_type == "chrome":
            if system == "Darwin":  # macOS
                paths = [
                    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                ]
            elif system == "Windows":
                paths = [
                    "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                    "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe"
                ]
            else:  # Linux
                paths = [
                    "/usr/bin/google-chrome",
                    "/usr/bin/chromium-browser",
                    "/opt/google/chrome/chrome"
                ]
        elif browser_type == "edge":
            if system == "Darwin":  # macOS
                paths = [
                    "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
                ]
            elif system == "Windows":
                paths = [
                    "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
                    "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe"
                ]
            else:  # Linux
                paths = [
                    "/usr/bin/microsoft-edge",
                    "/opt/microsoft/msedge/msedge"
                ]
        else:
            return None
        
        # パスの存在確認
        for path in paths:
            if os.path.exists(path):
                logger.debug(f"✅ ブラウザパス検出成功: {path}")
                return path
        
        logger.debug(f"❌ {browser_type}のパスが見つかりませんでした")
        return None

    async def _check_browser_running(self, port):
        """指定ポートでブラウザが実行中かチェック"""
        max_checks = 10  # 最大10回チェック
        for i in range(max_checks):
            try:
                import requests
                response = requests.get(f"http://localhost:{port}/json/version", timeout=2)
                logger.debug(f"✅ ポート{port}でブラウザが実行中: {response.status_code}")
                return True
            except Exception:
                if i < max_checks - 1:
                    logger.debug(f"❌ ポート{port}でブラウザは実行されていません (チェック {i+1}/{max_checks})、1秒待機...")
                    await asyncio.sleep(1)
                else:
                    logger.debug(f"❌ ポート{port}でブラウザは実行されていません (最終チェック)")
        return False

    async def _check_existing_chrome_with_debug_port(self, user_data_dir, debugging_port):
        """既存のChromeプロセスがデバッグポートを使用しているかチェック"""
        try:
            import psutil
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower():
                        cmdline = proc.info['cmdline']
                        if cmdline and any(f'--remote-debugging-port={debugging_port}' in arg for arg in cmdline):
                            logger.info(f"✅ 既存のChromeプロセスがポート{debugging_port}を使用しています (PID: {proc.info['pid']})")
                            return True
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except ImportError:
            logger.debug("psutilが利用できないため、既存プロセスチェックをスキップ")
        except Exception as e:
            logger.debug(f"既存Chromeプロセスチェック中にエラー: {e}")
        return False

    async def _start_browser_process(self, browser_path, user_data_dir, debugging_port):
        """ブラウザプロセスを起動"""
        if not browser_path or not os.path.exists(browser_path):
            raise Exception(f"ブラウザパスが無効です: {browser_path}")
        
        cmd_args = [
            browser_path,
            f"--remote-debugging-port={debugging_port}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        if user_data_dir:
            cmd_args.append(f"--user-data-dir={user_data_dir}")
        
        logger.info(f"🚀 ブラウザプロセス起動: {shlex.join(cmd_args)}")
        
        try:
            self.chrome_process = subprocess.Popen(cmd_args)
            # 起動待機時間を増やして接続可能になるまで待つ
            await asyncio.sleep(5)  # 3秒から5秒に増やす
            logger.info("✅ ブラウザプロセス起動完了")
        except Exception as e:
            logger.error(f"❌ ブラウザプロセス起動失敗: {e}")
            raise e
    
    async def initialize_browser(self, use_own_browser=False, headless=False, browser_type=None):
        """Initialize or reuse a browser instance with improved fallback logic."""
        logger.debug(f"🔍 initialize_browser 呼び出し - use_own_browser: {use_own_browser}, headless: {headless}, browser_type: {browser_type}")
        
        # Playwrightを初期化（まだ初期化されていない場合）
        await self._ensure_playwright_initialized()
        
        # ブラウザタイプの決定（UIで選択されたブラウザを優先）
        if browser_type is None:
            browser_type = browser_config.get_current_browser()
            logger.info(f"🔍 UIで選択されたブラウザタイプを使用: {browser_type}")
        
        # 現在のブラウザが利用可能かチェック
        if not browser_config.validate_current_browser():
            logger.warning("⚠️ 現在のブラウザが利用できません。フォールバック処理が実行されました")
            browser_type = browser_config.get_current_browser()  # フォールバック後の値を取得
        
        settings = browser_config.get_browser_settings(browser_type)
        browser_path = settings["path"]
        user_data_dir = settings["user_data"]
        debugging_port = settings["debugging_port"]
        
        logger.info(f"🔍 ブラウザ初期化設定:")
        logger.info(f"  - browser_type: {browser_type}")
        logger.info(f"  - browser_path: {browser_path}")
        logger.info(f"  - user_data_dir: {user_data_dir}")
        logger.info(f"  - debugging_port: {debugging_port}")

        if use_own_browser:
            # 既存のCDP接続を再利用
            if self.global_browser:
                try:
                    # ブラウザがまだ有効かテスト
                    contexts = self.global_browser.contexts
                    logger.info(f"✅ 既存のCDPブラウザを再利用 (contexts: {len(contexts)})")
                    return {"browser": self.global_browser, "status": "success", "browser_type": browser_type, "is_cdp": True}
                except Exception as e:
                    logger.warning(f"⚠️ 既存ブラウザが無効: {e} - 再初期化します")
                    self.global_browser = None
            
            # 外部ブラウザプロセスに接続
            logger.info(f"🔗 外部{browser_type}プロセスに接続を試行")
            
            # 既存のデバッグポートをチェック（既に起動中の可能性）
            if await self._check_browser_running(debugging_port):
                logger.info(f"✅ ポート{debugging_port}で既に{browser_type}が実行中です - 既存プロセスに接続します")
            else:
                # 一時プロファイルを使用（個人プロファイルとの競合を回避）
                import tempfile
                actual_user_data_dir = tempfile.mkdtemp(prefix="chrome_debug_cdp_")
                logger.info(f"🔧 CDP用の一時user-data-dirを作成: {actual_user_data_dir}")
                
                # ブラウザプロセスを起動
                logger.info(f"🚀 {browser_type}プロセスを起動")
                await self._start_browser_process(browser_path, actual_user_data_dir, debugging_port)
                
                # プロセス起動後に接続可能になるまで待つ
                if not await self._check_browser_running(debugging_port):
                    logger.error(f"❌ ブラウザプロセス起動後もポート{debugging_port}が利用できません")
                    return {"status": "error", "message": f"{browser_type}プロセス起動失敗またはCDPポートが利用できません"}
            
            # CDP接続をリトライ (最大3回)
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔗 CDP接続試行 {attempt + 1}/{max_retries}")
                    browser = await self.playwright.chromium.connect_over_cdp(
                        endpoint_url=f'http://localhost:{debugging_port}'
                    )
                    self.global_browser = browser
                    logger.info(f"✅ {browser_type}プロセスへの接続成功")
                    return {"browser": browser, "status": "success", "browser_type": browser_type, "is_cdp": True}
                except Exception as e:
                    logger.warning(f"❌ CDP接続失敗 (試行 {attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        logger.info("⏳ 1秒待機して再試行...")
                        await asyncio.sleep(1)
                    else:
                        logger.error(f"❌ CDP接続が {max_retries} 回失敗しました")
                        return {"status": "error", "message": f"{browser_type}へのCDP接続に失敗: {e}"}
        else:
            # Playwright管理ブラウザを起動
            logger.info(f"� Playwright管理{browser_type}を起動")
            launch_options = {"headless": headless}
            
            # 指定されたブラウザパスを優先して使用
            if browser_path and os.path.exists(browser_path):
                launch_options["executable_path"] = browser_path
                logger.info(f"✅ 指定されたブラウザパスを使用: {browser_path}")
            else:
                # フォールバック: 自動検出を試行
                detected_path = self._detect_browser_path(browser_type)
                if detected_path:
                    launch_options["executable_path"] = detected_path
                    logger.info(f"✅ 自動検出されたブラウザパスを使用: {detected_path}")
                else:
                    logger.warning(f"⚠️ {browser_type}パスが見つかりません。デフォルトChromiumを使用")
            
            try:
                browser = await self.playwright.chromium.launch(**launch_options)
                self.global_browser = browser
                
                # 成功時にブラウザ情報をログ
                actual_path = launch_options.get("executable_path", "デフォルトChromium")
                logger.info(f"✅ ブラウザ起動成功: {actual_path}")
                
                return {"browser": browser, "status": "success", "browser_type": browser_type, "is_cdp": False, "playwright": self.playwright}
            except Exception as e:
                logger.error(f"❌ {browser_type}起動失敗: {e}")
                
                # 最終フォールバック: デフォルトChromium
                if "executable_path" in launch_options:
                    logger.info("🔄 デフォルトChromiumでのフォールバックを実行")
                    try:
                        del launch_options["executable_path"]
                        browser = await self.playwright.chromium.launch(**launch_options)
                        self.global_browser = browser
                        logger.info("✅ デフォルトChromiumでの起動成功")
                        return {"browser": browser, "status": "success", "browser_type": "chromium", "is_cdp": False, "playwright": self.playwright}
                    except Exception as fallback_e:
                        logger.error(f"❌ デフォルトChromiumでの起動も失敗: {fallback_e}")
                
                return {"status": "error", "message": f"ブラウザ起動失敗: {e}"}

    async def initialize_with_session(self, session_id=None, use_own_browser=False, headless=False):
        """ブラウザセッションを初期化 - メインエントリーポイント"""
        logger.debug(f"🔍 initialize_with_session 開始 - use_own_browser: {use_own_browser}, headless: {headless}")
        
        try:
            # ブラウザ初期化を呼び出す（新しい統一されたメソッド）
            result = await self.initialize_browser(
                use_own_browser=use_own_browser,
                headless=headless,
                browser_type=None  # UIで選択されたブラウザを自動使用
            )
            
            if result.get("status") == "success":
                # セッション情報を追加
                session_id = session_id or str(uuid.uuid4())
                result["session_id"] = session_id
                
                current_browser = result.get("browser_type", "unknown")
                logger.info(f"✅ ブラウザセッション初期化成功: {session_id} (ブラウザ: {current_browser})")
                return result
            else:
                logger.error(f"❌ ブラウザセッション初期化失敗: {result.get('message')}")
                return result
            
        except Exception as e:
            logger.error(f"⚠️ ブラウザセッション初期化中の例外: {e}")
            import traceback
            logger.debug(f"スタックトレース: {traceback.format_exc()}")
            return {"status": "error", "message": f"ブラウザセッション初期化中の例外: {e}"}
                
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

    async def get_or_create_tab(self, strategy="new_tab"):
        """
        Get or create a tab in the browser using the specified strategy.
        
        Args:
            strategy: Tab selection strategy ("new_tab", "active_tab", "last_tab", "reuse_tab")
        
        Returns:
            tuple: (context, page, is_new_tab)
        """
        logger.debug(f"🔍 get_or_create_tab strategy={strategy}")
        
        if not self.global_browser:
            raise RuntimeError("ブラウザが初期化されていません")
        
        # Get or create context
        contexts = self.global_browser.contexts
        if not contexts:
            logger.debug("新しいコンテキストを作成します")
            context = await self.global_browser.new_context()
        else:
            logger.debug(f"既存のコンテキストを使用します ({len(contexts)} 個）")
            context = contexts[0]
        
        # Get or create page based on strategy
        pages = context.pages
        
        if strategy == "new_tab":
            logger.debug("✅ 新しいタブを作成します")
            page = await context.new_page()
            is_new = True
        elif strategy == "reuse_tab" and pages:
            logger.debug(f"♻️ 既存タブを再利用します (total: {len(pages)})")
            page = pages[-1]  # 最後のタブを再利用
            is_new = False
        elif strategy == "active_tab" and pages:
            logger.debug(f"✅ アクティブなタブを使用します (total: {len(pages)})")
            page = pages[0]
            is_new = False
        elif strategy == "last_tab" and pages:
            logger.debug(f"✅ 最後のタブを使用します (total: {len(pages)})")
            page = pages[-1]
            is_new = False
        else:
            logger.debug("デフォルト: 新しいタブを作成")
            page = await context.new_page()
            is_new = True
        
        logger.debug(f"🔍 タブ選択戦略: {strategy}")
        return context, page, is_new

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

    async def cleanup_resources(self, session_id=None, maintain_session=False):
        """リソースのクリーンアップ"""
        if not maintain_session:
            logger.info("🧹 ブラウザリソースをクリーンアップします")
            try:
                if self.global_browser:
                    await self.global_browser.close()
                    self.global_browser = None
                    logger.debug("✅ ブラウザインスタンスをクローズしました")
                    
                if self.global_playwright:
                    await self.global_playwright.stop()
                    self.global_playwright = None
                    self.playwright = None
                    logger.debug("✅ Playwrightインスタンスを停止しました")
                    
                # Chrome外部プロセスのクリーンアップ
                if self.chrome_process and self.have_psutil:
                    try:
                        process = self.psutil.Process(self.chrome_process.pid)
                        if process.is_running():
                            process.terminate()
                            logger.debug("✅ Chrome外部プロセスを終了しました")
                    except Exception as e:
                        logger.warning(f"⚠️ Chrome外部プロセス終了中にエラー: {e}")
                    finally:
                        self.chrome_process = None
                
                # セッション管理
                if session_id:
                    self.session_manager.remove_session(session_id)
                    logger.debug(f"✅ セッション {session_id} を削除しました")
                
                logger.info("✅ リソースクリーンアップ完了")
            except Exception as e:
                logger.error(f"❌ クリーンアップ中にエラー: {e}")
        else:
            logger.debug("ℹ️ セッション維持モード - 最小限のクリーンアップのみ実行")

    # ---------------------------------------------------------------------
    # Compatibility / Legacy Adapter Methods
    # ---------------------------------------------------------------------
    async def initialize_custom_browser(self, use_own_browser=False, headless=False, tab_selection_strategy="new_tab", browser_type=None, **kwargs):
        """Legacy wrapper expected by older code paths.

        The modern implementation consolidates logic in initialize_browser. We
        keep this thin wrapper to avoid AttributeError until all callers are
        migrated. Additional params (tab_selection_strategy, **kwargs) are
        currently ignored but accepted for forward compatibility.
        """
        logger.debug(
            "🔄 initialize_custom_browser wrapper呼び出し - use_own_browser=%s headless=%s tab_selection=%s browser_type=%s", 
            use_own_browser, headless, tab_selection_strategy, browser_type
        )
        return await self.initialize_browser(
            use_own_browser=use_own_browser,
            headless=headless,
            browser_type=browser_type,
        )
