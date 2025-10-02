#!/usr/bin/env python3
"""
ブラウザ起動テスト - ChromeとChromiumの違いを確認
"""

import os
import sys
import asyncio
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(override=True)

# Rely on tests/conftest.py to add the project's `src` to sys.path

from src.browser.browser_debug_manager import BrowserDebugManager
from src.browser.browser_config import BrowserConfig

async def test_browser_startup():
    print("=== ブラウザ起動テスト開始 ===")
    
    # 環境変数の確認
    print(f"\n環境変数確認:")
    print(f"  DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', '未設定')}")
    print(f"  CHROME_PATH: {os.environ.get('CHROME_PATH', '未設定')}")
    
    # ブラウザ設定の確認
    browser_config = BrowserConfig()
    chrome_settings = browser_config.get_browser_settings('chrome')
    print(f"\nブラウザ設定確認:")
    print(f"  current_browser: {browser_config.config.get('current_browser', '未設定')}")
    print(f"  chrome path: {chrome_settings.get('path', '未設定')}")
    print(f"  path exists: {os.path.exists(chrome_settings.get('path', ''))}")
    
    # ブラウザデバッグマネージャーでテスト
    try:
        manager = BrowserDebugManager()
        
        print(f"\nPlaywright管理ブラウザテスト:")
        result = await manager.initialize_browser(use_own_browser=False, headless=True)
        
        if result.get("status") == "success":
            browser = result["browser"]
            
            # ブラウザ情報を取得
            page = await browser.new_page()
            user_agent = await page.evaluate("navigator.userAgent")
            print(f"  User Agent: {user_agent}")
            
            # ChromeかChromiumかを判定
            if "Chrome" in user_agent and "Chromium" not in user_agent:
                print("  ✅ 実際のGoogle Chromeが起動されています")
            elif "Chromium" in user_agent:
                print("  ⚠️ Chromiumが起動されています（Google Chromeではありません）")
            else:
                print("  ❓ ブラウザタイプを特定できません")
            
            await page.close()
            await browser.close()
        else:
            print(f"  ❌ ブラウザ起動失敗: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"  ❌ テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n=== ブラウザ起動テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(test_browser_startup())
