# .github/ Directory Structure

このディレクトリには、GitHub関連のファイルとローカル作業用のドキュメントが含まれています。

## 📁 ディレクトリ構成

### `workflows/` - GitHub Actions（コミット対象）
CIパイプライン、自動テスト、デプロイメントの定義ファイル

### `copilot-instructions.md` - Copilot設定（コミット対象）
GitHub Copilotのプロジェクト固有の指示ファイル

### `pr-*/` - PR関連ドキュメント（ローカルのみ、.gitignore対象）
各PRの作業メモ、コメントドラフト、更新手順などを保存

**例**:
- `.github/pr-335/` - Issue #43 LLM分離対応PR
  - `PR_SUMMARY.md` - PR本文
  - `PR_UPDATE_COMMENT.md` - 更新コメント
  - `UPDATE_PR_335.md` - 更新手順
  - `ISSUE_43_COMPLETION_SUMMARY.md` - 完了サマリー

### `issues/` - Issue関連ドキュメント（ローカルのみ、.gitignore対象）
Issueの実装レポート、作業メモを保存

**例**:
- `.github/issues/IMPLEMENTATION_REPORT_255.md` - Issue #255実装レポート

## 🔒 .gitignore設定

以下のパターンは**Gitで追跡されません**（ローカル作業用のみ）:
```
.github/pr-*/
.github/issues/
```

## 📝 使い方

### PRの作業ドキュメントを作成する場合
```bash
# 新しいPRディレクトリを作成
mkdir .github/pr-XXX

# ドキュメントを作成（自動的にgitignoreされる）
touch .github/pr-XXX/PR_SUMMARY.md
touch .github/pr-XXX/PR_COMMENT.md
```

### Issueの実装レポートを保存する場合
```bash
# ドキュメントを作成（自動的にgitignoreされる）
touch .github/issues/IMPLEMENTATION_REPORT_YYY.md
```

## ✅ メリット

1. **リポジトリのクリーンさ**: ルート直下が散らからない
2. **PRメッセージの再利用**: 過去のPRコメントを参照できる
3. **作業履歴の保存**: ローカルに作業過程が残る
4. **Gitノイズの削減**: PR作業ファイルが履歴を汚さない

## 🗂️ プロジェクトドキュメント vs PR/Issueドキュメント

| カテゴリ | 保存場所 | Git追跡 | 用途 |
|---------|---------|---------|------|
| **プロジェクトドキュメント** | `docs/` | ✅ Yes | 長期的に有用な技術情報 |
| **PR/Issueドキュメント** | `.github/pr-*/, .github/issues/` | ❌ No | GitHub上のコミュニケーション下書き |

**プロジェクトドキュメントの例**:
- `docs/testing/TEST_RESULTS.md` - テスト結果（再現性のある情報）
- `docs/verification/MINIMAL_EDITION_STARTUP_VERIFICATION.md` - 検証手順

**PR/Issueドキュメントの例**:
- `.github/pr-335/PR_SUMMARY.md` - PR #335の本文（GitHub上に既に存在）
- `.github/issues/IMPLEMENTATION_REPORT_255.md` - Issue #255の実装メモ

---

**最終更新**: 2025-10-16
