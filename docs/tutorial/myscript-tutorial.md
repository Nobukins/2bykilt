# myscript チュートリアル

## 🎯 概要

このチュートリアルでは、2bykiltの `myscript/` ディレクトリを使用したブラウザ自動化スクリプトの開発方法を学習します。`myscript/` は、実行スクリプトと生成物を分離し、一貫したパス管理を行うための標準化された環境です。

## 📋 前提条件

- Python 3.11 以上
- Playwright がインストール済み
- 基本的な Python プログラミング知識
- コマンドライン操作の基礎知識

## 🛠️ 環境セットアップ

### 1. 基本的な環境変数設定

```bash
# 録画・生成物の出力先ディレクトリ（必須）
export RECORDING_PATH="./artifacts/my-first-script"

# プロジェクトのベースディレクトリ（オプション）
export BASE_DIR="$(pwd)"
```

### 2. ディレクトリ構造の確認

```
myscript/
  bin/              # 実行可能スクリプトを配置
  templates/        # スクリプトテンプレート
  helpers/          # 再利用可能なヘルパーモジュール
  README.md         # 利用方法の概要
```

## 📝 最初のスクリプト作成

### ステップ 1: スクリプトファイルの作成

`myscript/bin/` ディレクトリに新しいスクリプトファイルを作成します。

```bash
# スクリプトファイルを作成
touch myscript/bin/my_first_script.py
```

### ステップ 2: 基本的なスクリプト構造

`myscript/bin/my_first_script.py` を編集：

```python
#!/usr/bin/env python3
"""
My First myscript - 基本的なブラウザ自動化スクリプト
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def log_message(message):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def ensure_recording_path():
    """RECORDING_PATH環境変数を確認"""
    recording_path = os.environ.get("RECORDING_PATH")
    if not recording_path:
        log_message("❌ エラー: RECORDING_PATH環境変数が設定されていません")
        log_message("💡 例: export RECORDING_PATH=./artifacts/my-script")
        sys.exit(1)

    recording_dir = Path(recording_path)
    recording_dir.mkdir(parents=True, exist_ok=True)
    log_message(f"📁 RECORDING_PATH確認: {recording_dir}")
    return recording_dir

async def main():
    """メイン処理"""
    log_message("🚀 My First Script 開始")

    # RECORDING_PATH の確認
    recording_dir = ensure_recording_path()

    # ここにブラウザ自動化のコードを追加
    log_message("✅ スクリプト実行完了")

if __name__ == "__main__":
    asyncio.run(main())
```

### ステップ 3: スクリプトの実行

```bash
# 実行権限を付与
chmod +x myscript/bin/my_first_script.py

# 環境変数を設定
export RECORDING_PATH="./artifacts/my-first-script"

# スクリプトを実行
python myscript/bin/my_first_script.py
```

## 🌐 Playwright との連携

### ステップ 1: Playwright を使用したブラウザ操作

より実践的なスクリプトを作成します：

