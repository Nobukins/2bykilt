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

## 3. Unlock Future コマンドを CDP 経路で実行する（MVP 実装）

### 3.1 現状の制約と MVP アプローチ

Phase0〜4 で設計した `CDPEngine` / `EngineLoader` は `cdp-use` ライブラリの API 不整合により現時点で動作しません。本チュートリアルの MVP では **既存の `BrowserDebugManager` + `ExecutionDebugEngine` 経路**を活用し、Modern UI 経由で CDP 接続を検証します。

#### CDP 接続の仕組み（MVP）

1. `BrowserDebugManager.initialize_browser(use_own_browser=True)` で CDP デバッグポート接続
2. `global_browser` インスタンスを再利用してセッション永続化
3. 個人プロファイル (`user_data_dir`) を優先して起動

### 3.2 Modern UI 経由での CDP 実行手順（推奨: オプションA）

#### オプション A: 自動起動モード（推奨・最も簡単）

システムが自動的にChromeをCDP対応で起動します。**個人プロファイルとの競合を避けるため、一時プロファイルを使用します。**

1. **全てのChromeを終了**

   ```bash
   # macOS
   killall "Google Chrome"
   
   # Linux
   pkill -f chrome
   ```

2. **サーバー起動**

   ```bash
   python -m src.ui.main_ui
   ```

3. **ブラウザで <http://0.0.0.0:7860> を開く**

4. **Run Agent タブで設定**
   - `Runner Engine` → `cdp` を選択（表示用）
   - `🌐 Browser` アコーディオンを展開
   - `Use existing browser profile` を**オフ**（一時プロファイル使用）
   - `Keep browser open` をオン

5. 手順1（コマンド実行）と手順2（ログ確認）は共通手順を参照

#### オプション B: 事前起動モード（上級者向け）

既にデバッグポート付きで起動済みのChromeに接続します。個人プロファイル・拡張機能・ブックマークがそのまま使えますが、**設定が難しい**です。

**重要な前提条件**:

- Chrome を通常起動したままでは動作しません
- 個人プロファイルは一度完全に閉じる必要があります
- デバッグポート付きでのみ起動する必要があります

1. **全てのChromeを完全終了**

   ```bash
   killall "Google Chrome"
   # プロセスが完全に終了したことを確認
   sleep 2
   ```

2. **デバッグポート付きでChromeを手動起動（個人プロファイルは使用しない）**

   ```bash
   # macOS - 一時プロファイルで起動
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=$(mktemp -d) \
     --no-first-run \
     --no-default-browser-check &
   ```

   > 💡 起動後、`chrome://version` を開いてコマンドラインに `--remote-debugging-port=9222` が含まれることを確認してください

3. **接続確認**

   ```bash
   curl http://localhost:9222/json/version
   ```

   JSONレスポンスが返れば成功です。

4. **サーバー起動**

   ```bash
   python -m src.ui.main_ui
   ```

5. **ブラウザで <http://0.0.0.0:7860> を開く**（デバッグポート付きChromeの別タブで）

6. **Run Agent タブで設定**
   - `Runner Engine` → `cdp` を選択
   - `🌐 Browser` アコーディオンを展開
   - `Use existing browser profile` をオン（既存接続を使用）
   - `Keep browser open` をオン（セッション確認用）

#### 共通手順: コマンド実行と検証

1. **コマンド実行**  
   Task Description に以下を入力:

   ```text
   @nogtips-jsonpayload query=CDP
   ```

   `▶️ Run Agent` をクリック

2. **ログ確認**  
   ターミナルに以下のようなログが出力されたら CDP 経路です:

   ```text
   INFO [browser_debug_manager] ✅ 既存のCDPブラウザを再利用
   INFO - 🔍 個人user-data-dirを使用: /Users/.../Chrome
   INFO - ✅ chromeプロセスへの接続成功
   ```

3. **Chrome で検証（任意）**  
   立ち上がった Chrome で `chrome://version` を開き、コマンドラインに `--remote-debugging-port=9222` が含まれることを確認

### 3.3 連続コマンドのセッション再利用テスト

2回目のコマンド実行時、新規ブラウザが立ち上がらず既存タブが再利用されたら成功です:

1. 前述の手順でブラウザを立ち上げたまま
2. Task Description に別のコマンド（例: `@click-jsonpayload selector=#example`）を入力
3. `▶️ Run Agent` を再度クリック
4. ログに `✅ 既存のCDPブラウザを再利用` が出れば OK

### 3.4 トラブルシューティング

| 症状 | 原因 | 対処 |
|------|------|------|
| `TargetClosedError` | 前回のタブが手動で閉じられた | Chrome を完全終了して再実行 |
| 新しいブラウザが毎回立ち上がる | `Keep browser open` がオフ | UI で設定をオンに |
| 個人プロファイルが使えない | `Use existing browser profile` がオフ | UI で設定をオンに、またはログで `個人user-data-dirを使用` を確認 |

### 3.5 アーティファクト確認

実行後、以下に成果物が保存されます:

- **ログ**: `logs/runner.log` に CDP 接続ログ
- **スクリーンショット**: `artifacts/runs/<timestamp>/` 配下
- **Feature Flag 解決結果**: `artifacts/runs/*-flags/feature_flags_resolved.json`

```bash
# 最新の flags 結果を確認
cat "$(ls -td artifacts/runs/*-flags | head -n 1)/feature_flags_resolved.json" | grep runner.engine
```

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
