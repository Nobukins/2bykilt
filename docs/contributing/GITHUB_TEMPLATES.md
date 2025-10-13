# GitHub Templates Documentation

最終更新: 2025-10-13

## 概要

2bykiltプロジェクトのIssueとPRテンプレートのドキュメントです。これらのテンプレートは、Issue #287の一環として作成されました。

## 目的

- **一貫性**: すべてのIssueとPRが同じ構造を持つ
- **完全性**: 必要な情報が漏れなく記載される
- **効率性**: AgentとHumanの両方が効率的に作業できる
- **追跡可能性**: 依存関係とROADMAP同期が明確

## Issue Templates

### 1. Feature Request / 機能リクエスト

**ファイル**: `.github/ISSUE_TEMPLATE/feature_request.md`

**用途**:
- 新機能の提案
- 既存機能の改善
- 技術的な拡張

**主要セクション**:
- **概要**: 機能の簡潔な説明
- **目的**: なぜこの機能が必要か
- **背景 / 現状の課題**: 解決したい問題
- **提案内容（機能仕様）**: 詳細な実装提案
- **Acceptance Criteria**: 受け入れ基準
- **参照**: 関連ガイドライン
- **依存関係**: 前提条件と後続タスク
- **実装上の注意点 / リスク**: セキュリティ、パフォーマンス、互換性
- **ラベリング**: 推奨ラベル

**例**:
- Issue #265: 複数フォルダ配下の録画ファイルを再帰的に発見
- Issue #277: Artifacts UI の実装

### 2. Bug Report / バグ報告

**ファイル**: `.github/ISSUE_TEMPLATE/bug_report.md`

**用途**:
- バグの報告
- 予期しない動作の報告
- エラーの報告

**主要セクション**:
- **概要**: バグの簡潔な説明
- **環境情報**: OS、Python、ブラウザなど
- **再現手順**: 詳細な再現方法
- **期待される動作**: 本来の動作
- **実際の動作**: 現在の動作
- **エラーメッセージ / ログ**: スタックトレースなど
- **影響範囲**: 頻度、重大度、影響
- **調査結果**: 既に分かっていること（オプション）
- **提案される修正方法**: 修正案（オプション）
- **Acceptance Criteria**: 受け入れ基準

**例**:
- Issue #237: Recording file generation not working
- Issue #223: LOG_LEVEL 環境変数が反映されない

### 3. Documentation Update / ドキュメント更新

**ファイル**: `.github/ISSUE_TEMPLATE/documentation.md`

**用途**:
- ドキュメントの追加
- ドキュメントの修正
- ドキュメントの削除

**主要セクション**:
- **概要**: 更新の目的
- **現状の問題**: 何が問題か
- **提案される更新内容**: 追加、修正、削除
- **対象ドキュメント**: 更新対象ファイル
- **Acceptance Criteria**: 受け入れ基準

**例**:
- Issue #230: ドキュメントの改善とユーザガイドの充実
- Issue #244: action_runner_template 利用方法ドキュメント整備

### 4. Config (config.yml)

**ファイル**: `.github/ISSUE_TEMPLATE/config.yml`

**設定内容**:
- `blank_issues_enabled: false`: テンプレートなしのIssue作成を無効化
- **Contact Links**:
  - Discussion: 質問や議論
  - Documentation: ドキュメントへのリンク
  - Roadmap: ロードマップへのリンク

## Pull Request Template

**ファイル**: `.github/PULL_REQUEST_TEMPLATE.md`

**用途**:
- すべてのPRで使用される統一テンプレート
- コードレビューの効率化
- 品質基準の徹底

**主要セクション**:

### 1. 基本情報
- **PR Title**: `[type]: [説明] (Issue #XXX)`
- **概要**: PRの目的と実装内容
- **関連Issue**: Closes/Related to

### 2. 実装内容
- カテゴリごとの変更説明
- ファイルパスと変更理由

### 3. テスト
- **単体テスト**: テストファイル、カバレッジ
- **統合テスト**: 統合テストの説明
- **全体テスト結果**: リグレッションチェック

### 4. セキュリティ
- 入力バリデーション
- シークレット管理
- パストラバーサル対策

### 5. パフォーマンス
- パフォーマンス影響測定
- メモリ使用量確認

### 6. 技術的な決定
- アーキテクチャ
- 代替案との比較

### 7. 破壊的変更
- 破壊的変更の有無
- 移行方法
- 影響範囲

### 8. ドキュメント
- **Docs Updated**: yes/no
- 更新したドキュメント一覧

### 9. 依存関係
- 依存するPR/Issue
- このPRに依存するPR/Issue

