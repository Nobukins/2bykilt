#!/usr/bin/env python3
"""
現在の設定状況とブラウザ起動オプションを表示
"""
import os
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.browser_launcher import BrowserLauncher, ChromeLauncher, EdgeLauncher


def show_current_configuration():
    """現在の設定状況を表示"""
    print("🔍 2bykilt Browser Configuration Report")
    print("=" * 60)
    
    # 環境変数の確認
    print("\n📋 Environment Variables:")
    env_vars = [
        'DEFAULT_BROWSER', 'BYKILT_BROWSER_TYPE', 'BYKILT_USE_NEW_METHOD',
        'CHROME_PATH', 'CHROME_USER_DATA', 'EDGE_PATH', 'EDGE_USER_DATA',
        'PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH', 'PLAYWRIGHT_EDGE_EXECUTABLE_PATH'
    ]
    
    for var in env_vars:
        value = os.environ.get(var, 'NOT SET')
        print(f"  {var}: {value}")
    
    # Chrome設定の確認
    print("\n🔴 Chrome Configuration:")
    try:
        chrome_launcher = ChromeLauncher()
        chrome_info = chrome_launcher.get_detailed_browser_info()
        for key, value in chrome_info.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Edge設定の確認
    print("\n🔵 Edge Configuration:")
    try:
        edge_launcher = EdgeLauncher()
        edge_info = edge_launcher.get_detailed_browser_info()
        for key, value in edge_info.items():
            print(f"  {key}: {value}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # ブラウザファイルの存在確認
    print("\n📁 Browser File Existence Check:")
    browser_paths = {
        "Chrome": os.environ.get('CHROME_PATH', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
        "Edge": os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge'),
        "Playwright Chromium (built-in)": "Built into Playwright"
    }
    
    for name, path in browser_paths.items():
        if path == "Built into Playwright":
            print(f"  {name}: {path}")
        elif Path(path).exists():
            print(f"  {name}: ✅ EXISTS - {path}")
        else:
            print(f"  {name}: ❌ NOT FOUND - {path}")
    
    # 推奨の使用方法
    print("\n💡 Recommended Usage:")
    print("  1. For Google Chrome (with profile):")
    print("     - Set CHROME_PATH to your Chrome executable")
    print("     - Set CHROME_USER_DATA to your Chrome user data directory")
    print("     - Use GitScriptAutomator with browser_type='chrome'")
    print("")
    print("  2. For Microsoft Edge (with profile):")
    print("     - Set EDGE_PATH to your Edge executable")
    print("     - Set EDGE_USER_DATA to your Edge user data directory")
    print("     - Use GitScriptAutomator with browser_type='edge'")
    print("")
    print("  3. For Playwright Chromium (without profile, no API warnings):")
    print("     - Remove or set invalid CHROME_PATH")
    print("     - System will automatically use built-in Chromium")
    print("     - No Google API key warnings")
    
    # 起動方法の説明
    print("\n🚀 How to Launch Browser:")
    print("  Via Python script:")
    print("    from src.utils.git_script_automator import GitScriptAutomator")
    print("    automator = GitScriptAutomator('chrome', '/path/to/chrome/profile')")
    print("    async with automator.browser_context('/tmp/workspace') as context:")
    print("        # Your automation code here")
    print("")
    print("  Via Playwright Codegen (may use built-in Chromium):")
    print("    python -m playwright codegen https://example.com")
    print("")
    print("  Via bykilt.py Playwright Codegen tab:")
    print("    Access 🎭 Playwright Codegen tab in the web interface")
    
    print("\n" + "=" * 60)


if __name__ == "__main__":
    show_current_configuration()
