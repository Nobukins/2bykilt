#!/usr/bin/env python3
"""
環境変数のテストスクリプト
bykilt.pyと同様に.envファイルを読み込んで環境変数を確認
"""

import os
import pytest
from dotenv import load_dotenv

@pytest.mark.ci_safe
def test_env_vars():
    print("=== 環境変数テスト開始 ===")
    
    # システム環境変数の確認（.env読み込み前）
    print("\n1. システム環境変数（.env読み込み前）:")
    print(f"   DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', '未設定')}")
    print(f"   ENABLE_LLM: {os.environ.get('ENABLE_LLM', '未設定')}")
    print(f"   RECORDING_PATH: {os.environ.get('RECORDING_PATH', '未設定')}")
    print(f"   HEADLESS: {os.environ.get('HEADLESS', '未設定')}")
    
    # .envファイルを読み込み（override=True）
    print("\n2. .envファイル読み込み（override=True）:")
    load_dotenv(override=True)
    print(f"   DEFAULT_BROWSER: {os.environ.get('DEFAULT_BROWSER', '未設定')}")
    print(f"   ENABLE_LLM: {os.environ.get('ENABLE_LLM', '未設定')}")
    print(f"   RECORDING_PATH: {os.environ.get('RECORDING_PATH', '未設定')}")
    print(f"   HEADLESS: {os.environ.get('HEADLESS', '未設定')}")
    
    # .envファイルの内容確認
    print("\n3. .envファイルの主要設定:")
    try:
        with open('.env', 'r') as f:
            lines = f.readlines()
            for i, line in enumerate(lines, 1):
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    if any(var in line for var in ['DEFAULT_BROWSER', 'ENABLE_LLM', 'RECORDING_PATH', 'HEADLESS']):
                        print(f"   行{i}: {line}")
    except FileNotFoundError:
        print("   .envファイルが見つかりません")
    
    print("\n=== 環境変数テスト完了 ===")

if __name__ == "__main__":
    test_env_vars()