### 10. マイグレーション・ロールバック
- マイグレーション手順
- ロールバック手順

### 11. チェックリスト
- **実装**: 機能実装、コードレビュー用コメント
- **テスト**: 単体/統合/E2E、カバレッジ
- **ドキュメント**: コメント、Docstring、ドキュメント更新
- **品質**: Lint、Type hints、規約準拠
- **ROADMAP 同期**: ISSUE_DEPENDENCIES.yml更新、バリデーション、生成物再生成
- **CI/CD**: パイプラインパス、ビルド成功

### 12. スクリーンショット / デモ
- Before/After（UI変更の場合）

### 13. レビュー依頼
- 重点的にレビューしてほしいポイント
- 懸念事項

**例**:
- PR #317: Artifacts UI implementation

## 使用方法

### Issue作成時

1. GitHubでNew Issueをクリック
2. 適切なテンプレートを選択:
   - Feature Request: 新機能や改善提案
   - Bug Report: バグ報告
   - Documentation: ドキュメント更新
3. テンプレートの各セクションを埋める
4. 適切なラベルを付与（labeling-guidelines.md参照）
5. Issue作成

### PR作成時

1. ブランチ作成
   ```bash
   git checkout -b feature/issue-XXX-brief-description
   ```

2. 実装とコミット
   ```bash
   git add .
   git commit -m "feat(area): description"
   ```

3. PR作成
   ```bash
   gh pr create --fill
   # または
   git push origin feature/issue-XXX-brief-description
   # GitHubでPR作成
   ```

4. PRテンプレートの各セクションを埋める
5. チェックリストを確認
6. PR作成

## ベストプラクティス

### Issue作成

1. **明確なタイトル**: Issue番号とキーワードを含める
2. **完全な情報**: すべてのセクションを埋める
3. **依存関係の明記**: ISSUE_DEPENDENCIES.ymlと整合性を保つ
4. **適切なラベリング**: labeling-guidelines.mdに従う
5. **Acceptance Criteriaの明確化**: 完了条件を具体的に

### PR作成

1. **1 Issue = 1 PR**: 単一責任の原則
2. **詳細な説明**: 実装理由と技術的決定を記載
3. **完全なテスト**: カバレッジ >=80%
4. **ドキュメント更新**: 必ず更新状況を記載
5. **ROADMAP同期**: Section K チェックリスト完了
6. **レビュアーへの配慮**: レビューポイントを明記

## 自動化

### GitHub Actions連携

将来的に以下の自動化を検討:

1. **Issue作成時**:
   - ラベル自動付与（タイトルから判定）
   - ISSUE_DEPENDENCIES.yml自動更新チェック
   - 依存関係バリデーション

2. **PR作成時**:
   - チェックリスト完了度チェック
   - テストカバレッジチェック
   - ドキュメント更新チェック
   - Lint/Format自動実行

3. **PR マージ時**:
   - ISSUE_DEPENDENCIES.yml自動更新
   - ROADMAP進捗率更新
   - 生成物再生成

## トラブルシューティング

### テンプレートが表示されない

- `.github/ISSUE_TEMPLATE/`ディレクトリが正しい位置にあるか確認
- ファイル名が正しいか確認（拡張子`.md`）
- YAMLフロントマターが正しいか確認

### PRテンプレートが適用されない

- `.github/PULL_REQUEST_TEMPLATE.md`が正しい位置にあるか確認
- ファイル名が完全に一致しているか確認
- ブラウザキャッシュをクリア

### チェックリストが動作しない

- Markdownの構文が正しいか確認: `- [ ]`
- 空白の位置が正しいか確認

## 関連ドキュメント

- [CONTRIBUTING.md](../engineering/CONTRIBUTING.md): コントリビューションガイド
- [AGENT_PROMPT_GUIDE.md](../engineering/AGENT_PROMPT_GUIDE.md): Agentプロンプトガイド
- [HOW_TO_PROMPT_TO_AGENT.md](../roadmap/HOW_TO_PROMPT_TO_AGENT.md): Agent指示方法
- [ROADMAP.md](../roadmap/ROADMAP.md): プロジェクトロードマップ
- [ISSUE_DEPENDENCIES.yml](../roadmap/ISSUE_DEPENDENCIES.yml): Issue依存関係
- [labeling-guidelines.md](labeling-guidelines.md): ラベリングガイドライン

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-10-13 | 初期作成（Issue #287） | Copilot Agent |

---

このテンプレートシステムは、効率的で高品質な開発プロセスをサポートするために継続的に改善されます。
