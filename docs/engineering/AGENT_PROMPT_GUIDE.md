# Coding Agent Prompt Guide

最終更新: 2026-10-13
対象: 2bykilt で Issue を実装するコーディングエージェント (Copilot Coding Agent など) と、そのプロンプトを書く人

テスト実行・CI 再現の具体ルールは [`.github/copilot-instructions.md`](../../.github/copilot-instructions.md) を参照。

## 基本原則

1. **1 Prompt = 1 Issue**。複数 Issue をまとめない。
2. **依存未解決なら STOP & ASK**。`docs/roadmap/ISSUE_DEPENDENCIES.yml` で依存 Issue が done か確認してから着手する。
3. **最小変更**。既存の動作コードの削除・リファクタリングはしない (必要なら別 Issue)。破壊的変更は明示的に承認を得る。
4. **テストは実装と同時に書く**。リグレッションがないことを確認してから PR を出す。

## プロンプトテンプレート

```markdown
## Issue Context
- Issue Number: #XX
- Priority: P0/P1/P2/P3
- Size: S/M/L
- Dependencies: #YY, #ZZ (must be resolved)

## Current State Analysis
- [ ] 依存 Issue の完了確認
- [ ] 関連ファイル・既存テストの確認
- [ ] 影響範囲の特定

## Implementation Plan
- [ ] Step 1: Specific minimal change
- [ ] Step 2: Next minimal change
- [ ] Step 3: Validation step

## Acceptance Criteria
- [ ] Functional requirement 1
- [ ] No regression in existing tests
- [ ] Documentation updated if needed
```

## 停止時の返答コード

- 依存未解決: `BLOCKED: Issue #XX depends on unresolved #YY`
- 実装範囲超過: `SCOPE_EXCEEDED: Requires splitting into sub-issues`
- テスト失敗: `TEST_FAILURE: Reverting changes, need investigation`

## ISSUE_DEPENDENCIES.yml を編集した場合

`TASK_QUEUE.yml` / `TASK_DASHBOARD.md` / `DEPENDENCY_GRAPH.md` は生成物なので手で編集しない。
ROADMAP.md **Section K** の Pre-PR チェックリストで再生成・検証する。

## Feature Flag を使う変更

新機能は Flag で既存動作と切り替えられるようにする。Flag 定義は `config/feature_flags.yaml`、運用ルールは [`docs/feature_flags/FLAGS.md`](../feature_flags/FLAGS.md)。

```python
from src.config.feature_flags import FeatureFlags

if FeatureFlags.is_enabled("NEW_FEATURE"):
    ...  # 新機能
else:
    ...  # 既存動作
```

## 変更種別ごとの参照先

| 変更内容 | 参照するドキュメント |
|----------|----------------------|
| 設定 / 環境変数 | [`docs/config/CONFIG_SCHEMA.md`](../config/CONFIG_SCHEMA.md) |
| ログ出力 | [`docs/observability/LOGGING_GUIDE.md`](../observability/LOGGING_GUIDE.md) |
| メトリクス | [`docs/observability/METRICS_GUIDE.md`](../observability/METRICS_GUIDE.md) |
| Artifacts / Manifest | [`docs/artifacts/ARTIFACTS_MANIFEST.md`](../artifacts/ARTIFACTS_MANIFEST.md) |
| Secret / サンドボックス実行 | [`docs/security/SECURITY_MODEL.md`](../security/SECURITY_MODEL.md) |

## 改訂履歴

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-08-26 | 初期ドラフト作成 |
| 1.1.0 | 2026-10-13 | 一般論 (PEP 8・KPI 等) と存在しないスクリプト参照を削除、参照先を実パスのリンクに修正 |
