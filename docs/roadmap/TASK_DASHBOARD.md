# TASK DASHBOARD

Generated at (UTC): 2025-09-21T21:34:41+00:00

## 1. メタサマリー

- Total Issues: 100
- High Risk (declared): 8 → 31, 46, 49, 54, 62, 176, 237, 238
- Cycle Detected: false (none)
- Strict Orphans: 25
- Curated Orphan List Count: 33

## 2. 分布 (Distribution)

### Priority
- (none): 4 (4.0%)
- P0: 24 (24.0%)
- P1: 29 (29.0%)
- P2: 41 (41.0%)
- P3: 2 (2.0%)

### Phase
- (none): 12 (12.0%)
- 1: 20 (20.0%)
- 1-late: 14 (14.0%)
- 2: 54 (54.0%)

### Area
- (none): 19 (19.0%)
- artifacts: 16 (16.0%)
- automation: 4 (4.0%)
- batch: 7 (7.0%)
- config: 5 (5.0%)
- docs: 6 (6.0%)
- logging: 5 (5.0%)
- observability: 3 (3.0%)
- plugins: 1 (1.0%)
- runner: 23 (23.0%)
- security: 4 (4.0%)
- test: 1 (1.0%)
- uiux: 6 (6.0%)

### Risk
- high: 8 (8.0%)
- low: 12 (12.0%)
- medium: 4 (4.0%)
- none: 76 (76.0%)

## 3. リスク詳細 (High / Medium / etc.)

High Risk Issues:
- 31: 統一ログ設計 (JSON Lines) (area=logging, priority=P0)
- 46: Run/Job タイムアウト & キャンセル (area=runner, priority=P2)
- 49: ユーザースクリプト プラグインアーキテクチャ (area=plugins, priority=P3)
- 54: cdp-use デュアルエンジン抽象レイヤ (area=runner, priority=P1)
- 62: 実行サンドボックス機能制限 (area=security, priority=P0)
- 176: 宣言的抽出スキーマ (CSV列→コマンド引数/抽出ポリシーマッピング) (area=batch, priority=P1)
- 237: Bug: Recording file generation not working for any run type (area=artifacts, priority=P0)
- 238: Bug: Browser-control fails when ENABLE_LLM=false (area=runner, priority=P0)

## 4. Orphans

