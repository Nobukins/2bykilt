# TASK DASHBOARD

Generated at (UTC): 2025-08-26T15:17:50Z

## 1. メタサマリー

- Total Issues: 40
- High Risk (declared): 5 → 31, 46, 49, 54, 62
- Cycle Detected: false (none)
- Strict Orphans: 2
- Curated Orphan List Count: 14

## 2. 分布 (Distribution)

### Priority
- P0: 14 (35.0%)
- P1: 12 (30.0%)
- P2: 13 (32.5%)
- P3: 1 (2.5%)

### Phase
- 1: 17 (42.5%)
- 1-late: 7 (17.5%)
- 2: 16 (40.0%)

### Area
- artifacts: 8 (20.0%)
- batch: 4 (10.0%)
- config: 3 (7.5%)
- docs: 2 (5.0%)
- logging: 3 (7.5%)
- observability: 2 (5.0%)
- plugins: 1 (2.5%)
- runner: 14 (35.0%)
- security: 3 (7.5%)

### Risk
- high: 5 (12.5%)
- none: 35 (87.5%)

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
- 61: 依存セキュリティスキャン最適化

Curated Orphan List (summary.data_quality_checks.orphan_issues_without_dependents_or_depends):
- 34: 要素値キャプチャ & エクスポート
- 40: CSV D&D UI 連携
- 41: バッチ進捗・サマリー
- 42: バッチ部分リトライ
- 45: git_script 認証 & プロキシ
- 50: ディレクトリ名変更 & 移行
- 51: Windows プロファイル永続化
- 52: サンドボックス allow/deny パス
- 55: browser_control pytest パス修正
- 57: ログ保持期間 & ローテーション
- 59: Run メトリクス API
- 60: シークレットマスキング拡張
- 61: 依存セキュリティスキャン最適化
- 67: ドキュメント整備 第2弾

Missing Strict Orphans in curated list: (none)
Extra non-strict entries in curated list (WARNING only): 34, 40, 41, 42, 45, 50, 51, 52, 57, 59, 60, 67

## 5. クリティカルパス推定

Critical Path (自動算出): depends の有向エッジ (B→A) を距離 0 起点から最長距離でトレースしたパス。 実際の期間や見積りを考慮せず、依存段数のみで推定。

Auto Estimated Path (Longest Distance):
32 → 28 → 30 → 37 → 38

Provided Example (existing IDs only):
31 → 46

## 6. Issues Table (sorted)

Sorted By: critical_path_rank

| ID | Title | Pri | Phase | Area | Risk | CP Rank | LongestDist | Depends | Dependents | PrimaryPR |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 32 | Run/Job ID 基盤 | P0 | 1 | runner |  | 5 | 0 | 0 | 10 |  |
| 65 | マルチ環境設定ローダ | P0 | 1 | config |  | 5 | 0 | 0 | 4 |  |
| 28 | 録画ファイル保存パス統一 | P0 | 1 | artifacts |  | 4 | 1 | 1 | 1 |  |
| 64 | フィーチャーフラグフレームワーク | P0 | 1 | config |  | 4 | 1 | 1 | 3 |  |
| 25 | git_script が llms.txt で指定したスクリプトを正しく解決するよう修正 | P0 | 1 | runner |  | 3 | 0 | 0 | 4 | #27 |
| 30 | 録画タイプ間不整合是正 | P0 | 1 | artifacts |  | 3 | 2 | 1 | 2 |  |
| 31 | 統一ログ設計 (JSON Lines) | P0 | 1 | logging | high | 3 | 1 | 1 | 1 |  |
| 35 | アーティファクト manifest v2 | P0 | 1 | artifacts |  | 3 | 1 | 1 | 3 |  |
| 46 | Run/Job タイムアウト & キャンセル | P2 | 2 | runner | high | 3 | 1 | 1 | 1 |  |
| 63 | llms.txt スキーマ & バリデータ | P0 | 1-late | config |  | 3 | 2 | 2 | 1 |  |
| 33 | スクリーンショット取得ユーティリティ | P0 | 1 | artifacts |  | 2 | 1 | 1 | 2 |  |
| 36 | アーティファクト一覧 API | P1 | 1 | artifacts |  | 2 | 2 | 1 | 1 |  |
| 37 | 動画アーティファクト保持期間 | P1 | 1 | artifacts |  | 2 | 3 | 1 | 1 |  |
| 39 | CSV 駆動バッチエンジンコア | P1 | 2 | batch |  | 2 | 1 | 1 | 3 |  |
| 44 | git_script 解決ロジック不具合修正 | P0 | 1 | runner |  | 2 | 1 | 1 | 1 |  |
| 47 | 並列実行キュー & 制限 | P2 | 2 | runner |  | 2 | 2 | 1 | 1 |  |
| 53 | cdp-use 追加タイプ調査 | P2 | 2 | runner |  | 2 | 0 | 0 | 1 |  |
| 56 | 統一 JSON Lines ロギング実装 | P0 | 1 | logging |  | 2 | 2 | 2 | 3 |  |
| 58 | メトリクス計測基盤 | P1 | 2 | observability |  | 2 | 1 | 1 | 1 |  |
| 62 | 実行サンドボックス機能制限 | P0 | 2 | security | high | 2 | 1 | 1 | 1 |  |
| 66 | ドキュメント整備 第1弾 | P2 | 1-late | docs |  | 2 | 3 | 1 | 1 |  |
| 34 | 要素値キャプチャ & エクスポート | P1 | 1 | artifacts |  | 1 | 2 | 2 | 0 |  |
| 38 | 録画統一後回帰テストスイート | P2 | 1-late | artifacts |  | 1 | 4 | 5 | 0 |  |
| 40 | CSV D&D UI 連携 | P2 | 2 | batch |  | 1 | 2 | 1 | 0 |  |
| 41 | バッチ進捗・サマリー | P2 | 2 | batch |  | 1 | 3 | 2 | 0 |  |
| 42 | バッチ部分リトライ | P2 | 2 | batch |  | 1 | 2 | 1 | 0 |  |
| 43 | ENABLE_LLM パリティ | P1 | 1-late | runner |  | 1 | 2 | 2 | 0 |  |
| 45 | git_script 認証 & プロキシ | P1 | 1 | runner |  | 1 | 2 | 2 | 0 |  |
| 48 | 環境変数バリデーション & 診断 | P2 | 2 | runner |  | 1 | 1 | 1 | 0 |  |
| 49 | ユーザースクリプト プラグインアーキテクチャ | P3 | 2 | plugins | high | 1 | 2 | 2 | 0 |  |
| 50 | ディレクトリ名変更 & 移行 | P1 | 1 | runner |  | 1 | 1 | 1 | 0 |  |
| 51 | Windows プロファイル永続化 | P2 | 2 | runner |  | 1 | 3 | 1 | 0 |  |
| 52 | サンドボックス allow/deny パス | P2 | 2 | runner |  | 1 | 2 | 1 | 0 |  |
| 54 | cdp-use デュアルエンジン抽象レイヤ | P1 | 2 | runner | high | 1 | 1 | 2 | 0 |  |
| 55 | browser_control pytest パス修正 | P0 | 1 | runner |  | 1 | 0 | 0 | 0 |  |
| 57 | ログ保持期間 & ローテーション | P1 | 1-late | logging |  | 1 | 3 | 1 | 0 |  |
| 59 | Run メトリクス API | P2 | 2 | observability |  | 1 | 2 | 1 | 0 |  |
| 60 | シークレットマスキング拡張 | P1 | 1-late | security |  | 1 | 3 | 1 | 0 |  |
| 61 | 依存セキュリティスキャン最適化 | P1 | 2 | security |  | 1 | 0 | 0 | 0 |  |
| 67 | ドキュメント整備 第2弾 | P2 | 1-late | docs |  | 1 | 4 | 1 | 0 |  |

