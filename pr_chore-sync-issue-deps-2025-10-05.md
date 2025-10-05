# ISSUE_DEPENDENCIES.yml 同期: 2025-10-05

このPRは、リポジトリ内の機械可読な依存グラフ `docs/roadmap/ISSUE_DEPENDENCIES.yml` を最新の GitHub Issue 状態に合わせて同期するためのものです。

主な変更点:

- `last_synced.utc` を `2025-10-05T12:00:00Z` に更新
- 最近クローズした課題をスナップショットに反映:
  - Issue #101 を CLOSED に更新
  - Issue #263 を CLOSED に追加
- PR #286 により部分的に対応した課題を `progress.state: in-progress` に更新し、短いノートを追加:
  - Issue #81 (Async/Browser テスト安定化計画)
  - Issue #224 (RECORDING_PATH UI と環境変数の競合解消)
  - Issue #231 (テストスイートの改善とカバレッジ向上)
  - Issue #276 (Batch: Recording file copy)

注記:
- 本PRは `docs/roadmap/ISSUE_DEPENDENCIES.yml` のみを変更します。他のファイルは変更していません。
- `progress` フィールドの `note` に PR #286 を参照する文を追加しました。これは状態の説明のための補助情報です。
追加の変更 (このブランチで同時にコミット済み):

- `docs/roadmap/ROADMAP.md` を更新し、Phase2 の表示を `docs/roadmap/ISSUE_DEPENDENCIES.yml` に合わせて同期しました。
  - Phase2 に「全Issueインデックス (ISSUE_DEPENDENCIES.yml と一致)」を追加し、YAML に定義された全 Issue 番号 / タイトル (119 件) を列挙しました。
  - Phase2 表示の絵文字ルールを更新しました: 完了 -> ✅、進行中 -> 🏗️ 。これにより、Roadmap の可視性が改善されます。
  - 上記 ROADMAP の変更は同一ブランチ (`chore/sync-issue-deps-2025-10-05`) にコミット済みです。

お願い:

1. 内容をご確認ください（YAML のみを差分対象とする意図であれば、ROADMAP の変更を別 PR に切り出すこともできます）。
2. 問題なければこの PR をマージしてください。

必要に応じて状態ラベル（例: `partially-done`）を YAML 内に追加することも可能です。