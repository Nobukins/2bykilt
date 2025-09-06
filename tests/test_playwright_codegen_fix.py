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
    """playwright codegen のラッパーが自動化スタブモードと通常モードで動作することを検証"""
    test_url = "https://example.com/"

    # 1) AUTOMATE モード (ブラウザ非起動)
    os.environ["PLAYWRIGHT_CODEGEN_AUTOMATE"] = "1"
    auto_ok, auto_script = run_playwright_codegen(test_url, 'chrome')
    assert auto_ok, f"自動化モード失敗: {auto_script}"
    assert "await page.goto" in auto_script

    # 2) 通常モード (環境によってはスキップ)
    os.environ.pop("PLAYWRIGHT_CODEGEN_AUTOMATE", None)
    try:
        normal_ok, normal_result = run_playwright_codegen(test_url, 'chrome')
    except Exception as e:  # 非GUI / CI などでの失敗を許容
        normal_ok, normal_result = False, str(e)

    # 非対話環境では失敗を許容するが、成功した場合は基本構造を確認
    if normal_ok:
        assert "run_actions" in normal_result
    else:
        # 失敗理由はログ用途として残す
        print(f"[INFO] 通常モードはこの環境で失敗: {normal_result}")


if __name__ == "__main__":
    test_playwright_codegen()