```python
#!/usr/bin/env python3
"""
Web Search Script - Playwright を使用した検索スクリプト
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from playwright.async_api import async_playwright

# プロジェクトルートを Python パスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def log_message(message):
    """ログメッセージを出力"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")

def ensure_recording_path():
    """RECORDING_PATH環境変数を確認"""
    recording_path = os.environ.get("RECORDING_PATH")
    if not recording_path:
        log_message("❌ エラー: RECORDING_PATH環境変数が設定されていません")
        sys.exit(1)

    recording_dir = Path(recording_path)
    recording_dir.mkdir(parents=True, exist_ok=True)
    log_message(f"📁 RECORDING_PATH確認: {recording_dir}")
    return recording_dir

async def run_browser_automation(recording_dir):
    """ブラウザ自動化のメイン処理"""
    async with async_playwright() as p:
        # ブラウザを起動
        browser = await p.chromium.launch(headless=False)

        # 録画設定付きのコンテキストを作成
        context = await browser.new_context(record_video_dir=str(recording_dir))
        page = await context.new_page()
        # 録画は context 作成時に自動で開始されます

        try:
            # Google にアクセス
            log_message("🌐 Google にアクセス中...")
            await page.goto("https://www.google.com")

            # 検索ボックスにキーワードを入力
            search_query = "2bykilt browser automation"
            log_message(f"🔍 検索キーワード: {search_query}")
            await page.fill('input[name="q"]', search_query)

            # 検索を実行
            await page.press('input[name="q"]', 'Enter')

            # 検索結果を待機
            await page.wait_for_load_state('networkidle')
            log_message("✅ 検索完了")

            # スクリーンショットを撮影
            screenshot_path = recording_dir / "search_result.png"
            await page.screenshot(path=str(screenshot_path))
            log_message(f"📸 スクリーンショット保存: {screenshot_path}")

            # 少し待機して結果を確認
            await page.wait_for_timeout(3000)

        finally:
            # ブラウザを閉じる
            await browser.close()

async def main():
    """メイン処理"""
    log_message("🚀 Web Search Script 開始")

    # RECORDING_PATH の確認
    recording_dir = ensure_recording_path()

    # ブラウザ自動化を実行
    await run_browser_automation(recording_dir)

    log_message("✅ Web Search Script 完了")

if __name__ == "__main__":
    asyncio.run(main())
```

### ステップ 2: 実行と結果の確認

```bash
# 環境変数を設定
export RECORDING_PATH="./artifacts/web-search-demo"

# スクリプトを実行
python myscript/bin/web_search_script.py

# 生成されたファイルを確認
ls -la ./artifacts/web-search-demo/
```

## 📊 アーティファクト管理

### 動画録画の追加

```python
async def run_browser_automation_with_recording(recording_dir):
    """録画機能付きブラウザ自動化"""
    async with async_playwright() as p:
        # 録画設定付きでブラウザを起動
        browser = await p.chromium.launch(
            headless=False,
            args=[
                '--window-size=1280,720',
                '--no-sandbox',
                '--disable-setuid-sandbox'
            ]
        )

        # 録画設定付きのコンテキストを作成
        context = await browser.new_context(
            record_video_dir=str(recording_dir),
            record_video_size={"width": 1280, "height": 720}
        )

        page = await context.new_page()

        try:
            # 自動化処理
            await page.goto("https://example.com")
            await page.wait_for_timeout(2000)

            # 何らかの操作
            await page.click('text="More information"')
            await page.wait_for_timeout(2000)

        finally:
            await context.close()
            await browser.close()
```

### マニフェストファイルの作成

```python
import json

def create_manifest(recording_dir, script_info):
    """マニフェストファイルを作成"""
    manifest = {
        "script_name": script_info.get("name", "unknown"),
        "execution_time": datetime.now().isoformat(),
        "recording_path": str(recording_dir),
        "artifacts": []
    }

    # 生成されたファイルを検出
    for file_path in recording_dir.glob("*"):
        if file_path.is_file():
            artifact_info = {
                "filename": file_path.name,
                "path": str(file_path),
                "size": file_path.stat().st_size,
                "type": file_path.suffix
            }
            manifest["artifacts"].append(artifact_info)

    # マニフェストファイルを保存
    manifest_path = recording_dir / "manifest.json"
    with open(manifest_path, 'w', encoding='utf-8') as f:
        json.dump(manifest, f, indent=2, ensure_ascii=False)

    log_message(f"📋 マニフェスト作成: {manifest_path}")
```

## 🔧 高度なテクニック

### 1. 設定ファイルの使用

`myscript/config.json` を作成：

```json
{
  "default_browser": "chrome",
  "default_timeout": 30000,
  "screenshots": {
    "enabled": true,
    "format": "png",
    "quality": 90
  },
  "recording": {
    "enabled": true,
    "size": {
      "width": 1280,
      "height": 720
    }
  }
}
```

### 2. ヘルパーモジュールの作成

