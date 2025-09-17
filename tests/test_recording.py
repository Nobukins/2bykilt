#!/usr/bin/env python3
"""録画機能のテストスクリプト"""

import asyncio
import sys
from pathlib import Path
from myscript.browser_base import BrowserAutomationBase

async def test_recording():
    """録画機能をテストする"""
    print("=== 録画機能テスト開始 ===")
    
    # テスト用録画ディレクトリ
    test_recording_dir = Path("./tmp/test_recording").resolve()
    
    automation = BrowserAutomationBase(
        headless=False,  # 録画確認のため非ヘッドレス
        slowmo=1000,     # スロー実行
        recording_dir=str(test_recording_dir)
    )
    
    try:
        print(f"📁 録画ディレクトリ: {automation.recording_dir}")
        print(f"🖥️ プラットフォーム: {automation.is_windows and 'Windows' or 'Other'}")
        
        # ブラウザセットアップ
        print("🔧 ブラウザセットアップ中...")
        page = await automation.setup()
        
        print(f"✅ ブラウザセットアップ完了")
        print(f"📹 コンテキスト設定: {automation.context is not None}")
        
        # ディレクトリ存在確認
        print(f"📂 録画ディレクトリ存在: {automation.recording_dir.exists()}")
        if automation.recording_dir.exists():
            print(f"📂 ディレクトリ内容: {list(automation.recording_dir.iterdir())}")
        
        # 自動操作インジケーター表示
        await automation.show_automation_indicator()
        
        # 簡単なブラウザ操作を実行
        print("🌐 テストページにナビゲート中...")
        await page.goto("https://example.com")
        await page.wait_for_timeout(2000)
        
        print("🔍 ページタイトル取得中...")
        title = await page.title()
        print(f"📄 ページタイトル: {title}")
        
        print("⏱️ 追加待機...")
        await page.wait_for_timeout(3000)
        
        # カウントダウン表示
        print("🔚 カウントダウン表示...")
        await automation.show_countdown_overlay(3)
        
        print("🔒 ブラウザクリーンアップ中...")
        await automation.cleanup()
        
        # 録画ファイル確認
        print("\n=== 録画ファイル確認 ===")
        if automation.recording_dir.exists():
            video_files = []
            for ext in ['*.webm', '*.mp4']:
                video_files.extend(list(automation.recording_dir.glob(ext)))
            
            if video_files:
                print(f"✅ 録画ファイルが見つかりました: {len(video_files)}個")
                for video_file in video_files:
                    print(f"  📹 {video_file.name} ({video_file.stat().st_size} bytes)")
            else:
                print("❌ 録画ファイルが見つかりません")
                print(f"📂 ディレクトリ内容: {list(automation.recording_dir.iterdir())}")
        else:
            print("❌ 録画ディレクトリが存在しません")
        
        print("=== テスト完了 ===")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()
        
        try:
            await automation.cleanup()
        except:
            pass

if __name__ == "__main__":
    asyncio.run(test_recording())