Strict Orphans (自動抽出 = 依存なし & 参照されず):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 92: [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync
- 101: chore(test): async ブラウザ起動・event loop 衝突安定化
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- 194: [artifacts] Tab index manifest for multi-tab recordings
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

Curated Orphan List (summary.data_quality_checks.orphan_issues_without_dependents_or_depends):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 92: [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync
- 101: chore(test): async ブラウザ起動・event loop 衝突安定化
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- 194: [artifacts] Tab index manifest for multi-tab recordings
- 197: [dashboard] UI graphs and preset expansion
- 199: [ui/ux] Internationalization (i18n): JA base → EN 追加
- 208: [ui/ux] Option Availability - 利用可能なオプションの可視化改善
- 209: [ui/ux] Results menu - 実行結果表示メニューの改善
- 210: [ui/ux] Recordings menu - 録画ファイル管理メニューの改善
- 211: [docs] LLM 統合ドキュメント整備
- 212: [feat] Playwright Codegen 統合機能
- 218: テストカバレッジ率の向上
- 226: [runner][bug] search-linkedin 実行時エラー修正
- 227: [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保
- 228: [configuration][enhancement] LLM設定の改善と設定ガイドの明確化
- 229: [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立
- 230: [documentation][enhancement] ドキュメントの改善とユーザガイドの充実
- 231: [testing][enhancement] テストスイートの改善とカバレッジ向上
- 240: P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing
- 241: P0: Fix Unlock-Future type browser automation - Operations hang without execution
- 242: P1: Optimize Feature Flag usage for UI menu control - Hide LLM tabs when disabled
- 244: [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加

Missing Strict Orphans in curated list: (none)
Extra non-strict entries in curated list (WARNING only): 199, 208, 209, 210, 211, 212, 226, 242

## 5. クリティカルパス推定

Critical Path (自動算出): depends の有向エッジ (B→A) を距離 0 起点から最長距離でトレースしたパス。 実際の期間や見積りを考慮せず、依存段数のみで推定。

Auto Estimated Path (Longest Distance):
25 → 50 → 200 → 201 → 196 → 202 → 203

Provided Example (existing IDs only):
65 → 64 → 63 → 66 → 67

## 6. Issues Table (sorted)

Sorted By: critical_path_rank

| ID | Title | Pri | Phase | Area | Risk | CP Rank | LongestDist | Depends | Dependents | PrimaryPR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 219 | [runner][bug] search-linkedin 初期コマンド失敗 (pytest経由引数未解釈) | P0 | 2 | runner |  | 5 | 4 | 2 | 2 | #232 |
| 32 | Run/Job ID 基盤 | P0 | 1 | runner |  | 5 | 0 | 0 | 10 | #79 |
| 65 | マルチ環境設定ローダ | P0 | 1 | config |  | 5 | 0 | 0 | 4 |  |
| 220 | [runner][bug] browser-control タイプ実行失敗の調査と修正 | P1 | 2 | runner |  | 4 | 0 | 1 | 1 |  |
| 237 | Bug: Recording file generation not working for any run type | P0 | 2 | artifacts | high | 4 | 0 | 1 | 0 | #239 |
| 238 | Bug: Browser-control fails when ENABLE_LLM=false | P0 | 2 | runner | high | 4 | 0 | 1 | 0 |  |
| 28 | 録画ファイル保存パス統一 | P0 | 1 | artifacts |  | 4 | 1 | 1 | 1 | #112 |
| 64 | フィーチャーフラグフレームワーク | P0 | 1 | config |  | 4 | 1 | 1 | 3 |  |
| 110 | browser-control gap fix | P0 | 2 | runner |  | 3 | 0 | 1 | 1 | #188 |
| 111 | 録画/パス統合 | P0 | 2 | artifacts |  | 3 | 2 | 1 | 1 | #188 |
| 221 | [artifacts][bug] script 以外で録画ファイル未生成 (browser-control/git-script) | P1 | 2 | artifacts |  | 3 | 0 | 2 | 1 |  |
| 25 | git_script が llms.txt で指定したスクリプトを正しく解決するよう修正 | P0 | 1 | runner |  | 3 | 0 | 0 | 4 | #118 |
| 30 | 録画タイプ間不整合是正 | P0 | 1 | artifacts |  | 3 | 2 | 1 | 2 | #112 |
| 31 | 統一ログ設計 (JSON Lines) | P0 | 1 | logging | high | 3 | 1 | 1 | 1 | #80 |
| 35 | アーティファクト manifest v2 | P0 | 1 | artifacts |  | 3 | 1 | 1 | 3 | #94 |
| 46 | Run/Job タイムアウト & キャンセル | P2 | 2 | runner | high | 3 | 1 | 1 | 1 |  |
| 63 | llms.txt スキーマ & バリデータ | P0 | 1-late | config |  | 3 | 2 | 2 | 1 |  |
| 175 | バッチ行単位成果物キャプチャ基盤 (スクリーンショット/要素値/ログ関連紐付け) | P1 | 2 | artifacts | medium | 2 | 4 | 6 | 1 | #181 |
| 176 | 宣言的抽出スキーマ (CSV列→コマンド引数/抽出ポリシーマッピング) | P1 | 2 | batch | high | 2 | 3 | 3 | 0 | #181 |
| 222 | [logging][feat] ログ出力ディレクトリ/カテゴリ標準化 & src/logs/ 廃止 | P1 | 2 | logging |  | 2 | 4 | 2 | 1 |  |
| 33 | スクリーンショット取得ユーティリティ | P0 | 1 | artifacts |  | 2 | 1 | 1 | 3 |  |
| 36 | アーティファクト一覧 API | P1 | 1 | artifacts |  | 2 | 2 | 1 | 1 | #95 |
| 37 | 動画アーティファクト保持期間 | P1 | 1 | artifacts |  | 2 | 3 | 1 | 1 | #99 |
| 39 | CSV 駆動バッチエンジンコア | P1 | 2 | batch |  | 2 | 1 | 1 | 4 | #164 |
| 44 | git_script 解決ロジック不具合修正 | P0 | 1 | runner |  | 2 | 1 | 1 | 1 | #120 |
| 47 | 並列実行キュー & 制限 | P2 | 2 | runner |  | 2 | 2 | 1 | 1 |  |
| 53 | cdp-use 追加タイプ調査 | P2 | 2 | runner |  | 2 | 0 | 0 | 1 |  |
| 56 | 統一 JSON Lines ロギング実装 | P0 | 1 | logging |  | 2 | 2 | 2 | 3 | #83 |
| 58 | メトリクス計測基盤 | P1 | 2 | observability |  | 2 | 1 | 1 | 1 | #155 |
| 62 | 実行サンドボックス機能制限 | P0 | 2 | security | high | 2 | 1 | 1 | 1 |  |
| 66 | ドキュメント整備 第1弾 | P2 | 1-late | docs |  | 2 | 3 | 1 | 1 |  |
| 76 | 依存更新自動化パイプライン (PR 起票時の ISSUE_DEPENDENCIES.yml 自動更新) | P1 | 1-late | automation |  | 2 | 2 | 1 | 0 |  |
| 81 | Async/Browser テスト安定化計画 | P1 | 1 | runner |  | 2 | 0 | 0 | 0 |  |
| 102 | Flags artifacts helper | P2 | 2 | config |  | 1 | 2 | 1 | 0 |  |
| 154 | pip-audit stabilization in CI with normalizer + targeted suppressions | P1 | 1 | security |  | 1 | 0 | 0 | 0 | #160 |
| 173 | [UI][batch][#40 follow-up] CSV Preview & Command Argument Mapping | P2 | 2 | batch |  | 1 | 4 | 4 | 0 |  |
| 174 | [artifacts][batch] Clarify Artifact Output & Access Flow | P3 | 2 | artifacts | low | 1 | 3 | 5 | 0 |  |
| 177 | MVP エンタープライズ Readiness マトリクス定義 | P1 | 2 | docs |  | 1 | 4 | 5 | 0 | #189 |
| 178 | CI: dependency-pipeline workflow 追加 (生成物 idempotent 検証自動化) | P2 | 2 | automation | low | 1 | 3 | 1 | 0 |  |
| 196 | CI: local selector smoke を統合 | P2 | 2 | automation | low | 1 | 4 | 1 | 1 | #213 |
| 198 | [batch] CSV NamedString 入力の正規化 | P1 | 2 | batch | medium | 1 | 2 | 1 | 0 |  |
| 199 | [ui/ux] Internationalization (i18n): JA base → EN 追加 | P2 | 2 | uiux | low | 1 | 0 | 0 | 0 |  |
| 200 | [policy] myscript 配置規約の策定 | P2 | 2 | docs | low | 1 | 2 | 1 | 2 |  |
| 201 | [runner] myscript スクリプト修正（パス統一・生成物出力） | P2 | 2 | runner | low | 1 | 3 | 1 | 3 | #213 |
| 202 | [ci] アーティファクト収集/キャッシュ更新（myscript 構成対応） | P2 | 2 | automation | low | 1 | 5 | 2 | 1 | #214 |
| 203 | [docs] README/チュートリアル/ガイド更新（myscript 構成・出力ポリシー） | P2 | 2 | docs | low | 1 | 6 | 3 | 0 |  |
| 208 | [ui/ux] Option Availability - 利用可能なオプションの可視化改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 209 | [ui/ux] Results menu - 実行結果表示メニューの改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 210 | [ui/ux] Recordings menu - 録画ファイル管理メニューの改善 | P2 | 2 | uiux | low | 1 | 1 | 1 | 0 |  |
| 211 | [docs] LLM 統合ドキュメント整備 | P1 | 2 | docs | low | 1 | 3 | 1 | 0 |  |
| 212 | [feat] Playwright Codegen 統合機能 | P1 | 2 | runner | medium | 1 | 2 | 1 | 0 |  |
| 223 | [logging][bug] LOG_LEVEL 環境変数が反映されない (初期化順序バグ) | P0 | 2 | logging |  | 1 | 0 | 1 | 0 | #233 |
| 224 | [ui/ux][config] RECORDING_PATH UI と環境変数の競合解消 | P1 | 2 | uiux |  | 1 | 0 | 1 | 0 |  |
| 226 | [runner][bug] search-linkedin 実行時エラー修正 | P0 | 2 | runner |  | 1 | 4 | 2 | 0 | #232 |
| 240 | P0: Fix user profile utilization in browser launch - Critical SSO/Cookie functionality missing | P0 | 2 | config |  | 1 | 0 | 0 | 0 |  |
| 241 | P0: Fix Unlock-Future type browser automation - Operations hang without execution | P0 | 2 | runner |  | 1 | 0 | 0 | 0 |  |
| 242 | P1: Optimize Feature Flag usage for UI menu control - Hide LLM tabs when disabled | P1 | 2 | uiux |  | 1 | 2 | 1 | 0 |  |
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
| 55 | browser_control pytest パス修正 | P0 | 1 | runner |  | 1 | 0 | 0 | 0 |  |
| 57 | ログ保持期間 & ローテーション | P1 | 1-late | logging |  | 1 | 3 | 1 | 0 | #83 |
| 59 | Run メトリクス API | P2 | 2 | observability |  | 1 | 2 | 1 | 0 | #185 |
| 60 | シークレットマスキング拡張 | P1 | 1-late | security |  | 1 | 3 | 1 | 0 |  |
| 61 | [maint][security] 既存依存セキュリティスキャン基盤の最適化 & 運用強化 | P1 | 2 | security | medium | 1 | 1 | 1 | 0 |  |
| 67 | ドキュメント整備 第2弾 | P2 | 1-late | docs |  | 1 | 4 | 1 | 0 |  |
| 87 | スクリーンショット重複保存フラグ導入 | P1 | 1-late | artifacts |  | 1 | 2 | 2 | 1 | #96 |
| 88 | スクリーンショット例外分類と特定例外キャッチ | P2 | 1-late | artifacts |  | 1 | 2 | 2 | 0 | #97 |
| 89 | Screenshot ログイベント整備 (metrics 連携準備) | P2 | 1-late | observability |  | 1 | 2 | 2 | 0 | #98 |
| 91 | 統一録画パス Rollout (flag default 有効化 & legacy 廃止) | P0 | 1-late | artifacts |  | 1 | 2 | 1 | 0 | #105 |
| 101 | chore(test): async ブラウザ起動・event loop 衝突安定化 | P2 | 1 |  |  |  | 0 | 0 | 0 |  |
| 107 | Cleanup: PytestReturnNotNone warnings across component tests | P2 | 1-late |  |  |  | 0 | 0 | 0 |  |
| 108 | Stabilize Edge headless navigation flake (TargetClosedError) | P2 | 1-late |  |  |  | 0 | 0 | 0 |  |
| 109 | [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随) | P2 | 2 |  |  |  | 0 | 0 | 0 |  |
| 113 | docs: cleanup archived references to tests/pytest.ini (post PR #112) | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 114 | ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112) | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 115 | [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成) |  |  |  |  |  | 0 | 0 | 0 |  |
| 127 | [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善 | P1 | 2 |  |  |  | 0 | 0 | 0 |  |
| 192 | [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule | P1 | 2 |  |  |  | 0 | 0 | 0 |  |
| 194 | [artifacts] Tab index manifest for multi-tab recordings |  |  |  |  |  | 0 | 0 | 0 |  |
| 197 | [dashboard] UI graphs and preset expansion |  |  |  |  |  | 0 | 0 | 0 |  |
| 218 | テストカバレッジ率の向上 |  |  |  |  |  | 0 | 0 | 0 |  |
| 227 | [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保 | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 228 | [configuration][enhancement] LLM設定の改善と設定ガイドの明確化 | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 229 | [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立 | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 230 | [documentation][enhancement] ドキュメントの改善とユーザガイドの充実 | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 231 | [testing][enhancement] テストスイートの改善とカバレッジ向上 | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 244 | [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加 | P2 | 2 |  |  |  | 0 | 0 | 0 |  |
| 90 | Temp test issue for enrichment | P2 | 2 | test |  |  | 0 | 0 | 0 |  |
| 92 | [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync | P2 |  |  |  |  | 0 | 0 | 0 |  |

## 7. 依存詳細 (Fan-in / Fan-out)

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

### Issue 238: Bug: Browser-control fails when ENABLE_LLM=false
- Priority: P0, Phase: 2, Area: runner
- Risk: high
- CriticalPathRank: 4
- LongestDistance: 0
- Depends (1): 220
- Dependents (0): (none)
- Progress: {"state": "open"}

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

### Issue 58: メトリクス計測基盤
- Priority: P1, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 59
- Progress: {"state": "done", "primary_pr": 155}

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

### Issue 102: Flags artifacts helper
- Priority: P2, Phase: 2, Area: config
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
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

### Issue 196: CI: local selector smoke を統合
- Priority: P2, Phase: 2, Area: automation
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (1): 201
- Dependents (1): 202
- Progress: {"state": "done", "primary_pr": 213}

### Issue 198: [batch] CSV NamedString 入力の正規化
- Priority: P1, Phase: 2, Area: batch
- Risk: medium
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)
- Progress: {"state": "planned"}

### Issue 199: [ui/ux] Internationalization (i18n): JA base → EN 追加
- Priority: P2, Phase: 2, Area: uiux
- Risk: low
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)
- Progress: {"state": "planned"}

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

### Issue 212: [feat] Playwright Codegen 統合機能
- Priority: P1, Phase: 2, Area: runner
- Risk: medium
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 64
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
- Progress: {"state": "open"}

### Issue 226: [runner][bug] search-linkedin 実行時エラー修正
- Priority: P0, Phase: 2, Area: runner
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (2): 200, 201
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 232}

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

### Issue 101: chore(test): async ブラウザ起動・event loop 衝突安定化
- Priority: P2, Phase: 1, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 107: Cleanup: PytestReturnNotNone warnings across component tests
- Priority: P2, Phase: 1-late, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 108: Stabilize Edge headless navigation flake (TargetClosedError)
- Priority: P2, Phase: 1-late, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- Priority: P2, Phase: 2, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成)
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- Priority: P1, Phase: 2, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 192: [security][follow-up] Issue #154 pip-audit stabilization - monthly security monitoring schedule
- Priority: P1, Phase: 2, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 194: [artifacts] Tab index manifest for multi-tab recordings
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 197: [dashboard] UI graphs and preset expansion
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 218: テストカバレッジ率の向上
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 227: [ui/ux][enhancement] LLM有効時のエラーメッセージ改善とUI統一性確保
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 228: [configuration][enhancement] LLM設定の改善と設定ガイドの明確化
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 229: [ui/ux][enhancement] UI/UXの統一性確保とデザインシステムの確立
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 230: [documentation][enhancement] ドキュメントの改善とユーザガイドの充実
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 231: [testing][enhancement] テストスイートの改善とカバレッジ向上
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 244: [docs][feat] action_runner_template 利用方法ドキュメント整備 & 実装サンプル追加
- Priority: P2, Phase: 2, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 90: Temp test issue for enrichment
- Priority: P2, Phase: 2, Area: test
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 92: [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

