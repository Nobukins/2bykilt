# CDP 有効化のためのFeature Flag マッピング

## 概要

このドキュメントでは、Modern UI の設定がどのように CDP 接続を制御するかを詳細に説明します。

## UI 設定とバックエンド処理の対応表

| Modern UI 設定 | Feature Flag / パラメータ | 効果 | 推奨値（CDP使用時） |
|---------------|-------------------------|------|-------------------|
| **Runner Engine** ドロップダウン | `FeatureFlags.set_override("runner.engine", value)` | エンジン選択（現状は表示のみ、実際の切り替えはブラウザ設定経由） | `cdp` |
| **Use existing browser profile** | `use_own_browser` パラメータ | `True`: CDP接続モード / `False`: Playwright管理モード | `True` (CDP接続) |
| **Keep browser open** | `keep_browser_open` パラメータ | セッション終了後もブラウザを開いたままにする | `True` (セッション確認用) |
| **Browser Type** | `browser_config.get_current_browser()` | 接続対象ブラウザ（chrome/edge） | `chrome` |

## CDP 接続の実際の制御フロー

### 現状の実装（MVP）

```text
Modern UI "Use existing browser profile" = True
    ↓
ExecutionDebugEngine.execute_commands(use_own_browser=True)
    ↓
BrowserDebugManager.initialize_custom_browser(use_own_browser=True)
    ↓
BrowserDebugManager.initialize_browser(use_own_browser=True)
    ↓
[CDP接続パス] playwright.chromium.connect_over_cdp(endpoint_url='http://localhost:9222')
```

**重要**: 現在の MVP 実装では、`Runner Engine` ドロップダウンは**表示専用**です。実際の CDP 接続は `Use existing browser profile` チェックボックスで制御されます。

### 設計上の CDP 接続パス（将来実装予定）

```text
Modern UI "Runner Engine" = "cdp"
    ↓
FeatureFlags.set_override("runner.engine", "cdp")
    ↓
EngineLoader.load_engine()  # Feature Flagを読み取り
    ↓
CDPEngine インスタンス化
    ↓
cdp-use ライブラリ経由でブラウザ自動化
```

**現状**: `CDPEngine` は cdp-use v1.4.0 の API 要件（`url` パラメータ必須）により動作しません。

## CDP 実行のための正しい設定手順

### オプション A: 自動起動モード（一時プロファイル）

1. 全てのChromeを終了
2. Modern UI で以下を設定:
   - `Runner Engine`: **表示のみ（現在は影響なし）**
   - `Use existing browser profile`: **OFF** ← これでCDP接続
   - `Keep browser open`: ON
3. コマンド実行

**動作**: システムが一時プロファイルでChromeを`--remote-debugging-port=9222`付きで起動し、CDP接続

### オプション B: 事前起動モード（個人プロファイル・推奨）

1. ターミナルでChromeをデバッグポート付きで手動起動:

   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --no-first-run \
     --no-default-browser-check &
   ```

2. Modern UI で以下を設定:
   - `Runner Engine`: **表示のみ（現在は影響なし）**
   - `Use existing browser profile`: **ON** ← 既存CDP接続を検出
   - `Keep browser open`: ON
3. コマンド実行

**動作**: 既にポート9222が利用可能なため、新規起動せず既存プロセスに接続

## ログによる CDP 接続の確認方法

### CDP 接続成功時のログパターン

```text
INFO [browser_debug_manager] 🔍 UIで選択されたブラウザタイプを使用: chrome
INFO [browser_debug_manager] ✅ ポート9222で既にchromeが実行中です - 既存プロセスに接続します
INFO [browser_debug_manager] 🔗 CDP接続試行 1/3
INFO [browser_debug_manager] ✅ chromeプロセスへの接続成功
```

### Playwright 管理モード時のログパターン

```text
INFO [browser_debug_manager] 🚀 Playwright管理chromeを起動
INFO [browser_debug_manager] ✅ ブラウザ起動成功: /Applications/Google Chrome.app/...
```

## トラブルシューティング

### 症状: `❌ ブラウザプロセス起動後もポート9222が利用できません`

**原因**: 個人プロファイルが既に別のChromeプロセスで使用中

**対処**:

1. 全てのChromeを完全終了: `killall "Google Chrome"`
2. オプションAで自動起動（一時プロファイル）を試す
3. または、オプションBで手動起動してから接続

### 症状: `Runner Engine`を`cdp`にしても動作が変わらない

**説明**: 現在の MVP 実装では、`Runner Engine` ドロップダウンは表示専用です。実際の動作は `Use existing browser profile` で制御されます。

**今後の改善**: Phase5+ で `EngineLoader` と `CDPEngine` の統合により、`Runner Engine` 選択が実際に動作に影響するようになる予定です。

## Feature Flag の優先順位

```text
環境変数 RUNNER_ENGINE > FeatureFlags.set_override() > config.yaml > デフォルト値
```

現在の実装では、`FeatureFlags.get("runner.engine")` は取得できますが、`ExecutionDebugEngine` は直接 `BrowserDebugManager` を使用しているため、この値は反映されません。

## 次のステップ: 完全なCDP統合への道筋

1. ✅ **現在**: `BrowserDebugManager` 経由の CDP 接続（MVP完成）
2. 🔄 **Phase5**: `cdp-use` API 互換性修正 → `CDPEngine` 実装
3. 🔄 **Phase5**: `EngineLoader` と `ExecutionDebugEngine` の統合
4. 🎯 **最終形**: `Runner Engine` ドロップダウンで真のエンジン切り替えが可能に

## まとめ

現時点では、**`Use existing browser profile` がCDP接続の実質的なスイッチ**です。チュートリアルの手順に従い、オプションA（自動）またはオプションB（事前起動）で正しく設定すれば、CDP経由のブラウザ自動化が可能です。
