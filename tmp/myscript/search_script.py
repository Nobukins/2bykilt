# search_script.py 
import pytest
from playwright.async_api import async_playwright, Page, expect
import asyncio
import os

pytest_plugins = ["pytest_asyncio"]  # Add this line to enable async test support

def pytest_addoption(parser):
    parser.addoption("--query", action="store", default=None, help="Search query to use")
    parser.addoption("--slowmo", action="store", type=int, default=0, help="Slow motion delay in milliseconds")

async def show_countdown_overlay(page, seconds=5):
    """
    ブラウザを閉じる前に画面いっぱいのカウントダウンオーバーレイを表示する
    """
    # JavaScriptでカウントダウンオーバーレイを作成して表示
    await page.evaluate(f"""() => {{
        // すでに存在するオーバーレイを削除
        const existingOverlay = document.getElementById('countdown-overlay');
        if (existingOverlay) existingOverlay.remove();
        
        // オーバーレイ要素を作成
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
        
        // カウントダウン表示用の要素
        const counterDisplay = document.createElement('div');
        counterDisplay.style.cssText = `
            font-size: 120px;
            font-weight: bold;
        `;
        counterDisplay.textContent = '{seconds}';
        
        // 「自動操作中」のテキスト
        const statusText = document.createElement('div');
        statusText.style.cssText = `
            font-size: 36px;
            margin-top: 20px;
        `;
        statusText.textContent = '自動操作が完了します';
        
        // 要素を追加
        overlay.appendChild(counterDisplay);
        overlay.appendChild(statusText);
        document.body.appendChild(overlay);
    }}""")
    
    # カウントダウンを実行
    for i in range(seconds, -1, -1):
        await page.evaluate(f"""(count) => {{
            const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
            if (counterDisplay) counterDisplay.textContent = count;
        }}""", i)
        await page.wait_for_timeout(1000)  # 1秒待機
    
    # "closing..."のメッセージを表示
    await page.evaluate("""() => {
        const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
        const statusText = document.querySelector('#countdown-overlay > div:last-child');
        if (counterDisplay) counterDisplay.textContent = 'closing...';
        if (statusText) statusText.textContent = 'ブラウザを終了しています';
    }""")
    await page.wait_for_timeout(1000)  # 閉じる前に1秒待機

@pytest.mark.asyncio  # This mark will now be recognized
async def test_text_search(request) -> None:
    query = request.config.getoption("--query")
    slowmo = request.config.getoption("--slowmo")
    if not query:
        pytest.skip("No query provided. Use --query to specify a search term.")

    # 録画ディレクトリの設定（環境変数から取得するか、デフォルト値を使用）
    recording_dir = os.environ.get("RECORDING_PATH", "./tmp/record_videos")
    os.makedirs(recording_dir, exist_ok=True)  # ディレクトリが存在しない場合は作成
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, 
            slow_mo=slowmo, 
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-zygote',
                '--single-process',
                '--window-position=50,50',  # ウィンドウの位置を指定
                '--window-size=1280,720'    # ウィンドウのサイズを指定
            ]
        )  
        # 録画オプションを指定してコンテキストを作成
        context = await browser.new_context(
            record_video_dir=recording_dir,
            record_video_size={"width": 1280, "height": 720}  # 録画解像度
        )
        page = await context.new_page()

        # 開始時に自動操作中であることを示すオーバーレイを表示
        await page.evaluate("""() => {
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

        # nogtips検索処理
        await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=30000)
        await page.get_by_role("button", name="閉じて承認").click()
        await page.get_by_role("link", name="nogtips").click()
        await page.get_by_role("heading", name="Personal AI Assistant（PAIA）を作る").get_by_role("link").click()
        await page.get_by_role("link", name="bykilt", exact=True).click()
        await page.get_by_role("searchbox", name="検索:").click()
        await page.get_by_role("searchbox", name="検索:").fill(query)
        await page.get_by_role("searchbox", name="検索:").press("Enter")

        await page.wait_for_timeout(5000)  # 検索結果を少し表示

        # ブラウザを閉じる前にカウントダウン表示
        await show_countdown_overlay(page, 5)  # 5秒カウントダウン

        await context.close()
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_text_search(None))