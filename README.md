<img src="./assets/bykilt.png" alt="Bykilt - Browser Use Web UI" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/browser-use/web-ui?style=social)](https://github.com/browser-use/web-ui/stargazers)
[![Discord](https://img.shields.io/discord/1303749220842340412?color=7289DA&label=Discord&logo=discord&logoColor=white)](https://link.browser-use.com/discord)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.browser-use.com)
[![WarmShao](https://img.shields.io/twitter/follow/warmshao?style=social)](https://x.com/warmshao)

This project builds upon the foundation of the [browser-use](https://github.com/browser-use/browser-use), which is designed to make websites accessible for AI agents.

We would like to officially thank [WarmShao](https://github.com/warmshao) for his contribution to this project.

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
source .venv/bin/activate
```

#### Step 3: Install Dependencies
Install Python packages:
```bash
pip install -r requirements.txt
pip install requests pyyaml pytest pytest-playwright 
```

Install Playwright:
```bash
playwright install
```

#### Step 4: Configure Environment
1. Create a copy of the example environment file:
- Windows (Command Prompt):
```bash
copy .env.example .env
```
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

#### Usage / debug_bykilt.py の使用方法
Run the debug tool by providing a JSON file containing LLM response data:

このツールを使用すると、JSONファイルを使ってLLMからのレスポンスをシミュレートし、Playwrightを使ってブラウザ操作を直接実行できます。

```bash
python debug_bykilt.py <llm_response_file>
```

2. サンプルJSONファイルをテストします：
```bash
python debug_bykilt.py external/samples/navigate_url.json
```
```bash
python debug_bykilt.py external/samples/search_word.json
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
- [x] **2025/03/06:** Thanks @Nobukins, you made magic comes true, Bykilt!
- [x] **2025/01/26:** Thanks to @vvincent1234. Now browser-use-webui can combine with DeepSeek-r1 to engage in deep thinking!
- [x] **2025/01/10:** Thanks to @casistack. Now we have Docker Setup option and also Support keep browser open between tasks.[Video tutorial demo](https://github.com/browser-use/web-ui/issues/1#issuecomment-2582511750).
- [x] **2025/01/06:** Thanks to @richard-devbot. A New and Well-Designed WebUI is released. [Video tutorial demo](https://github.com/warmshao/browser-use-webui/issues/1#issuecomment-2573393113).
