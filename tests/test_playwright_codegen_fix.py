#!/usr/bin/env python3
"""
修正後のPlaywright Codegenのテスト
"""
import asyncio
import os
import sys

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.playwright_codegen import run_playwright_codegen


def test_playwright_codegen():
    """修正後のplaywright_codegenをテスト"""
    print("🎭 Playwright Codegen テスト")
    print("=" * 50)
    
    # 現在の設定を表示
    print("\n📋 Current Settings:")
    print(f"  CHROME_PATH: {os.environ.get('CHROME_PATH', 'NOT SET')}")
    print(f"  EDGE_PATH: {os.environ.get('EDGE_PATH', 'NOT SET')}")
    
    test_url = "https://httpbin.org/get"
    
    # Chromeテスト
    print(f"\n🔴 Testing Chrome codegen with URL: {test_url}")
    print("⚠️ Note: This will actually launch a browser for codegen")
    print("   Close the browser window after a few seconds to continue the test")
    
    try:
        success, result = run_playwright_codegen(test_url, 'chrome')
        if success:
            print("✅ Chrome codegen completed successfully")
            print(f"📄 Generated script length: {len(result)} characters")
        else:
            print(f"❌ Chrome codegen failed: {result}")
    except Exception as e:
        print(f"❌ Chrome codegen error: {e}")
    
    print("\n" + "=" * 50)
    print("🏁 Test completed")
    print("💡 If you saw Google Chrome (not Chromium) launch, the fix is working!")
    print("💡 If you saw Chromium launch, check your CHROME_PATH setting")


if __name__ == "__main__":
    test_playwright_codegen()
