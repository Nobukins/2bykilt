# 効率的なAgent指示出し方法

最も効率的に Agent（Copilot Coding Agent）へ順次タスク指示を出し、ロードマップと同期しつつ迷いなく開発を進める」ための推奨運用設計をまとめます。  

ポイントは 

- (1) 情報の一次ソースを一か所に固定 (単一真実源 / SSOT)
- (2) Agent へのプロンプト最小化 & 再現性確保、
- (3) 「READY キュー」を自動抽出し To-Do ダッシュボード化、
- (4) 1 イテレーション＝1 Issue (or サブ Issue) 

の原則徹底 です。

----

## 1. 推奨全体像（情報レイヤ構造）

Source of Truth 層:

- ROADMAP.md（戦略 / WAVE / KPI）
- ISSUE_DEPENDENCIES.yml（機械可読依存）
- FLAGS.md / CONFIG_SCHEMA.md / LOGGING_GUIDE.md / METRICS_GUIDE.md / ARTIFACTS_MANIFEST.md / SECURITY_MODEL.md

実行オーケストレーション層（新規追加提案）:
- TASK_QUEUE.yml （現在の READY / NEXT / BLOCKED 分類）
- TASK_DASHBOARD.md（人間視認用ダッシュボード：優先度×フェーズ×進行）
- (将来) GitHub Project View（自動フィルタ） or GitHub Actions で再生成

指示テンプレ層:
- AGENT_PROMPT_GUIDE.md（形式契約）
- （オプション）AGENT_CONTEXT_CHECKLIST.md（プロンプト生成チェックリストのみ抜粋軽量版）

運用自動化層（未実装）:
- scripts/generate_task_dashboard.py（ISSUE_DEPENDENCIES.yml + GitHub API → TASK_QUEUE.yml / TASK_DASHBOARD.md 再生成）
- PR テンプレチェック（Docs 反映済みか）

----

## 2. ダッシュボード & キューの役割分担

- TASK_QUEUE.yml: 機械処理 / スクリプト対象（RAG 風に Agent 用 context を抽出しやすい）
- TASK_DASHBOARD.md: 人間用ハイレベル表示（優先度と波状進行の可視化）
- 生成ロジック: 
  1) 依存が全て Done → READY  
  2) 未完依存あり → BLOCKED  
  3) 進行中 (アサイン or Draft PR) → IN_PROGRESS  
  4) 優先順位ソート: P0→P1→P2→P3, 同順位なら Wave 順 / size(S→M→L) / 作成日

----

## 3. 最小ステップ運用フロー（1タスクのライフサイクル）

1. 朝/新イテレーション: generate_task_dashboard.py 実行（未実装） → 最新 TASK_QUEUE.yml/TASK_DASHBOARD.md 更新  
2. 次に着手する READY の最上位を選択（P0 最優先 / 依存清算 / size=S 候補でウォームアップ）  
3. AGENT プロンプト作成（テンプレ準拠・ROADMAP 最新 commit hash を context 固定）  
4. Agent から PR 生成 → レビュー → (マージ時) Docs & DEPENDENCIES.yml & FLAGS 等更新  
5. スクリプト再実行 → 次タスクへ

（重要）commit hash をプロンプトに入れることで「どのバージョンの ROADMAP を参照しているか」再現性を保証。差分があれば「ROADMAP changed since <hash>; please re-sync」ガード。

----
## 4. Agent への具体プロンプトテンプレ（最適化版）

目的：トークンを無駄にせず、必要な確定情報のみをコンパクトに渡す。Issue 本文長い場合は Acceptance Criteria 抜粋＋依存確認＋変更範囲のみ。

Prompt Skeleton（実際に送るテキスト例）:

```prompt
Action: Implement
Issue: #64 フィーチャーフラグ フレームワーク
RoadmapVersion: <ROADMAP.md の最新 commit hash>
TaskQueueVersion: <TASK_QUEUE.yml の最新 commit hash>
Context:
- Goal: Provide unified feature flag resolution (override > env > file) to enable progressive rollout & rollback.
Acceptance Criteria (mirrored):
- Resolution order: runtime override > env > config file
- Support bool & string
- API: is_enabled(name, context=None)
- 100% tests for resolution paths
Dependencies (must be DONE): #65 (config loader base), #32 (Run/Job ID not required)  
If any dependency not merged → STOP & ASK.

Scope:
- Create: bykilt/config/flags.py
- Modify: bykilt/config/loader.py
- Tests: tests/config/test_flags.py

Non-Scope:
- Admin UI
- Flag deletion lifecycle

Tests:
- test_resolution_order
- test_bool_and_string
- test_missing_flag_default_false
- test_env_override

Constraints:
- No public API break in loader
- No network I/O
- Keep performance: init <50ms

Rollback:
- Single module revert; default path returns False

Questions:
- Return False vs raise KeyError for unknown flags? (Assume False if not clarified)

On ambiguity or unmet dependency: Reply ONLY with questions; do not implement.
```

