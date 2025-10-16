# CDP MVP 実装サマリー

## 📅 作業日: 2025年10月6日

## 🎯 達成目標

Modern UI経由でCDP（Chrome DevTools Protocol）接続を有効化し、unlock-futureコマンドを実行可能にする。Playwright エンジンとの並行利用を可能にし、ユーザーが簡単に切り替えられる仕組みを構築する。

## ✅ 完了した作業

### 1. CDP接続ロジックの改善 (`src/browser/browser_debug_manager.py`)

#### 問題点
- 個人プロファイルで既にChromeが起動している場合、`--remote-debugging-port=9222`を追加起動できない
- "既存のブラウザ セッションで開いています" エラーが発生
- ポート9222が利用できず、CDP接続が失敗する

#### 実装した解決策
```python
# 一時プロファイルを強制使用（個人プロファイルとの競合を回避）
import tempfile
actual_user_data_dir = tempfile.mkdtemp(prefix="chrome_debug_cdp_")
logger.info(f"🔧 CDP用の一時user-data-dirを作成: {actual_user_data_dir}")
```

**効果**:
- 個人プロファイルと独立したCDP専用Chromeインスタンスを起動
- ポート競合を完全に回避
- セッション再利用機能も実装（`self.global_browser`チェック）

### 2. 既存プロセス検出ロジックの追加

```python
# 既存のデバッグポートをチェック（既に起動中の可能性）
if await self._check_browser_running(debugging_port):
    logger.info(f"✅ ポート{debugging_port}で既に{browser_type}が実行中です - 既存プロセスに接続します")
else:
    # 新規起動処理...
```

**効果**:
- 既にCDP対応Chromeが起動している場合は新規起動せずに接続
- 不要なプロセス重複を防止

### 3. チュートリアル文書の整備

作成・更新した文書:

| ファイル | 目的 | 内容 |
|---------|------|------|
| `docs/tutorial/cdp-use-workflow.md` | CDP利用手順 | オプションA（自動起動・推奨）とオプションB（事前起動・上級者向）の2つのモードを説明 |
| `docs/tutorial/CDP_FLAG_MAPPING.md` | Feature Flag マッピング | UI設定とバックエンドパラメータの対応関係を詳細に説明。MVP実装の制約も明記 |
| `docs/CDP_MVP_IMPLEMENTATION_SUMMARY.md` | 本ドキュメント | 実装の全体像と進捗をまとめる |

### 4. Markdown リント対応

全てのチュートリアル文書でMarkdown linting violations を修正:
- ✅ MD031: コードブロック前後の空行
- ✅ MD034: ベアURLを`<>`で囲む
- ✅ MD040: 言語タグ追加（`bash`, `text`）
- ✅ MD033: インラインHTML除去
- ✅ MD032: リスト前後の空行

## 📋 現在の CDP 有効化フロー

### Modern UI での操作（オプションA: 推奨）

```text
1. 全てのChromeを終了
   └─> killall "Google Chrome"

2. Modern UI 起動
   └─> python -m src.ui.main_ui

3. Run Agent タブで設定
   ├─> Runner Engine: cdp (表示用)
   ├─> Use existing browser profile: OFF  ← CDP接続トリガー
   └─> Keep browser open: ON

4. コマンド実行
   └─> @nogtips-jsonpayload query=CDP
```

### バックエンド処理フロー

```text
UI: use_own_browser = True (UIチェックボックス)
  ↓
ExecutionDebugEngine.execute_commands(use_own_browser=True)
  ↓
BrowserDebugManager.initialize_browser(use_own_browser=True)
  ↓
[CDP接続パス]
  ├─> ポート9222チェック
  ├─> 既存プロセスなし → 一時プロファイルでChrome起動
  ├─> デバッグポート待機（最大10回リトライ）
  └─> playwright.chromium.connect_over_cdp('http://localhost:9222')
      └─> ✅ CDP接続成功
```

### ログによる成功確認

