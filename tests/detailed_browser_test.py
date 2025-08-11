#!/usr/bin/env python3
"""
詳細ブラウザテスト - ログ付きでブラウザ起動プロセスを完全追跡
"""

import os
import sys
import asyncio
import logging
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(override=True)

# プロジェクトのsrcディレクトリをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# ログレベルをDEBUGに設定
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

from browser.browser_manager import initialize_browser
from browser.browser_config import BrowserConfig

async def detailed_browser_test():
    print("=== 詳細ブラウザテスト開始 ===")
    
    # 環境変数の確認
    print(f"\n📋 環境変数確認:")
    print(f"  DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', '未設定')}")
    print(f"  CHROME_PATH: {os.environ.get('CHROME_PATH', '未設定')}")
    print(f"  BROWSER_USE_LOGGING_LEVEL: {os.environ.get('BROWSER_USE_LOGGING_LEVEL', '未設定')}")
    
    # BrowserConfig初期化
    print(f"\n🔧 BrowserConfig初期化:")
    browser_config = BrowserConfig()
    print(f"  current_browser: {browser_config.config.get('current_browser', '未設定')}")
    
    # ブラウザ設定確認
    chrome_settings = browser_config.get_browser_settings('chrome')
    print(f"\n🌐 Chrome設定:")
    for key, value in chrome_settings.items():
        print(f"  {key}: {value}")
    
    try:
        print(f"\n🚀 ブラウザ初期化テスト:")
        
        # browser_manager.initialize_browser を使用（実際のアプリケーションと同じパス）
        result = await initialize_browser(
            use_own_browser=False,  # Playwright管理
            headless=False,  # 目視確認のため
            browser_type=None,  # デフォルト（chrome）を使用
            auto_fallback=True
        )
        
        if result.get("status") == "success":
            browser = result["browser"]
            playwright = result.get("playwright")
            
            print(f"✅ ブラウザ起動成功!")
            
            # 新しいページを作成
            page = await browser.new_page()
            
            # User Agentとブラウザ情報を取得
            user_agent = await page.evaluate("navigator.userAgent")
            app_name = await page.evaluate("navigator.appName")
            app_version = await page.evaluate("navigator.appVersion")
            vendor = await page.evaluate("navigator.vendor")
            
            print(f"\n🔍 ブラウザ詳細情報:")
            print(f"  User Agent: {user_agent}")
            print(f"  App Name: {app_name}")
            print(f"  App Version: {app_version}")
            print(f"  Vendor: {vendor}")
            
            # ChromeかChromiumかを判定
            if "Chrome" in user_agent and "Chromium" not in user_agent:
                print(f"  ✅ 実際のGoogle Chromeが起動されています")
            elif "Chromium" in user_agent:
                print(f"  ⚠️ Chromiumが起動されています（Google Chromeではありません）")
            else:
                print(f"  ❓ ブラウザタイプを特定できません")
            
            # テスト用サイトにアクセス
            print(f"\n🌍 テストサイトにアクセス中...")
            await page.goto("https://www.whatismybrowser.com/")
            await page.wait_for_timeout(3000)  # 3秒待機
            
            await page.close()
            await browser.close()
            
        else:
            print(f"❌ ブラウザ起動失敗: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n=== 詳細ブラウザテスト完了 ===")

if __name__ == "__main__":
    asyncio.run(detailed_browser_test())
