import os
import asyncio
from playwright.async_api import async_playwright

class BrowserAutomationBase:
    """ブラウザ自動化の共通機能を提供するベースクラス"""
    
    def __init__(self, headless=False, slowmo=0, recording_dir="./tmp/record_videos"):
        self.headless = headless
        self.slowmo = slowmo
        self.recording_dir = recording_dir
        self.browser = None
        self.context = None
        self.page = None
    
    async def setup(self):
        """ブラウザとコンテキストを設定"""
        os.makedirs(self.recording_dir, exist_ok=True)
        
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.headless, 
            slow_mo=self.slowmo, 
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-zygote',
                '--single-process',
                '--window-position=50,50',
                '--window-size=1280,720'
            ]
        )
        
        self.context = await self.browser.new_context(
            record_video_dir=self.recording_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        
        self.page = await self.context.new_page()
        return self.page
    
    async def show_automation_indicator(self):
        """自動操作中であることを示すオーバーレイを表示"""
        if not self.page:
            return
        
        await self.page.evaluate("""() => {
            const overlay = document.createElement('div');
            overlay.id = 'automation-indicator';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;'+
                'background:rgba(76,175,80,0.8);padding:10px;text-align:center;'+
                'font-weight:bold;color:white;font-size:18px;';
            overlay.textContent = '🤖 自動操作中 - テスト実行中です';
            document.body.appendChild(overlay);
            
            // ウィンドウにフォーカスを強制
            window.focus();
        }""")
    
    async def show_countdown_overlay(self, seconds=5):
        """ブラウザを閉じる前にカウントダウンオーバーレイを表示"""
        if not self.page:
            return
            
        await self.page.evaluate(f"""() => {{
            const existingOverlay = document.getElementById('countdown-overlay');
            if (existingOverlay) existingOverlay.remove();
            
            const overlay = document.createElement('div');
            overlay.id = 'countdown-overlay';
            overlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.7);
                display: flex;
                flex-direction: column;
                justify-content: center;
                align-items: center;
                z-index: 10000;
                color: white;
                font-family: Arial, sans-serif;
            `;
            
            const counterDisplay = document.createElement('div');
            counterDisplay.style.cssText = `
                font-size: 120px;
                font-weight: bold;
            `;
            counterDisplay.textContent = '{seconds}';
            
            const statusText = document.createElement('div');
            statusText.style.cssText = `
                font-size: 36px;
                margin-top: 20px;
            `;
            statusText.textContent = '自動操作が完了します';
            
            overlay.appendChild(counterDisplay);
            overlay.appendChild(statusText);
            document.body.appendChild(overlay);
        }}""")
        
        for i in range(seconds, -1, -1):
            await self.page.evaluate(f"""(count) => {{
                const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
                if (counterDisplay) counterDisplay.textContent = count;
            }}""", i)
            await self.page.wait_for_timeout(1000)
        
        await self.page.evaluate("""() => {
            const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
            const statusText = document.querySelector('#countdown-overlay > div:last-child');
            if (counterDisplay) counterDisplay.textContent = 'closing...';
            if (statusText) statusText.textContent = 'ブラウザを終了しています';
        }""")
        await self.page.wait_for_timeout(1000)
    
    async def cleanup(self):
        """リソースの解放"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
