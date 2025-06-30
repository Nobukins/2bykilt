#!/usr/bin/env python3
"""
Windows環境対応テストスクリプト
2bykiltのWindows固有機能をテストします
"""

import sys
import platform
import os
import asyncio
from pathlib import Path

def test_platform_detection():
    """プラットフォーム検出テスト"""
    print("🔍 Platform Detection Test")
    print(f"  Platform: {platform.system()}")
    print(f"  Python: {sys.version}")
    print(f"  Architecture: {platform.architecture()}")
    
    is_windows = platform.system() == "Windows"
    print(f"  Windows detected: {is_windows}")
    
    if is_windows:
        print(f"  Windows version: {platform.release()}")
    
    return is_windows

def test_path_handling():
    """パス処理テスト"""
    print("\n📁 Path Handling Test")
    
    # テスト用パスの作成
    test_paths = [
        "./tmp/test_windows",
        Path.cwd() / "tmp" / "test_windows",
        Path.cwd() / "tmp" / "record_videos"
    ]
    
    for path in test_paths:
        try:
            path_obj = Path(path)
            path_obj.mkdir(parents=True, exist_ok=True)
            print(f"  ✅ Created: {path_obj.resolve()}")
        except Exception as e:
            print(f"  ❌ Failed: {path} - {e}")

def test_subprocess_env():
    """環境変数・subprocessテスト"""
    print("\n🔧 Environment & Subprocess Test")
    
    # 環境変数テスト
    env = os.environ.copy()
    env['PYTHONPATH'] = str(Path.cwd())
    print(f"  PYTHONPATH: {env.get('PYTHONPATH')}")
    print(f"  Python executable: {sys.executable}")
    
    # Windows固有の設定確認
    if platform.system() == "Windows":
        print(f"  Using Windows-specific settings:")
        print(f"    Shell: True")
        print(f"    Executable: {sys.executable}")

def test_browser_path_detection():
    """ブラウザパス検出テスト"""
    print("\n🌐 Browser Path Detection Test")
    
    if platform.system() == "Windows":
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
        ]
        
        print("  Chrome paths:")
        for path in chrome_paths:
            exists = os.path.exists(path)
            print(f"    {'✅' if exists else '❌'} {path}")
        
        print("  Edge paths:")
        for path in edge_paths:
            exists = os.path.exists(path)
            print(f"    {'✅' if exists else '❌'} {path}")
    else:
        print("  Skipping browser detection (not Windows)")

async def test_browser_automation():
    """ブラウザ自動化テスト"""
    print("\n🤖 Browser Automation Test")
    
    try:
        # browser_baseをインポートしてテスト
        from tmp.myscript.browser_base import BrowserAutomationBase
        
        automation = BrowserAutomationBase(
            headless=True,
            recording_dir="./tmp/test_record"
        )
        
        print(f"  Platform detection in BrowserAutomationBase:")
        print(f"    Windows: {automation.is_windows}")
        print(f"    macOS: {automation.is_macos}")
        print(f"    Linux: {automation.is_linux}")
        print(f"    Recording dir: {automation.recording_dir}")
        
        # 簡単なセットアップテスト
        print("  Testing browser setup...")
        try:
            page = await automation.setup()
            print("  ✅ Browser setup successful")
            await automation.cleanup()
            print("  ✅ Browser cleanup successful")
        except Exception as e:
            print(f"  ⚠️ Browser setup failed: {e}")
        
    except ImportError as e:
        print(f"  ⚠️ Cannot test browser automation: {e}")

def test_requirements():
    """依存関係テスト"""
    print("\n📦 Requirements Test")
    
    required_packages = [
        'gradio',
        'playwright',
        'fastapi',
        'psutil',  # Windows対応
        'colorama'  # Windows対応
    ]
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"  ✅ {package}")
        except ImportError:
            print(f"  ❌ {package} (not installed)")

def main():
    """メインテスト実行"""
    print("🔬 Windows Compatibility Test for 2bykilt")
    print("=" * 50)
    
    is_windows = test_platform_detection()
    test_path_handling()
    test_subprocess_env()
    test_browser_path_detection()
    test_requirements()
    
    # 非同期テストの実行
    try:
        asyncio.run(test_browser_automation())
    except Exception as e:
        print(f"\n⚠️ Async test failed: {e}")
    
    print("\n🎯 Test Summary")
    print("=" * 50)
    
    if is_windows:
        print("✅ Running on Windows - all Windows-specific features should work")
        print("📋 Next steps:")
        print("  1. Run: python bykilt.py")
        print("  2. Check browser automation works")
        print("  3. Test recording functionality")
        print("  4. Refer to WINDOWS_SETUP_GUIDE.md for detailed setup")
    else:
        print("ℹ️ Not running on Windows - Windows-specific tests skipped")
        print("📋 Cross-platform compatibility should still work")
    
    print("\n🔗 Useful files:")
    print("  - WINDOWS_SETUP_GUIDE.md: Detailed Windows setup instructions")
    print("  - requirements-minimal.txt: Minimal dependencies with Windows support")
    print("  - LLM_AS_OPTION.prompt.md: Troubleshooting guide")

if __name__ == "__main__":
    main()
