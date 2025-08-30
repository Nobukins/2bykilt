# Labeling Guidelines

目的:
Issue / PR に付与するラベルの意味と適用ルールを明確化し、優先度・リスク・進行状況の判断と自動化 (Actions/Bot) を一貫させる。

対象読者:
- 外部/内部コントリビューター
- Triage / メンテナ
- ロードマップ作成担当

関連資料:
- 依存グラフ: docs/roadmap/DEPENDENCY_GRAPH.md
- 依存定義 YAML: docs/roadmap/ISSUE_DEPENDENCIES.yml
- CONTRIBUTING.md (初期参加手順)
- (自動検証) scripts/validate_dependencies.py

---

## 1. ラベル分類体系 (Taxonomy)

### Priority
| ラベル | 意味 | 目安対応 SLA / 期待反応 |
|-------|------|-------------------------|
| priority:critical | ブロッカー。開発/運用が停止する | 24h 内アクション |
| priority:high | 重要。直近マイルストン影響 | 2-3d 内トリアージ |
| priority:medium | 通常 | 計画スプリントで検討 |
| priority:low | 後回し可 | バックログ整理時 |

### Size
(1 つのみ付与。推定実装コスト/複雑度指標)
| ラベル | 目安（純実装時間 / LoE） |
|--------|---------------------------|
| size:XS | < 0.5d |
| size:S  | 0.5d - 1d |
| size:M  | 1d - 2d |
| size:L  | 2d - 4d |
| size:XL | > 1 週間 / Epic へ再評価 |

### Phase
| ラベル | 意味 |
|-------|------|
| phase:discovery | 要件探索/PoC |
| phase:design | 設計レビュー段階 |
| phase:implementation | 実装中 |
| phase:stabilization | バグ修正/調整 |
| phase:release | リリース準備/直前タスク |

### Type
| ラベル | 用途 |
|-------|------|
| type:feature | 機能追加 |
| type:enhancement | 既存改善 |
| type:bug | バグ修正 |
| type:chore | 雑多作業 (CI/依存更新) |
| type:refactor | 内部構造整理 |
| type:docs | ドキュメント |
| type:test | テスト関連 |
| type:infra | ビルド/運用・環境 |

### Area (ドメイン/モジュール例)
| ラベル | 範囲例 |
|-------|--------|
| area:api | 公開/内部 API 層 |
| area:cli | CLI ツール |
| area:ui | フロント/UI |
| area:data | データモデル / ストレージ |
| area:metrics | メトリクス/観測関連 |
| area:auth | 認証/認可 |
| area:build | ビルド/パッケージ |
| area:ci | CI / ワークフロー |

### Stability
| ラベル | 意味 |
|-------|------|
| stability:experimental | 試験的 / 非互換変更の可能性 |
| stability:beta | 安定化途中・API 変更あり得る |
| stability:stable | 互換性前提 |
| stability:deprecated | 廃止予定 (後継リンク必須) |

### Risk
(ISSUE_DEPENDENCIES.yml の summary.high_risk と同期)
| ラベル | 意味 | 対応 |
|-------|------|------|
| risk:high | 失敗時影響大 (高額再工数 / クリティカル品質) | 詳細設計レビュー必須 |
| risk:medium | 中程度影響 | 通常レビュー |
| risk:low | 低リスク | 迅速マージ可 |

---

## 2. 適用ルール

- Priority: 必ず 1 つ (未確定の場合は付与保留可)
- Size: 必ず 1 つ (不明なら size:estimation-needed を一時利用可)
- Phase: 0 または 1。進行に伴って更新（履歴は PR / Issue タイムラインで追跡）
- Type: 1 つ推奨（複合なら最も支配的な性質）
- Area: 複数可 (最大 3 推奨)
- Stability: feature 系 Issue/PR のみ該当
- Risk: high を付与する場合は説明欄に「リスク要因 / 緩和策」を最低 1 行書く

補助ラベル (例):
- blocked / needs-info / security-review / design-review
(必要に応じて拡張)

---

## 3. Triage フロー（概要）

1. 新規 Issue 登録時
   - Reporter: Type / Area / (任意) Priority
2. 初回 Triage (24-48h 以内目安)
   - Priority / Size / Phase=discovery or design / Risk 推定
3. 設計合意
   - Phase を design→implementation へ
4. 実装完了 PR マージ前
   - Phase=stabilization へ（バグ修正期間）
5. リリース タグ付け
   - Phase=release → 完了後 Phase ラベル除去 (任意)

---

## 4. Size 見積り指針

| Size | 典型指標 |
|------|----------|
| XS | 単一ファイル / テスト最小 |
| S  | 複数ファイル / 既存テスト拡張 |
| M  | 新規モジュール or インタフェース追加 |
| L  | 複数モジュール横断 / 移行処理 |
| XL | 仕様再設計 / 依存大規模更新 |

再見積り条件:
- 実装途中で 1 ランク以上乖離が判明
- 仕様拡張で要素追加 (コメントで理由明記)

---

## 5. Risk ラベルと依存グラフ

- ISSUE_DEPENDENCIES.yml summary.high_risk に列挙された Issue は risk:high を必ず保持
- high_risk ノードを先行着手することでクリティカルパス遅延を軽減
- 依存グラフ再生成時 (scripts/gen_mermaid.py) に highrisk クラスで視覚化

---

## 6. ラベル追加・変更のガバナンス

手順:
1. 提案: 新規 Issue (Type=chore / label-governance) に動機・用途・衝突懸念を記述
2. レビュー: メンテナ 2 名以上 + 24h 意見募集
3. 承認後:
   - 実際にラベル作成 (UI / API)
   - 本ガイド更新 (カテゴリ / 定義)
   - 関連自動化（Actions/Bot スクリプト）更新
4. Deprecated 運用:
   - deprecated ラベル付与 + ガイド内「Deprecated セクション」追記
   - 新 label への移行方針明記

---

## 7. 典型的な誤用とアンチパターン

| 誤用 | 説明 | 対応 |
|------|------|------|
| Priority と Size を空のままマージ | 計画計測不能 | マージ前に Triage 再要求 |
| Size=XL だが Issue が細分化されていない | 粒度過大 | Epic/分割タスク化 |
| Risk=high だが根拠未記載 | 管理不能 | コメントで根拠追加 or Risk 降格 |
| 同時に複数 Size | 集計困難 | 主 Size 1 つに統一 |

---

## 8. 参考リンク

- GitHub ラベル管理 Docs (公式): https://docs.github.com/
- Mermaid ドキュメント: https://mermaid.js.org/

---

## 9. 変更履歴 (Changelog 抜粋)

| 日付 | 変更 | 担当 |
|------|------|------|
| 2025-08-24 | 初回配置 (ルート labels.md から移行) | (記入) |
| 2025-08-24 | 分類体系再構成 / リスク紐付け明文化 | (記入) |

(以後、更新都度追記)

---
