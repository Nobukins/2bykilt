import asyncio
import os
import sys
import subprocess

class BrowserDebugManager:
    """ブラウザの初期化と管理のためのクラス"""
    
    def __init__(self):
        """ブラウザマネージャの初期化"""
        self.chrome_process = None
        self.global_browser = None
        self.global_playwright = None
        
        # psutilの利用可能性チェック
        self.have_psutil = False
        try:
            import psutil
            self.have_psutil = True
            self.psutil = psutil
        except ImportError:
            pass
    
    async def initialize_custom_browser(self, use_own_browser=False, headless=False):
        """カスタムプロファイル付きでブラウザインスタンスを初期化、
        またはCDPを介して接続します。"""
        # すでにブラウザインスタンスが存在する場合はそれを返す
        if self.global_browser is not None:
            print("✅ 既存のブラウザインスタンスを再利用します")
            return {"browser": self.global_browser, "playwright": self.global_playwright, "is_cdp": True}
        
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
            # Chromeが実行中かチェック
            chrome_running = False
            if self.have_psutil:
                chrome_running = any("Google Chrome" in p.name() for p in self.psutil.process_iter(['name']))
            
            if chrome_running:
                print("⚠️ Chromeが既に実行中です。デバッグポートを有効にして接続を試みます...")
                # 既存のChromeを一度閉じずに、タイムアウトを設定してCDPに接続を試みる
                try:
                    browser = await playwright.chromium.connect_over_cdp(
                        endpoint_url=f'http://localhost:{chrome_debugging_port}',
                        timeout=3000  # 3秒のタイムアウト
                    )
                    print(f"✅ 既存のChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
                    self.global_browser = browser
                    
                    # Return the default context if available
                    default_context = browser.contexts[0] if browser.contexts else None
                    return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True}
                except Exception:
                    # 失敗したら既存のChromeをデバッグモードで再起動するか確認
                    print("\n⚠️ 既存のChromeに接続できませんでした。")
                    print("既存のChromeを閉じてデバッグモードで再起動しますか？")
                    print("⚠️ これにより、現在開いているすべてのChromeタブが閉じられます。")
                    result = input("続行しますか？ (y/n): ").lower().startswith('y')
                    
                    if result:
                        # ユーザーが確認したので、Chromeを終了して再起動
                        print("既存のChromeインスタンスを終了しています...")
                        if sys.platform == 'darwin':  # macOS
                            subprocess.run(['killall', 'Google Chrome'], stderr=subprocess.DEVNULL)
                        elif sys.platform == 'win32':  # Windows
                            subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], stderr=subprocess.DEVNULL)
                        else:  # Linux and others
                            subprocess.run(['killall', 'chrome'], stderr=subprocess.DEVNULL)
                        
                        print("Chromeが完全に終了するのを待っています...")
                        await asyncio.sleep(2)
                    else:
                        print("新しいChromeウィンドウの開始を試みます...")
            
            # 新しいChromeインスタンスを起動（既存が閉じられたか、ユーザーが拒否した場合）
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
            
            print(f"Chromeを起動しています: {' '.join(cmd_args)}")
            self.chrome_process = subprocess.Popen(cmd_args)
            print(f"🔄 デバッグモードでChromeを起動しました (ポート {chrome_debugging_port})")
            await asyncio.sleep(3)  # Chromeが起動する時間を確保

            # 接続を再試行
            try:
                browser = await playwright.chromium.connect_over_cdp(
                    endpoint_url=f'http://localhost:{chrome_debugging_port}'
                )
                print(f"✅ 起動したChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
                self.global_browser = browser
                
                # Return the default context if available
                default_context = browser.contexts[0] if browser.contexts else None
                return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True}
            except Exception as e:
                print(f"⚠️ 起動したChromeへの接続に失敗しました: {e}")
                print("新しいブラウザインスタンスの起動にフォールバックします...")
        
        # フォールバック: 通常のPlaywright管理ブラウザを使用
        browser = await playwright.chromium.launch(headless=headless)
        context = await browser.new_context()
        self.global_browser = browser
        return {"browser": browser, "context": context, "playwright": playwright, "is_cdp": False}

    async def cleanup_resources(self):
        """リソースをクリーンアップする"""
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
