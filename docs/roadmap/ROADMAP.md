# 2bykilt 開発ロードマップ (Baseline v1)

最終更新: 2025-08-30

対象リポジトリ: https://github.com/Nobukins/2bykilt

本ロードマップは以下を目的とする:

- 基盤 (設定/Flag/ID/Logging/Artifacts/Security/Observability/Docs) を Phase 1 (Group A) で確立
- Phase 2 (Group B) で拡張 (Runner 高度化 / Batch / Plugins / Sandbox 強化 / Hardening)
- 各 Issue は Priority (P0–P3), Size (S/M/L), Dependencies を常に最新化
- Copilot Coding Agent を使った小刻みな自動実装を前提とした「一度に一タスク」運用

> 更新ルール: 各 Issue / PR 完了直後に:
> 1. ISSUE_DEPENDENCIES.yml を更新
> 2. ROADMAP の該当 Wave 進捗率を更新
> 3. 関連ガイド (LOGGING / METRICS / FLAGS / CONFIG_SCHEMA / ARTIFACTS_MANIFEST / SECURITY_MODEL / AGENT_PROMPT_GUIDE) を必要に応じ更新
> 4. PR に「Docs Updated: yes/no(理由)」行を必須記載
> 5. 未反映差分があればラベル `docs/desync` を付与し次の最優先 (P0) タスク化

---

## A. カテゴリ定義 (Domain Buckets)

| Category | Issue Examples (初期) | 概要 |
|----------|-----------------------|------|
| Config | #64, #65, #63 | Feature Flags / Multi-env / Schema Versioning |
| Logging / Observability | #31, #56, #57, #58, #59 | 統一ログ + Metrics Export |
| Artifacts | #28, #30, #33, #34, #35, #36, #37, #38 | 動画・スクショ・要素値・Manifest |
| Runner Core / Reliability | #25, #44, #45, #50, #32 | git_script / Run/Job ID |
| Security (Base) | #60, #61 | Secret Mask / Scan Ops |
| Security (Hardening) | #52, #62 | Sandbox / Path Control |
| Batch Processing | #39, #41, #42, #40 | CSV 駆動実行 |
| Plugins / Extensibility | #49, #53 | User Script Plugin Architecture |
| LLM Control | #43 | Flag による有効/無効 |
| Docs | #66, #67 | 契約 / 最終仕様文書化 |

---

## B. フェーズ (Group A / Group B)

### Group A (Phase 1 – 基盤 & 早期価値)

| Wave | Issues | Status | 備考 |
|------|--------|--------|------|
| A1 | #64 #65 #63 | ✅ Done | Feature Flags / Multi-env Loader / llms.txt Validator 実装完了 (PR #20 由来) |
| A2 | #32 ✅ #31 #56 #57 | 🚧 In Progress | #32 Run/Job ID 完了 (PR #79) → 次: Logging 設計 (#31) / 実装 (#56) / ローテーション (#57) |
| A3 | #28 #30 #33 #35 #36 #34 #37 #38 | Planned | Artifacts 基盤拡張 & 回帰テスト |
| A4 | #25 #44 #45 #50 (#55) | Planned | Runner Reliability / git_script 系統 |
| A5 | #60 #61 | Planned | Security Base (Mask / Scan) |
| A6 | #58 #59 | Planned | Metrics 基盤 & Run API |
| A7 | #43 | Planned | LLM Toggle パリティ |
| Docs | #66 → #67 | In Progress | Doc Sync >90% 維持方針 |

Progress Summary (Phase 1): Wave A1 100% / Wave A2 25% (#32 完了) / 残り Waves queued. Draft/試行 PR は進捗計測に含めず（分析除外方針）。

### Group B (Phase 2 – 拡張 / 高度化)

- Wave B1: #46 → #47 → #48
- Wave B2: #52 → (#62 PoC) → (#62 Enforce) → #54 → #55
- Wave B3: #51
- Wave B4: #39(part1/part2) → #41 → #42 → #40
- Wave B5: #53 → #49(part1/part2)
- Wave B6: Hardening / Cleanup

Gate 条件:

- Group A
  - P0/P1 ≥95%
  - #58 稼働
  - #38 緑
- Docs
  - 同期率>90%

---

## C. 優先度 / サイズ / 基準

- Priority:
  - P0=基盤/重大バグ
  - P1=早期価値
  - P2=重要(後回し可)
  - P3=拡張/実験

- Size:
  - S≤1d
  - M=2-3d
  - L=4-6d(要分割)

---

## D. 依存関係

機械可読: ISSUE_DEPENDENCIES.yml を参照。


Issue 本文に "Depends on: #x, #y" を単一行で明記。

---

## E. シーケンス (Group A)

A1 Config → A2 Logging/ID → A3 Artifacts → A4 Runner Reliability → A5 Security Base → A6 Metrics → A7 LLM Toggle → Docs 並行。

---

## F. Copilot Coding Agent 運用 (要約)

1 Prompt = 1 Issue

依存未解決なら STOP & ASK。

テンプレは AGENT_PROMPT_GUIDE.md。

---


## G. KPI

P0 Burn-down / Wave Completion / Blocked >2d / Cycle Time / Regression Green / Doc Sync Lag / Flag Stale Count

---

## H. ロールバック

Flags / 後方互換 Schema / 追加専用ログ→削除遅延 / Sandbox enforcement 段階化。

---

## I. 次アクション

短期 (A2 進行中):

1. Run/Job ID (#32) 仕様確定 ✅ 済 (PR #79 / ISSUE_DEPENDENCIES.yml 進捗反映済)
2. Logging 設計下書き (#31) 着手中 (フィールド確定 + format 契約 + rotation インタフェース雛形)
3. JSON Lines logger 実装 (#56) 着手ゲート: 設計レビュー完了 / 最低 1 smoke test 方針合意

中期 (A2 実装着手後):

1. JSON Lines ロギング実装 (#56)
2. ローテーション/保持ポリシー (#57) 設計 + flag 化

長期 (先読み):

1. #62 分割検討 (PoC / Enforce) 継続
2. Dashboard 自動化 / Prompt スクリプト化 (#76 と連動した依存更新自動化)

---

## J. 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト | Copilot Agent |
| 1.0.1 | 2025-08-30 | Wave A1 完了反映 / 進捗テーブル追加 / 次アクション更新 | Copilot Agent |
| 1.0.2 | 2025-08-30 | Wave A2 #32 完了反映 / Progress Summary & 次アクション更新 | Copilot Agent |



(EOF)