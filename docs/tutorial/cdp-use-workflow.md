# CDP-use 実行ワークフローチュートリアル

## 🎯 ゴール

このチュートリアルでは、2bykilt に統合された `cdp-use` ベースのブラウザエンジンを有効化し、Playwright エンジンとの切り替えや実行結果の確認、トレース/テレメトリーの取得方法を学びます。Phase0〜4 で整備した Runner 抽象化・モダン UI・セキュリティ統制を前提に、安全かつ段階的に CDP 経路を利用できるようになります。

## ✅ 成果物の確認ポイント

- `CDPEngine` が `EngineLoader` に登録されており、`runner.engine=cdp` で自動選択できる。
- Modern UI (Gradio) の設定パネルから Playwright / CDP を動的に切り替えられる。
- Unlock Future コマンドを CDP エンジンで実行し、スクリーンショットとトレース ZIP を生成できる。
- `logs/` と `artifacts/` に CDP 固有のメトリクスが残り、テレメトリーが `metrics/` 経由で集計される。

## 🧩 前提条件

| 項目 | 詳細 |
|------|------|
| Python | 3.11 以上 (プロジェクトは `venv312` を標準化) |
| 依存パッケージ | `pip install -r requirements.txt` 実行済み |
| ブラウザ | `playwright install chromium` 完了済み |
| CDP ライブラリ | `pip install "cdp-use>=0.6.0"` |
| FFmpeg (任意) | トレース/動画プレビューを行う場合に推奨 |

> 💡 `install-minimal.sh` を利用する場合でも、CDP 経路を使う際は `cdp-use` の追加インストールが必須です。

## 1. エンジンの有効化と検証

### 1.1 利用可能エンジンの確認

プロジェクトルートで Python REPL または下記スニペットを実行し、`cdp` が認識されていることを確認します。

```python
from src.browser.engine.loader import EngineLoader
print(EngineLoader.list_available_engines())  # 例: ['playwright', 'cdp']
```

`cdp` が表示されない場合は `cdp-use` のインストールを再確認してください。

### 1.2 環境変数で切り替える

最もシンプルな方法は `RUNNER_ENGINE=cdp` を設定してからコマンドを実行することです。`EngineLoader.load_engine()` は `RUNNER_ENGINE` → Feature Flag → デフォルト (playwright) の優先順でエンジンを決定します。

| 環境変数 | 意味 | 既定値 |
|----------|------|--------|
| `RUNNER_ENGINE` | `playwright` / `cdp` | `playwright` |
| `ENABLE_LLM` | LLM サンドボックスの有効化 | `false` |
| `UI_MODERN_LAYOUT` | Modern UI レイアウト | `false` |

### 1.3 FeatureFlags API で切り替える

`src/config/feature_flags.py` のランタイムオーバーライドを利用すると、アプリケーション稼働中に切り替えできます。

```python
from src.config.feature_flags import FeatureFlags

FeatureFlags.set_override("runner.engine", "cdp")
print(FeatureFlags.get("runner.engine"))  # -> 'cdp'
```

Modern UI の設定パネルも内部的にこのメソッドを利用しています。

## 2. Modern UI からの切り替え手順

Modern UI は Phase3 で導入した Gradio ベースの画面です。設定パネルからワンクリックでエンジンと関連フラグを切り替えられます。

1. サーバーを起動します。

    ```bash
    python -m src.ui.main_ui
    ```

2. ブラウザで表示される UI の「⚙️ 設定 / Settings」タブを開きます。
3. 「ブラウザエンジン」アコーディオン内のドロップダウンから `cdp` を選択します。
4. **現行エンジン** 表示が `cdp` になり、`override:runtime` バッジが付いたら切り替え成功です。
5. 必要に応じて `ui.modern_layout` や `ui.trace_viewer` のチェックボックスも ON にします。

> ℹ️ Modern UI を閉じるとランタイムオーバーライドはリセットされます。永続化したい場合は環境変数または `.env` で設定してください。

## 3. Unlock Future コマンドを CDP 経路で実行する

### 3.1 サンプル JSON の作成

`myscript/templates/` など任意の場所に `cdp_demo.json` を作成し、以下の最小アクションを定義します。

```json
[
  {"action": "command", "args": ["https://example.com"]},
  {"action": "wait_for_navigation"},
  {"action": "screenshot", "args": ["artifacts/cdp-demo/example.png"]}
]
```

