import os
import asyncio
import platform
import sys
from pathlib import Path
from playwright.async_api import async_playwright

class BrowserAutomationBase:
    """ブラウザ自動化の共通機能を提供するベースクラス（Windows対応済み）"""
    
    def __init__(self, headless=False, slowmo=0, recording_dir="./tmp/record_videos"):
        self.headless = headless
        self.slowmo = slowmo
        # Windows対応: pathlib使用による汎用パス処理
        self.recording_dir = Path(recording_dir).resolve()
        self.browser = None
        self.context = None
        self.page = None
        self.playwright_instance = None
        
        # プラットフォーム情報
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
    
    async def setup(self):
        """ブラウザとコンテキストを設定（Windows対応済み）"""
        try:
            # ディレクトリ作成（Windows対応）
            self.recording_dir.mkdir(parents=True, exist_ok=True)
            
            # Playwright起動
            self.playwright_instance = await async_playwright().start()
            
            # Windows固有のブラウザ設定
            browser_args = self._get_browser_args()
            
            self.browser = await self.playwright_instance.chromium.launch(
                headless=self.headless, 
                slow_mo=self.slowmo, 
                args=browser_args
            )
            
            # コンテキスト作成（録画ディレクトリはWindowsパス対応）
            context_options = {
                "record_video_dir": str(self.recording_dir),
                "record_video_size": {"width": 1280, "height": 720}
            }
            
            # Windows固有の設定追加
            if self.is_windows:
                context_options.update({
                    "viewport": {"width": 1280, "height": 720},
                    "ignore_https_errors": True
                })
            
            self.context = await self.browser.new_context(**context_options)
            
            self.page = await self.context.new_page()
            
            # Windows環境でのエラーハンドリング強化
            await self._setup_error_handlers()
            
            return self.page
            
        except Exception as e:
            print(f"❌ Browser setup failed: {e}")
            print(f"Platform: {platform.system()}")
            print(f"Python: {sys.version}")
            await self.cleanup()
            raise
    
    def _get_browser_args(self):
        """プラットフォーム別ブラウザ引数を取得"""
        base_args = [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-zygote',
            '--single-process',
            '--window-position=50,50',
            '--window-size=1280,720'
        ]
        
        if self.is_windows:
            # Windows固有の引数
            windows_args = [
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-web-security',
                '--allow-running-insecure-content',
                '--no-first-run',
                '--no-default-browser-check'
            ]
            base_args.extend(windows_args)
        elif self.is_linux:
            # Linux固有の引数
            linux_args = [
                '--disable-gpu',
                '--disable-software-rasterizer'
            ]
            base_args.extend(linux_args)
        
        return base_args
    
    async def _setup_error_handlers(self):
        """エラーハンドリングの設定"""
        if not self.page:
            return
        
        # コンソールエラーのキャッチ
        self.page.on("console", lambda msg: print(f"🔍 Console: {msg.text}"))
        self.page.on("pageerror", lambda error: print(f"❌ Page Error: {error}"))
        
        # Windows環境でのタイムアウト延長
        if self.is_windows:
            self.page.set_default_timeout(60000)  # 60秒
            self.page.set_default_navigation_timeout(60000)
    
    async def show_automation_indicator(self):
        """自動操作中であることを示すオーバーレイを表示（Windows対応済み）"""
        if not self.page:
            return
        
        try:
            await self.page.evaluate("""() => {
                // 既存のインジケーターを削除
                const existing = document.getElementById('automation-indicator');
                if (existing) existing.remove();
                
                const overlay = document.createElement('div');
                overlay.id = 'automation-indicator';
                overlay.style.cssText = `
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    right: 0 !important;
                    z-index: 999999 !important;
                    background: rgba(76,175,80,0.9) !important;
                    padding: 15px !important;
                    text-align: center !important;
                    font-weight: bold !important;
                    color: white !important;
                    font-size: 18px !important;
                    font-family: Arial, sans-serif !important;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.3) !important;
                `;
                overlay.textContent = '🤖 自動操作中 - テスト実行中です';
                
                // bodyが存在しない場合の対策
                if (document.body) {
                    document.body.appendChild(overlay);
                } else {
                    document.documentElement.appendChild(overlay);
                }
                
                // Windows環境での表示確保
                window.focus();
                overlay.scrollIntoView();
            }""")
            
            # Windows環境での追加ウェイト
            if self.is_windows:
                await self.page.wait_for_timeout(500)
                
        except Exception as e:
            print(f"⚠️ Warning: Could not show automation indicator: {e}")
    
    async def show_countdown_overlay(self, seconds=5):
        """ブラウザを閉じる前にカウントダウンオーバーレイを表示（Windows対応済み）"""
        if not self.page:
            return
        
        try:
            await self.page.evaluate(f"""() => {{
                // 既存のオーバーレイを削除
                const existingOverlay = document.getElementById('countdown-overlay');
                if (existingOverlay) existingOverlay.remove();
                
                const overlay = document.createElement('div');
                overlay.id = 'countdown-overlay';
                overlay.style.cssText = `
                    position: fixed !important;
                    top: 0 !important;
                    left: 0 !important;
                    width: 100% !important;
                    height: 100% !important;
                    background-color: rgba(0, 0, 0, 0.8) !important;
                    display: flex !important;
                    flex-direction: column !important;
                    justify-content: center !important;
                    align-items: center !important;
                    z-index: 9999999 !important;
                    color: white !important;
                    font-family: Arial, sans-serif !important;
                `;
                
                const counterDisplay = document.createElement('div');
                counterDisplay.style.cssText = `
                    font-size: 120px !important;
                    font-weight: bold !important;
                    text-shadow: 2px 2px 4px rgba(0,0,0,0.5) !important;
                `;
                counterDisplay.textContent = '{seconds}';
                
                const statusText = document.createElement('div');
                statusText.style.cssText = `
                    font-size: 36px !important;
                    margin-top: 20px !important;
                    text-shadow: 1px 1px 2px rgba(0,0,0,0.5) !important;
                `;
                statusText.textContent = '自動操作が完了します';
                
                overlay.appendChild(counterDisplay);
                overlay.appendChild(statusText);
                
                // Windows環境での確実な表示
                if (document.body) {{
                    document.body.appendChild(overlay);
                }} else {{
                    document.documentElement.appendChild(overlay);
                }}
            }}""")
            
            # カウントダウン実行（Windows環境での安定性向上）
            for i in range(seconds, -1, -1):
                try:
                    await self.page.evaluate(f"""(count) => {{
                        const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
                        if (counterDisplay) {{
                            counterDisplay.textContent = count;
                            // Windows環境での視覚的フィードバック
                            counterDisplay.style.transform = 'scale(1.1)';
                            setTimeout(() => {{
                                if (counterDisplay) counterDisplay.style.transform = 'scale(1)';
                            }}, 200);
                        }}
                    }}""", i)
                    
                    # Windows環境での適切なウェイト
                    await self.page.wait_for_timeout(1000)
                    
                except Exception as e:
                    print(f"⚠️ Countdown display error: {e}")
                    continue
            
            # 終了メッセージ
            await self.page.evaluate("""() => {
                const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
                const statusText = document.querySelector('#countdown-overlay > div:last-child');
                if (counterDisplay) {
                    counterDisplay.textContent = '✅';
                    counterDisplay.style.color = '#4CAF50';
                }
                if (statusText) {
                    statusText.textContent = 'ブラウザを終了しています...';
                }
            }""")
            
            await self.page.wait_for_timeout(1500)
            
        except Exception as e:
            print(f"⚠️ Warning: Could not show countdown overlay: {e}")
            # フォールバック: シンプルなアラート
            try:
                await self.page.evaluate(f"alert('操作完了 - {seconds}秒後にブラウザを閉じます')")
                await self.page.wait_for_timeout(seconds * 1000)
            except:
                pass
    
    async def cleanup(self):
        """リソースの解放"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