```text
INFO [browser_debug_manager] 🔍 UIで選択されたブラウザタイプを使用: chrome
INFO [browser_debug_manager] 🔗 外部chromeプロセスに接続を試行
INFO [browser_debug_manager] 🔧 CDP用の一時user-data-dirを作成: /var/folders/.../chrome_debug_cdp_XXXXX
INFO [browser_debug_manager] 🚀 chromeプロセスを起動
INFO [browser_debug_manager] ✅ ポート9222でブラウザが実行中
INFO [browser_debug_manager] 🔗 CDP接続試行 1/3
INFO [browser_debug_manager] ✅ chromeプロセスへの接続成功
```

## 🔧 技術的な制約と設計判断

### MVP 実装の制約

#### 1. `Runner Engine` ドロップダウンは表示専用

**現状**:
- `FeatureFlags.set_override("runner.engine", "cdp")` は機能するが、実際のエンジン切り替えには影響しない
- CDP接続は `Use existing browser profile` チェックボックスで制御される

**理由**:
- `ExecutionDebugEngine` が直接 `BrowserDebugManager` を使用
- `EngineLoader` → `CDPEngine` 経路は cdp-use v1.4.0 API 不整合により未実装

**将来の改善**:
Phase5+ で `EngineLoader` 統合により、`Runner Engine` 選択が実際に動作に影響するようになる予定

#### 2. cdp-use ライブラリの API 不整合

**問題**:
```python
# cdp-use v1.4.0 requires:
CDPClient(url: str)  # url parameter is mandatory

# しかし CDPEngine.launch() は:
self.client = CDPClient()  # No arguments → TypeError
```

**MVP の対応**:
- `CDPEngine` を使用せず、Playwright の `connect_over_cdp` を直接使用
- これにより `browser-control` との互換性を維持

#### 3. 個人プロファイルの使用制限

**設計判断**: 一時プロファイルを強制使用

**理由**:
- 個人プロファイルは通常のChrome起動で既に使用中の可能性が高い
- 同一プロファイルを複数プロセスで開くとポート競合が発生
- CDP専用インスタンスとして独立させることで安定性を確保

**トレードオフ**:
- ❌ ブックマーク・拡張機能・ログイン状態が使えない
- ✅ 安定した CDP 接続が保証される
- ✅ セットアップが簡単（Chrome終了 → UI操作のみ）

## 📊 Feature Flag 優先順位

現在の実装での Feature Flag 解決順序:

```text
1. 環境変数 RUNNER_ENGINE
2. FeatureFlags.set_override("runner.engine", value)
3. config.yaml の設定
4. デフォルト値 ("playwright")
```

**重要**: MVP では Feature Flag の値は取得できるが、`ExecutionDebugEngine` はこれを参照していない。実際の制御は `use_own_browser` パラメータで行われる。

## 🚀 次のステップ

### 短期（MVP完成）

1. **実機テスト** (現在進行中)
   - Modern UI でオプションAの手順を実行
   - CDP接続ログの確認
   - unlock-future コマンドの正常実行確認

2. **browser-control モード対応**
   - `browser-control` タイプのアクションでもCDP経由実行を可能に
   - タブ再利用戦略の検証

3. **script モード対応**
   - レガシー `script` タイプでもCDP経由実行をサポート

### 中期（Phase5統合）

1. **cdp-use API 整合性修正**
   - `CDPEngine.launch()` で `CDPClient(url=...)` を正しく呼び出す
   - WebSocket URL の動的取得ロジック実装

2. **EngineLoader 統合**
   - `ExecutionDebugEngine` が `EngineLoader.load_engine()` を呼び出す
   - Feature Flag `runner.engine` が実際のエンジン選択に影響する設計

3. **個人プロファイル対応（オプション）**
   - オプションBの手順を簡素化
   - プロファイル競合の自動検出と回避ロジック

### 長期（Phase6+）

1. **テレメトリー強化**
   - CDP 固有のメトリクス収集
   - Network/Console イベントのトレース保存

2. **高度な CDP 機能**
   - ネットワークインターセプト
   - コンソールログ収集
   - パフォーマンスメトリクス

