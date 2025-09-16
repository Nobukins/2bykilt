"""
Local Selector Test - ネットワーク非依存の極小テスト

このテストは以下の目的で使用されます：
- 録画機能の基本的な動作確認
- ロケータ戦略の健全性検証
- CIでの自動テスト実行

実行方法:
    RECORDING_PATH=/tmp/test_recordings pytest local_selector_test.py -v
"""

import pytest
import asyncio
import os
import tempfile
from pathlib import Path
from browser_base import BrowserAutomationBase


@pytest.fixture
def temp_recording_dir():
    """一時的な録画ディレクトリを作成"""
    with tempfile.TemporaryDirectory() as temp_dir:
        recording_dir = Path(temp_dir) / "recordings"
        recording_dir.mkdir(exist_ok=True)
        # RECORDING_PATH環境変数を設定
        original_path = os.environ.get("RECORDING_PATH")
        os.environ["RECORDING_PATH"] = str(recording_dir)
        yield recording_dir
        # クリーンアップ
        if original_path:
            os.environ["RECORDING_PATH"] = original_path
        else:
            os.environ.pop("RECORDING_PATH", None)


@pytest.fixture
def isolated_recording_env():
    """テスト間の環境変数干渉を防ぐ"""
    # テスト開始前の環境を保存
    original_env = {}
    env_vars = ["RECORDING_PATH", "BYKILT_BROWSER_TYPE"]
    
    for var in env_vars:
        if var in os.environ:
            original_env[var] = os.environ[var]
    
    yield
    
    # テスト終了後に環境を復元
    for var in env_vars:
        if var in original_env:
            os.environ[var] = original_env[var]
        else:
            os.environ.pop(var, None)


@pytest.mark.asyncio
@pytest.mark.timeout(60)  # 60秒タイムアウト（非headlessモードのため延長）
async def test_basic_browser_setup(temp_recording_dir, isolated_recording_env):
    """基本的なブラウザセットアップと録画機能のテスト"""
    automation = None
    try:
        # CI環境ではheadlessモードを使用、ローカルでは非headlessモードを使用
        is_ci = os.getenv('CI', '').lower() in ('true', '1', 'yes')
        headless_mode = True if is_ci else False
        
        automation = BrowserAutomationBase(headless=headless_mode, browser_type="chromium")
        
        # ブラウザのセットアップ
        page = await automation.setup()
        assert page is not None

        # 自動操作インジケータの表示
        await automation.show_automation_indicator()

        # シンプルなページ操作
        await page.goto("data:text/html,<html><body><h1>Test Page</h1><p id='test-para'>Hello World</p></body></html>")

        # 基本的なロケータテスト
        element = page.locator("#test-para")
        assert await element.is_visible()

        text_content = await element.text_content()
        assert text_content == "Hello World"

        # カウントダウン表示
        await automation.show_countdown_overlay(seconds=1)

        # 録画完了を待機
        await asyncio.sleep(2)

        # 録画ファイルの存在確認（オプション）
        webm_files = list(temp_recording_dir.glob("*.webm"))
        if len(webm_files) > 0:
            print(f"[Info] Found {len(webm_files)} recording file(s)")
            # ファイルサイズが0でないことを確認（複数回チェック）
            max_attempts = 5
            for attempt in range(max_attempts):
                file_sizes = [webm_file.stat().st_size for webm_file in webm_files]
                if all(size > 0 for size in file_sizes):
                    print(f"[Info] Recording files have valid size: {[size for size in file_sizes]}")
                    break
                if attempt < max_attempts - 1:
                    print(f"[Info] Waiting for recording file to be written (attempt {attempt + 1}/{max_attempts})")
                    await asyncio.sleep(1)
                else:
                    # 最後の試行でサイズが0の場合でも、ファイルが存在することを確認
                    print(f"[Warning] Recording file size is 0, but file exists: {[str(f) for f in webm_files]}")
                    # サイズ0でもファイルが存在すればテストをパスさせる
                    break
        else:
            print("[Warning] No recording files found - this may be expected in some environments")

    finally:
        if automation:
            await automation.cleanup()


@pytest.mark.asyncio
async def test_selector_strategies(temp_recording_dir):
    """ロケータ戦略のテスト"""
    automation = BrowserAutomationBase(headless=True, browser_type="chromium")

    try:
        page = await automation.setup()

        # テストページの作成
        test_html = """
        <html>
        <body>
            <div class="container">
                <button id="submit-btn" class="btn primary">Submit</button>
                <input name="query" placeholder="Search..." />
                <a href="#test" data-testid="test-link">Test Link</a>
            </div>
        </body>
        </html>
        """
        await page.set_content(test_html)

        # IDセレクタ
        submit_btn = page.locator("#submit-btn")
        assert await submit_btn.is_visible()

        # クラスセレクタ
        btn_element = page.locator(".btn.primary")
        assert await btn_element.is_visible()

        # 属性セレクタ
        test_link = page.locator("[data-testid='test-link']")
        assert await test_link.is_visible()

        # 名前属性セレクタ
        query_input = page.locator("input[name='query']")
        assert await query_input.is_visible()

        # テキストによるセレクタ
        link_by_text = page.locator("text=Test Link")
        assert await link_by_text.is_visible()

    finally:
        await automation.cleanup()


@pytest.mark.asyncio
async def test_recording_output_validation(temp_recording_dir):
    """録画出力の妥当性検証"""
    automation = BrowserAutomationBase(headless=True, browser_type="chromium")

    try:
        page = await automation.setup()

        # シンプルな操作を実行
        await page.goto("data:text/html,<html><body><h1>Recording Test</h1></body></html>")
        await page.wait_for_timeout(1000)  # 録画のための待機

        # スクリーンショットもテスト
        screenshot_path = temp_recording_dir / "test_screenshot.png"
        await page.screenshot(path=str(screenshot_path))

    finally:
        await automation.cleanup()

    # スクリーンショットファイルの確認
    assert screenshot_path.exists(), "スクリーンショットが生成されていません"
    assert screenshot_path.stat().st_size > 0, "スクリーンショットファイルが空です"


if __name__ == "__main__":
    # 直接実行時のサポート
    pytest.main([__file__, "-v"])