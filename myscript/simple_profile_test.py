# simple_profile_test.py - プロファイル付きブラウザの基本動作確認
import pytest
from playwright.async_api import async_playwright
import asyncio
import os
import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

pytest_plugins = ["pytest_asyncio"]

@pytest.mark.asyncio
async def test_simple_profile_browser(request) -> None:
    """シンプルなプロファイル付きブラウザテスト"""
    browser_type = request.config.getoption("--browser-type", default="chrome")
    use_profile = request.config.getoption("--use-profile", default=False)
    
    # 環境変数からブラウザ設定を取得
    browser_executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
    chrome_user_data = os.environ.get('CHROME_USER_DATA')
    
    print(f"🔍 Browser type: {browser_type}")
    print(f"🔍 Use profile: {use_profile}")
    print(f"🔍 Browser executable: {browser_executable}")
    print(f"🔍 Chrome user data: {chrome_user_data}")
    
    if not browser_executable:
        pytest.skip("No browser executable specified")
    
    async with async_playwright() as p:
        if use_profile and chrome_user_data and os.path.exists(chrome_user_data):
            print("✅ Testing with user profile...")
            try:
                # プロファイル付きで起動
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=chrome_user_data,
                    headless=False,
                    slow_mo=1000,
                    executable_path=browser_executable,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--window-position=100,100',
                        '--window-size=800,600'
                    ]
                )
                
                print("✅ Browser launched with profile")
                
                # 既存ページの確認
                existing_pages = context.pages
                print(f"📄 Found {len(existing_pages)} existing pages")
                
                for i, page in enumerate(existing_pages):
                    url = page.url
                    print(f"📄 Page {i}: {url}")
                
                # 新しいページを作成せずに、既存のページを使用
                if existing_pages:
                    page = existing_pages[0]
                    print("🔧 Using existing page")
                else:
                    page = await context.new_page()
                    print("🔧 Created new page")
                
                print(f"🔍 Current page URL: {page.url}")
                
                # about:blankでない場合はGoogleに移動
                if page.url == 'about:blank':
                    print("⚠️ Page is about:blank, navigating to Google...")
                    await page.goto("https://www.google.com", wait_until='domcontentloaded', timeout=15000)
                    print("✅ Navigated to Google")
                
                # 5秒待機して確認
                await page.wait_for_timeout(5000)
                
                print("✅ Test completed successfully")
                await context.close()
                
            except Exception as e:
                print(f"❌ Error with profile: {e}")
                raise
        else:
            print("✅ Testing without profile...")
            try:
                # プロファイルなしで起動
                browser = await p.chromium.launch(
                    headless=False,
                    slow_mo=1000,
                    executable_path=browser_executable,
                    args=[
                        '--no-sandbox',
                        '--disable-setuid-sandbox',
                        '--window-position=100,100',
                        '--window-size=800,600'
                    ]
                )
                
                context = await browser.new_context()
                page = await context.new_page()
                
                print("✅ Browser launched without profile")
                print(f"🔍 Current page URL: {page.url}")
                
                # Googleに移動
                await page.goto("https://www.google.com", wait_until='domcontentloaded', timeout=15000)
                print("✅ Navigated to Google")
                
                # 5秒待機して確認
                await page.wait_for_timeout(5000)
                
                print("✅ Test completed successfully")
                await context.close()
                await browser.close()
                
            except Exception as e:
                print(f"❌ Error without profile: {e}")
                raise

if __name__ == "__main__":
    asyncio.run(test_simple_profile_browser(None))