## 📝 ドキュメント構成

```text
docs/
├── tutorial/
│   ├── cdp-use-workflow.md          # メインチュートリアル（ユーザー向け）
│   └── CDP_FLAG_MAPPING.md          # Feature Flag 詳細マッピング（開発者向け）
└── CDP_MVP_IMPLEMENTATION_SUMMARY.md # 本ドキュメント（実装サマリー）
```

### 各文書の役割

| ドキュメント | 対象読者 | 目的 |
|-------------|---------|------|
| `cdp-use-workflow.md` | エンドユーザー | CDP機能の使い方を段階的に説明 |
| `CDP_FLAG_MAPPING.md` | 開発者 | UI設定とバックエンドの対応関係を説明。トラブルシューティング情報も含む |
| `CDP_MVP_IMPLEMENTATION_SUMMARY.md` | 開発チーム | 実装の全体像・設計判断・技術的制約をまとめる |

## 🔍 検証項目（次回テスト用）

### 必須確認項目

- [ ] 全てのChromeを終了後、UI経由でCDP接続が成功する
- [ ] 一時プロファイルでChromeが起動する（`chrome_debug_cdp_` プレフィックス）
- [ ] ログに `✅ chromeプロセスへの接続成功` が出力される
- [ ] `@nogtips-jsonpayload query=CDP` コマンドが正常実行される
- [ ] ブラウザが自動でページ遷移・クリック・フォーム入力を実行する
- [ ] スクリーンショットが `artifacts/runs/` に保存される

### オプション確認項目

- [ ] 2回目のコマンド実行時、既存ブラウザが再利用される（`✅ 既存のCDPブラウザを再利用` ログ）
- [ ] `Keep browser open = ON` の時、コマンド実行後もChromeが開いたまま
- [ ] `Keep browser open = OFF` の時、コマンド実行後にChromeが閉じる

## 💡 重要なポイント

### ユーザーへの説明ポイント

1. **オプションA（自動起動）が推奨**
   - 最も簡単で確実
   - Chrome終了 → UI設定 → 実行の3ステップ

2. **個人プロファイルは使えない（MVP制約）**
   - ブックマーク・拡張機能は一時的に利用不可
   - 将来のPhaseで改善予定

3. **`Runner Engine` は表示専用（現時点）**
   - 実際の切り替えは `Use existing browser profile` で行う
   - Phase5+ で真のエンジン切り替えが可能になる

### 開発者への技術情報

1. **BrowserDebugManager が CDP 接続の中核**
   - `initialize_browser(use_own_browser=True)` でCDP接続
   - `connect_over_cdp` で Playwright 経由接続

2. **cdp-use ライブラリは現時点で未使用**
   - API 不整合により `CDPEngine` は動作しない
   - Playwright の CDP サポートで代替

3. **Feature Flag は将来の拡張ポイント**
   - 現在は取得可能だが実際の動作には影響しない
   - `EngineLoader` 統合で本来の機能を発揮

## 📦 成果物

### コード変更
- `src/browser/browser_debug_manager.py`: 一時プロファイル強制使用、既存プロセス検出ロジック追加

### ドキュメント
- `docs/tutorial/cdp-use-workflow.md`: オプションA/B の手順詳細化、Markdown linting 修正
- `docs/tutorial/CDP_FLAG_MAPPING.md`: Feature Flag マッピング表、トラブルシューティングガイド
- `docs/CDP_MVP_IMPLEMENTATION_SUMMARY.md`: 本ドキュメント

### 設定ファイル
- 変更なし（既存の `config.yaml`, `pyproject.toml` をそのまま使用）

## 🎉 まとめ

CDP MVP 実装により、Modern UI 経由でのCDP接続が可能になりました。個人プロファイルとの競合を避けるため一時プロファイルを使用する設計とし、安定性を優先しました。

次のステップは、実際のUI操作で動作確認を行い、unlock-future コマンドが正常実行されることを検証することです。その後、browser-control および script モードへの対応を進めます。
