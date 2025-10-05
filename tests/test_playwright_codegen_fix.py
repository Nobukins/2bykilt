#!/usr/bin/env python3
"""
修正後のPlaywright Codegenのテスト
"""
import asyncio
import os
import sys
import pytest

# プロジェクトのルートディレクトリをパスに追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.playwright_codegen import run_playwright_codegen


def test_playwright_codegen_automate_mode():
    """playwright codegen の自動化スタブモードのみをテスト（ブラウザ非起動）"""
    test_url = "https://example.com/"

    # AUTOMATE モード (ブラウザ非起動)
    os.environ["PLAYWRIGHT_CODEGEN_AUTOMATE"] = "1"
    auto_ok, auto_script = run_playwright_codegen(test_url, 'chrome')
    assert auto_ok, f"自動化モード失敗: {auto_script}"
    assert "await page.goto" in auto_script
    
    # cleanup
    os.environ.pop("PLAYWRIGHT_CODEGEN_AUTOMATE", None)


@pytest.mark.skip(reason="通常モードは対話型UIが必要なため、自動テストではスキップ。手動確認用。")
@pytest.mark.timeout(300)
def test_playwright_codegen_normal_mode():
    """playwright codegen の通常モード（手動確認用、自動テストではスキップ）"""
    test_url = "https://example.com/"
    
    normal_ok, normal_result = run_playwright_codegen(test_url, 'chrome')
    if normal_ok:
        assert "run_actions" in normal_result


if __name__ == "__main__":
    test_playwright_codegen_automate_mode()
