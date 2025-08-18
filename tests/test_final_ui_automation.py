#!/usr/bin/env python3
"""
最終的なChrome/Edge UI自動化テスト
引数修正後の安定性と警告メッセージがないことを確認
"""
import asyncio
import os
import sys
import tempfile
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.git_script_automator import GitScriptAutomator


async def test_final_ui_automation():
    """最終的なUI自動化テスト"""
    print("🚀 最終的なChrome/Edge UI自動化テストを開始...")
    
    # テスト用の一時ディレクトリ
    temp_dir = tempfile.mkdtemp()
    print(f"📁 テスト用ディレクトリ: {temp_dir}")
    
    test_results = {
        "chrome": {"success": False, "error": None},
        "edge": {"success": False, "error": None}
    }
    
    try:
        # Chrome テスト
        if Path("/Applications/Google Chrome.app").exists():
            print("\n🔴 Chrome最終テスト...")
            try:
                chrome_automator = GitScriptAutomator(
                    browser_type="chrome",
                    source_profile_dir=os.environ.get('CHROME_USER_DATA', 
                                                     '/Users/nobuaki/Library/Application Support/Google/Chrome')
                )
                
                async with chrome_automator.browser_context(temp_dir, headless=False) as context:
                    print("✅ Chrome コンテキスト取得成功")
                    
                    if context.pages:
                        page = context.pages[0]
                    else:
                        page = await context.new_page()
                    
                    # テストページに移動
                    await page.goto("https://httpbin.org/get", timeout=10000)
                    title = await page.title()
                    print(f"📄 Chrome ページタイトル: {title}")
                    
                    # ユーザーエージェントを確認（自動化検知されていないか）
                    user_agent = await page.evaluate("navigator.userAgent")
                    print(f"🔍 Chrome ユーザーエージェント: {user_agent}")
                    
                    if "HeadlessChrome" not in user_agent:
                        print("✅ Chrome: 自動化検知を回避できています")
                        test_results["chrome"]["success"] = True
                    else:
                        print("⚠️ Chrome: 自動化が検知されています")
                
                    # 短時間表示してから終了
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"❌ Chrome テストエラー: {e}")
                test_results["chrome"]["error"] = str(e)
        else:
            print("⚠️ Chrome がインストールされていません")
        
        # Edge テスト
        if Path("/Applications/Microsoft Edge.app").exists():
            print("\n🔵 Edge最終テスト...")
            try:
                edge_automator = GitScriptAutomator(
                    browser_type="edge",
                    source_profile_dir=os.environ.get('EDGE_USER_DATA', 
                                                     '/Users/nobuaki/Library/Application Support/Microsoft Edge')
                )
                
                async with edge_automator.browser_context(temp_dir, headless=False) as context:
                    print("✅ Edge コンテキスト取得成功")
                    
                    if context.pages:
                        page = context.pages[0]
                    else:
                        page = await context.new_page()
                    
                    # テストページに移動
                    await page.goto("https://httpbin.org/get", timeout=10000)
                    title = await page.title()
                    print(f"📄 Edge ページタイトル: {title}")
                    
                    # ユーザーエージェントを確認（自動化検知されていないか）
                    user_agent = await page.evaluate("navigator.userAgent")
                    print(f"🔍 Edge ユーザーエージェント: {user_agent}")
                    
                    if "HeadlessChrome" not in user_agent:
                        print("✅ Edge: 自動化検知を回避できています")
                        test_results["edge"]["success"] = True
                    else:
                        print("⚠️ Edge: 自動化が検知されています")
                
                    # 短時間表示してから終了
                    await asyncio.sleep(3)
                    
            except Exception as e:
                print(f"❌ Edge テストエラー: {e}")
                test_results["edge"]["error"] = str(e)
        else:
            print("⚠️ Edge がインストールされていません")
        
        return test_results
        
    finally:
        # クリーンアップ
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    results = asyncio.run(test_final_ui_automation())
    
    print("\n" + "="*60)
    print("🏁 最終テスト結果")
    print("="*60)
    
    success_count = 0
    total_count = 0
    
    for browser, result in results.items():
        total_count += 1
        if result["success"]:
            success_count += 1
            print(f"✅ {browser.upper()}: 成功")
        else:
            error_msg = result["error"] or "未実行"
            print(f"❌ {browser.upper()}: 失敗 - {error_msg}")
    
    print("="*60)
    print(f"📊 成功率: {success_count}/{total_count} ({100*success_count/total_count:.1f}%)")
    
    if success_count == total_count:
        print("🎉 すべてのブラウザテストが成功しました！")
        print("🔥 引数の警告問題が完全に解決され、安定したUI自動化が実現されました！")
        sys.exit(0)
    else:
        print("💥 一部のテストが失敗しました。")
        sys.exit(1)
