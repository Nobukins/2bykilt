#!/usr/bin/env python3
"""
ブラウザ起動の詳細デバッグスクリプト
どのブラウザが実際に起動されているかを確認
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.profile_manager import ProfileManager
from src.utils.browser_launcher import BrowserLauncher, ChromeLauncher, EdgeLauncher


async def debug_browser_execution():
    """ブラウザ実行の詳細デバッグ"""
    print("🔍 ブラウザ実行のデバッグを開始...")
    
    # テスト用の一時ディレクトリ
    temp_dir = tempfile.mkdtemp()
    print(f"📁 テスト用ディレクトリ: {temp_dir}")
    
    try:
        # Chrome設定の確認
        print("\n🔴 Chrome設定の確認...")
        chrome_launcher = ChromeLauncher()
        chrome_info = chrome_launcher.get_browser_info()
        
        print("📊 Chrome設定情報:")
        for key, value in chrome_info.items():
            print(f"  {key}: {value}")
        
        # 実行ファイルの存在確認
        chrome_path = chrome_launcher.executable_path
        print(f"\n🔍 Chrome実行ファイル: {chrome_path}")
        if chrome_path and Path(chrome_path).exists():
            print("✅ Chrome実行ファイルが存在します")
            # ファイルの詳細情報
            chrome_file = Path(chrome_path)
            print(f"  サイズ: {chrome_file.stat().st_size:,} bytes")
            print(f"  最終更新: {chrome_file.stat().st_mtime}")
        else:
            print("❌ Chrome実行ファイルが見つかりません")
        
        # 起動オプションの確認
        print("\n🔧 Chrome起動オプションの確認...")
        profile_mgr = ProfileManager(
            source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                             '')
        )
        selenium_profile = profile_mgr.create_selenium_profile(temp_dir)
        
        launch_options = chrome_launcher._get_launch_options(selenium_profile)
        print("📋 起動オプション:")
        for key, value in launch_options.items():
            if key == 'args':
                print(f"  {key}: {len(value)} 個の引数")
                for i, arg in enumerate(value, 1):
                    print(f"    {i:2d}. {arg}")
            else:
                print(f"  {key}: {value}")
        
        # 実際の起動テスト
        print("\n🚀 実際のブラウザ起動テスト...")
        try:
            context = await chrome_launcher.launch_with_profile(selenium_profile)
            print("✅ ブラウザが正常に起動しました")
            
            if context.pages:
                page = context.pages[0]
                
                # ブラウザ情報を取得
                user_agent = await page.evaluate("navigator.userAgent")
                print(f"🔍 ユーザーエージェント: {user_agent}")
                
                vendor = await page.evaluate("navigator.vendor")
                print(f"🏪 ベンダー: {vendor}")
                
                app_name = await page.evaluate("navigator.appName")
                print(f"📱 アプリ名: {app_name}")
                
                app_version = await page.evaluate("navigator.appVersion")
                print(f"📱 アプリバージョン: {app_version}")
                
                # ChromiumかChromeかを判定
                if "Chromium" in user_agent:
                    print("⚠️ 起動されたのはChromiumです（Playwrightの内蔵Chromium）")
                elif "Chrome" in user_agent and "Google" in vendor:
                    print("✅ 起動されたのはGoogle Chromeです")
                else:
                    print(f"❓ 不明なブラウザです: {user_agent}")
                
                # テストページに移動
                await page.goto("chrome://version/", timeout=5000)
                await asyncio.sleep(2)  # ページ読み込み待機
                
                title = await page.title()
                print(f"📄 chrome://version/ タイトル: {title}")
                
            # 5秒待機してからクローズ
            await asyncio.sleep(5)
            await context.close()
            
        except Exception as e:
            print(f"❌ ブラウザ起動エラー: {e}")
            import traceback
            traceback.print_exc()
        
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    asyncio.run(debug_browser_execution())