`myscript/helpers/browser_utils.py` を作成：

```python
"""
Browser utilities for myscript
"""

import json
from pathlib import Path
from typing import Optional

def load_config(config_path: Optional[Path] = None) -> dict:
    """設定ファイルを読み込み"""
    if config_path is None:
        config_path = Path(__file__).parent.parent / "config.json"

    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    return {}

def get_recording_path():
    """RECORDING_PATH環境変数からパスを取得"""
    recording_path = os.environ.get("RECORDING_PATH")
    if not recording_path:
        raise ValueError("RECORDING_PATH環境変数が設定されていません")
    return Path(recording_path)

def setup_browser_context(playwright, config: dict):
    """ブラウザコンテキストを設定"""
    browser_type = config.get("default_browser", "chromium")

    launch_options = {
        "headless": False,
        "args": [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--window-size=1280,720'
        ]
    }

    if config.get("recording", {}).get("enabled", False):
        recording_config = config["recording"]
        launch_options["record_video_dir"] = str(get_recording_path())
        launch_options["record_video_size"] = recording_config["size"]

    return launch_options
```

### 3. エラーハンドリングの改善

```python
class ScriptError(Exception):
    """スクリプト実行時のカスタムエラー"""
    pass

async def safe_browser_operation(page, operation_func, max_retries=3):
    """安全なブラウザ操作（リトライ機能付き）"""
    for attempt in range(max_retries):
        try:
            return await operation_func(page)
        except Exception as e:
            log_message(f"⚠️ 操作失敗 (試行 {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                await page.wait_for_timeout(1000 * (attempt + 1))  # 待機時間を増やす
            else:
                raise ScriptError(f"操作が {max_retries} 回失敗しました: {e}")
```

## 🐛 トラブルシューティング

### よくある問題と解決法

#### 1. RECORDING_PATH が設定されていない

```
❌ エラー: RECORDING_PATH環境変数が設定されていません
```

**解決法:**
```bash
export RECORDING_PATH="./artifacts/my-script"
```

#### 2. ブラウザが起動しない

**解決法:**
```bash
# Playwright ブラウザのインストールを確認
playwright install chromium

# または特定のブラウザを指定
playwright install chrome
```

#### 3. 権限エラー

**解決法:**
```bash
# artifacts ディレクトリの権限を確認
chmod 755 ./artifacts

# または新規作成
mkdir -p ./artifacts/my-script
```

#### 4. モジュールが見つからない

**解決法:**
```python
# Python パスにプロジェクトルートを追加
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
```

## 📚 次のステップ

### 学習リソース

1. **Playwright 公式ドキュメント**: https://playwright.dev/python/
2. **Python asyncio チュートリアル**: https://docs.python.org/3/library/asyncio.html
3. **pathlib モジュール**: https://docs.python.org/3/library/pathlib.html

### 実践的なプロジェクト

- ウェブスクレイピングスクリプト
- フォーム自動入力ツール
- E2E テストスイート
- データ収集パイプライン

### ベストプラクティス

- 常に `RECORDING_PATH` を検証する
- エラーハンドリングを適切に実装する
- ログを詳細に出力する
- 設定を外部ファイルで管理する
- 再利用可能なヘルパー関数を作成する

## 🎉 まとめ

このチュートリアルでは、以下のことを学習しました：

- ✅ myscript ディレクトリの構造と役割
- ✅ RECORDING_PATH 環境変数の使用方法
- ✅ 基本的なブラウザ自動化スクリプトの作成
- ✅ Playwright との連携方法
- ✅ アーティファクトの管理
- ✅ エラーハンドリングとトラブルシューティング

これであなたも myscript を使用したブラウザ自動化のエキスパートです！ 🚀

## 📞 サポート

質問や問題がある場合は：

- [GitHub Issues](../../issues) でバグ報告
- [Discussions](../../discussions) で質問
- [CONTRIBUTING.md](../../CONTRIBUTING.md) で詳細なガイドラインを確認