差分だけ入れたい場合は Acceptance Criteria を Issue 正文からコピー＆最小化。  
各プロンプト最初に RoadmapVersion/TaskQueueVersion を付けるだけで、Agent が古い文書を参照しているか検知しやすい。

----

## 5. “Dashboard / To-Do リスト” 提案ファイル（ドラフト例）

```markdown name=docs/roadmap/TASK_DASHBOARD.md
# Task Dashboard (Auto-Generated Draft)

最終更新: (生成日時挿入)
Roadmap Commit: <hash>
Dependencies Commit: <hash>

## 1. READY QUEUE (順序: Priority → Wave → Size)
| Rank | Issue | Priority | Size | Wave/Phase | Short Title | Notes |
|------|-------|----------|------|-----------|-------------|-------|
| 1 | #64 | P0 | M | A1 | Feature Flag Framework | dependencies satisfied |
| 2 | #65 | P0 | M | A1 | Multi-env Loader | waits #64 merge (if already merged, move to READY) |
| 3 | #63 | P0 | S | A1 | llms.txt Schema Validator | after #64,#65 |
| 4 | #32 | P0 | S | A2 | Run/Job ID | no deps |
| 5 | #31(part1) | P0 | (M) | A2 | Logging Design (config) | split from L |
| 6 | #56 | P0 | M | A2 | JSON Lines Logging | needs #31(part1), #32 |
| 7 | #28 | P0 | S | A3 | Recording Path Unify | needs #32 |
| ... | ... | ... | ... | ... | ... | ...

(READY は “全依存 Done” のみ)

## 2. IN PROGRESS
| Issue | Assignee | Started | ETA | Blockers |
|-------|----------|--------|-----|----------|
| (例) #64 | userX | 2025-08-25 | 2025-08-26 | none |

## 3. BLOCKED
| Issue | Priority | Blocking Issues |
|-------|----------|-----------------|
| #65 | P0 | #64 |
| #63 | P0 | #64,#65 |
| #56 | P0 | #31,#32 |
| #57 | P1 | #56 |
| #34 | P1 | #33,#35 |

## 4. LARGE (L) Splitting Candidate
| Issue | Current Size | Proposed Split |
|-------|--------------|----------------|
| #31 | L | #31a (config/dictConfig), #31b (UI mapping) |
| #39 | L | #39a (Parser+Schema), #39b (Executor) |
| #47 | L | #47a (Queue infra), #47b (Concurrency limits) |
| #49 | L | #49a (Loader), #49b (Lifecycle Hooks) |
| #62 | (M→split) | #62a (PoC syscalls), #62b (Enforce) |

## 5. KPI Snapshot (手入力 or 自動集計)
- P0 Remaining: X
- Wave A1 Progress: (done/total)
- Blocked >2d: N
- Doc Sync Lag: 0 (good)
- Regression Suite Pass: 100%

## 6. Next Candidate Logic
Algorithm:
1. Select READY with priority=P0
2. If none → READY P1
3. Break ties: smaller size → earlier wave → oldest creation date
4. If multiple S remain, batch two sequential prompts only if completely independent; otherwise strict 1-by-1.

## 7. Change Log
| Date | Change | Author |
|------|--------|--------|
| (初版) | Draft dashboard added | |

(自動生成時は上書き)
(EOF)
```

