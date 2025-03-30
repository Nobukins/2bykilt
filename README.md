<img src="./assets/2bykilt-ai.png" alt="2Bykilt - 業務効率化魔法「2bykilt」" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/Nobukins/2bykilt?style=social)](https://github.com/Nobukins/2bykilt/stargazers)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.browser-use.com)

This project builds upon the foundation of the [browser-use/web-ui](https://github.com/browser-use/browser-use/web-ui), which is designed to make websites accessible for AI agents.

**WebUI:** is built on Gradio and supports most of `browser-use` functionalities. This UI is designed to be user-friendly and enables easy interaction with the browser agent.

**Expanded LLM Support:** We've integrated support for various Large Language Models (LLMs), including: Google, OpenAI, Azure OpenAI, Anthropic, DeepSeek, Ollama etc. And we plan to add support for even more models in the future.

**Custom Browser Support:** You can use your own browser with our tool, eliminating the need to re-login to sites or deal with other authentication challenges. This feature also supports high-definition screen recording.

**Persistent Browser Sessions:** You can choose to keep the browser window open between AI tasks, allowing you to see the complete history and state of AI interactions.

<video src="https://github.com/user-attachments/assets/56bc7080-f2e3-4367-af22-6bf2245ff6cb" controls="controls">Your browser does not support playing this video!</video>

## Installation Guide

### Prerequisites
- Python 3.11 or higher
- Git (for cloning the repository)

### Option 1: Local Installation

Read the [quickstart guide](https://docs.browser-use.com/quickstart#prepare-the-environment) or follow the steps below to get started.

#### Step 1: Clone the Repository
```bash
git clone https://github.com/Nobukins/2bykilt.git
cd bykilt
```

#### Step 2: Set Up Python Environment
We recommend using [uv](https://docs.astral.sh/uv/) for managing the Python environment.

Using venv:
```bash
python3.12 -m venv venv
```

Activate the virtual environment:
- macOS/Linux:
```bash
source ./venv/bin/activate
```

#### Step 3: Install Dependencies
Install Python packages:
```bash
pip install -r requirements.txt
```

Install Playwright:
```bash
playwright install
```

#### Step 4: Configure Environment
1. Create a copy of the example environment file:
- macOS/Linux/Windows (PowerShell):
```bash
cp .env.example .env
```
2. Open `.env` in your preferred text editor and add your API keys and other settings

#### Step 5: Prepare template script
1. Create a copy of the example template file:
- Windows (Command Prompt):
```bash
copy ./example/* ./tmp/myscript/*
```
- macOS/Linux/Windows (PowerShell):
```bash
mkdir ./tmp && mkdir ./tmp/myscript
cp ./example/* ./tmp/myscript/
```
2. Open `./tmp/myscript/search_script.py` in your preferred text editor and update pytest based script with your automation script.

## Usage

### Local Setup
1.  **Run the WebUI:**
    After completing the installation steps above, start the application:
    ```bash
    python bykilt.py --ip 127.0.0.1 --port 7788
    ```
2. WebUI options:
   - `--ip`: The IP address to bind the WebUI to. Default is `127.0.0.1`.
   - `--port`: The port to bind the WebUI to. Default is `7788`.
   - `--theme`: The theme for the user interface. Default is `Ocean`.
     - **Default**: The standard theme with a balanced design.
     - **Soft**: A gentle, muted color scheme for a relaxed viewing experience.
     - **Monochrome**: A grayscale theme with minimal color for simplicity and focus.
     - **Glass**: A sleek, semi-transparent design for a modern appearance.
     - **Origin**: A classic, retro-inspired theme for a nostalgic feel.
     - **Citrus**: A vibrant, citrus-inspired palette with bright and fresh colors.
     - **Ocean** (default): A blue, ocean-inspired theme providing a calming effect.
   - `--dark-mode`: Enables dark mode for the user interface.
3.  **Access the WebUI:** Open your web browser and navigate to `http://127.0.0.1:7788`.
4.  **Using Your Own Browser(Optional):**
    - Set `CHROME_PATH` to the executable path of your browser and `CHROME_USER_DATA` to the user data directory of your browser. Leave `CHROME_USER_DATA` empty if you want to use local user data.
      - Windows
        ```env
         CHROME_PATH="C:\Program Files\Google\Chrome\Application\chrome.exe"
         CHROME_USER_DATA="C:\Users\YourUsername\AppData\Local\Google\Chrome\User Data"
        ```
        > Note: Replace `YourUsername` with your actual Windows username for Windows systems.
      - Mac
        ```env
         CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
         CHROME_USER_DATA="/Users/YourUsername/Library/Application Support/Google/Chrome"
        ```
    - Close all Chrome windows
    - Open the WebUI in a non-Chrome browser, such as Firefox or Edge. This is important because the persistent browser context will use the Chrome data when running the agent.
    - Check the "Use Own Browser" option within the Browser Settings.
5. **Keep Browser Open(Optional):**
    - Set `CHROME_PERSISTENT_SESSION=true` in the `.env` file.

### Using Ollama with Bykilt
For users who want to use Ollama as their LLM provider, follow these specific configuration steps:

1. **Start Bykilt:**
   ```bash
   python bykilt.py
   ```

2. **Access the WebUI:**
   Open your web browser and navigate to `http://127.0.0.1:7788`

3. **Configure Ollama:**
   - Disable the **Vision** option
   - Navigate to **LLM Configurations** menu
   - Set **LLM Provider** to `ollama`
   - Select **Model Name** `deepseek-r1-distill-llama-8b` (or your preferred Ollama model)
   - Enable **Dev Mode** by toggling it on
   - set LM Studio hosting LLM API endpoint url as `http://127.0.0.1:1234/v1`

> **Note:** LLMを利用するAgent開発においてはLLMとの通信を理解する必要があります。このため、LM Studioを利用したローカルでのLLMホストを開発環境では推奨します。この環境構築により実際にLLMからの自然言語での返信を確認する事が出来るので効率的なプロンプトエンジニアリングを実現されます。逆に言うと、ここまでやらないと何が起きているのか全くわからないブラックボックスになってしまいます。

## Prompt inputs / プロンプト入力例

#### LinkedIn search
```
search-linkedin query=Personal_AI_Assistant 
```

#### Beatport search
```
search-beatport query=Minimal 
```

## コマンドナビゲーション機能

2Bykiltでは、AIによる自然言語処理だけでなく、事前定義されたコマンドを直接実行することも可能です。コマンドナビゲーション機能により、利用可能なコマンドを簡単に見つけて実行できます。

### コマンド入力方法

コマンドは以下の形式で入力できます：

```
@コマンド名 パラメータ1=値1 パラメータ2=値2
```

または

```
/コマンド名 パラメータ1=値1 パラメータ2=値2
```

例：
```
@phrase-search query=AI開発
/search-linkedin query=Python開発者
```

### コマンドサジェスト機能

タスク入力欄に「@」または「/」を入力すると、利用可能なコマンドの候補が表示されます：

1. 入力欄に「@」または「/」を入力
2. 表示されるコマンド候補から選択するか、続けて入力
3. コマンドを選択すると、必要なパラメータのテンプレートが自動的に挿入される

### コマンドテーブル

「Run Agent」タブの「Available Commands」アコーディオンには、すべての利用可能なコマンドとその説明が表示されます：

1. アコーディオンを開くとコマンド一覧が表示される
2. テーブルからコマンドをクリックすると、そのコマンドがタスク入力欄に挿入される
3. 「Refresh Commands」ボタンで最新のコマンド一覧を更新できる

### タブ選択戦略

ブラウザ設定で「Use Own Browser」を有効にしている場合、どのブラウザタブを自動化に使用するかを選択できます：

- **新しいタブ (new_tab)**: 常に新しいタブで操作を実行
- **アクティブタブ (active_tab)**: 現在アクティブなタブで操作を実行（デフォルト）
- **最後のタブ (last_tab)**: 最後に開いたタブで操作を実行

この設定は「Browser Settings」タブの「Tab Selection Strategy」で変更できます。

### カスタムコマンドの定義とパラメータ

前述の「llms.txt」ファイルでYAML形式のアクションを定義すると、それらがコマンドとして自動的に利用可能になります。コマンド定義には以下の要素を含めることができます：

- **name**: コマンド名（@または/の後に入力する識別子）
- **type**: コマンドの種類（browser-control、script、unlock-futureなど）
- **params**: コマンドパラメータの定義
  - **name**: パラメータ名
  - **required**: 必須かどうか（true/false）
  - **type**: データ型（string、number、booleanなど）
  - **description**: パラメータの説明
- **flow**: アクションの実行フロー

パラメータ定義により、コマンドサジェスト機能で適切なパラメータテンプレートが提供されます。

### コマンド実行フロー

2Bykiltでは、入力されたテキストを以下のように処理します：

1. 入力がコマンド形式（@または/で始まる）の場合、コマンド処理へ
2. コマンドが見つかった場合、そのコマンドに対応するアクションを実行
3. コマンドが見つからない、または通常のテキストの場合、LLMでの処理へ

これにより、定型的なタスクは迅速に実行しつつ、複雑な処理はAIに任せることができます。

## カスタマイズとスクリプト作成

### llms.txtでアクションを定義

プロジェクトルートにllms.txtを編集・更新しカスタマイズした自動化操作手順をYAML形式で保存する

この場合、最初に宣言するname属性がコマンド呼び出し時の識別子となる。つまり「phrase-search」がそれに該当する。
```yaml
actions:
  - name: phrase-search
    type: browser-control
    params:
      - name: query
        required: true
        type: string
        description: "Search query to execute"
    slowmo: 1000
    flow:
      - action: command
        url: "https://www.google.com"
        wait_for: "#APjFqb"
      - action: click
        selector: "#APjFqb"
        wait_for_navigation: true
      - action: fill_form
        selector: "#APjFqb"
        value: "${params.query}"
      - action: keyboard_press
        selector: "Enter"
```

上記の様にカスタムで組んだ自動化スクリプトがllms.txtにあれば、以下のようなプロンプト入力でカスタム利用が可能となる。
```
phrase-search query=Personal_AI_Assistant
```

## Debug tool / デバッグツール

Bykiltでは、LLM（大規模言語モデル）からのレスポンスをシミュレートし、ブラウザ操作をデバッグするための簡易ツールを提供しています。

### デバッグ機能強化（2025/03/23）

今回のアップデートでは、以下のデバッグ機能が強化されました：

1. **詳細なログ出力**:
   - コマンド実行フローの追跡が可能になりました
   - llms.txtの解析過程を可視化
   - パラメータ置換の詳細な診断情報

2. **ビジュアルデバッグ**:
   - 要素インデックス付け機能（`setup_element_indexer`）でページ内の要素に番号を表示
   - ブラウザ操作の各ステップをより明確に確認可能

3. **yaml_parser統合**:
   - llms.txtからのアクション読み込みを効率化
   - 様々なYAML形式に対応

4. **エラー診断の強化**:
   - 問題の原因特定を容易にする詳細なエラーメッセージ
   - コマンド実行中の状態追跡

### 使用方法

#### debug_bykilt.py の使用方法
Run the debug tool by providing a JSON file containing LLM response data:

このツールを使用すると、JSONファイルを使ってLLMからのレスポンスをシミュレートし、Playwrightを使ってブラウザ操作を直接実行できます。

```bash
python debug_bykilt.py <llm_response_file>
```

サンプルJSONファイルをテストします：
```bash
python debug_bykilt.py external/samples/navigate_url.json
```
```bash
python debug_bykilt.py external/samples/search_word.json
```

#### 要素インデキシングの使用方法
```python
from src.utils.debug_utils import DebugUtils

async def debug_page(page):
    debug = DebugUtils()
    await debug.setup_element_indexer(page)  # ページ内の操作可能な要素に番号を表示
    
    # 他のデバッグ機能
    debug.show_help()  # ヘルプ情報を表示
    samples = debug.list_samples()  # 利用可能なサンプルを一覧表示
```

### サポートされている機能

- URLへの移動とナビゲーション
- 検索機能（Beatportなど）
- フォーム入力
- 要素のクリック
- テキスト抽出
- 複雑なシーケンシャルアクション

### サンプルファイル

`external/samples/` ディレクトリには、様々なタイプのアクションをテストするためのサンプルJSONファイルが用意されています：

- `navigate_url.json`: 基本的なURL移動
- `search_word.json`: 検索クエリの実行
- `form_input.json`: フォーム入力操作
- `extract_content.json`: コンテンツ抽出操作
- `complex_sequence.json`: 複数アクションの連続実行

これらのサンプルを使用して、Bykiltの機能をテストおよびデバッグできます。

#### Supported Formats
The tool supports JSON files with the following formats:

1. Script-based format:
```json
{
    "script_name": "search-beatport",
    "params": {
      "query": "minimal"
    }
}
```

2. Command-based format:
```json
{
  "commands": [
    {
      "action": "command",
      "args": ["https://www.google.com"]
    },
    {
      "action": "wait_for_navigation"
    }
  ]
}
```

The debug tool will execute the commands in a browser window, allowing you to see how they would behave when processed by Bykilt.

## デバッグツールの改良内容

Bykiltのデバッグツール(debug_bykilt.py)には、以下の改善が施されています:

### ブラウザ管理の最適化 (2025/03/21)

- **単一ブラウザインスタンス**: ユーザーの既存のChromeブラウザを活用し、新しいタブで処理を実行
- **ユーザー体験の向上**: 
  - 普段使っているブラウザをそのまま利用することで安心感を提供
  - 複数ウィンドウを起動せず、タブ管理で操作を完結
- **セキュリティの改善**: 不要なフラグを削除してセキュリティ警告を防止
- **状態管理の強化**: グローバルブラウザインスタンスを適切に管理し、リソースリークを防止

### タブベースの操作改善 (2025/03/21)

- **新しいウィンドウではなくタブで開く**: 既存のChromeウィンドウの中に新しいタブとして処理を実行
- **コンテキスト管理の統一**: すべての実行関数でブラウザコンテキストを一貫して使用
- **デフォルトコンテキスト活用**: CDB接続時に既存のブラウザコンテキストを利用
- **効率的なタブ操作**: 処理完了後、ブラウザは開いたままでタブのみを閉じる設計
- **プロセスフロー制御**: リクエスト処理→タブ作成→コマンド実行→タブ閉じる の一連の流れを最適化

### 依存関係処理の改善

- **柔軟なモジュール依存**: 必須でないモジュール(psutil)が無くても動作するよう条件分岐を実装
- **プラットフォーム対応**: Windows、macOS、Linuxなど様々なOS環境での動作に対応
- **ユーザー通知**: ブラウザを再起動する必要がある場合、明確なメッセージで警告

### 使用方法の例

1. 既存のChromeブラウザが開いていない状態で実行:
```bash
python debug_bykilt.py external/samples/search_word.json --use-own-browser
```

2. 既存のChromeブラウザを開いた状態で実行:
```bash
# 確認ダイアログが表示され、承認するとブラウザを再起動
python debug_bykilt.py external/samples/search_word.json --use-own-browser
```

### 処理フロー

```
1. JSONファイル読み込み
   ↓
2. ブラウザインスタンス初期化
   |→ 既存インスタンスがある場合: 再利用
   |→ 接続可能なChromeがある場合: CDPで接続
   |→ それ以外: 新しいChromeを起動
   ↓
3. コマンド実行
   |→ デフォルトコンテキスト取得
   |→ 新しいタブ作成
   |→ コマンドシーケンス実行
   |→ タブ閉じる（ブラウザは維持）
   ↓
4. リソースクリーンアップ
   |→ CDP接続の場合: Playwrightのみ停止
   |→ 非CDP接続の場合: 全リソース解放
```

詳細については、「Debug tool / デバッグツール」セクションを参照してください。

## ロードマップ

- [ ] **録画・ログの共通化**: Web-UIと同じブラウザ設定の継承と利用（録画、ログ、Agent historyなど）
- [ ] **llms.txtパーサー**: カスタムアクション定義をより良くするためのllms.txtパーサーの実装と改良
- [ ] **配布パッケージ**: PyinstallerとElectron(Mochas)を使用したクライアントインストール配布用パッケージの作成
- [ ] **モジュール開発**: 各種モジュールの追加開発:
  - [ ] **アクションテンプレート**: 共有と再利用のための再利用可能なブラウザ操作パターン
  - [ ] **ワークフロービルダー**: コーディングなしでブラウザ自動化のビジュアルワークフロー構築
  - [ ] **人間協調型インターフェース**: AIと人間のコラボレーションを可能にするハイブリッド操作インターフェース
  - [ ] **実行エンジン**: 最小限のLLM呼び出しで効率的にワークフローを実行
  - [ ] **コミュニティハブ**: コミュニティ内でテンプレートやワークフローを共有

## Changelog
- [x] **2025/03/23:** デバッグ機能強化: llms.txtパース改善、要素インデックス機能追加、コマンド実行フロー視覚化
- [x] **2025/03/21:** ブラウザ管理・タブ操作の最適化: 単一ブラウザインスタンス、タブベースの操作改善
- [x] **2025/03/06:** Thanks @Nobukins, you made magic comes true, Bykilt!
- [x] **2025/01/26:** Thanks to @vvincent1234. Now browser-use-webui can combine with DeepSeek-r1 to engage in deep thinking!
- [x] **2025/01/10:** Thanks to @casistack. Now we have Docker Setup option and also Support keep browser open between tasks.[Video tutorial demo](https://github.com/browser-use/web-ui/issues/1#issuecomment-2582511750).
- [x] **2025/01/06:** Thanks to @richard-devbot. A New and Well-Designed WebUI is released. [Video tutorial demo](https://github.com/warmshao/browser-use-webui/issues/1#issuecomment-2573393113).

# 2Bykilt

Enhanced browser control with AI and human interaction.

## Features

- AI-powered browser automation
- Multiple action types for different automation needs
- JSON-based command execution
- Script-based browser control
- Circular reference detection and prevention
- Support for custom parameters in actions

## Action Examples

### Browser Control Actions

Browser control actions allow you to automate web browser interactions using a structured flow.

```yaml
# Example: Search on Google
- name: phrase-search
  type: browser-control
  params:
    - name: query
      required: true
      type: string
      description: "Search query to execute"
  flow:
    - action: command
      url: "https://www.google.com"
      wait_for: "#APjFqb"
    - action: click
      selector: "#APjFqb"
      wait_for_navigation: true
    - action: fill_form
      selector: "#APjFqb"
      value: "${params.query}"
    - action: keyboard_press
      selector: "Enter"
```

### Script Actions

Script actions allow you to execute pytest-based scripts for browser automation.

```yaml
# Example: LinkedIn Search Script
- name: search-linkedin
  type: script
  script: search_script.py
  params:
    - name: query
      required: true
      type: string
      description: "LinkedIn search query"
  command: pytest ./tmp/myscript/search_script.py --query ${params.query}
  slowmo: 2500
```

### JSON-Based Actions

JSON-based actions (unlock-future type) use a JSON command structure for execution.

```yaml
# Example: JSON-based Google Search
- name: json
  type: unlock-future
  params:
    - name: query
      required: true
      type: string
      description: "Search query to execute"
  flow:
    - action: command
      url: "https://www.google.com"
      wait_for: "#APjFqb"
    - action: click
      selector: "#APjFqb"
    - action: fill_form
      selector: "#APjFqb"
      value: "${params.query}"
    - action: keyboard_press
      selector: "Enter"
```

## Usage

You can execute these actions by providing the action name followed by parameters:

```
phrase-search query="Personal AI Assistant"
search-linkedin query="AI developers"
json query="Python programming"
```

## Installation

Please refer to the installation guide for setup instructions.
