# TASK DASHBOARD

Generated at (UTC): 2025-09-11T12:19:47+00:00

## 1. メタサマリー

- Total Issues: 68
- High Risk (declared): 5 → 31, 46, 49, 54, 62
- Cycle Detected: false (none)
- Strict Orphans: 22
- Curated Orphan List Count: 22

## 2. 分布 (Distribution)

### Priority
- (none): 7 (10.3%)
- P0: 17 (25.0%)
- P1: 17 (25.0%)
- P2: 25 (36.8%)
- P3: 2 (2.9%)

### Phase
- (none): 13 (19.1%)
- 1: 20 (29.4%)
- 1-late: 15 (22.1%)
- 2: 20 (29.4%)

### Area
- (none): 19 (27.9%)
- artifacts: 12 (17.6%)
- automation: 1 (1.5%)
- batch: 5 (7.4%)
- config: 3 (4.4%)
- docs: 2 (2.9%)
- logging: 3 (4.4%)
- observability: 3 (4.4%)
- plugins: 1 (1.5%)
- runner: 15 (22.1%)
- security: 4 (5.9%)

### Risk
- high: 5 (7.4%)
- low: 1 (1.5%)
- medium: 1 (1.5%)
- none: 61 (89.7%)

## 3. リスク詳細 (High / Medium / etc.)

High Risk Issues:
- 31: 統一ログ設計 (JSON Lines) (area=logging, priority=P0)
- 46: Run/Job タイムアウト & キャンセル (area=runner, priority=P2)
- 49: ユーザースクリプト プラグインアーキテクチャ (area=plugins, priority=P3)
- 54: cdp-use デュアルエンジン抽象レイヤ (area=runner, priority=P1)
- 62: 実行サンドボックス機能制限 (area=security, priority=P0)

## 4. Orphans