## 7. 依存詳細 (Fan-in / Fan-out)

### Issue 32: Run/Job ID 基盤
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 5
- LongestDistance: 0
- Depends (0): (none)
- Dependents (10): 28, 31, 33, 35, 46, 54, 56, 58, 39, 62

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
- Progress: {"primary_pr": 27, "coverage": "partial"}

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

### Issue 35: アーティファクト manifest v2
- Priority: P0, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 3
- LongestDistance: 1
- Depends (1): 32
- Dependents (3): 34, 36, 38

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
- Dependents (2): 38, 34

### Issue 36: アーティファクト一覧 API
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 2
- Depends (1): 35
- Dependents (1): 38

### Issue 37: 動画アーティファクト保持期間
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 3
- Depends (1): 30
- Dependents (1): 38

### Issue 39: CSV 駆動バッチエンジンコア
- Priority: P1, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (3): 40, 41, 42

### Issue 44: git_script 解決ロジック不具合修正
- Priority: P0, Phase: 1, Area: runner
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 25
- Dependents (1): 45

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

### Issue 58: メトリクス計測基盤
- Priority: P1, Phase: 2, Area: observability
- Risk: (none)
- CriticalPathRank: 2
- LongestDistance: 1
- Depends (1): 32
- Dependents (1): 59

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

### Issue 34: 要素値キャプチャ & エクスポート
- Priority: P1, Phase: 1, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (2): 33, 35
- Dependents (0): (none)

### Issue 38: 録画統一後回帰テストスイート
- Priority: P2, Phase: 1-late, Area: artifacts
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (5): 30, 33, 35, 36, 37
- Dependents (0): (none)

### Issue 40: CSV D&D UI 連携
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)

### Issue 41: バッチ進捗・サマリー
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 3
- Depends (2): 39, 56
- Dependents (0): (none)

### Issue 42: バッチ部分リトライ
- Priority: P2, Phase: 2, Area: batch
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 2
- Depends (1): 39
- Dependents (0): (none)

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

### Issue 61: 依存セキュリティスキャン最適化
- Priority: P1, Phase: 2, Area: security
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 0
- Depends (0): (none)
- Dependents (0): (none)

### Issue 67: ドキュメント整備 第2弾
- Priority: P2, Phase: 1-late, Area: docs
- Risk: (none)
- CriticalPathRank: 1
- LongestDistance: 4
- Depends (1): 66
- Dependents (0): (none)

## 8. INTERNAL (Diagnostics)

Raw Aggregations (JSON-like):
```json
{
  "by_priority": {
    "P0": 14,
    "P1": 12,
    "P2": 13,
    "P3": 1
  },
  "by_phase": {
    "1": 17,
    "1-late": 7,
    "2": 16
  },
  "by_area": {
    "artifacts": 8,
    "batch": 4,
    "config": 3,
    "docs": 2,
    "logging": 3,
    "observability": 2,
    "plugins": 1,
    "runner": 14,
    "security": 3
  },
  "risk_dist": {
    "high": 5,
    "none": 35
  },
  "strict_orphans": [
    "55",
    "61"
  ],
  "curated_orphans": [
    "34",
    "40",
    "41",
    "42",
    "45",
    "50",
    "51",
    "52",
    "55",
    "57",
    "59",
    "60",
    "61",
    "67"
  ],
  "missing_in_curated": [],
  "extra_in_curated": [
    "34",
    "40",
    "41",
    "42",
    "45",
    "50",
    "51",
    "52",
    "57",
    "59",
    "60",
    "67"
  ]
}
```

