# Copilot Coding Agent Prompt Guide

最終更新: 2025-08-26
対象: GitHub Copilot Coding Agent による自動実装

## 概要

このガイドは、2bykilt プロジェクトにおける Copilot Coding Agent を使用した効率的な Issue 実装のためのプロンプト構造と標準を定義します。

## 基本原則

### 1. 単一責任原則
- 1 Prompt = 1 Issue
- 複数の Issue を一度に扱わない
- 依存関係が未解決の場合は STOP & ASK

### 2. 最小変更原則
- 既存の動作コードを削除・変更しない
- 追加のみで機能を実装
- 破壊的変更は明示的に承認を得る

### 3. 段階的実装
- 小さな機能単位で実装
- 各段階で動作確認
- リグレッションテストを実行

## プロンプト構造テンプレート

```markdown
## Issue Context
- Issue Number: #XX
- Priority: P0/P1/P2/P3
- Size: S/M/L
- Dependencies: #YY, #ZZ (must be resolved)

## Current State Analysis
- [ ] 依存 Issue の完了確認
- [ ] 関連ファイルの調査
- [ ] 既存テストの確認
- [ ] 影響範囲の特定

## Implementation Plan
- [ ] Step 1: Specific minimal change
- [ ] Step 2: Next minimal change
- [ ] Step 3: Validation step

## Acceptance Criteria
- [ ] Functional requirement 1
- [ ] Functional requirement 2
- [ ] No regression in existing tests
- [ ] Documentation updated if needed

## Validation Steps
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual verification completed
- [ ] Performance impact assessed
```

## 実装ガイドライン

### 1. 依存関係チェック
```bash
# 依存関係確認スクリプト例
python scripts/validate_dependencies.py docs/roadmap/DEPENDENCIES.yml
```

### 2. 基本的な変更フロー
1. Issue 本文の依存関係確認
2. DEPENDENCIES.yml の更新
3. 実装の最小単位での実行
4. テスト実行とバリデーション
5. ドキュメント更新（必要に応じて）

### 3. エラーハンドリング
- 依存未解決: "BLOCKED: Issue #XX depends on unresolved #YY"
- 実装範囲超過: "SCOPE_EXCEEDED: Requires splitting into sub-issues"
- テスト失敗: "TEST_FAILURE: Reverting changes, need investigation"

## コード品質基準

### 1. Python コード
- PEP 8 準拠
- Type hints 使用
- Docstring 記載
- Error handling 実装

### 2. テストコード
- 既存テスト構造に従う
- Edge case を考慮
- Mock を適切に使用
- Coverage 維持

### 3. ドキュメント
- Markdown lint 準拠
- 日本語/英語混在OK
- リンク切れチェック
- バージョン情報更新

## Flag & Config 連携

### 1. Feature Flag 使用
```python
from src.config.feature_flags import FeatureFlags

if FeatureFlags.is_enabled("NEW_FEATURE"):
    # 新機能実装
    pass
else:
    # 既存動作維持
    pass
```

### 2. Configuration Schema
- CONFIG_SCHEMA.md に準拠
- 環境変数の適切な使用
- デフォルト値の設定

## Logging & Observability

### 1. ログ出力
```python
import logging
logger = logging.getLogger(__name__)

logger.info("Feature implementation started", extra={
    "issue": "#XX",
    "component": "module_name",
    "action": "feature_start"
})
```

### 2. メトリクス
- METRICS_GUIDE.md に従う
- パフォーマンス影響を測定
- エラー率を監視

## セキュリティ考慮事項

### 1. Secret 管理
- 環境変数使用
- Hardcode 禁止
- Secret scanning 対応

### 2. Sandbox 実行
- SECURITY_MODEL.md に準拠
- 権限最小化
- Path traversal 防止

## 成功パターン集

### 1. 設定系 Issue
```markdown
1. feature_flags/FLAGS.md の Flag 追加
2. Config schema 更新
3. 実装での Flag チェック追加
4. テストケース追加
5. ドキュメント更新
```

### 2. Logging 系 Issue
```markdown
1. ログフォーマット定義
2. Logger 設定追加
3. 該当箇所でのログ出力実装
4. ログレベル調整
5. 運用ガイド更新
```

### 3. Artifacts 系 Issue
```markdown
1. Manifest スキーマ更新
2. 収集処理実装
3. Export 機能追加
4. テストデータ作成
5. 統合テスト実行
```

## 失敗パターンと対策

### 1. 依存関係無視
❌ 問題: 依存 Issue 未確認で実装開始
✅ 対策: Issue 開始前に DEPENDENCIES.yml 必須確認

### 2. 過度な変更
❌ 問題: 既存コードの大幅リファクタリング
✅ 対策: 追加実装に限定、リファクタリングは別 Issue

### 3. テスト不備
❌ 問題: 新機能のテストなし
✅ 対策: 実装と同時にテストケース作成

## 自動化対応

### 1. Prompt スクリプト化
```bash
# 将来的な自動化例
./scripts/generate_prompt.py --issue 64 --template engineering
```

### 2. Dashboard 連携
- TASK_QUEUE.yml 自動更新
- Progress tracking
- Blocking 状況の可視化

## KPI & 品質指標

### 1. 実装効率
- Issue 完了時間
- リワーク率
- テスト成功率

### 2. 品質指標
- リグレッション発生率
- Code coverage 維持率
- ドキュメント同期率

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-27 | 初期ドラフト作成 | Copilot Agent |

---

**注意**: このガイドは進化するドキュメントです。実装経験に基づいて継続的に更新してください。