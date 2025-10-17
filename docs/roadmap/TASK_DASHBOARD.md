# TASK DASHBOARD

Generated at (UTC): 2025-10-17T03:19:52+00:00

## 1. メタサマリー

- Total Issues: 132
- High Risk (declared): 8 → 31, 46, 49, 54, 62, 176, 237, 285
- Cycle Detected: false (none)
- Strict Orphans: 29
- Curated Orphan List Count: 31

## 2. 分布 (Distribution)

### Priority
- P0: 28 (21.2%)
- P1: 39 (29.5%)
- P2: 61 (46.2%)
- P3: 4 (3.0%)

### Phase
- 1: 23 (17.4%)
- 1-late: 14 (10.6%)
- 2: 92 (69.7%)
- 3: 3 (2.3%)

### Area
- artifacts: 30 (22.7%)
- automation: 5 (3.8%)
- batch: 10 (7.6%)
- config: 12 (9.1%)
- docs: 12 (9.1%)
- flags: 1 (0.8%)
- logging: 7 (5.3%)
- observability: 5 (3.8%)
- plugins: 1 (0.8%)
- quality: 1 (0.8%)
- runner: 25 (18.9%)
- security: 5 (3.8%)
- test: 1 (0.8%)
- testing: 4 (3.0%)
- uiux: 13 (9.8%)

### Risk
- high: 8 (6.1%)
- low: 12 (9.1%)
- medium: 3 (2.3%)
- none: 109 (82.6%)

## 3. リスク詳細 (High / Medium / etc.)

High Risk Issues:
- 31: 統一ログ設計 (JSON Lines) (area=logging, priority=P0)
- 46: Run/Job タイムアウト & キャンセル (area=runner, priority=P2)
- 49: ユーザースクリプト プラグインアーキテクチャ (area=plugins, priority=P3)
- 54: cdp-use デュアルエンジン抽象レイヤ (area=runner, priority=P1)
- 62: 実行サンドボックス機能制限 (area=security, priority=P0)
- 176: 宣言的抽出スキーマ (CSV列→コマンド引数/抽出ポリシーマッピング) (area=batch, priority=P1)
- 237: Bug: Recording file generation not working for any run type (area=artifacts, priority=P0)
- 285: Browser-Use/Web-UIをベースとしてUI周りのリファクタリング (area=uiux, priority=P2)

## 4. Orphans

