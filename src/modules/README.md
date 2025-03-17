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

## 6. YAML Parser & Automation Manager (YAML構文解析＆自動化マネージャー)

**目的**: カスタムアクションの定義をYAMLで効率的に管理し、ブラウザ操作を自動化します。

**機能**:
- Markdown内のYAMLブロック解析
- ローカルファイルとリモートソースからのアクション定義読み込み
- テンプレート化されたブラウザ操作フロー
- 優先順位付きのソース管理（ローカル → リモート → LLMフォールバック）

**使用方法**:
```python
from src.modules.yaml_parser import InstructionLoader
from src.modules.automation_manager import BrowserAutomationManager

# ローカルとリモートの両方のソースを設定
loader = InstructionLoader(
    local_path="llms.txt",
    website_url="https://example.com/automation-configs.md"
)

# 自動化マネージャーのセットアップと初期化
manager = BrowserAutomationManager(
    local_path="llms.txt",
    website_url="https://example.com/automation-configs.md"
)
manager.initialize()

# アクションの実行
result = manager.execute_action("search-nogtips", query="automation testing")
if result:
    print("アクションが正常に実行されました")
```

**カスタムアクション定義例**（llms.txt）:
```yaml
actions:
  - name: search-google
    type: browser-control
    params:
      - name: query
        required: true
        type: string
        description: "検索クエリ"
    flow:
      - action: command
        url: "https://www.google.com"
      - action: fill_form
        selector: "#APjFqb"
        value: "${params.query}"
      - action: keyboard_press
        selector: "Enter"
```

**プロンプト処理のフロー**:
```graph TD
    A[ユーザー入力: "Googleでおそばを検索して"] --> B[pre_evaluate_prompt]
    B --> C{YAMLパーサー: llms.txtのマッチ}
    C -->|マッチあり| D[アクションテンプレート実行]
    C -->|マッチなし| E[LLMによる処理]
    D --> F[BrowserAutomationManager処理]
    F --> G[テンプレート内のパラメータ置換]
    G --> H[ブラウザアクション実行]
    E --> I[CustomAgent処理]
```

1. ユーザープロンプトがシステムに入力される
2. `pre_evaluate_prompt`関数がYAMLパーサーを使用して`llms.txt`内のパターンと照合
3. マッチするアクションが見つかった場合:
   - `InstructionLoader`がアクション定義を読み込み
   - `BrowserAutomationManager`がパラメータを抽出（例：「おそば」を検索クエリとして）
   - 定義されたフローに従ってブラウザ操作を実行
4. マッチがない場合:
   - 従来のLLMベースのCustomAgentが処理を引き継ぐ

**ユースケース**:
- **再利用可能な検索フロー**: 複数のウェブサイトに対する標準化された検索操作の定義
- **サイト特化型アクション**: 特定サイト向けのカスタマイズされた複雑な操作シーケンス
- **コミュニティ共有**: ユーザー間でのYAML定義の共有とカスタマイズ

### モジュール連携の詳細

YAML Parser、Automation Manager、Mainの3つのファイルは以下のように連携して動作します：

#### 基本的なファイル構成と役割

1. **yaml_parser.py**: YAMLフォーマットのアクション定義を解析します
   - `InstructionLoader`: ローカルファイルやリモートソースからアクション定義を読み込み
   - `MarkdownYamlParser`: Markdown内のYAMLブロックを抽出・解析
   - `BrowserAutomationConfig`: 設定の読み込みと検証を担当

2. **automation_manager.py**: 解析されたアクション定義を管理し実行します
   - `BrowserAutomationManager`: アクションの登録と実行を管理
   - `setup_browser_automation`: 優先順位に従った初期化を行う便利な関数

3. **main.py**: エンドユーザー向けのシンプルなインターフェイスを提供します
   - 設定の読み込みと初期化
   - アクション実行のワンストップエントリーポイント

#### 実装例: カスタム検索アクションの実行

```python
# 1. 基本的な使用方法（最もシンプル）
from src.modules.main import main
main()  # search-nogtipsアクションを自動的に実行

# 2. カスタム検索の実装例
from src.modules.automation_manager import setup_browser_automation

def search_with_custom_engine(search_engine, query):
    # マネージャーの初期化
    manager = setup_browser_automation()
    
    # 検索エンジンに応じたアクション選択
    if search_engine == "google":
        action_name = "phrase-search"
    elif search_engine == "nogtips":
        action_name = "search-nogtips"
    else:
        return False
    
    # 検索実行
    return manager.execute_action(action_name, query=query)

# 使用例
search_with_custom_engine("google", "Python自動化")
```

#### モジュール間の連携フロー

1. **ユーザー入力処理**
   ```
   ユーザー入力 → main.py → automation_manager.py → yaml_parser.py → llms.txt
   ```

2. **アクション実行**
   ```
   main.py
     ↓
   setup_browser_automation() → BrowserAutomationManager
     ↓
   manager.execute_action() → _execute_browser_control()/_execute_script()
     ↓
   実際のブラウザ操作の実行
   ```

3. **パラメータ処理**
   ```
   アクション定義内の "${params.query}" → パラメータ抽出 → 値の置換 → 実行
   ```

#### 応用: 複数ソースからのアクション定義の優先順位管理

```python
# 複数のソースからアクション定義を読み込み、優先順位を設定
sources = [
    {"type": "local", "path": "custom_actions.txt", "priority": 1},
    {"type": "remote", "url": "https://example.com/actions.md", "priority": 2},
    {"type": "llm", "priority": 3}  # フォールバックとしてLLM処理
]

# 設定に基づいた初期化
manager = setup_advanced_automation(sources)

# アクション実行（複数ソースからのマージ結果を使用）
result = manager.execute_action("search-combined", query="最新技術動向")
```

このシステムを活用することで、LLM呼び出しを削減しながら、効率的かつ柔軟なブラウザ自動化を実現できます。

## 7. Git Script Repository (Gitスクリプトリポジトリ)

**目的**: GitリポジトリからスクリプトやツールセットをBykilt内で活用できるようにします。

**機能**:
- Gitリポジトリからのスクリプト取得・実行
- バージョン指定によるスクリプト管理
- キャッシュによる効率的な実行
- 柔軟なパラメータ受け渡し

**使用方法**:
```python
from src.modules.automation_manager import BrowserAutomationManager

# マネージャーの初期化
manager = BrowserAutomationManager(local_path="llms.txt")

# Gitベースのスクリプト実行
result = manager.execute_action(
    "login-script", 
    username="myuser", 
    password="mysecret"
)
```

**YAMLでの定義例** (llms.txt):
```yaml
actions:
  - name: login-script
    git: https://github.com/username/automation-scripts.git
    script_path: login.py
    version: main  # オプション: ブランチ、タグ、コミットハッシュ
    command: python ${script_path} --username ${username} --password ${password}
    timeout: 120  # 秒単位
    slowmo: 1000  # ブラウザの動作を遅くする（ミリ秒）
```

**技術的詳細**:
- スクリプトは `./tmp/git_scripts/<リポジトリ名>` にクローンされます
- 1時間おきに自動更新（設定変更可能）
- スクリプト実行が失敗した場合はLLMにフォールバック

**ユースケース**:
- **共有自動化スクリプト**: チーム間で標準化された自動化ツールを共有
- **専門的な処理**: 複雑なデータ処理や特定サイト向けのスクリプトをリポジトリで管理
- **コミュニティリソース**: 公開リポジトリから有用なツールを直接活用