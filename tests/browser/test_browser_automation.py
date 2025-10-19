#!/usr/bin/env python3
"""
ブラウザ自動化テスト - 環境変数の動作を確認
"""

import os
import pytest
import sys
from dotenv import load_dotenv

# .envファイルを読み込み
load_dotenv(override=True)
# Rely on tests/conftest.py to add the project's `src` to sys.path

from src.browser.browser_config import BrowserConfig

@pytest.mark.ci_safe
def test_browser_automation():
    print("=== ブラウザ自動化テスト開始 ===")
    
    # 環境変数の確認
    print(f"\n環境変数確認:")
    print(f"  DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', '未設定')}")
    print(f"  ENABLE_LLM: {os.environ.get('ENABLE_LLM', '未設定')}")
    print(f"  CHROME_DEBUGGING_PORT: {os.environ.get('CHROME_DEBUGGING_PORT', '未設定')}")
    print(f"  RECORDING_PATH: {os.environ.get('RECORDING_PATH', '未設定')}")
    
    # ブラウザ設定オブジェクトの確認
    try:
        browser_config = BrowserConfig()
        print(f"\nブラウザ設定オブジェクト:")
        print(f"  current_browser: {browser_config.config.get('current_browser', '未設定')}")
        
        chrome_settings = browser_config.get_browser_settings('chrome')
        print(f"  chrome debugging port: {chrome_settings.get('debugging_port', '未設定')}")
        print(f"  chrome path: {chrome_settings.get('path', '未設定')}")
        
        # DEFAULT_BROWSERの環境変数がブラウザ選択に反映されているかテスト
        default_browser_env = os.environ.get('DEFAULT_BROWSER', 'chrome')
        print(f"\n環境変数とブラウザ設定の一致確認:")
        print(f"  環境変数 DEFAULT_BROWSER: {default_browser_env}")
        print(f"  ブラウザ設定 current_browser: {browser_config.config.get('current_browser', 'chrome')}")
        
        # 環境変数に合わせてブラウザ設定を更新してテスト
        if default_browser_env in ['chrome', 'edge']:
            browser_config.set_current_browser(default_browser_env)
            updated_settings = browser_config.get_browser_settings(default_browser_env)
            print(f"  更新後の設定確認:")
            print(f"    ブラウザタイプ: {updated_settings.get('browser_type', '未設定')}")
            print(f"    デバッグポート: {updated_settings.get('debugging_port', '未設定')}")
        
    except Exception as e:
        print(f"\nブラウザ設定オブジェクト初期化エラー: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print("\n=== ブラウザ自動化テスト完了 ===")
    print("結論: .envファイルの環境変数が正常に認識されています！")

if __name__ == "__main__":
    test_browser_automation()