Strict Orphans (自動抽出 = 依存なし & 参照されず):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / flags 再生成 / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- 197: [dashboard] UI graphs and preset expansion
- 218: テストカバレッジ率の向上
- 227: [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保
- 228: [configuration][enhancement] LLM設定の改善と設定ガイドの明確化
- 229: [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立
- 230: [documentation][enhancement] ドキュメントの改善とユーザガイドの充実
- 231: [testing][enhancement] テストスイートの改善とカバレッジ向上
- 240: P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing
- 241: P0: Fix Unlock-Future type browser automation - Operations hang without execution
- 244: [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加
- 255: git-scriptのURL評価制限緩和
- 276: Batch: Recording file not copied to artifacts runs folder when using CSV batch
- 277: Artifacts UI: Provide UI listing for screenshots, text & element extracts
- 279: Config: Consolidate configuration menus, env files, and defaults
- 280: Browser Settings: Improve Browser Settings menu clarity & enforce behavior across run types
- 285: Browser-Use/Web-UIをベースとしてUI周りのリファクタリング
- 287: Template for new issue and new PR

Curated Orphan List (summary.data_quality_checks.orphan_issues_without_dependents_or_depends):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / flags 再生成 / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- 197: [dashboard] UI graphs and preset expansion
- 218: テストカバレッジ率の向上
- 227: [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保
- 228: [configuration][enhancement] LLM設定の改善と設定ガイドの明確化
- 229: [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立
- 230: [documentation][enhancement] ドキュメントの改善とユーザガイドの充実
- 231: [testing][enhancement] テストスイートの改善とカバレッジ向上
- 240: P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing
- 241: P0: Fix Unlock-Future type browser automation - Operations hang without execution
- 244: [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加
- 255: git-scriptのURL評価制限緩和
- 264: リファクタ提案: 大きすぎる Python ファイルの分割とモジュール化
- 276: Batch: Recording file not copied to artifacts runs folder when using CSV batch
- 277: Artifacts UI: Provide UI listing for screenshots, text & element extracts
- 279: Config: Consolidate configuration menus, env files, and defaults
- 280: Browser Settings: Improve Browser Settings menu clarity & enforce behavior across run types
- 285: Browser-Use/Web-UIをベースとしてUI周りのリファクタリング
- 287: Template for new issue and new PR
- 320: feat: Auto-discovery and import of browser automation commands from remote llms.txt files

Missing Strict Orphans in curated list: (none)
Extra non-strict entries in curated list (WARNING only): 264, 320

## 5. クリティカルパス推定

Critical Path (自動算出): depends の有向エッジ (B→A) を距離 0 起点から最長距離でトレースしたパス。 実際の期間や見積りを考慮せず、依存段数のみで推定。

Auto Estimated Path (Longest Distance):
25 → 50 → 200 → 201 → 196 → 202 → 203

Provided Example (existing IDs only):
302 → 303 → 304 → 305

## 6. Issues Table (sorted)

Sorted By: critical_path_rank

| ID | Title | Pri | Phase | Area | Risk | CP Rank | LongestDist | Depends | Dependents | PrimaryPR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 302 | [ui/ux][artifacts] 🎥 Recordings: リカーシブ検出 + LLM無効時GIF代替 (Flag対応) | P2 | 2 | artifacts |  | 6 | 0 | 0 | 5 |  |
| 219 | [runner][bug] search-linkedin 初期コマンド失敗 (pytest経由引数未解釈) | P0 | 2 | runner |  | 5 | 4 | 2 | 2 | #232 |
| 32 | Run/Job ID 基盤 | P0 | 1 | runner |  | 5 | 0 | 0 | 10 | #79 |
| 65 | マルチ環境設定ローダ | P0 | 1 | config |  | 5 | 0 | 0 | 4 |  |
| 220 | [runner][bug] browser-control タイプ実行失敗の調査と修正 | P1 | 2 | runner |  | 4 | 0 | 1 | 1 |  |
| 237 | Bug: Recording file generation not working for any run type | P0 | 2 | artifacts | high | 4 | 0 | 1 | 0 | #239 |
| 28 | 録画ファイル保存パス統一 | P0 | 1 | artifacts |  | 4 | 1 | 1 | 1 | #112 |
| 64 | フィーチャーフラグフレームワーク | P0 | 1 | config |  | 4 | 1 | 1 | 3 |  |
| 110 | browser-control gap fix | P0 | 2 | runner |  | 3 | 0 | 1 | 1 | #188 |
| 111 | 録画/パス統合 | P0 | 2 | artifacts |  | 3 | 2 | 1 | 1 | #188 |
| 221 | [artifacts][bug] script 以外で録画ファイル未生成 (browser-control/git-script) | P1 | 2 | artifacts |  | 3 | 0 | 2 | 1 |  |
| 25 | git_script が llms.txt で指定したスクリプトを正しく解決するよう修正 | P0 | 1 | runner |  | 3 | 0 | 0 | 4 | #118 |
| 30 | 録画タイプ間不整合是正 | P0 | 1 | artifacts |  | 3 | 2 | 1 | 2 | #112 |
| 303 | [artifacts] 🎥 Recordings: 再帰探索ユーティリティ + テスト (Flag対応) [Sub of #302] | P2 | 2 | artifacts |  | 3 | 1 | 1 | 1 | #308 |
| 31 | 統一ログ設計 (JSON Lines) | P0 | 1 | logging | high | 3 | 1 | 1 | 1 | #80 |
| 35 | アーティファクト manifest v2 | P0 | 1 | artifacts |  | 3 | 1 | 1 | 3 | #94 |
| 46 | Run/Job タイムアウト & キャンセル | P2 | 2 | runner | high | 3 | 1 | 1 | 1 |  |
| 63 | llms.txt スキーマ & バリデータ | P0 | 1-late | config |  | 3 | 2 | 2 | 1 |  |
| 175 | バッチ行単位成果物キャプチャ基盤 (スクリーンショット/要素値/ログ関連紐付け) | P1 | 2 | artifacts | medium | 2 | 4 | 6 | 1 | #181 |
| 176 | 宣言的抽出スキーマ (CSV列→コマンド引数/抽出ポリシーマッピング) | P1 | 2 | batch | high | 2 | 3 | 3 | 0 | #181 |
| 222 | [logging][feat] ログ出力ディレクトリ/カテゴリ標準化 & src/logs/ 廃止 | P1 | 2 | logging |  | 2 | 4 | 2 | 1 |  |
| 304 | [service] 🎥 Recordings: 一覧取得サービス/API (Flag連携) [Sub of #302] | P2 | 2 | artifacts |  | 2 | 2 | 2 | 1 | #309 |
| 306 | [worker] 🎥 Recordings: GIF変換ワーカー/キャッシュ + Flag [Sub of #302] | P2 | 2 | artifacts |  | 2 | 1 | 1 | 1 |  |
| 329 | Split script/script_manager.py into executor modules | P1 | 2 | runner |  | 2 | 1 | 1 | 0 | #334 |
| 33 | スクリーンショット取得ユーティリティ | P0 | 1 | artifacts |  | 2 | 1 | 1 | 3 |  |
| 36 | アーティファクト一覧 API | P1 | 1 | artifacts |  | 2 | 2 | 1 | 1 | #95 |
| 37 | 動画アーティファクト保持期間 | P1 | 1 | artifacts |  | 2 | 3 | 1 | 1 | #99 |
| 39 | CSV 駆動バッチエンジンコア | P1 | 2 | batch |  | 2 | 1 | 1 | 4 | #164 |
| 44 | git_script 解決ロジック不具合修正 | P0 | 1 | runner |  | 2 | 1 | 1 | 1 | #120 |
| 47 | 並列実行キュー & 制限 | P2 | 2 | runner |  | 2 | 2 | 1 | 1 |  |
| 53 | cdp-use 追加タイプ調査 | P2 | 2 | runner |  | 2 | 0 | 0 | 1 |  |
| 56 | 統一 JSON Lines ロギング実装 | P0 | 1 | logging |  | 2 | 2 | 2 | 3 | #83 |
| 58 | メトリクス計測基盤 & エクスポータ | P1 | 2 | observability |  | 2 | 1 | 1 | 1 | #156 |
| 62 | 実行サンドボックス機能制限 | P0 | 2 | security | high | 2 | 1 | 1 | 1 |  |
| 66 | ドキュメント整備 第1弾 | P2 | 1-late | docs |  | 2 | 3 | 1 | 1 |  |
| 76 | 依存更新自動化パイプライン (PR 起票時の ISSUE_DEPENDENCIES.yml 自動更新) | P1 | 1-late | automation |  | 2 | 2 | 1 | 0 |  |
| 81 | Async/Browser テスト安定化計画 | P1 | 1 | runner |  | 2 | 0 | 0 | 0 |  |
| 102 | Flags artifacts helper | P2 | 2 | config |  | 1 | 2 | 1 | 0 |  |
| 107 | Cleanup: PytestReturnNotNone warnings across component tests | P2 | 1-late | testing |  | 1 | 0 | 0 | 0 |  |
| 108 | Stabilize Edge headless navigation flake (TargetClosedError) | P2 | 1-late | artifacts |  | 1 | 0 | 0 | 0 |  |
| 109 | [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随) | P2 | 2 | quality |  | 1 | 0 | 0 | 0 |  |
| 113 | docs: cleanup archived references to tests/pytest.ini (post PR #112) | P2 | 2 | docs |  | 1 | 0 | 0 | 0 |  |
| 114 | ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112) | P2 | 2 | automation |  | 1 | 0 | 0 | 0 |  |
| 115 | [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / flags 再生成 / パス可搬性 / flags 再生成) | P2 | 2 | testing |  | 1 | 0 | 0 | 0 |  |
| 127 | [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善 | P1 | 2 | batch |  | 1 | 0 | 0 | 0 |  |
| 154 | pip-audit stabilization in CI with normalizer + targeted suppressions | P1 | 1 | security |  | 1 | 0 | 0 | 0 | #160 |
| 173 | [UI][batch][#40 follow-up] CSV Preview & Command Argument Mapping | P2 | 2 | batch |  | 1 | 4 | 4 | 0 |  |
| 174 | [artifacts][batch] Clarify Artifact Output & Access Flow | P3 | 2 | artifacts | low | 1 | 3 | 5 | 0 |  |
| 177 | MVP エンタープライズ Readiness マトリクス定義 | P1 | 2 | docs |  | 1 | 4 | 5 | 0 | #189 |
| 178 | CI: dependency-pipeline workflow 追加 (生成物 idempotent 検証自動化) | P2 | 2 | automation | low | 1 | 3 | 1 | 0 |  |
| 192 | [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule | P1 | 2 | security |  | 1 | 0 | 0 | 0 |  |
| 194 | [artifacts] Tab index manifest for multi-tab recordings | P2 | 2 | artifacts |  | 1 | 0 | 0 | 2 |  |
| 196 | CI: local selector smoke を統合 | P2 | 2 | automation | low | 1 | 4 | 1 | 1 | #213 |
| 197 | [dashboard] UI graphs and preset expansion | P2 | 2 | observability |  | 1 | 0 | 0 | 0 |  |
| 198 | [batch] CSV NamedString 入力の正規化 | P1 | 2 | batch | medium | 1 | 2 | 1 | 0 | #256 |
| 199 | [ui/ux] Internationalization (i18n): JA base → EN 追加 | P2 | 2 | uiux | low | 1 | 0 | 0 | 3 |  |
| 200 | [policy] myscript 配置規約の策定 | P2 | 2 | docs | low | 1 | 2 | 1 | 2 |  |
| 201 | [runner] myscript スクリプト修正（パス統一・生成物出力） | P2 | 2 | runner | low | 1 | 3 | 1 | 3 | #213 |
| 202 | [ci] アーティファクト収集/キャッシュ更新（myscript 構成対応） | P2 | 2 | automation | low | 1 | 5 | 2 | 1 | #214 |
| 203 | [docs] README/チュートリアル/ガイド更新（myscript 構成・出力ポリシー） | P2 | 2 | docs | low | 1 | 6 | 3 | 0 |  |
| 208 | [ui/ux] Option Availability - 利用可能なオプションの可視化改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 209 | [ui/ux] Results menu - 実行結果表示メニューの改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 210 | [ui/ux] Recordings menu - 録画ファイル管理メニューの改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 211 | [docs] LLM 統合ドキュメント整備 | P1 | 2 | docs | low | 1 | 3 | 1 | 0 |  |
| 212 | [ui/ux] Playwright Codegenメニューの保存ボタン統合改善 | P1 | 2 | uiux |  | 1 | 1 | 1 | 0 |  |
| 218 | テストカバレッジ率の向上 | P2 | 2 | testing |  | 1 | 0 | 0 | 0 |  |
| 223 | [logging][bug] LOG_LEVEL 環境変数が反映されない (初期化順序バグ) | P0 | 2 | logging |  | 1 | 0 | 1 | 0 | #233 |
| 224 | [ui/ux][config] RECORDING_PATH UI と環境変数の競合解消 | P1 | 2 | uiux |  | 1 | 0 | 1 | 0 |  |
| 226 | [runner][bug] search-linkedin 実行時エラー修正 | P0 | 2 | runner |  | 1 | 4 | 2 | 0 | #232 |
| 227 | [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保 | P2 | 2 | uiux |  | 1 | 0 | 0 | 0 |  |
| 228 | [configuration][enhancement] LLM設定の改善と設定ガイドの明確化 | P2 | 2 | config |  | 1 | 0 | 0 | 0 |  |
| 229 | [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立 | P2 | 2 | uiux |  | 1 | 0 | 0 | 0 |  |
| 230 | [documentation][enhancement] ドキュメントの改善とユーザガイドの充実 | P2 | 2 | docs |  | 1 | 0 | 0 | 0 |  |
| 231 | [testing][enhancement] テストスイートの改善とカバレッジ向上 | P2 | 2 | testing |  | 1 | 0 | 0 | 0 |  |
| 240 | P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing | P0 | 2 | config |  | 1 | 0 | 0 | 0 |  |
| 241 | P0: Fix Unlock-Future type browser automation - Operations hang without execution | P0 | 2 | runner |  | 1 | 0 | 0 | 0 |  |
| 242 | P1: Optimize Feature Flag usage for UI menu control - Hide LLM tabs when disabled | P1 | 2 | uiux |  | 1 | 2 | 1 | 0 |  |
| 244 | [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加 | P2 | 2 | docs |  | 1 | 0 | 0 | 0 |  |
| 246 | [artifacts][feat] スクリーンショットの取得・保存機能強化 | P1 | 2 | artifacts |  | 1 | 1 | 1 | 0 |  |
| 247 | [artifacts][feat] ブラウザ要素の取得・保存機能強化 | P1 | 2 | artifacts |  | 1 | 1 | 1 | 0 |  |
| 248 | CSV Batch Processing Enhancement Priority | P1 | 2 | batch |  | 1 | 3 | 2 | 0 |  |
| 249 | Phase2-07 Metrics Advancement | P0 | 2 | observability |  | 1 | 0 | 1 | 0 |  |
| 250 | Phase2-13 Runner Fixes Parallel | P0 | 2 | runner |  | 1 | 0 | 2 | 0 |  |
| 251 | Phase2-14 Config Conflicts | P0 | 2 | config |  | 1 | 0 | 1 | 0 |  |
| 255 | git-scriptのURL評価制限緩和 | P2 | 2 | runner |  | 1 | 0 | 0 | 0 |  |
| 257 | [batch] CSV Batch Job Execution Not Triggered - Browser Automation Missing | P0 | 2 | batch |  | 1 | 3 | 2 | 0 |  |
| 264 | リファクタ提案: 大きすぎる Python ファイルの分割とモジュール化 | P2 | 2 | docs |  | 1 | 0 | 0 | 1 |  |
| 265 | 改善提案: 複数フォルダ配下の録画ファイルを再帰的に発見・一覧表示 | P2 | 2 | artifacts |  | 1 | 0 | 0 | 3 | #317 |
| 266 | Discovery: 録画ファイル検出ユーティリティ（Discovery） | P2 | 2 | artifacts |  | 1 | 1 | 1 | 0 |  |
| 267 | API: 録画ファイル検索 API 設計 | P2 | 2 | artifacts |  | 1 | 2 | 2 | 0 |  |
| 268 | UI: 録画ファイル集約ビューと実装 | P2 | 2 | artifacts |  | 1 | 2 | 3 | 0 | #317 |
| 269 | 提案: Feature Flag の全面活用とプロファイルベースの機能有効化 | P1 | 1 | config |  | 1 | 0 | 0 | 3 |  |
| 270 | 設計: Feature Flag 運用設計とメタデータ仕様 | P1 | 1 | config |  | 1 | 1 | 1 | 1 |  |
| 271 | 実装: Feature Flags コアライブラリと Profile ベースセットアップ | P1 | 1 | config |  | 1 | 2 | 2 | 1 |  |
| 272 | UI: Admin UI による Feature Flag 管理画面の実装 | P1 | 1 | flags |  | 1 | 3 | 2 | 0 | #319 |
| 276 | Batch: Recording file not copied to artifacts runs folder when using CSV batch | P1 | 2 | artifacts |  | 1 | 0 | 0 | 0 |  |
| 277 | Artifacts UI: Provide UI listing for screenshots, text & element extracts | P2 | 2 | artifacts |  | 1 | 0 | 0 | 0 | #317 |
| 278 | UI: Control tab visibility with Feature Flags (per-tab toggles & presets) | P1 | 2 | uiux |  | 1 | 2 | 1 | 0 |  |
| 279 | Config: Consolidate configuration menus, env files, and defaults | P2 | 2 | config |  | 1 | 0 | 0 | 0 |  |
| 280 | Browser Settings: Improve Browser Settings menu clarity & enforce behavior across run types | P2 | 2 | uiux |  | 1 | 0 | 0 | 0 |  |
| 285 | Browser-Use/Web-UIをベースとしてUI周りのリファクタリング | P2 | 2 | uiux | high | 1 | 0 | 0 | 0 |  |
| 287 | Template for new issue and new PR | P3 | 2 | docs |  | 1 | 0 | 0 | 0 | #318 |
| 305 | [ui/ux] 🎥 Recordings: タブ統合（ソート/フィルタ/ページング、LLM無効時非表示制御、Flag連携）[Sub of #302] | P2 | 2 | uiux |  | 1 | 2 | 3 | 0 | #310 |
| 307 | [docs] 🎥 Recordings: 仕様/Flags/運用手順の更新 [Sub of #302] | P2 | 2 | docs |  | 1 | 2 | 5 | 3 | #312 |
| 313 | [refactor] bykilt.py run_with_stream コード重複解消 (DRY原則適用) | P3 | 3 | runner |  | 1 | 0 | 1 | 0 |  |
| 314 | [enhancement] OutputCapture スレッドセーフ性改善 (threading.Lock 追加) | P2 | 3 | logging |  | 1 | 0 | 1 | 0 |  |
| 315 | [bug] try-finally によるリソースクリーンアップ強化 | P2 | 3 | logging |  | 1 | 0 | 1 | 0 |  |
| 320 | feat: Auto-discovery and import of browser automation commands from remote llms.txt files | P0 | 2 | config |  | 1 | 2 | 1 | 0 | #322 |
| 34 | 要素値キャプチャ & エクスポート | P1 | 1 | artifacts |  | 1 | 2 | 2 | 0 | #93 |
| 38 | 録画統一後回帰テストスイート | P2 | 1-late | artifacts |  | 1 | 4 | 5 | 0 | #103 |
| 40 | CSV D&D UI 連携 | P2 | 2 | batch |  | 1 | 2 | 1 | 0 | #172 |
| 41 | バッチ進捗・サマリー | P2 | 2 | batch |  | 1 | 3 | 2 | 0 | #162 |
| 42 | バッチ部分リトライ | P2 | 2 | batch |  | 1 | 2 | 1 | 0 | #163 |
| 43 | ENABLE_LLM パリティ | P1 | 1-late | runner |  | 1 | 2 | 2 | 0 |  |
| 45 | git_script 認証 & プロキシ | P1 | 1 | runner |  | 1 | 2 | 2 | 0 | #120 |
| 48 | 環境変数バリデーション & 診断 | P2 | 2 | runner |  | 1 | 1 | 1 | 0 |  |
| 49 | ユーザースクリプト プラグインアーキテクチャ | P3 | 2 | plugins | high | 1 | 2 | 2 | 0 |  |
| 50 | ディレクトリ名変更 & 移行 | P1 | 1 | runner |  | 1 | 1 | 1 | 1 |  |
| 51 | Windows プロファイル永続化 | P2 | 2 | runner |  | 1 | 3 | 1 | 0 |  |
| 52 | サンドボックス allow/deny パス | P2 | 2 | runner |  | 1 | 2 | 1 | 0 |  |
| 54 | cdp-use デュアルエンジン抽象レイヤ | P1 | 2 | runner | high | 1 | 1 | 2 | 0 |  |
| 55 | browser_control pytest パス修正 | P0 | 1 | runner |  | 1 | 0 | 0 | 0 | #187 |
| 57 | ログ保持期間 & ローテーション | P1 | 1-late | logging |  | 1 | 3 | 1 | 0 | #83 |
| 59 | Run メトリクス API | P2 | 2 | observability |  | 1 | 2 | 1 | 0 | #185 |
| 60 | シークレットマスキング拡張 | P1 | 1-late | security |  | 1 | 3 | 1 | 0 |  |
| 61 | [maint][security] 既存依存セキュリティスキャン基盤の最適化 & 運用強化 | P1 | 2 | security | medium | 1 | 1 | 1 | 0 |  |
| 67 | ドキュメント整備 第2弾 | P2 | 1-late | docs |  | 1 | 4 | 1 | 0 |  |
| 87 | スクリーンショット重複保存フラグ導入 | P1 | 1-late | artifacts |  | 1 | 2 | 2 | 1 | #96 |
| 88 | スクリーンショット例外分類と特定例外キャッチ | P2 | 1-late | artifacts |  | 1 | 2 | 2 | 0 | #97 |
| 89 | Screenshot ログイベント整備 (metrics 連携準備) | P2 | 1-late | observability |  | 1 | 2 | 2 | 0 | #98 |
| 91 | 統一録画パス Rollout (flag default 有効化 & legacy 廃止) | P0 | 1-late | artifacts |  | 1 | 2 | 1 | 0 | #105 |
| 90 | Temp test issue for enrichment | P2 | 2 | test |  |  | 0 | 0 | 0 |  |

## 7. 依存詳細 (Fan-in / Fan-out)

### Issue 302: [ui/ux][artifacts] 🎥 Recordings: リカーシブ検出 + LLM無効時GIF代替 (Flag対応)
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 6
- LongestDistance: 0
- Depends (0): (none)
- Dependents (5): 303, 304, 305, 306, 307
- Progress: {"state": "in-progress", "note": "4/5 sub-issues done; PR #311, #312 pending merge"}

### Issue 219: [runner][bug] search-linkedin 初期コマンド失敗 (pytest経由引数未解釈)
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 5
- LongestDistance: 4
- Depends (2): 200, 201
- Dependents (2): 220, 221
- Progress: {"state": "done", "primary_pr": 232}

### Issue 32: Run/Job ID 基盤
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 5
- LongestDistance: 0
- Depends (0): (none)
- Dependents (10): 28, 31, 33, 35, 46, 54, 56, 58, 39, 62
- Progress: {"state": "done", "primary_pr": 79}

### Issue 65: マルチ環境設定ローダ
- Priority: P0, Phase: 1, Area: config
- Risk: (none)
- CriticalPathRank: 5
- LongestDistance: 0
- Depends (0): (none)
- Dependents (4): 64, 63, 43, 48

### Issue 220: [runner][bug] browser-control タイプ実行失敗の調査と修正
- Priority: P1, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 4
- LongestDistance: 0
- Depends (1): 219
- Dependents (1): 221
- Progress: {"state": "open"}

### Issue 237: Bug: Recording file generation not working for any run type
- Priority: P0, Phase: 2, Area: artifacts
- Risk: high
- CriticalPathRank: 4
- LongestDistance: 0
- Depends (1): 221
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 239}

### Issue 28: 録画ファイル保存パス統一
- Priority: P0, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 4
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 30
- Progress: {"state": "done", "primary_pr": 112}

### Issue 64: フィーチャーフラグフレームワーク
- Priority: P0, Phase: 1, Area: config
- Risk: (none)
- CriticalPathRank: 4
- LongestDistance: 1
- Depends (1): 65
- Dependents (3): 63, 43, 49

### Issue 110: browser-control gap fix
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 0
- Depends (1): 111
- Dependents (1): 106
- Progress: {"state": "done", "primary_pr": 188}

### Issue 111: 録画/パス統合
- Priority: P0, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 2
- Depends (1): 28
- Dependents (1): 110
- Progress: {"state": "done", "primary_pr": 188}

### Issue 221: [artifacts][bug] script 以外で録画ファイル未生成 (browser-control/git-script)
- Priority: P1, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 0
- Depends (2): 219, 220
- Dependents (1): 224
- Progress: {"state": "open"}

### Issue 25: git_script が llms.txt で指定したスクリプトを正しく解決するよう修正
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 0
- Depends (0): (none)
- Dependents (4): 44, 45, 49, 50
- Progress: {"state": "done", "primary_pr": 118}

### Issue 30: 録画タイプ間不整合是正
- Priority: P0, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 2
- Depends (1): 28
- Dependents (2): 37, 38
- Progress: {"state": "done", "primary_pr": 112}

### Issue 303: [artifacts] 🎥 Recordings: 再帰探索ユーティリティ + テスト (Flag対応) [Sub of #302]
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 1
- Depends (1): 302
- Dependents (1): 305
- Progress: {"state": "done", "primary_pr": 308}

### Issue 31: 統一ログ設計 (JSON Lines)
- Priority: P0, Phase: 1, Area: logging
- Risk: high
- CriticalPathRank: 3
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 56
- Progress: {"state": "done", "primary_pr": 80}

### Issue 35: アーティファクト manifest v2
- Priority: P0, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 1
- Depends (1): 32
- Dependents (3): 34, 36, 38
- Progress: {"state": "done", "primary_pr": 94}

### Issue 46: Run/Job タイムアウト & キャンセル
- Priority: P2, Phase: 2, Area: runner
- Risk: high
- CriticalPathRank: 3
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 47

### Issue 63: llms.txt スキーマ & バリデータ
- Priority: P0, Phase: 1-late, Area: config
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 2
- Depends (2): 64, 65
- Dependents (1): 66

### Issue 175: バッチ行単位成果物キャプチャ基盤 (スクリーンショット/要素値/ログ関連紐付け)
- Priority: P1, Phase: 2, Area: artifacts
- Risk: medium
- CriticalPathRank: 2
- LongestDistance: 4
- Depends (6): 39, 40, 41, 42, 33, 35
- Dependents (1): 176
- Progress: {"state": "done", "primary_pr": 181}

### Issue 176: 宣言的抽出スキーマ (CSV列→コマンド引数/抽出ポリシーマッピング)
- Priority: P1, Phase: 2, Area: batch
- Risk: high
- CriticalPathRank: 2
- LongestDistance: 3
- Depends (3): 175, 39, 40
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 181}

### Issue 222: [logging][feat] ログ出力ディレクトリ/カテゴリ標準化 & src/logs/ 廃止
- Priority: P1, Phase: 2, Area: logging
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 4
- Depends (2): 56, 57
- Dependents (1): 223
- Progress: {"state": "open"}

### Issue 304: [service] 🎥 Recordings: 一覧取得サービス/API (Flag連携) [Sub of #302]
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (2): 302, 303
- Dependents (1): 305
- Progress: {"state": "done", "primary_pr": 309}

### Issue 306: [worker] 🎥 Recordings: GIF変換ワーカー/キャッシュ + Flag [Sub of #302]
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 302
- Dependents (1): 307
- Progress: {"state": "in-progress", "note": "implementation complete; PR #311 awaiting merge"}

### Issue 329: Split script/script_manager.py into executor modules
- Priority: P1, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 264
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "Phase 4 done (PR #332 merged: git_operations, artifact_management); Phase 2 in PR #334 (open: browser_control_executor, process_helpers)", "primary_pr": 334, "related_prs": [332]}

### Issue 33: スクリーンショット取得ユーティリティ
- Priority: P0, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (3): 38, 34, 76

### Issue 36: アーティファクト一覧 API
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (1): 35
- Dependents (1): 38
- Progress: {"state": "done", "primary_pr": 95}

### Issue 37: 動画アーティファクト保持期間
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 3
- Depends (1): 30
- Dependents (1): 38
- Progress: {"state": "done", "primary_pr": 99}

### Issue 39: CSV 駆動バッチエンジンコア
- Priority: P1, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (4): 40, 41, 42, 198
- Progress: {"state": "done", "primary_pr": 164}

### Issue 44: git_script 解決ロジック不具合修正
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 25
- Dependents (1): 45
- Progress: {"state": "done", "primary_pr": 120}

### Issue 47: 並列実行キュー & 制限
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (1): 46
- Dependents (1): 51

### Issue 53: cdp-use 追加タイプ調査
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 0
- Depends (0): (none)
- Dependents (1): 54

### Issue 56: 統一 JSON Lines ロギング実装
- Priority: P0, Phase: 1, Area: logging
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (2): 31, 32
- Dependents (3): 57, 60, 41
- Progress: {"state": "done", "primary_pr": 83}

### Issue 58: メトリクス計測基盤 & エクスポータ
- Priority: P1, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 59
- Progress: {"state": "done", "primary_pr": 156}

### Issue 62: 実行サンドボックス機能制限
- Priority: P0, Phase: 2, Area: security
- Risk: high
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 52

### Issue 66: ドキュメント整備 第1弾
- Priority: P2, Phase: 1-late, Area: docs
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 3
- Depends (1): 63
- Dependents (1): 67

### Issue 76: 依存更新自動化パイプライン (PR 起票時の ISSUE_DEPENDENCIES.yml 自動更新)
- Priority: P1, Phase: 1-late, Area: automation
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (1): 33
- Dependents (0): (none)

### Issue 81: Async/Browser テスト安定化計画
- Priority: P1, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "partial: PR #286 applied - further stability work remains"}

### Issue 102: Flags artifacts helper
- Priority: P2, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
- Dependents (0): (none)
- Progress: {"state": "in-progress"}

### Issue 107: Cleanup: PytestReturnNotNone warnings across component tests
- Priority: P2, Phase: 1-late, Area: testing
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 108: Stabilize Edge headless navigation flake (TargetClosedError)
- Priority: P2, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- Priority: P2, Phase: 2, Area: quality
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- Priority: P2, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- Priority: P2, Phase: 2, Area: automation
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / flags 再生成 / パス可搬性 / flags 再生成)
- Priority: P2, Phase: 2, Area: testing
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- Priority: P1, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "in-progress"}

### Issue 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- Priority: P1, Phase: 1, Area: security
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 160}

### Issue 173: [UI][batch][#40 follow-up] CSV Preview & Command Argument Mapping
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (4): 39, 40, 41, 42
- Dependents (0): (none)

### Issue 174: [artifacts][batch] Clarify Artifact Output & Access Flow
- Priority: P3, Phase: 2, Area: artifacts
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (5): 28, 30, 33, 35, 39
- Dependents (0): (none)

### Issue 177: MVP エンタープライズ Readiness マトリクス定義
- Priority: P1, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (5): 60, 58, 35, 39, 43
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 189}

### Issue 178: CI: dependency-pipeline workflow 追加 (生成物 idempotent 検証自動化)
- Priority: P2, Phase: 2, Area: automation
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 76
- Dependents (0): (none)

### Issue 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- Priority: P1, Phase: 2, Area: security
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 194: [artifacts] Tab index manifest for multi-tab recordings
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (2): 246, 247
- Progress: {"state": "open"}

### Issue 196: CI: local selector smoke を統合
- Priority: P2, Phase: 2, Area: automation
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (1): 201
- Dependents (1): 202
- Progress: {"state": "done", "primary_pr": 213}

### Issue 197: [dashboard] UI graphs and preset expansion
- Priority: P2, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 198: [batch] CSV NamedString 入力の正規化
- Priority: P1, Phase: 2, Area: batch
- Risk: medium
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 256}

### Issue 199: [ui/ux] Internationalization (i18n): JA base → EN 追加
- Priority: P2, Phase: 2, Area: uiux
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (3): 208, 209, 210
- Progress: {"state": "open"}

### Issue 200: [policy] myscript 配置規約の策定
- Priority: P2, Phase: 2, Area: docs
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 50
- Dependents (2): 201, 203
- Progress: {"state": "in-progress"}

### Issue 201: [runner] myscript スクリプト修正（パス統一・生成物出力）
- Priority: P2, Phase: 2, Area: runner
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 200
- Dependents (3): 196, 202, 203
- Progress: {"state": "done", "primary_pr": 213}

### Issue 202: [ci] アーティファクト収集/キャッシュ更新（myscript 構成対応）
- Priority: P2, Phase: 2, Area: automation
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 5
- Depends (2): 201, 196
- Dependents (1): 203
- Progress: {"state": "done", "primary_pr": 214}

### Issue 203: [docs] README/チュートリアル/ガイド更新（myscript 構成・出力ポリシー）
- Priority: P2, Phase: 2, Area: docs
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 6
- Depends (3): 200, 201, 202
- Dependents (0): (none)
- Progress: {"state": "planned"}

### Issue 208: [ui/ux] Option Availability - 利用可能なオプションの可視化改善
- Priority: P2, Phase: 2, Area: uiux
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 199
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 209: [ui/ux] Results menu - 実行結果表示メニューの改善
- Priority: P2, Phase: 2, Area: uiux
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 199
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 210: [ui/ux] Recordings menu - 録画ファイル管理メニューの改善
- Priority: P2, Phase: 2, Area: uiux
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 199
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 211: [docs] LLM 統合ドキュメント整備
- Priority: P1, Phase: 2, Area: docs
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 43
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 212: [ui/ux] Playwright Codegenメニューの保存ボタン統合改善
- Priority: P1, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 53
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 218: テストカバレッジ率の向上
- Priority: P2, Phase: 2, Area: testing
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 223: [logging][bug] LOG_LEVEL 環境変数が反映されない (初期化順序バグ)
- Priority: P0, Phase: 2, Area: logging
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 222
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 233}

### Issue 224: [ui/ux][config] RECORDING_PATH UI と環境変数の競合解消
- Priority: P1, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 221
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "partial: PR #286 addressed script/artifact paths; UI follow-up required"}

### Issue 226: [runner][bug] search-linkedin 実行時エラー修正
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (2): 200, 201
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 232}

### Issue 227: [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保
- Priority: P2, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 228: [configuration][enhancement] LLM設定の改善と設定ガイドの明確化
- Priority: P2, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 229: [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立
- Priority: P2, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 230: [documentation][enhancement] ドキュメントの改善とユーザガイドの充実
- Priority: P2, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 231: [testing][enhancement] テストスイートの改善とカバレッジ向上
- Priority: P2, Phase: 2, Area: testing
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "partial: many tests stabilized in PR #286; additional coverage tasks remain"}

### Issue 240: P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing
- Priority: P0, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 241: P0: Fix Unlock-Future type browser automation - Operations hang without execution
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 242: P1: Optimize Feature Flag usage for UI menu control - Hide LLM tabs when disabled
- Priority: P1, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 244: [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加
- Priority: P2, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 246: [artifacts][feat] スクリーンショットの取得・保存機能強化
- Priority: P1, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 194
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 247: [artifacts][feat] ブラウザ要素の取得・保存機能強化
- Priority: P1, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 194
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 248: CSV Batch Processing Enhancement Priority
- Priority: P1, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (2): 198, 173
- Dependents (0): (none)
- Progress: {"state": "in-progress"}

### Issue 249: Phase2-07 Metrics Advancement
- Priority: P0, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 222
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 250: Phase2-13 Runner Fixes Parallel
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (2): 220, 221
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 251: Phase2-14 Config Conflicts
- Priority: P0, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 224
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 255: git-scriptのURL評価制限緩和
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 257: [batch] CSV Batch Job Execution Not Triggered - Browser Automation Missing
- Priority: P0, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (2): 39, 198
- Dependents (0): (none)
- Progress: {"state": "done"}

### Issue 264: リファクタ提案: 大きすぎる Python ファイルの分割とモジュール化
- Priority: P2, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (1): 329
- Progress: {"state": "open"}

### Issue 265: 改善提案: 複数フォルダ配下の録画ファイルを再帰的に発見・一覧表示
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (3): 266, 267, 268
- Progress: {"state": "in-progress", "note": "partial: PR #317 implemented recursive scanning & filtering; multiple roots config pending", "primary_pr": 317}

### Issue 266: Discovery: 録画ファイル検出ユーティリティ（Discovery）
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 265
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 267: API: 録画ファイル検索 API 設計
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 265, 266
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 268: UI: 録画ファイル集約ビューと実装
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (3): 265, 266, 267
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 317}

### Issue 269: 提案: Feature Flag の全面活用とプロファイルベースの機能有効化
- Priority: P1, Phase: 1, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (3): 270, 271, 272
- Progress: {"state": "open"}

### Issue 270: 設計: Feature Flag 運用設計とメタデータ仕様
- Priority: P1, Phase: 1, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 269
- Dependents (1): 271
- Progress: {"state": "open"}

### Issue 271: 実装: Feature Flags コアライブラリと Profile ベースセットアップ
- Priority: P1, Phase: 1, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 269, 270
- Dependents (1): 272
- Progress: {"state": "open"}

### Issue 272: UI: Admin UI による Feature Flag 管理画面の実装
- Priority: P1, Phase: 1, Area: flags
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (2): 269, 271
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 319}

### Issue 276: Batch: Recording file not copied to artifacts runs folder when using CSV batch
- Priority: P1, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "partial: run_script artifact move added in PR #286; CSV batch integration verification pending"}

### Issue 277: Artifacts UI: Provide UI listing for screenshots, text & element extracts
- Priority: P2, Phase: 2, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 317}

### Issue 278: UI: Control tab visibility with Feature Flags (per-tab toggles & presets)
- Priority: P1, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 279: Config: Consolidate configuration menus, env files, and defaults
- Priority: P2, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 280: Browser Settings: Improve Browser Settings menu clarity & enforce behavior across run types
- Priority: P2, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 285: Browser-Use/Web-UIをベースとしてUI周りのリファクタリング
- Priority: P2, Phase: 2, Area: uiux
- Risk: high
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 287: Template for new issue and new PR
- Priority: P3, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 318}

### Issue 305: [ui/ux] 🎥 Recordings: タブ統合（ソート/フィルタ/ページング、LLM無効時非表示制御、Flag連携）[Sub of #302]
- Priority: P2, Phase: 2, Area: uiux
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (3): 302, 303, 304
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 310}

