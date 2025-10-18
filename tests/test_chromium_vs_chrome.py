#!/usr/bin/env python3
"""
Chromium vs Chrome テストスクリプト
プロファイル使用の違いを検証
"""
import asyncio
import pytest
import os
import sys
import tempfile
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.git_script_automator import GitScriptAutomator


async @pytest.mark.local_only
def test_chromium_vs_chrome():
    """ChromiumとChromeの動作の違いをテスト"""
    print("🔍 Chromium vs Chrome テストを開始...")
    
    # テスト用の一時ディレクトリ
    temp_dir = tempfile.mkdtemp()
    print(f"📁 テスト用ディレクトリ: {temp_dir}")
    
    try:
        # Chrome automator の初期化
        print("\n🔴 Chrome Automator での検証...")
        chrome_automator = GitScriptAutomator(
            browser_type="chrome",
            source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                             '/Users/nobuaki/Library/Application Support/Google/Chrome')
        )
        
        # 詳細なブラウザ情報を取得
        chrome_info = chrome_automator.browser_launcher.get_detailed_browser_info()
        print("📊 Chrome Launcher 詳細情報:")
        for key, value in chrome_info.items():
            print(f"  {key}: {value}")
        
        # 実際の起動テスト
        print("\n🚀 Chrome起動テスト...")
        try:
            async with chrome_automator.browser_context(temp_dir, headless=False) as context:
                print("✅ Chrome コンテキスト取得成功")
                
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()
                
                # ブラウザ識別情報を取得
                user_agent = await page.evaluate("navigator.userAgent")
                vendor = await page.evaluate("navigator.vendor")
                app_name = await page.evaluate("navigator.appName")
                
                print(f"🔍 実行中のブラウザ情報:")
                print(f"  ユーザーエージェント: {user_agent}")
                print(f"  ベンダー: {vendor}")
                print(f"  アプリ名: {app_name}")
                
                # ChromiumかChromeかを判定
                if "Chromium" in user_agent and "Google Inc." not in vendor:
                    print("⚠️ 起動されたのはChromiumです（Playwright内蔵）")
                    print("  → プロファイルは使用されていません（API key警告回避）")
                elif "Chrome" in user_agent and "Google Inc." in vendor:
                    print("✅ 起動されたのはGoogle Chromeです")
                    print("  → プロファイルが使用されています")
                else:
                    print(f"❓ 不明なブラウザです")
                
                # chrome://version/ で詳細確認
                try:
                    await page.goto("chrome://version/", timeout=5000)
                    title = await page.title()
                    print(f"📄 chrome://version/ タイトル: {title}")
                    
                    # ページが読み込まれるまで少し待つ
                    await asyncio.sleep(2)
                    
                    # 実行ファイルパスを取得（可能であれば）
                    try:
                        executable_path = await page.evaluate("""
                            () => {
                                const versionInfo = document.body.innerText;
                                const executableMatch = versionInfo.match(/実行可能ファイルのパス[\\s:]+(.+?)\\n/);
                                return executableMatch ? executableMatch[1].trim() : null;
                            }
                        """)
                        if executable_path:
                            print(f"📍 ブラウザ実行ファイル: {executable_path}")
                    except:
                        pass
                        
                except Exception as e:
                    print(f"⚠️ chrome://version/ アクセスエラー: {e}")
                
                # 5秒表示
                await asyncio.sleep(5)
                
        except Exception as e:
            print(f"❌ Chrome起動エラー: {e}")
            import traceback
            traceback.print_exc()
        
        # Chromium専用テスト（executable_pathを無効化）
        print("\n🔵 Chromium専用テスト（executable_pathを無効化）...")
        
        # 環境変数を一時的に変更
        original_chrome_path = os.environ.get('CHROME_PATH')
        os.environ['CHROME_PATH'] = '/nonexistent/path/to/chrome'
        
        try:
            chromium_automator = GitScriptAutomator(
                browser_type="chrome",
                source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                                 '/Users/nobuaki/Library/Application Support/Google/Chrome')
            )
            
            chromium_info = chromium_automator.browser_launcher.get_detailed_browser_info()
            print("📊 Chromium Launcher 詳細情報:")
            for key, value in chromium_info.items():
                print(f"  {key}: {value}")
            
            print("\n🚀 Chromium起動テスト...")
            async with chromium_automator.browser_context(temp_dir, headless=False) as context:
                print("✅ Chromium コンテキスト取得成功")
                
                if context.pages:
                    page = context.pages[0]
                else:
                    page = await context.new_page()
                
                user_agent = await page.evaluate("navigator.userAgent")
                vendor = await page.evaluate("navigator.vendor")
                
                print(f"🔍 Chromiumブラウザ情報:")
                print(f"  ユーザーエージェント: {user_agent}")
                print(f"  ベンダー: {vendor}")
                
                if "Google Inc." not in vendor:
                    print("✅ Playwright内蔵Chromiumが起動されました")
                    print("  → プロファイルなしで起動（API key警告なし）")
                
                await asyncio.sleep(3)
        
        finally:
            # 環境変数を復元
            if original_chrome_path:
                os.environ['CHROME_PATH'] = original_chrome_path
            else:
                os.environ.pop('CHROME_PATH', None)
        
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(test_chromium_vs_chrome())
