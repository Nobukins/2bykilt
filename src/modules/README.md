
# Bykilt Enhanced Modules

Bykiltには以下の拡張モジュールが含まれており、ブラウザ操作とAIエージェントの連携をさらに強化します。(全て今後実装予定。ロードマップとしてのみここに策定する。)

## 1. Action Templates (アクションテンプレート)

**目的**: 再利用可能なブラウザ操作パターンを定義して共有する機能を提供します。

**機能**:
- 頻繁に使用するブラウザ操作をテンプレート化
- パラメータ化されたテンプレートで柔軟性を確保
- 複雑な操作シーケンスを簡単に再利用

**使用方法**:
```python
from src.modules.action_templates import ActionTemplate

# テンプレートの作成
login_template = ActionTemplate()
login_template.add_template("amazon_login", {
    "url": "https://www.amazon.co.jp/",
    "username_selector": "input[name='email']",
    "password_selector": "input[name='password']",
    "submit_selector": "input[type='submit']"
})

# テンプレートの使用
amazon_login = login_template.get_template("amazon_login")
```

**ユースケース**:
- **EC自動購入**: Amazonログイン→商品検索→カート追加→購入手続きを再利用可能なテンプレートで実行
- **定期レポート生成**: ビジネスダッシュボードへのログイン→データ抽出→CSVダウンロードを自動化

## 2. Workflow Builder (ワークフロービルダー)

**目的**: コードを書かずに視覚的にブラウザ自動化ワークフローを構築できます。

**機能**:
- ドラッグ&ドロップでワークフロー構築
- 条件分岐とループの組み込み
- エラーハンドリングの追加

**使用方法**:
```python
from src.modules.workflow_builder import WorkflowBuilder

# ワークフローの構築
builder = WorkflowBuilder()
builder.add_action({"type": "navigate", "url": "https://example.com"})
builder.add_condition({
    "if": {"element_exists": "#login-form"},
    "then": [{"type": "fill", "selector": "#username", "value": "user"}],
    "else": [{"type": "click", "selector": "#register-button"}]
})
workflow = builder.build()

# デバッグ実行
builder.debug_run(headless=False, slow_mo=500, highlight_elements=True)
```

**ユースケース**:
- **マルチステップフォーム**: 複数ページにまたがる申請フォームの自動入力と送信
- **データ収集パイプライン**: 複数サイトから順次データを抽出し、特定の条件で処理を分岐

## 3. Human Collaboration (人間協調型インターフェース)

**目的**: AIと人間のハイブリッド操作を実現し、重要な判断ポイントで人間の確認を得ます。

**機能**:
- 操作の確認要求
- インタラクション編集
- 視覚的フィードバック

**使用方法**:
```python
from src.modules.human_collab import HumanCollaborationInterface

# インターフェースの初期化
collab = HumanCollaborationInterface()

# 確認を求める
collab.request_confirmation({
    "action": "purchase",
    "item": "商品名",
    "price": "¥10,000",
    "quantity": 1
})

# 自動レスポンスでシミュレーション（デバッグ用）
collab.simulate(
    auto_responses={"purchase": {"action": "approve"}},
    log_decisions=True,
    log_path="collaboration_log.json"
)
```

**ユースケース**:
- **購入承認フロー**: 商品選択はAIが行い、最終購入決定は人間が承認
- **データ入力検証**: AIが自動入力した内容を人間が確認・修正してから送信

## 4. Execution Engine (実行エンジン)

**目的**: LLM呼び出しを最小限に抑えつつ、効率的にワークフローを実行します。

**機能**:
- スクリプト優先実行
- キャッシュ機能によるLLM呼び出し削減
- 再試行と回復メカニズム

**使用方法**:
```python
from src.modules.execution_engine import ExecutionEngine

# エンジンの初期化
engine = ExecutionEngine()

# スクリプト実行
engine.execute_script("search_script.py")

# 必要な場合のみLLM呼び出し
result = engine.get_cached_result("search_query")
if not result:
    result = engine.call_llm("新しい検索クエリを生成して")
    engine.cache_result("search_query", result)

# デバッグモードで実行
engine.execute_with_debug(
    workflow_path="workflows/data_collection.json",
    dump_state_after_each_step=True,
    pause_on_error=True
)
```

**ユースケース**:
- **バッチ処理**: 多数のサイトから同様のデータを効率的に収集
- **定期実行タスク**: 毎日の在庫チェックや価格監視を最小限のLLM使用で実行

## 5. Community Hub (コミュニティハブ)

**目的**: テンプレートやワークフローをコミュニティで共有し、再利用を促進します。

**機能**:
- テンプレート共有と検索
- 評価システム
- バージョン管理

**使用方法**:
```python
from src.modules.community_hub import CommunityHub

# ハブの初期化
hub = CommunityHub()

# テンプレートのアップロード
hub.upload_template("amazon_purchase_flow", my_workflow)

# 人気テンプレートのダウンロード
popular_template = hub.download_template("booking_automation")

# デバッグ用に操作をテスト
hub.debug_operations(
    test_download=True,
    network_conditions={"latency": 200}
)
```

**ユースケース**:
- **ナレッジ共有**: 特定ドメイン向けの最適化されたワークフローを共有
- **コラボレーション**: 複数チームが協力して複雑な自動化シナリオを開発・改良