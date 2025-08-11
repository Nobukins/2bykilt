#!/usr/bin/env python3
"""
プロセス確認テスト - 起動されたブラウザプロセスを詳細に確認
"""

import os
import sys
import asyncio
import subprocess
import psutil
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(override=True)

# プロジェクトのsrcディレクトリをPythonパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from browser.browser_manager import initialize_browser

async def process_verification_test():
    print("=== プロセス確認テスト開始 ===")
    
    print("\n🔍 テスト前のブラウザプロセス確認:")
    chrome_processes_before = []
    for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
        try:
            if proc.info['name'] and ('chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower()):
                chrome_processes_before.append(proc.info)
                print(f"  PID: {proc.info['pid']}, Name: {proc.info['name']}, Exe: {proc.info['exe']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    
    print(f"\n🚀 ブラウザ起動中...")
    try:
        result = await initialize_browser(
            use_own_browser=False,
            headless=False,
            browser_type=None,
            auto_fallback=True
        )
        
        if result.get("status") == "success":
            browser = result["browser"]
            
            print(f"\n🔍 テスト後のブラウザプロセス確認:")
            chrome_processes_after = []
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    if proc.info['name'] and ('chrome' in proc.info['name'].lower() or 'chromium' in proc.info['name'].lower()):
                        chrome_processes_after.append(proc.info)
                        if proc.info not in chrome_processes_before:
                            print(f"  新規プロセス - PID: {proc.info['pid']}, Name: {proc.info['name']}")
                            print(f"    実行ファイル: {proc.info['exe']}")
                            if proc.info['cmdline']:
                                print(f"    コマンドライン: {' '.join(proc.info['cmdline'][:3])}...")  # 最初の3要素のみ表示
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # ページを作成してブラウザ情報を取得
            page = await browser.new_page()
            
            # より詳細なブラウザ情報を取得
            browser_info = await page.evaluate("""
                () => {
                    return {
                        userAgent: navigator.userAgent,
                        vendor: navigator.vendor,
                        appName: navigator.appName,
                        appVersion: navigator.appVersion,
                        platform: navigator.platform,
                        language: navigator.language,
                        webdriver: navigator.webdriver,
                        chrome: typeof window.chrome !== 'undefined',
                        webkitGetUserMedia: typeof navigator.webkitGetUserMedia !== 'undefined'
                    };
                }
            """)
            
            print(f"\n📊 詳細ブラウザ情報:")
            for key, value in browser_info.items():
                print(f"  {key}: {value}")
            
            # Chrome固有のプロパティをチェック
            chrome_specific = await page.evaluate("""
                () => {
                    const isChrome = /Chrome/.test(navigator.userAgent) && /Google Inc/.test(navigator.vendor);
                    const isChromium = /Chromium/.test(navigator.userAgent);
                    
                    return {
                        isChrome: isChrome,
                        isChromium: isChromium,
                        hasGoogleAnalytics: typeof window.ga !== 'undefined',
                        chromeLoadTimes: typeof window.chrome?.loadTimes === 'function',
                        chromeRuntime: typeof window.chrome?.runtime !== 'undefined'
                    };
                }
            """)
            
            print(f"\n🔍 Chrome/Chromium判定:")
            for key, value in chrome_specific.items():
                print(f"  {key}: {value}")
            
            await page.close()
            await browser.close()
            
        else:
            print(f"❌ ブラウザ起動失敗: {result.get('message', 'Unknown error')}")
            
    except Exception as e:
        print(f"❌ テスト中にエラー: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n=== プロセス確認テスト完了 ===")

if __name__ == "__main__":
    asyncio.run(process_verification_test())
