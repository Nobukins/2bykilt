# 効率的な Agent 指示出し方法

ロードマップと同期しながら、コーディングエージェントへ 1 タスクずつ迷わず指示を出すための運用。
プロンプトの形式契約は [`docs/engineering/AGENT_PROMPT_GUIDE.md`](../engineering/AGENT_PROMPT_GUIDE.md) を参照。

原則:

1. 情報の一次ソースを一か所に固定する (SSOT)
2. プロンプトは最小限にし、参照したロードマップの版を明示して再現性を確保する
3. 着手順は自動生成の READY キューから選ぶ
4. 1 イテレーション = 1 Issue (またはサブ Issue)

## 1. ファイル構成

| 役割 | ファイル | 編集 |
|------|----------|------|
| 戦略 / Wave / KPI | `ROADMAP.md` | 手動 |
| 依存関係・状態 (SSOT) | `ISSUE_DEPENDENCIES.yml` | 手動 (唯一の編集対象) |
| 機械可読キュー (READY / BLOCKED / IN_PROGRESS) | `TASK_QUEUE.yml` | 生成 (`scripts/generate_task_queue.py`) |
| 人間用ダッシュボード | `TASK_DASHBOARD.md` | 生成 (`scripts/generate_task_dashboard.py`) |
| 依存グラフ | `DEPENDENCY_GRAPH.md` | 生成 (`scripts/gen_mermaid.py`) |

生成物は `.github/workflows/dependency-pipeline.yml` が `ISSUE_DEPENDENCIES.yml` の変更時・毎日定時に再生成する。
ローカルで再生成・検証する手順は ROADMAP.md **Section K** に従う。

## 2. 1 タスクのライフサイクル

1. `TASK_QUEUE.yml` / `TASK_DASHBOARD.md` が最新か確認 (古ければ Section K の手順で再生成)
2. READY の最上位を選ぶ: P0 → P1、同順位なら size 小 → Wave 順 → 作成日順
3. 下記テンプレでプロンプトを作成し、`RoadmapVersion` に ROADMAP の commit hash を入れる
4. Agent が PR 作成 → レビュー → マージ時に `ISSUE_DEPENDENCIES.yml` (`progress.state: done` など) を更新
5. 再生成して次のタスクへ

`RoadmapVersion` を入れておくと、ROADMAP が変わった後に古い前提で実装していないかを検知できる。

## 3. 実装プロンプトの例

```prompt
Action: Implement
Issue: #64 フィーチャーフラグ フレームワーク
RoadmapVersion: <ROADMAP.md の最新 commit hash>
Context:
- Goal: Provide unified feature flag resolution (override > env > file).
Acceptance Criteria (mirrored):
- Resolution order: runtime override > env > config file
- 100% tests for resolution paths
Dependencies (must be DONE): #65
If any dependency not merged → STOP & ASK.

Scope:
- Modify: src/config/feature_flags.py
- Tests: tests/config/

Non-Scope:
- Admin UI

Constraints:
- No public API break
- No network I/O

Questions:
- Return False vs raise KeyError for unknown flags? (Assume False if not clarified)

On ambiguity or unmet dependency: Reply ONLY with questions; do not implement.
```

- Acceptance Criteria は Issue 本文から必要部分だけ抜粋する
- Questions は常に最後に置く (Agent の確認質問を拾いやすくするため)
- L サイズの Issue はサブ Issue に分割してから渡す

## 4. BLOCKED の Issue 用最小プロンプト

依存未完の Issue は詳細を渡さず、状態確認だけさせる。

```prompt
Issue #65 is BLOCKED (depends on: #64 not yet merged).
Do not implement. Confirm blocking status or ask clarifications if dependency is actually resolved.
```