### Issue 307: [docs] 🎥 Recordings: 仕様/Flags/運用手順の更新 [Sub of #302]
- Priority: P2, Phase: 2, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (5): 302, 303, 304, 305, 306
- Dependents (3): 313, 314, 315
- Progress: {"state": "done", "primary_pr": 312}

### Issue 313: [refactor] bykilt.py run_with_stream コード重複解消 (DRY原則適用)
- Priority: P3, Phase: 3, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 307
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 314: [enhancement] OutputCapture スレッドセーフ性改善 (threading.Lock 追加)
- Priority: P2, Phase: 3, Area: logging
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 307
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 315: [bug] try-finally によるリソースクリーンアップ強化
- Priority: P2, Phase: 3, Area: logging
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (1): 307
- Dependents (0): (none)
- Progress: {"state": "open"}

### Issue 320: feat: Auto-discovery and import of browser automation commands from remote llms.txt files
- Priority: P0, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
- Dependents (0): (none)
- Progress: {"state": "in-progress", "note": "Phase 1+2 complete (PR #321 merged); Phase 3+4 in PR #322 (open)", "primary_pr": 322, "related_prs": [321]}

### Issue 34: 要素値キャプチャ & エクスポート
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 33, 35
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 93}

### Issue 38: 録画統一後回帰テストスイート
- Priority: P2, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (5): 30, 33, 35, 36, 37
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 103}