Strict Orphans (自動抽出 = 依存なし & 参照されず):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 92: [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync
- 101: chore(test): async ブラウザ起動・event loop 衝突安定化
- 102: chore(flags): FeatureFlags アーティファクト生成とテスト補助ヘルパ
- 104: #91 統一録画パス Rollout (flag default 有効化 & legacy 廃止)
- 106: Phase 2 enforcement: unified recording path flag false warning
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 110: [bug][artifacts] Browser-control モードで録画ファイル未生成 (enable_recording未伝播/開始トリガ未配線)
- 111: [refactor][artifacts] ArtifactManager.resolve_recording_dir を recording_dir_resolver へ統合
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 175: [feat][batch][artifacts] Policy row processing artifact capture (final screenshot + structured extraction)
- 176: [feat][batch] Declarative field extraction spec (YAML) for batch jobs
- 177: [docs][mvp] MVP definition & enterprise readiness matrix
- 178: [ci][workflow] Add dependency-pipeline.yml to align with roadmap Section K

Curated Orphan List (summary.data_quality_checks.orphan_issues_without_dependents_or_depends):
- 55: browser_control pytest パス修正
- 81: Async/Browser テスト安定化計画
- 90: Temp test issue for enrichment
- 92: [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync
- 101: chore(test): async ブラウザ起動・event loop 衝突安定化
- 102: chore(flags): FeatureFlags アーティファクト生成とテスト補助ヘルパ
- 104: #91 統一録画パス Rollout (flag default 有効化 & legacy 廃止)
- 106: Phase 2 enforcement: unified recording path flag false warning
- 107: Cleanup: PytestReturnNotNone warnings across component tests
- 108: Stabilize Edge headless navigation flake (TargetClosedError)
- 109: [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随)
- 110: [bug][artifacts] Browser-control モードで録画ファイル未生成 (enable_recording未伝播/開始トリガ未配線)
- 111: [refactor][artifacts] ArtifactManager.resolve_recording_dir を recording_dir_resolver へ統合
- 113: docs: cleanup archived references to tests/pytest.ini (post PR #112)
- 114: ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112)
- 115: [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成)
- 127: [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善
- 154: pip-audit stabilization in CI with normalizer + targeted suppressions
- 175: [feat][batch][artifacts] Policy row processing artifact capture (final screenshot + structured extraction)
- 176: [feat][batch] Declarative field extraction spec (YAML) for batch jobs
- 177: [docs][mvp] MVP definition & enterprise readiness matrix
- 178: [ci][workflow] Add dependency-pipeline.yml to align with roadmap Section K

Missing Strict Orphans in curated list: (none)
Extra non-strict entries in curated list: (none)

## 5. クリティカルパス推定

Critical Path (自動算出): depends の有向エッジ (B→A) を距離 0 起点から最長距離でトレースしたパス。 実際の期間や見積りを考慮せず、依存段数のみで推定。

Auto Estimated Path (Longest Distance):
32 → 28 → 30 → 37 → 38

Provided Example (existing IDs only):
65 → 64 → 63 → 66 → 67

## 6. Issues Table (sorted)

Sorted By: critical_path_rank

| ID | Title | Pri | Phase | Area | Risk | CP Rank | LongestDist | Depends | Dependents | PrimaryPR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32 | Run/Job ID 基盤 | P0 | 1 | runner |  | 5 | 0 | 0 | 10 | #79 |
| 65 | マルチ環境設定ローダ | P0 | 1 | config |  | 5 | 0 | 0 | 4 |  |
| 28 | 録画ファイル保存パス統一 | P0 | 1 | artifacts |  | 4 | 1 | 1 | 1 | #112 |
| 64 | フィーチャーフラグフレームワーク | P0 | 1 | config |  | 4 | 1 | 1 | 3 |  |
| 25 | git_script が llms.txt で指定したスクリプトを正しく解決するよう修正 | P0 | 1 | runner |  | 3 | 0 | 0 | 4 | #118 |
| 30 | 録画タイプ間不整合是正 | P0 | 1 | artifacts |  | 3 | 2 | 1 | 2 |  |
| 31 | 統一ログ設計 (JSON Lines) | P0 | 1 | logging | high | 3 | 1 | 1 | 1 | #80 |
| 35 | アーティファクト manifest v2 | P0 | 1 | artifacts |  | 3 | 1 | 1 | 3 | #94 |
| 46 | Run/Job タイムアウト & キャンセル | P2 | 2 | runner | high | 3 | 1 | 1 | 1 |  |
| 63 | llms.txt スキーマ & バリデータ | P0 | 1-late | config |  | 3 | 2 | 2 | 1 |  |
| 33 | スクリーンショット取得ユーティリティ | P0 | 1 | artifacts |  | 2 | 1 | 1 | 3 |  |
| 36 | アーティファクト一覧 API | P1 | 1 | artifacts |  | 2 | 2 | 1 | 1 | #95 |
| 37 | 動画アーティファクト保持期間 | P1 | 1 | artifacts |  | 2 | 3 | 1 | 1 | #99 |
| 39 | CSV 駆動バッチエンジンコア | P1 | 2 | batch |  | 2 | 1 | 1 | 3 | #164 |
| 44 | git_script 解決ロジック不具合修正 | P0 | 1 | runner |  | 2 | 1 | 1 | 1 | #120 |
| 47 | 並列実行キュー & 制限 | P2 | 2 | runner |  | 2 | 2 | 1 | 1 |  |
| 53 | cdp-use 追加タイプ調査 | P2 | 2 | runner |  | 2 | 0 | 0 | 1 |  |
| 56 | 統一 JSON Lines ロギング実装 | P0 | 1 | logging |  | 2 | 2 | 2 | 3 | #83 |
| 58 | メトリクス計測基盤 | P1 | 2 | observability |  | 2 | 1 | 1 | 1 | #155 |
| 62 | 実行サンドボックス機能制限 | P0 | 2 | security | high | 2 | 1 | 1 | 1 |  |
| 66 | ドキュメント整備 第1弾 | P2 | 1-late | docs |  | 2 | 3 | 1 | 1 |  |
| 76 | 依存更新自動化パイプライン (PR 起票時の ISSUE_DEPENDENCIES.yml 自動更新) | P1 | 1-late | automation |  | 2 | 2 | 1 | 0 |  |
| 81 | Async/Browser テスト安定化計画 | P1 | 1 | runner |  | 2 | 0 | 0 | 0 |  |
| 154 | pip-audit stabilization in CI with normalizer + targeted suppressions | P1 | 1 | security |  | 1 | 0 | 0 | 0 | #160 |
| 173 | [UI][batch][#40 follow-up] CSV Preview & Command Argument Mapping | P2 | 2 | batch |  | 1 | 4 | 4 | 0 |  |
| 174 | [artifacts][batch] Clarify Artifact Output & Access Flow | P3 | 2 | artifacts | low | 1 | 3 | 5 | 0 |  |
| 34 | 要素値キャプチャ & エクスポート | P1 | 1 | artifacts |  | 1 | 2 | 2 | 0 | #93 |
| 38 | 録画統一後回帰テストスイート | P2 | 1-late | artifacts |  | 1 | 4 | 5 | 0 | #103 |
| 40 | CSV D&D UI 連携 | P2 | 2 | batch |  | 1 | 2 | 1 | 0 | #172 |
| 41 | バッチ進捗・サマリー | P2 | 2 | batch |  | 1 | 3 | 2 | 0 | #162 |
| 42 | バッチ部分リトライ | P2 | 2 | batch |  | 1 | 2 | 1 | 0 | #163 |
| 43 | ENABLE_LLM パリティ | P1 | 1-late | runner |  | 1 | 2 | 2 | 0 |  |
| 45 | git_script 認証 & プロキシ | P1 | 1 | runner |  | 1 | 2 | 2 | 0 | #120 |
| 48 | 環境変数バリデーション & 診断 | P2 | 2 | runner |  | 1 | 1 | 1 | 0 |  |
| 49 | ユーザースクリプト プラグインアーキテクチャ | P3 | 2 | plugins | high | 1 | 2 | 2 | 0 |  |
| 50 | ディレクトリ名変更 & 移行 | P1 | 1 | runner |  | 1 | 1 | 1 | 0 | #120 |
| 51 | Windows プロファイル永続化 | P2 | 2 | runner |  | 1 | 3 | 1 | 0 |  |
| 52 | サンドボックス allow/deny パス | P2 | 2 | runner |  | 1 | 2 | 1 | 0 |  |
| 54 | cdp-use デュアルエンジン抽象レイヤ | P1 | 2 | runner | high | 1 | 1 | 2 | 0 |  |
| 55 | browser_control pytest パス修正 | P0 | 1 | runner |  | 1 | 0 | 0 | 0 |  |
| 57 | ログ保持期間 & ローテーション | P1 | 1-late | logging |  | 1 | 3 | 1 | 0 | #83 |
| 59 | Run メトリクス API | P2 | 2 | observability |  | 1 | 2 | 1 | 0 |  |
| 60 | シークレットマスキング拡張 | P1 | 1-late | security |  | 1 | 3 | 1 | 0 |  |
| 61 | [maint][security] 既存依存セキュリティスキャン基盤の最適化 & 運用強化 | P1 | 2 | security | medium | 1 | 1 | 1 | 0 |  |
| 67 | ドキュメント整備 第2弾 | P2 | 1-late | docs |  | 1 | 4 | 1 | 0 |  |
| 87 | スクリーンショット重複保存フラグ導入 | P1 | 1-late | artifacts |  | 1 | 2 | 2 | 1 | #96 |
| 88 | スクリーンショット例外分類と特定例外キャッチ | P2 | 1-late | artifacts |  | 1 | 2 | 2 | 0 | #97 |
| 89 | Screenshot ログイベント整備 (metrics 連携準備) | P2 | 1-late | observability |  | 1 | 2 | 2 | 0 | #98 |
| 91 | 統一録画パス Rollout (flag default 有効化 & legacy 廃止) | P0 | 1-late | artifacts |  | 1 | 2 | 1 | 0 | #105 |
| 101 | chore(test): async ブラウザ起動・event loop 衝突安定化 | P2 | 1 |  |  |  | 0 | 0 | 0 |  |
| 102 | chore(flags): FeatureFlags アーティファクト生成とテスト補助ヘルパ | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 104 | #91 統一録画パス Rollout (flag default 有効化 & legacy 廃止) | P0 |  |  |  |  | 0 | 0 | 0 |  |
| 106 | Phase 2 enforcement: unified recording path flag false warning | P0 | 1-late |  |  |  | 0 | 0 | 0 |  |
| 107 | Cleanup: PytestReturnNotNone warnings across component tests | P2 | 1-late |  |  |  | 0 | 0 | 0 |  |
| 108 | Stabilize Edge headless navigation flake (TargetClosedError) | P2 | 1-late |  |  |  | 0 | 0 | 0 |  |
| 109 | [quality][coverage] Sonar 新規行カバレッジ向上とQuality Gate再挑戦 (#105 追随) | P2 | 2 |  |  |  | 0 | 0 | 0 |  |
| 110 | [bug][artifacts] Browser-control モードで録画ファイル未生成 (enable_recording未伝播/開始トリガ未配線) |  |  |  |  |  | 0 | 0 | 0 |  |
| 111 | [refactor][artifacts] ArtifactManager.resolve_recording_dir を recording_dir_resolver へ統合 |  |  |  |  |  | 0 | 0 | 0 |  |
| 113 | docs: cleanup archived references to tests/pytest.ini (post PR #112) | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 114 | ci: evaluate relaxing pytest.ini guard scope for docs/archive references (follow-up to PR #112) | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 115 | [A3][regression][hardening] Post-#38 回帰スイート強化 (破損動画 / 強制移行 / retention トグル / パス可搬性 / flags 再生成) |  |  |  |  |  | 0 | 0 | 0 |  |
| 127 | [docs][batch] CSVバッチエンジン統合ドキュメントの包括的改善 | P1 | 2 |  |  |  | 0 | 0 | 0 |  |
| 175 | [feat][batch][artifacts] Policy row processing artifact capture (final screenshot + structured extraction) |  |  |  |  |  | 0 | 0 | 0 |  |
| 176 | [feat][batch] Declarative field extraction spec (YAML) for batch jobs |  |  |  |  |  | 0 | 0 | 0 |  |
| 177 | [docs][mvp] MVP definition & enterprise readiness matrix |  |  |  |  |  | 0 | 0 | 0 |  |
| 178 | [ci][workflow] Add dependency-pipeline.yml to align with roadmap Section K |  |  |  |  |  | 0 | 0 | 0 |  |
| 90 | Temp test issue for enrichment | P2 |  |  |  |  | 0 | 0 | 0 |  |
| 92 | [enhance][roadmap] Enrichment Phase 3: reverse dependents validation & high-risk strict sync | P2 |  |  |  |  | 0 | 0 | 0 |  |

## 7. 依存詳細 (Fan-in / Fan-out)

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
- Dependents (3): 40, 41, 42
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
- Dependents (0): (none)
- Progress: {"state": "done", "primary_pr": 120}

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

### Issue 102: chore(flags): FeatureFlags アーティファクト生成とテスト補助ヘルパ
- Priority: P2, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 104: #91 統一録画パス Rollout (flag default 有効化 & legacy 廃止)
- Priority: P0, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 106: Phase 2 enforcement: unified recording path flag false warning
- Priority: P0, Phase: 1-late, Area: None
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

### Issue 110: [bug][artifacts] Browser-control モードで録画ファイル未生成 (enable_recording未伝播/開始トリガ未配線)
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 111: [refactor][artifacts] ArtifactManager.resolve_recording_dir を recording_dir_resolver へ統合
- Priority: None, Phase: None, Area: None
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

### Issue 175: [feat][batch][artifacts] Policy row processing artifact capture (final screenshot + structured extraction)
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 176: [feat][batch] Declarative field extraction spec (YAML) for batch jobs
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 177: [docs][mvp] MVP definition & enterprise readiness matrix
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 178: [ci][workflow] Add dependency-pipeline.yml to align with roadmap Section K
- Priority: None, Phase: None, Area: None
- Risk: (none)
- CriticalPathRank: None
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 90: Temp test issue for enrichment
- Priority: P2, Phase: None, Area: None
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

