# PR Title: feat: git-script 許可ドメインの導入 (Issue #255)

## 概要

git-scriptのURL評価を拡張し、環境変数または設定ファイルで許可ドメインを指定できるようにします。これにより GitHub Enterprise / 社内GitLab / その他のホストからのスクリプト実行が可能になります。デフォルトでは引き続き `github.com` のみを許可し、後方互換性を維持します。

## 関連Issue

Closes #255

## 実装内容

### 1. 設定

- **ファイル**: `config/base/core.yaml`
- **内容**: `git_script.allowed_domains` を追加し、デフォルトで `"github.com"` を設定。
- **理由**: デフォルト設定で後方互換性を担保しつつ、運用側で任意のドメインを指定できるようにするため。

### 2. Feature Flag

- **ファイル**: `config/feature_flags.yaml`
- **内容**: `git_script.custom_domains_enabled` フラグを追加（default: true）。
- **理由**: エンタープライズ環境等でUIによる動的変更を無効化するための制御。

### 3. ロジック変更

- **ファイル**: `src/script/git_script_resolver.py`
- **内容**: 以下を実装
  - Lazy-load で設定を取得する `config` property
  - `_get_allowed_domains()` ヘルパー（優先順位: ENV -> config -> default）
  - `_is_safe_git_url()` を HTTPS/SSH 両対応に変更し、許可ドメインで検証
  - `_resolve_from_git()` / `validate_git_script_info()` 内の `github.com` 固定チェックを許可ドメイン検査へ置換
- **理由**: 設定可能なホストをサポートすることでエンタープライズや自ホスト環境での利用が可能になる。

### 4. テスト

- **ファイル**: `tests/test_git_script_resolver.py`
- **テスト数**: 8（新規追加）
- **内容**:
  - デフォルト（github.com）を許可するケース
  - 環境変数でカスタムドメインを追加する（HTTPS/SSH）
  - 許可外ドメインの拒否
  - 危険文字を含むURLの拒否
- **理由**: 安全性を担保しつつ、新機能の振る舞いを保証するため。

### 5. ドキュメント

- **ファイル**: `README.md`
- **内容**: `🔐 Git Script Configuration` セクションを追加（環境変数、例、セキュリティ注意事項）
- **理由**: 運用者が設定方法を素早く理解できるようにするため。

## テスト

### 単体テスト

- **コマンド**:
```bash
pytest tests/test_git_script_resolver.py -v
```

- **結果サマリー**:
```
24 passed
```

- **リグレッション**: なし

### 統合テスト / E2E

- 該当なし（Stage 1: 環境変数/設定ベースの実装）。将来的に E2E を追加予定。

## セキュリティ

- [x] 入力バリデーション（危険文字チェック）を維持
- [x] 許可リスト方式（deny-by-default）を採用
- [x] github.com は常時許可（後方互換）

注意: 設定ミスによる誤った許可を避けるため、READMEにセキュリティ注意を追加しました。プライベートIPブロック等は Stage 2 での検討事項です。

## パフォーマンス

- 設定読み込みは遅延初期化してキャッシュ、ドメインチェックは set lookup なので低コストです。

## 技術的な決定

- Lazy-loading の config adapter を使用して起動時のオーバーヘッドを低減。
- ENV > config > default の優先順位により運用での上書きを容易に。

## 破壊的変更

- [ ] 破壊的変更なし

## ドキュメント

- [x] Docs Updated: `README.md`

### 更新したドキュメント

- `README.md`

## 依存関係

- なし（独立機能）

## マイグレーション手順

- 該当なし

## ロールバック手順

- 該当なし

## チェックリスト

### 実装
- [x] 機能実装完了
- [x] コードレビュー用のコメント追加済み
- [x] 既存コードとの統一性確保
- [x] Feature Flag 対応
- [x] エラーハンドリング実装済み

### テスト
- [x] 単体テスト追加済み
- [ ] 統合/E2Eテスト（予定）
- [x] すべてのテストがパス
- [x] リグレッションなし

### ドキュメント
- [x] コードコメント追加済み
- [x] Docstring 追加済み
- [x] ドキュメント更新済み

### 品質
- [x] Lint エラーなし（ローカルチェック）
- [x] Markdown lint 目視で確認済み

### ROADMAP 同期
- [x] ISSUE_DEPENDENCIES.yml: 影響なし
- [x] 依存関係バリデーション: 実行済み
- [x] 生成物（graph/dashboard/queue）: 実行済み

## レビュー依頼

### 重点的にレビューしてほしいポイント
1. `_get_allowed_domains()` の実装（ENV / config / default の優先順位）
2. `_is_safe_git_url()` における HTTPS / SSH のパースと検証ロジック
3. セキュリティ観点での危険文字チェックと追加の防御（プライベートIPブロックの検討）

### 懸念事項
- UIベースのドメイン編集は未実装（Stage 2）

## 追加情報

- 実装者: GitHub Copilot
- ブランチ: `feature/issue-255-git-script-domain-allowlist`
- コミット: `cbaf093`

---

```
