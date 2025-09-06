#!/usr/bin/env python3
"""
ブラウザ引数の警告メッセージ検証スクリプト
Chrome/Edgeで不正な引数による警告が表示されないことを確認
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
from src.utils.git_script_automator import GitScriptAutomator


async def test_browser_arguments_validation():
    """ブラウザ引数の検証テスト"""
    print("🔍 ブラウザ引数の検証テストを開始...")
    
    # テスト用の一時ディレクトリ
    temp_dir = tempfile.mkdtemp()
    print(f"📁 テスト用ディレクトリ: {temp_dir}")
    
    try:
        # Chrome テスト
        print("\n🔴 Chrome引数の検証...")
        chrome_launcher = ChromeLauncher()
        chrome_args = chrome_launcher._get_browser_args()
        print(f"📊 Chrome引数数: {len(chrome_args)}")
        print("🔧 Chrome引数:")
        for i, arg in enumerate(chrome_args, 1):
            print(f"  {i:2d}. {arg}")
        
        # Edge テスト
        print("\n🔵 Edge引数の検証...")
        edge_launcher = EdgeLauncher()
        edge_args = edge_launcher._get_browser_args()
        print(f"📊 Edge引数数: {len(edge_args)}")
        print("🔧 Edge引数:")
        for i, arg in enumerate(edge_args, 1):
            print(f"  {i:2d}. {arg}")
        
        # macOSで問題のある引数をチェック
        problematic_args = [
            "--no-sandbox",            # Linuxでのみ有効
            "--disable-dev-shm-usage", # Linuxでのみ有効
            "--memory-pressure-off",   # 古いバージョンでのみ有効
            "--max_old_space_size",    # Node.js引数、ブラウザでは無効
            "--js-flags",              # V8エンジン直接制御、現在は非推奨
            "--disable-singleton-lock", # プロファイルロック制御、現在は不要
        ]
        
        print("\n⚠️ 問題のある引数の確認...")
        chrome_issues = []
        edge_issues = []
        
        for arg in chrome_args:
            for problematic in problematic_args:
                if problematic in arg:
                    chrome_issues.append(arg)
        
        for arg in edge_args:
            for problematic in problematic_args:
                if problematic in arg:
                    edge_issues.append(arg)
        
        if chrome_issues:
            print("❌ Chrome で問題のある引数が検出されました:")
            for issue in chrome_issues:
                print(f"  - {issue}")
        else:
            print("✅ Chrome: 問題のある引数は検出されませんでした")
        
        if edge_issues:
            print("❌ Edge で問題のある引数が検出されました:")
            for issue in edge_issues:
                print(f"  - {issue}")
        else:
            print("✅ Edge: 問題のある引数は検出されませんでした")
        
        # 実際のブラウザ起動テスト（ヘッドフルモード、短時間のみ）
        if Path("/Applications/Google Chrome.app").exists():
            print("\n🚀 Chrome実起動テスト（5秒間）...")
            try:
                chrome_profile_mgr = ProfileManager(
                    source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                                     '/Users/nobuaki/Library/Application Support/Google/Chrome')
                )
                selenium_profile = chrome_profile_mgr.create_selenium_profile(temp_dir)
                
                context = await chrome_launcher.launch_with_profile(selenium_profile)
                print("✅ Chrome が正常に起動しました")
                if context.pages:
                    page = context.pages[0]
                    await page.goto("https://httpbin.org/user-agent", timeout=5000)
                    print(f"📄 ページタイトル: {await page.title()}")
                
                # 5秒待機してからクローズ
                await asyncio.sleep(5)
                await context.close()
                
                print("✅ Chrome テスト完了")
                    
            except Exception as e:
                print(f"❌ Chrome テストエラー: {e}")
        
        if Path("/Applications/Microsoft Edge.app").exists():
            print("\n🚀 Edge実起動テスト（5秒間）...")
            try:
                edge_profile_mgr = ProfileManager(
                    source_profile_dir=os.environ.get('EDGE_USER_DATA', 
                                                     '/Users/nobuaki/Library/Application Support/Microsoft Edge')
                )
                selenium_profile = edge_profile_mgr.create_selenium_profile(temp_dir)
                
                context = await edge_launcher.launch_with_profile(selenium_profile)
                print("✅ Edge が正常に起動しました")
                if context.pages:
                    page = context.pages[0]
                    await page.goto("https://httpbin.org/user-agent", timeout=5000)
                    print(f"📄 ページタイトル: {await page.title()}")
                
                # 5秒待機してからクローズ
                await asyncio.sleep(5)
                await context.close()
                
                print("✅ Edge テスト完了")
                    
            except Exception as e:
                print(f"❌ Edge テストエラー: {e}")
        
        return chrome_issues == [] and edge_issues == []
        
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    result = asyncio.run(test_browser_arguments_validation())
    if result:
        print("\n🎉 すべての引数検証テストが成功しました！")
        sys.exit(0)
    else:
        print("\n💥 引数に問題が検出されました。修正が必要です。")
        sys.exit(1)