```yaml name=docs/roadmap/TASK_QUEUE.yml
# Machine-readable task queue
# Fields: status = READY | BLOCKED | IN_PROGRESS | DONE
generated_at: "REPLACE_ME"
roadmap_commit: "REPLACE_ME"
dependencies_commit: "REPLACE_ME"
items:
  - issue: 64
    title: "フィーチャーフラグ フレームワーク"
    priority: P0
    size: M
    wave: A1
    status: READY
    depends_on: []
  - issue: 65
    title: "マルチ環境設定ローダ"
    priority: P0
    size: M
    wave: A1
    status: BLOCKED
    depends_on: [64]
  - issue: 63
    title: "llms.txt スキーマ & バリデータ"
    priority: P0
    size: S
    wave: A1
    status: BLOCKED
    depends_on: [64,65]
  - issue: 32
    title: "Run/Job ID 実装"
    priority: P0
    size: S
    wave: A2
    status: READY
    depends_on: []
  - issue: "31a"
    base_issue: 31
    title: "Logging Design Part1 (dictConfig)"
    priority: P0
    size: M
    wave: A2
    status: BLOCKED
    depends_on: [32]
  - issue: "31b"
    base_issue: 31
    title: "Logging Design Part2 (UI mapping)"
    priority: P0
    size: M
    wave: A2
    status: BLOCKED
    depends_on: ["31a"]
  - issue: 56
    title: "統一 JSON Lines ロギング"
    priority: P0
    size: M
    wave: A2
    status: BLOCKED
    depends_on: ["31a",32]
  - issue: 28
    title: "録画パス統一"
    priority: P0
    size: S
    wave: A3
    status: BLOCKED
    depends_on: [32]
  # ... (他 Issue も同パターンで続ける)
notes: >
  This file is regenerated; manual edits may be overwritten.
```

----

## 6. 自動生成スクリプト方針（概要）

Pseudo steps (scripts/generate_task_dashboard.py):

1. Load ISSUE_DEPENDENCIES.yml
2. Query GitHub API for each issue state/labels (priority, size, wave)
3. Determine dependency states; classify status
4. Apply splitting rules (L を 2 M に分割マッピング表)
5. Render Jinja2 templates → TASK_QUEUE.yml & TASK_DASHBOARD.md
6. Commit (optional) with message: docs: regen task dashboard (auto)

GitHub Actions (例トリガ):

- schedule: cron(“*/30 * * * *”) で 30分毎
- or workflow_dispatch
- PR merge event (main に)

----

## 7. Agent プロンプト生成高速化 Tips

- 生成コマンド例: `./scripts/make_agent_prompt.py --issue 64 --roadmap-commit $(git rev-parse HEAD)`  
  → Issue 本文 + TASK_QUEUE.yml から Acceptance/Dependencies 抽出  
- テンプレ内 Questions セクションは常に最後固定（Agent の clarifying question が検出しやすい）  
- 依存未完なら “STOP & ASK” だけを期待するので Acceptance Criteria の詳細まで渡さない簡易版を使いトークン節約可能（Status=BLOCKED の場合）。

Blocked 用 最小プロンプト例:

```prompt
Issue #65 is BLOCKED (depends on: #64 not yet merged).
Do not implement. Confirm blocking status or ask clarifications if dependency is actually resolved.
```

----

## 8. リスク & 対策

| リスク | 事象 | 対処 |
|--------|------|------|
| ROADMAP と Dashboard の乖離 | ヒューマン更新漏れ | 自動スクリプト + CI チェック |
| 依存変更時の古いプロンプト | 実装ズレ | RoadmapVersion hash チェック |
| L タスク着手による停滞 | PR 巨大化 | L 自動検出 → 強制シナリオ分割 |
| Flag 未削除 | レガシー蓄積 | 月次 stale flag レポート |
| Docs 反映遅延 | Acceptance 誤差 | PR テンプレ “Docs Updated” 強制 |

----

## 9. 導入ステップ（すぐ動ける順）

1. 上記 2 ファイル (TASK_DASHBOARD.md / TASK_QUEUE.yml) をリポジトリに追加  
2. L 分割対象にサブ Issue (例: #31a/#31b) Draft 生成  
3. generate_task_dashboard.py の簡易版（最初は手動 YAML 更新で可）  
4. 次タスク (#64) 用 Prompt 作成 & Agent 実行  
5. マージ後 → DEPENDENCIES.yml / Dashboard 更新 → #65 Prompt  
6. 2 サイクル後 自動生成スクリプト/Actions 導入  

----

## 10. まとめ（運用の肝）

- “一つの READY キュー” 可視化で迷いゼロ
- すべてのプロンプトは整形テンプレ＋ RoadmapVersion
- L を機械的に分割し Agent ターン時間短縮
- 自動再生成ダッシュボードで常時最新 / 手動二重管理回避
- STOP & ASK プロトコルで未解決依存の早期検出
