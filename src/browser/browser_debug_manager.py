import asyncio
import os
import sys
import subprocess
import uuid
from datetime import datetime
from src.browser.session_manager import SessionManager

browser_sessions = {}

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
    
    async def initialize_browser(self, use_own_browser=False, headless=False, maintain_session=False):
        """
        Initialize or reuse a browser instance.
        
        Args:
            use_own_browser: Whether to use the user's own browser.
            headless: Whether to run in headless mode.
            maintain_session: Whether to maintain an existing session.
        
        Returns:
            dict: Browser session information.
        """
        # Check if we should reuse an existing session
        if maintain_session and self.global_browser:
            return {
                "browser": self.global_browser,
                "context": self.global_context,
                "page": self.global_page,
                "playwright": self.global_playwright,
                "is_cdp": True,
                "is_reused": True
            }
        
        # Start new playwright instance if needed
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        self.global_playwright = playwright
        
        chrome_debugging_port = os.getenv("CHROME_DEBUGGING_PORT", "9222")
        chrome_path = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        
        # Check user data directory
        chrome_user_data = os.getenv("CHROME_USER_DATA")
        if not chrome_user_data or chrome_user_data.strip() == "":
            chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        
        if use_own_browser:
            # Check if Chrome is running
            chrome_running = False
            try:
                chrome_running = any("Google Chrome" in p.name() for p in psutil.process_iter(['name']))
            except:
                pass
            
            if chrome_running:
                # Try to connect to existing Chrome
                try:
                    browser = await playwright.chromium.connect_over_cdp(
                        endpoint_url=f'http://localhost:{chrome_debugging_port}',
                        timeout=3000
                    )
                    self.global_browser = browser
                    
                    # Get or create a context
                    context = browser.contexts[0] if browser.contexts else await browser.new_context()
                    self.global_context = context
                    
                    # Create a new page
                    page = await context.new_page()
                    self.global_page = page
                    
                    return {
                        "browser": browser,
                        "context": context,
                        "page": page,
                        "playwright": playwright,
                        "is_cdp": True,
                        "is_reused": False
                    }
                except Exception:
                    pass  # Handle connection failure
            
            # Start new Chrome instance
            cmd_args = [
                chrome_path,
                f"--remote-debugging-port={chrome_debugging_port}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            if chrome_user_data and chrome_user_data.strip():
                cmd_args.append(f"--user-data-dir={chrome_user_data}")
            
            chrome_process = subprocess.Popen(cmd_args)
            await asyncio.sleep(3)  # Wait for Chrome to start
            
            try:
                browser = await playwright.chromium.connect_over_cdp(
                    endpoint_url=f'http://localhost:{chrome_debugging_port}'
                )
                self.global_browser = browser
                
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                self.global_context = context
                
                page = await context.new_page()
                self.global_page = page
                
                return {
                    "browser": browser,
                    "context": context,
                    "page": page,
                    "playwright": playwright,
                    "is_cdp": True,
                    "is_reused": False
                }
            except Exception:
                pass  # Fallback to standard browser
        
        # Fallback: Launch a new browser instance
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        page = await context.new_page()
        
        self.global_browser = browser
        self.global_context = context
        self.global_page = page
        
        return {
            "browser": browser,
            "context": context,
            "page": page,
            "playwright": playwright,
            "is_cdp": False,
            "is_reused": False
        }

    async def initialize_custom_browser(self, use_own_browser=False, headless=False, tab_selection_strategy="new_tab"):
        """カスタムプロファイル付きでブラウザインスタンスを初期化、
        またはCDPを介して接続します。"""
        # すでにブラウザインスタンスが存在する場合はそれを返す
        if self.global_browser is not None:
            print("✅ 既存のブラウザインスタンスを再利用します")
            return {"browser": self.global_browser, "playwright": self.global_playwright, "is_cdp": True, "status": "success"}
        
        from playwright.async_api import async_playwright
        
        playwright = await async_playwright().start()
        self.global_playwright = playwright
        
        chrome_debugging_port = os.getenv("CHROME_DEBUGGING_PORT", "9222")
        chrome_path = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
        
        # ユーザーデータディレクトリの確認
        chrome_user_data = os.getenv("CHROME_USER_DATA")
        if not chrome_user_data or chrome_user_data.strip() == "":
            chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
            print(f"⚠️ CHROME_USER_DATA が設定されていないため、デフォルト値を使用します: {chrome_user_data}")
        
        if use_own_browser:
            print(f"🔍 use_own_browser が有効です。Chrome を探します...")
            # Chromeが実行中かチェック
            chrome_running = False
            if self.have_psutil:
                chrome_running = any("Google Chrome" in p.name() for p in self.psutil.process_iter(['name']))
                print(f"🔍 Chrome 実行中: {chrome_running}")
            
            if chrome_running:
                print(f"⚠️ Chromeが既に実行中です。CDPデバッグポート {chrome_debugging_port} に接続を試みます...")
                # 既存のChromeを一度閉じずに、タイムアウトを設定してCDPに接続を試みる
                try:
                    endpoint_url = f'http://localhost:{chrome_debugging_port}'
                    print(f"🔌 接続先: {endpoint_url}")
                    browser = await playwright.chromium.connect_over_cdp(
                        endpoint_url=endpoint_url,
                        timeout=5000  # 5秒のタイムアウト
                    )
                    print(f"✅ 既存のChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
                    self.global_browser = browser
                    
                    # Return the default context if available
                    default_context = browser.contexts[0] if browser.contexts else None
                    return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True, "status": "success"}
                except Exception as e:
                    print(f"⚠️ 既存のChromeに接続失敗: {str(e)}")
                    # 失敗したら既存のChromeをデバッグモードで再起動するか確認
                    return {
                        "status": "needs_restart",
                        "message": "既存のChromeに接続できませんでした。再起動が必要です。",
                        "playwright": playwright
                    }
            
            # 新しいChromeインスタンスを起動
            try:
                print(f"🚀 新しいChrome起動: {chrome_path}")
                # Chrome起動引数を構築
                cmd_args = [
                    chrome_path,
                    f"--remote-debugging-port={chrome_debugging_port}",
                    "--no-first-run",
                    "--no-default-browser-check"
                ]
                
                # ユーザーデータディレクトリの追加
                if chrome_user_data and chrome_user_data.strip():
                    cmd_args.append(f"--user-data-dir={chrome_user_data}")
                    print(f"📁 ユーザーデータディレクトリを使用: {chrome_user_data}")
                
                print(f"🚀 コマンド: {' '.join(cmd_args)}")
                self.chrome_process = subprocess.Popen(cmd_args)
                print(f"🔄 デバッグモードでChromeを起動しました (ポート {chrome_debugging_port})")
                await asyncio.sleep(3)  # Chromeが起動する時間を確保

                # 接続を試行
                try:
                    endpoint_url = f'http://localhost:{chrome_debugging_port}'
                    browser = await playwright.chromium.connect_over_cdp(
                        endpoint_url=endpoint_url
                    )
                    print(f"✅ 起動したChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
                    self.global_browser = browser
                    
                    # Return the default context if available
                    default_context = browser.contexts[0] if browser.contexts else None
                    return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True, "status": "success"}
                except Exception as e:
                    print(f"⚠️ 起動したChromeへの接続に失敗しました: {e}")
                    # フォールバックへ進む
            except Exception as e:
                print(f"⚠️ Chromeの起動中にエラーが発生しました: {e}")
                # フォールバックへ進む
        
        # フォールバック: 通常のPlaywright管理ブラウザを使用
        print("🔄 Playwright管理ブラウザを使用します")
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        self.global_browser = browser
        return {"browser": browser, "context": context, "playwright": playwright, "is_cdp": False, "status": "success"}

    async def initialize_with_session(self, session_id=None, use_own_browser=False, headless=False):
        """セッションIDを使用してブラウザを初期化（既存または新規）"""
        browser = None
        
        # 既存セッションがあれば再利用を試みる
        if session_id and self.session_manager.get_session(session_id):
            browser = await self._try_reuse_browser(session_id)
        
        # 既存ブラウザが見つからないか利用できない場合、新しいブラウザを作成
        if not browser:
            browser = await self._create_new_browser(use_own_browser, headless)
            
            if browser:
                # 新しいセッション情報を作成
                browser_info = self._get_browser_info(browser)
                session_id = self.session_manager.create_session(browser_info)
            else:
                return {"status": "error", "message": "ブラウザの初期化に失敗しました"}
        
        # セッション情報を返す
        return {
            "status": "success", 
            "message": "ブラウザセッションを初期化しました", 
            "session_id": session_id
        }
    
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
    
    async def initialize_with_session(self, session_id=None, use_own_browser=False, headless=False):
        """
        Initialize or reuse a browser session.
        
        Args:
            session_id: Optional session ID to reuse an existing session.
            use_own_browser: Whether to use the user's own browser.
            headless: Whether to run in headless mode.
        
        Returns:
            dict: Browser session information.
        """
        if session_id and session_id in browser_sessions:
            # Reuse existing session
            self.browser = browser_sessions[session_id].get('browser')
            self.page = browser_sessions[session_id].get('page')
            return {"status": "success", "session_id": session_id}
        else:
            # Create a new session
            result = await self.initialize(use_own_browser, headless)
            if result.get("status") == "success":
                new_session_id = str(uuid.uuid4())
                browser_sessions[new_session_id] = {
                    "browser": self.browser,
                    "page": self.page,
                    "created_at": datetime.now()
                }
                return {"status": "success", "session_id": new_session_id}
            return result

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
                    if page._target_id == active_tab_id:
                        return page, False
        except Exception as e:
            logger.error(f"Active tab detection via CDP failed: {e}")

        # Fallback: Use the last tab as the active tab
        return all_pages[-1], False

    async def get_or_create_tab(self, tab_selection="active"):
        """
        Get or create a tab based on the specified selection strategy.
        
        Args:
            tab_selection: Strategy for selecting a tab:
                - "new_tab": Create a new tab.
                - "active_tab": Use the currently visible tab.
                - "last_tab": Use the last tab in the context.
        
        Returns:
            tuple: (context, page, is_new)
        """
        if not self.global_browser:
            raise ValueError("Browser must be initialized before creating or selecting tabs")

        context = self.global_browser.contexts[0] if self.global_browser.contexts else await self.global_browser.new_context()
        
        if tab_selection == "new_tab" or not context.pages:
            print("✅ 新しいタブを作成します")
            page = await context.new_page()
            return context, page, True
        elif tab_selection == "active_tab":
            if context.pages:
                page, is_new = await self.get_active_tab(self.global_browser)
                if not is_new:
                    print("✅ 現在表示中のタブを操作します")
                    return context, page, False
        elif tab_selection == "last_tab" and context.pages:
            print(f"✅ 既存の最後のタブを再利用します (合計 {len(context.pages)} タブ中)")
            return context, context.pages[-1], False
        
        # デフォルトケース - 新しいタブを作成
        print("✅ 新しいタブを作成します")
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