### Issue 40: CSV D&D UI 連携
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 172}

### Issue 41: バッチ進捗・サマリー
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (2): 39, 56
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 162}

### Issue 42: バッチ部分リトライ
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 163}

### Issue 43: ENABLE_LLM パリティ
- Priority: P1, Phase: 1-late, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 64, 65
- Dependents (0): (none)

### Issue 45: git_script 認証 & プロキシ
- Priority: P1, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 25, 44
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 120}

### Issue 48: 環境変数バリデーション & 診断
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 65
- Dependents (0): (none)

### Issue 49: ユーザースクリプト プラグインアーキテクチャ
- Priority: P3, Phase: 2, Area: plugins
- Risk: high
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 64, 25
- Dependents (0): (none)

### Issue 50: ディレクトリ名変更 & 移行
- Priority: P1, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 25
- Dependents (1): 200
- Progress: {"state": "in-progress"}

### Issue 51: Windows プロファイル永続化
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 47
- Dependents (0): (none)

### Issue 52: サンドボックス allow/deny パス
- Priority: P2, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 62
- Dependents (0): (none)

### Issue 54: cdp-use デュアルエンジン抽象レイヤ
- Priority: P1, Phase: 2, Area: runner
- Risk: high
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (2): 32, 53
- Dependents (0): (none)

