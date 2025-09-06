# 2bykilt 開発ロードマップ (Baseline v1)

最終更新: 2025-09-07

対象リポジトリ: <https://github.com/Nobukins/2bykilt>

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
| A2 | #32 ✅ #31 ✅ #56 ✅ #57 ✅ | ✅ Done | #56 / #57 実装完了 (PR #83) |
| A3 | #28 ✅ #30 ✅ #33 ✅ #35 ✅ #36 ✅ #34 ✅ #37 ✅ #38 ✅ #87 ✅ #88 ✅ #89 ✅ #91 ✅ | ✅ Done | 全 A3 アーティファクト系 Issue 完了 (#38 PR #103 反映) / Hardening follow-up (非機能) は別 Issue 検討 |
| A4 | #25 #44 #45 #50 (#55) | Planned | Runner Reliability / git_script 系統 |
| A5 | #60 #61 | Planned | Security Base (Mask / Scan) |
| A6 | #58 #59 | Planned | Metrics 基盤 & Run API |
| A7 | #43 | Planned | LLM Toggle パリティ |
| Docs | #66 → #67 | In Progress | Doc Sync >90% 維持方針 |

Progress Summary (Phase 1): Wave A1 100% / Wave A2 100% / Wave A3 100% ( #34 PR #93, #35 PR #94, #36 PR #95, #87 PR #96, #88 PR #97, #89 PR #98, #37 PR #99, #91 PR #105, #28 PR #112, #38 PR #103 ) 残: A4 以降へ移行。Draft/試行 PR は進捗計測に含めず。

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

Wave A3 は rev 1.0.15 で完了。以下は Wave A4 (Runner Reliability) へのトランジション計画と、後続 Metrics (A6) へ向けた先行整備。

### 短期 (Wave A4 Kickoff / 直近 1–2 PR)

1. Runner Reliability Core 着手: #25 再検証 (git_script 解決), 続いて #44 バグ拡張, #45 認証/プロキシ設計スコープ確定, #50 ディレクトリ移行アナウンス草案。
2. 録画パス移行フェーズ 2 警告 (#106): legacy 強制利用時の一度きり警告 (構造化ログ) 実装で drift 防止。
3. Browser-control 録画未生成バグ (#110): enable_recording 伝播 & video オプション設定修正、回帰テスト追加。
4. Resolver 委譲リファクタ (#111): ArtifactManager.resolve_recording_dir → 統一 resolver 呼び出しへ移行し重複除去。
5. 回帰ハードニング (#115): 破損動画 / 強制移行 / portability / flags 再生成 テストのうち ci_safe 適用可能 subset を統合。
6. Docs / Guard 整理 (#113, #114): tests/pytest.ini 旧参照除去 & guard スコープ方針決定 (スクリプト化是非)。

### 中期 (A4 中盤 / Metrics 先行準備)

1. Metrics 基盤 事前作業 (#58): イベントタクソノミ (flag.resolve, artifact.video.register, screenshot.capture) 草案 + コード内 TODO 埋め込み (実装は A6 本番)。
2. カバレッジ改善 (#109): 新規行 >80% 目標で Quality Gate PASS 再挑戦 (信頼性改修前にベースライン安定)。
3. FeatureFlags アーティファクト補助 (#102): eager 生成 API / テストヘルパ設計確定 (実装は信頼性改修に影響しない範囲)。

### 長期 / バックログ (A4 後半～)

1. Async / Browser 安定化 (#81, #101, #108): Edge flake (#108) 50-run 安定後 xfail 除去、統一 TEST_STRATEGY.md 完了。
2. Guard スクリプト化・差分限定走査 (#114) 実装 (方針が "実装する" になった場合)。
3. Sandbox / Security 強化 (#62 事前検討) は Runner 基盤の安定後に着手。

### メモ / ポリシー

- A4 期間中に Metrics (#58) の instrumentation コードは "NO-OP + TODO" コメントに留め、本番エクスポータ / API (#59) は A6 で実装。
- ハードニング (#115) のうち高負荷/非 determinism リスクのあるシナリオは nightly へ分離する方針を検討。
- 依存自動更新 (#76) は A4 初期の負荷を鑑み後半再評価。

---

## J. 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-08-26 | 初期ドラフト | Copilot Agent |
| 1.0.1 | 2025-08-30 | Wave A1 完了反映 / 進捗テーブル追加 / 次アクション更新 | Copilot Agent |
| 1.0.2 | 2025-08-30 | Wave A2 #32 完了反映 / Progress Summary & 次アクション更新 | Copilot Agent |
| 1.0.3 | 2025-08-31 | Wave A2 #31 完了反映 (#31 done / PR #80) / 進捗率更新 / 次アクション再構成 | Copilot Agent |
| 1.0.4 | 2025-08-31 | Wave A2 #56/#57 完了反映 (PR #83) / Progress 更新 / 次アクション整理 | Copilot Agent |
| 1.0.5 | 2025-09-01 | A3 In Progress (#87 #88 #89 追加) / 短期アクション更新 / Flag 追加反映 | Copilot Agent |
| 1.0.6 | 2025-09-01 | #76 を A3 にスケジュール、短期 Next Actions に追加 | Copilot Agent |
| 1.0.7 | 2025-09-03 | #34 完了 (PR #93) / Wave A3 テーブル反映 / Progress Summary 更新 | Copilot Agent |
| 1.0.8 | 2025-09-03 | #35 最小 manifest v2 スキーマ + flag gating + tests 追加 | Copilot Agent |
| 1.0.9 | 2025-09-03 | #87 duplicate screenshot copy flag 完了 (PR #96) / A3 進捗更新 | Copilot Agent |
| 1.0.10 | 2025-09-03 | #88 screenshot exception classification 完了 (PR #97) / #89 着手反映 | Copilot Agent |
| 1.0.11 | 2025-09-03 | #89 screenshot logging events 完了 (PR #98) / #37 着手 | Copilot Agent |
| 1.0.12 | 2025-09-04 | #37 完了 (PR #99) / #38 regression suite 着手 | Copilot Agent |
| 1.0.13 | 2025-09-04 | #91 統一録画パス rollout 完了 (flag default 有効化, legacy path warn, async loop 安定化, flaky tests 正常化) | Copilot Agent |
| 1.0.14 | 2025-09-06 | #28 録画ファイル保存パス統一 完了 (PR #112) / ISSUE_DEPENDENCIES 進捗同期 / Progress Summary 更新 | Copilot Agent |
| 1.0.15 | 2025-09-07 | #38 回帰スイート完了 (PR #103) / A3 Wave 全完了反映 / 次アクション A4 移行準備 | Copilot Agent |

---

## K. 依存グラフ更新 / Pre-PR ローカル検証 & CI 方針

本セクションは `ISSUE_DEPENDENCIES.yml` を触る (Issue 状態変更 / 追加 / 進捗付与 / risk 変更 など) すべての PR に適用する統一プロセス。

### 1. 更新原則

- 単一ソース: 依存/メタ情報の唯一の編集対象は `docs/roadmap/ISSUE_DEPENDENCIES.yml`。
- 派生物 (`DEPENDENCY_GRAPH.md`, `TASK_DASHBOARD.md`, `TASK_QUEUE.yml`) は常に再生成し差分をコミット。
- 生成物は「再生成直後に再度生成しても差分 0 (idempotent)」でなければならない。
- Issue 完了時: `progress.state: done` & `progress.primary_pr: <PR番号>` を必須。`risk` 変更や `high_risk` 追加があれば `summary.high_risk` を同期。
- 新規 root issue 追加時: strict orphan に該当する場合 curated orphan リストへ追加 (superset 運用)。

### 2. ローカル Pre-PR チェックリスト

| Step | 必須 | コマンド / 内容 | 成功条件 |
|------|------|----------------|----------|
| 1 | ✅ | Edit `ISSUE_DEPENDENCIES.yml` | YAML パース成功 (エディタ/validator) |
| 2 | ✅ | `python scripts/validate_dependencies.py docs/roadmap/ISSUE_DEPENDENCIES.yml` | ERROR 0 / WARN 期待内 (curated orphan 追加のみ) |
| 3 | ✅ | `python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.md` | ファイル更新 / グラフ生成成功 |
| 4 | ✅ | `python scripts/generate_task_dashboard.py` | `[OK] Generated` 表示 |
| 5 | ✅ | `python scripts/generate_task_queue.py --repo <owner/repo> --input docs/roadmap/ISSUE_DEPENDENCIES.yml --output docs/roadmap/TASK_QUEUE.yml --no-api` | 成功ログ / ステータス分類表示 |
| 6 | ✅ | `python scripts/validate_task_queue.py --queue docs/roadmap/TASK_QUEUE.yml --dependencies docs/roadmap/ISSUE_DEPENDENCIES.yml` | PASSED 表示 |
| 7 | ✅ | `git add . && git diff --cached` (or 再生成後 `git diff`) | 生成コマンドを再実行して差分 0 (idempotent) |
| 8 | ✅ | ROADMAP Wave 進捗調整 | 完了 Issue の ✅ 反映 / Progress Summary 更新 |
| 9 | ⭕ | (任意) 厳格孤立検査: `python scripts/validate_dependencies.py --orphan-mode exact docs/roadmap/ISSUE_DEPENDENCIES.yml` | (開発者が curated 上書き影響を精査) |
| 10 | ✅ | PR Description 更新 | 下記テンプレ項目を含む |

PR Description 追記テンプレ:

```text
Docs Updated: yes/no(<理由>)
Dependency Graph: regenerated
Validation: dependencies=pass, queue=pass (warnings=<数>)
Orphan List: updated|unchanged (strict_missing=0)
Idempotent Check: pass
```

### 3. CI 推奨ジョブ (GitHub Actions 例)

`/.github/workflows/dependency-pipeline.yml`

```yaml
name: dependency-pipeline
on:
  pull_request:
    paths:
      - 'docs/roadmap/ISSUE_DEPENDENCIES.yml'
      - 'scripts/**.py'
jobs:
  validate-deps:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install pyyaml
      - name: Dependency Validation
        run: python scripts/validate_dependencies.py docs/roadmap/ISSUE_DEPENDENCIES.yml
  regenerate-and-check:
    needs: validate-deps
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.12'}
      - run: pip install pyyaml requests
      - name: Regenerate
        run: |
          python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.md
          python scripts/generate_task_dashboard.py
          python scripts/generate_task_queue.py --repo ${{ github.repository }} --input docs/roadmap/ISSUE_DEPENDENCIES.yml --output docs/roadmap/TASK_QUEUE.yml --no-api
      - name: Queue Validate
        run: python scripts/validate_task_queue.py --queue docs/roadmap/TASK_QUEUE.yml --dependencies docs/roadmap/ISSUE_DEPENDENCIES.yml
      - name: Idempotency Check
        run: |
          cp docs/roadmap/TASK_QUEUE.yml /tmp/TASK_QUEUE.yml.bak
          python scripts/generate_task_queue.py --repo ${{ github.repository }} --input docs/roadmap/ISSUE_DEPENDENCIES.yml --output docs/roadmap/TASK_QUEUE.yml --no-api
          diff -u /tmp/TASK_QUEUE.yml.bak docs/roadmap/TASK_QUEUE.yml
  diff-guard:
    needs: regenerate-and-check
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Ensure committed artifacts up to date
        run: |
          python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > /tmp/graph.md
          diff -q /tmp/graph.md docs/roadmap/DEPENDENCY_GRAPH.md || (echo 'Graph out-of-sync' && exit 1)
```

### 4. 失敗時の対応基準

- Validation ERROR: 即修正 (進捗・risk・依存齟齬)。
- Orphan strict missing: curated リスト更新 or 孤立要件再確認。
- Idempotent 差分: 生成スクリプトの非決定要素 (timestamp 等) を抑止 / オプション化。
- Queue Validate 失敗: `status` 判定ルール (done / blocked) のロジック再確認。

### 5. 改善予定 (追跡用)

1. done 判定に GitHub API 無効時 `progress.state` fallback 追加 (#TBD)
2. Mermaid 生成時刻抑制フラグ (`--stable`) 追加 (#TBD)
3. curated orphan を strict / extra 二段表示 (#TBD)

---



(EOF)
