# 2bykilt 開発者ガイドライン

このドキュメントは、2bykilt のIssueトリアージ・優先付け・日常的な開発選定を支援するための簡潔な開発者ガイドラインです。

目的

- 大量のIssueの中から次に何をやるべきかを迅速かつ心理的負担少なく決定するための共通ルールを提供します。
- GitHub上での宣言的な管理（YAML + PR）と、プロジェクトマネジメント的手法（Impact/Effortなど）を組み合わせたワークフローを推奨します。

適用範囲

- このガイドラインはすべての開発者とコントリビューターに適用されます。

---

## 3ステップ選択フロー（概要）

1. クイック・トリアージ（2〜5分/Issue）

   - 評価指標: Impact, Effort, Risk, Confidence を 0–5 で付与
   - スコア例: Score = Impact*3 - Effort*2 - Risk + Confidence
   - Score ≥ 10: High, 5–9: Medium, ≤4: Low
   - ラベル付与: priority:high/priority:medium/priority:low

2. 個人・チーム適合性チェック（1〜3分）

   - 自分の得意分野・空き時間を確認
   - マイクロタスク化（1時間以内に終わる粒度）を優先
   - 必要ならペア割当て（心理的負担軽減）

3. 即行動プラン（20–60分スパイク）

   - 最小実行可能な作業（MVP）を決め、タイムボックスを設定
   - スパイク後にPR/Issueコメントで学び（1行）を残す

---

## 評価基準（テンプレート）

- Impact (0-5): ユーザ/運用/セキュリティへの影響度
- Effort (0-5): 想定工数（0:数分〜5:数週間）
- Risk (0-5): 変更による副作用やリスク
- Confidence (0-5): 原因/対処法の明確さ
- Score: Impact*3 - Effort*2 - Risk + Confidence

運用例: Issue にコメントテンプレを貼り、triage担当が数値を埋める。

---

## 心理的配慮と小さな成功の仕組み

- 3択ルール: 候補を3つまでに絞る。迷ったらランダムピック+拒否1回。
- 一日一小勝利: 1日1つは小さな完了を出す（例: テスト1件追加、ドキュメント1行）
- Timeboxing: 作業は30〜90分で区切る。中断は許可される。
- バディ制度: 迷ったら15分一緒に考える相手を決める
- 休憩の推奨: 判断疲れを感じたら短い休憩を取る

---

## GitHub のベストプラクティスとの整合

- すべての変更はPRベースで行う（YAMLで宣言→CIで検証→PRでレビュー）
- `docs/roadmap/ISSUE_DEPENDENCIES.yml` を単一ソースとして管理し、CIで派生物を自動生成
- ラベル運用で triage 結果を可視化 (priority:, size:, phase:, area:, risk:)

---

## 具体的なワークフロー（短）

1. 週次15分トリアージを実施（全OpenをQuick-TriageしてHigh/Medium/Lowに振り分け）

2. 各メンバーは週に1回、60分スパイクを実施して何かを完了させる

3. スパイク後はPRかIssueコメントで1行の学び（何がわかったか）を残す

---

## ツール & コマンド（参考）

- Validator 実行

```bash
./venv/bin/python scripts/validate_dependencies.py docs/roadmap/ISSUE_DEPENDENCIES.yml
```

- 生成物をローカルで出す（CIが実行するためPRには含めない）

```bash
./venv/bin/python scripts/gen_mermaid.py docs/roadmap/ISSUE_DEPENDENCIES.yml > docs/roadmap/DEPENDENCY_GRAPH.md
./venv/bin/python scripts/generate_task_dashboard.py
./venv/bin/python scripts/generate_task_queue.py --repo Nobukins/2bykilt --input docs/roadmap/ISSUE_DEPENDENCIES.yml --output docs/roadmap/TASK_QUEUE.yml --no-api
```

---

## テンプレ（Issue コメント／PR説明）

簡易 triage コメントテンプレ:

```text
Triage: Impact=4, Effort=2, Risk=1, Confidence=4
Score = 4*3 - 2*2 - 1 + 4 = 11 (priority: high)
```

PR 説明テンプレは `docs/roadmap/PR_281_BODY.md` を参照

---

## 測定指標（KPI）

- 週あたりの完了数（目標: 週3小勝利）
- 未評価Issueの割合（目標: 週次トリアージで0に近づける）
- チームの満足度（簡易アンケート）

---

このガイドラインは軽量で運用しやすいことを優先しています。必要なら、Issueテンプレ/Actionの雛形/triageスプレッドシートを追加で作成します。どれを作りましょうか？