### 3.2 ワークフロースクリプトの作成

`myscript/bin/run_cdp_demo.py` を新規作成し、以下のコードを配置します。`UnlockFutureAdapter` が JSON を読み込み、指定したエンジンで順次アクションを実行します。

```python
#!/usr/bin/env python3
"""CDP デモスクリプト"""

import asyncio
from pathlib import Path

from src.browser.engine.browser_engine import LaunchContext
from src.browser.engine.loader import EngineLoader
from src.browser.unlock_future_adapter import UnlockFutureAdapter

JSON_PATH = Path("myscript/templates/cdp_demo.json")

async def main() -> None:
    engine = EngineLoader.load_engine("cdp")
    adapter = UnlockFutureAdapter(engine)

    try:
        await engine.launch(LaunchContext(headless=True, trace_enabled=True))
        results = await adapter.execute_unlock_future_json(JSON_PATH)

        for i, result in enumerate(results, start=1):
            status = "✅" if result.success else "❌"
            print(f"{status} Step {i}: {result.action_type} ({result.duration_ms:.1f}ms)")
    finally:
        await engine.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### 3.3 実行と確認

```bash
RUNNER_ENGINE=cdp python myscript/bin/run_cdp_demo.py
```

出力例:

```text
✅ Step 1: navigate (1245.2ms)
✅ Step 2: wait_for_navigation (994.7ms)
✅ Step 3: screenshot (312.4ms)
```

アーティファクト:

- `artifacts/cdp-demo/example.png` : スクリーンショット
- `artifacts/traces/trace_*.zip` : `LaunchContext.trace_enabled=True` によって生成されたトレースファイル

## 4. テレメトリーとログの確認

| ディレクトリ | 内容 |
|--------------|------|
| `logs/runner.log` | `EngineLoader` のロード結果、アクションごとのメトリクスが出力されます。`engine=cdp` ラベルを確認してください。 |
| `metrics/engine/` | `EngineMetrics` シリアライズ結果。成功率や平均レイテンシが CSV/JSON 形式で保存されます。 |
| `artifacts/traces/` | Playwright/CDP 双方のトレース ZIP。CDP では `cdp` プレフィックス付きの JSON 断片を同梱します。 |
| `artifacts/screenshots/` | スクリーンショット、動画、コンソールログなど。 |

Phase4 で導入した `src/browser/engine/telemetry.py` を介して、トレースやメトリクスは Prometheus/OTLP エクスポーターに転送可能です。`ENABLE_OTLP_EXPORT=true` を設定すると、CDP 実行時のラベル (`engine=cdp`, `sandbox=seccomp`) がダッシュボードに反映されます。

## 5. よくあるトラブルと対処

| 症状 | 原因 | 対処 |
|------|------|------|
| `ValueError: Unsupported engine type 'cdp'` | `cdp-use` がインストールされていない | `pip install "cdp-use>=0.6.0"` を再実行し、仮想環境を再読み込みする |
| ブラウザが起動直後に終了する | サンドボックスオプションが利用できない環境 | `LaunchContext` の `sandbox_mode` を `False` にするか、`DockerLLMSandbox` と同様に許可リストを調整する |
| スクリーンショットが生成されない | 指定した出力パスのディレクトリが存在しない | `Path(...).parent.mkdir(parents=True, exist_ok=True)` を事前に実行する |
| Modern UI のドロップダウンが戻ってしまう | プロセス再起動でオーバーライドがリセット | `.env` または環境変数で `RUNNER_ENGINE=cdp` を固定する |
| `ENABLE_LLM=true` で遅延が大きい | Docker サンドボックスの pull / cold start | `DockerLLMServiceGateway.prewarm()` を利用する、またはステージングでキャッシュする |

## 6. 次のステップ

- `tests/integration/ui/test_modern_ui_integration.py` を参考に、Gradio UI 経由での自動テストを追加します。
- `UnlockFutureAdapter` の `execute_unlock_future_commands()` に CDP 固有アクション（Network/Console）を拡張して、Phase4 の高度機能を活用しましょう。
- `docs/security/SECURITY_MODEL.md` に記載されたフローに従い、`ENABLE_LLM=true` + `cdp` 構成でサンドボックス境界を検証します。

> 🚀 ここまで完了すれば、Playwright / CDP の両エンジンを安全に切り替えながら、Unlock Future フローとモダン UI を活用できる状態になります。