### Issue 55: browser_control pytest パス修正
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 187}

### Issue 57: ログ保持期間 & ローテーション
- Priority: P1, Phase: 1-late, Area: logging
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 56
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 83}

### Issue 59: Run メトリクス API
- Priority: P2, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 58
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 185}

### Issue 60: シークレットマスキング拡張
- Priority: P1, Phase: 1-late, Area: security
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (1): 56
- Dependents (0): (none)

### Issue 61: [maint][security] 既存依存セキュリティスキャン基盤の最適化 & 運用強化
- Priority: P1, Phase: 2, Area: security
- Risk: medium
- CriticalPathRank: 1
- LongestDistance: 1
- Depends (1): 32
- Dependents (0): (none)

### Issue 67: ドキュメント整備 第2弾
- Priority: P2, Phase: 1-late, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (1): 66
- Dependents (0): (none)

### Issue 87: スクリーンショット重複保存フラグ導入
- Priority: P1, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 33, 35
- Dependents (1): 83
- Progress: {"state": "done", "primary_pr": 96}

### Issue 88: スクリーンショット例外分類と特定例外キャッチ
- Priority: P2, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 33, 35
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 97}

### Issue 89: Screenshot ログイベント整備 (metrics 連携準備)
- Priority: P2, Phase: 1-late, Area: observability
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 33, 58
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 98}

### Issue 91: 統一録画パス Rollout (flag default 有効化 & legacy 廃止)
- Priority: P0, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 28
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 105}

### Issue 90: Temp test issue for enrichment
- Priority: P2, Phase: 2, Area: test
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

