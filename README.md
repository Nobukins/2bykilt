<img src="./assets/2bykilt-ai.png" alt="2Bykilt - 業務効率化魔法「2bykilt」" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/Nobukins/2bykilt?style=social)](https://github.com/Nobukins/2bykilt/stargazers)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/Nobukins/2bykilt)

# 💫 2bykilt - 伝説の業務効率化の魔法

# スクリプト実行の基本

myscriptを使用した基本的な実行例：

## ⚙️ スクリプト実行環境の準備（myscript）

```bash
# 環境変数を設定
export RECORDING_PATH="./artifacts/my-task"

# スクリプトを実行
python myscript/bin/my_script.py --target https://example.com
```

### RECORDING_PATH 設定ガイド

#### 優先順位と競合解消
2bykiltでは、録画ファイルの保存先を以下の優先順位で決定します：

1. **UI設定 (Browser Settings)**: 実行時のUIで指定されたパス（最も優先）
2. **環境変数 RECORDING_PATH**: シェルで設定されたパス
3. **デフォルトパス**: `./record_videos`（上記いずれも未設定時）

#### 設定例
```bash
# 環境変数のみ設定
export RECORDING_PATH="./artifacts/my-session"
python myscript/bin/script.py

# UI設定が優先される場合
# UIのBrowser Settingsで "./custom/path" を指定すると環境変数より優先
```

#### 注意点
- UI設定が空欄の場合のみ環境変数が使用されます
- 実行ログに最終採用パスが `recording_path_resolved` イベントとして記録されます
- パスが存在しない場合は自動作成されます

### 実践的な使用例

#### 1. 検索スクリプトの実行

```bash
# 環境変数を設定
export RECORDING_PATH="./artifacts/search-demo"

# pytestで検索スクリプトを実行
cd myscript
pytest search_script.py --query "業務効率化ツール" --browser-type chrome
```

#### 2. アクションランナーの使用

```bash
# RECORDING_PATHを設定
export RECORDING_PATH="./artifacts/action-demo"

# アクションランナーを実行
python myscript/action_runner.py --action login --url https://example.com
```

#### 3. アーティファクト収集の確認

実行後に生成されるファイル構造：

```
artifacts/
  search-demo/
    Tab-01-recording.webm      # 録画ファイル
    Tab-02-screenshot.png      # スクリーンショット
    tab_index_manifest.json    # マニフェストファイル
    logs/
      action_runner_debug.log  # 実行ログ
```

### 高度な使用例

#### プロファイルを使用した実行

```bash
# Chromeプロファイルを指定
export RECORDING_PATH="./artifacts/profile-demo"
export CHROME_USER_DATA="/Users/username/Library/Application Support/Google/Chrome"

# プロファイルを使用して実行
cd myscript
pytest search_script.py --query "test" --use-profile --browser-type chrome
```

#### 複数タスクのバッチ実行

```bash
# 異なるタスクごとにRECORDING_PATHを設定
export RECORDING_PATH="./artifacts/batch-task-1"
python myscript/bin/task1.py

export RECORDING_PATH="./artifacts/batch-task-2"
python myscript/bin/task2.py
```

## ⚙️ スクリプト実行の基本

業務の冒険者たちよ、もはや複雑な作業に時間を費やす必要はない。**2bykilt**（ツーバイキルト）は、あなたの日々の作業を自動化する伝説の魔法道具だ。ブラウザ操作を簡単に録画し、再生し、共有できる。まるで伝説の魔法書のように。

詳しいドキュメントの一覧は docs/DOCS_INDEX.md を参照してください。

## 🚀 クイックスタート

### 🪟 Windows環境セットアップ
Windows 10/11での推奨インストール手順：

```powershell
# 1. Python 3.12+インストール確認
python --version

# 2. プロジェクトクローン
git clone https://github.com/Nobukins/2bykilt.git
cd 2bykilt

# 3. 仮想環境作成・有効化
python -m venv .venv
.venv\Scripts\activate

# 4. 軽量インストール（推奨）
pip install -r requirements-minimal.txt
playwright install chromium

# 5. 起動
$env:ENABLE_LLM = "false"
python bykilt.py

# 詳細なWindows設定: WINDOWS_SETUP_GUIDE.md を参照
```

### 🔧 軽量インストール（推奨）
LLM機能なしでブラウザ自動化のみを利用：

```bash
# 基本パッケージのインストール
pip install -r requirements-minimal.txt

# Playwrightブラウザのインストール
playwright install

# LLM機能を無効化して起動
export ENABLE_LLM=false
python bykilt.py
```

### 🧙‍♂️ フル機能インストール
LLM機能も含めた全機能を利用：

```bash
# 全パッケージのインストール
pip install -r requirements.txt

# Playwrightブラウザのインストール
playwright install

# LLM機能を有効化して起動
export ENABLE_LLM=true
python bykilt.py
```

### 🖥️ CLI起動オプション

UIを起動するためのCLI呼び出しは以下のいずれの形式でも利用できます。既存のIP/PORTやテーマのオプションと組み合わせ可能です。

- `python bykilt.py`（デフォルト動作）
- `python bykilt.py --ui`
- `python bykilt.py ui`

例: `python bykilt.py --ui --ip 0.0.0.0 --port 8080 --theme Glass`

## ✨ 2bykiltの魔法の力

### 🎮 ブラウザ操作を魔法として記録・再生

**「その動きを記録せよ。何度でも再現できる魔法となる」**

- **魔法の記録器**：`playwright codegen <URL>` で操作を記録するだけ
- **魔法の再現**：記録した操作を何度でも同じように実行
- **魔法の共有**：チーム全体で使える魔法として保存・共有

### 📜 コード知識不要の魔術

**「魔法の呪文を理解せずとも、その力を使うことができる」**

- ブラウザでの操作を記録するだけで自動化の魔法が完成
- プログラミングを知らなくても使える直感的なインターフェース
- コピー&ペーストだけで魔法のスクリプトを登録可能

### 🧙‍♂️ 最後の砦としてのAI魔導士（オプション）

**「迷った時は、魔導士に相談せよ。道を示してくれるだろう」**

- 定型作業は自動化スクリプトで処理（LLM不要）
- 複雑な判断が必要な場合はLLM（魔導士）が対応（オプション機能）
- 人間とAIの最適な協力関係を実現

### � 並行実行制御の魔法（Phase2-01）

**「複数の魔法を同時に唱え、時間を効率的に操れ」**

- **並行実行制御**: 設定可能な同時実行数で複数のタスクを効率的に処理
- **優先順位付け**: 重要な魔法を優先的に実行する賢い制御システム
- **状態追跡**: 実行中の魔法の状態をリアルタイムで監視・記録
- **自動負荷分散**: システムリソースを最適に活用する賢い配分

#### 並行実行制御の基本魔法

```python
from src.runner.queue_manager import get_queue_manager

# 魔法の実行制御装置を取得
manager = get_queue_manager(max_concurrency=3)

# 魔法を登録（優先順位付き）
manager.enqueue("urgent-task", "緊急の業務処理", priority=5)
manager.enqueue("normal-task", "通常の業務処理", priority=3)
manager.enqueue("batch-task", "バッチ処理", priority=1)

# 魔法の実行を開始
await manager.execute_next()
```

#### 実行状態の監視魔法

```python
# 現在の実行状態を確認
status = manager.get_queue_status()
print(f"実行中: {status['running_count']}")
print(f"待機中: {status['queue_length']}")
print(f"完了済: {status['completed_count']}")

# 統計情報を取得
stats = manager.get_queue_stats()
print(f"平均待ち時間: {stats['avg_wait_time']:.2f}秒")
```

## 🧙‍♂️ データ抽出の秘術

### 知識の収集術

```
# 「データ抽出」タブを開き、情報を集めたいページのURLを入力
https://example.com
```

魔術師はシンプルな呪文と高度な呪文、二つの方法で知識を集められます：

### シンプルな抽出術

基本の魔法陣（セレクター）を使って必要な情報を素早く集めます：

```
h1, .main-content, #title, .price
```

### 高度な抽出術

複雑な情報を集める場合は、詳細な魔法陣（JSON形式）を使います：

```json
{
  "書名": {"selector": "h1.book-title", "type": "text"},
  "著者": {"selector": ".author", "type": "inner_text"},
  "表紙画像": {"selector": ".cover img", "type": "attribute", "attribute": "src"},
  "内容紹介": {"selector": ".description", "type": "html"}
}
```

### 抽出魔法の種類

- **text**: 生の文字情報を取り出す基本魔法
- **inner_text**: 表示されたままの形で文字を写し取る魔法
- **html**: 構造そのものを含めて情報を複写する魔法
- **attribute**: 特定の属性（src、href、alt）のみを取り出す魔法
- **count**: 要素の数を数え上げる計数魔法

### 知識の保存法

集めた知識は「秘伝書」として保存できます：

1. 「保存形式」で知識の記録方法を選択（json または csv）
2. 必要であれば「保存先ファイルパス」を指定
3. 「データを保存」の魔法で知識を結晶化

## 🏺 抽出された知識の活用例

### 商品情報の収集

```json
{
  "商品名": {"selector": "h1.product-title", "type": "text"},
  "価格": {"selector": ".price", "type": "inner_text"},
  "評価": {"selector": ".rating", "type": "text"},
  "在庫数": {"selector": ".stock-count", "type": "inner_text"}
}
```

### ニュース記事の要約作成

```json
{
  "見出し": {"selector": "h1.headline", "type": "text"},
  "著者": {"selector": ".author-name", "type": "text"},
  "発行日": {"selector": ".publish-date", "type": "text"},
  "本文": {"selector": ".article-content p", "type": "inner_text"}
}
```

## 🪄 魔法の使い方

### 魔法の記録法

```bash
# この呪文で魔法の記録が始まる
playwright codegen https://example.com
```

この呪文を唱えると、ブラウザ操作の記録が始まります。あなたがブラウザで行うすべての操作が魔法のスクリプトとして記録されます。

### 魔法の登録法

記録した魔法は、2bykiltに簡単に登録できます：

1. 記録された魔法のコードをコピー
2. 2bykiltの「新しい魔法を登録」ボタンをクリック
3. 名前とパラメータを設定して保存

### 魔法の呼び出し法

登録した魔法は、シンプルなコマンドで呼び出せます：

```
@魔法の名前 パラメータ1=値1 パラメータ2=値2
```

例えば：
```
@google-search query=業務効率化ツール
@login-system username=brave_warrior password=dragon_slayer
```

## 🛡️ 魔法装備の準備（インストール方法）

### 必要な道具
- Python 3.11以上
- Git (魔法書の複製用)

### 魔法の書を入手

```bash
git clone https://github.com/Nobukins/2bykilt.git
cd bykilt
```

### 魔法陣の作成

```bash
python3.12 -m venv venv
source ./venv/bin/activate  # macOS/Linux
```

### 魔法の素材を集める

```bash
pip install -r requirements.txt
playwright install
```

### 魔法の設定

```bash
cp .env.example .env
# .envファイルを編集して設定を行う
```

## 📖 実際の魔法の例

### Googleでの情報収集の魔法

```yaml
- name: google-search
  type: action_runner_template
  params:
    - name: query
      required: true
      type: string
      description: "検索したいキーワード"
  code: |
    async def run(page, params):
        # Playwrightで記録したコードがそのまま使える！
        await page.goto('https://www.google.com')
        await page.fill('input[name="q"]', params['query'])
        await page.press('input[name="q"]', 'Enter')
        await page.wait_for_load_state('networkidle')
        return {"status": "success", "message": "検索完了"}
```

### 業務システムへのログイン魔法

```yaml
- name: system-login
  type: action_runner_template
  params:
    - name: username
      required: true
    - name: password
      required: true
  code: |
    async def run(page, params):
        await page.goto('https://your-company-system.com/login')
        await page.fill('#username', params['username'])
        await page.fill('#password', params['password'])
        await page.click('button[type="submit"]')
        await page.wait_for_navigation()
        return {"status": "success"}
```

## ⚙️ スクリプト実行環境の準備（myscript）

### myscript ディレクトリの役割

**「魔法の実行を支える堅牢な基盤を整えよ」**

2bykiltでは、ブラウザ自動化スクリプトを `myscript/` ディレクトリで一元管理しています。このディレクトリは以下の役割を担います：

- **実行スクリプトの格納**: `myscript/bin/` に実行可能なスクリプトを配置
- **テンプレート管理**: `myscript/templates/` にスクリプトテンプレートを保管
- **ヘルパーモジュール**: `myscript/helpers/` に再利用可能な機能を配置

### 環境変数の設定

スクリプト実行には以下の環境変数を設定する必要があります：

```bash
# 録画・生成物の出力先ディレクトリ（必須）
export RECORDING_PATH="./artifacts"

# スクリプトの基点ディレクトリ（オプション）
export BASE_DIR="$(pwd)"
```

### 出力先の構成

生成物は以下のルールに従って配置されます：

```
artifacts/
  <task>/                    # タスクごとのディレクトリ
    Tab-XX-<name>.webm       # 録画ファイル（XXは2桁ゼロ詰め）
    tab_index_manifest.json  # マニフェストファイル
    logs/                    # ログファイル
```

### スクリプト実行の基本

myscriptを使用した基本的な実行例：

```bash
# 環境変数を設定
export RECORDING_PATH="./artifacts/my-task"

# スクリプトを実行
python myscript/bin/my_script.py --target https://example.com
```

## 💎 ビジネスでの魔法の使い方

### 🏢 経理部門の英雄

**「毎日のデータ入力という試練を、魔法で乗り越えよ」**

- 会計システムへの自動ログイン
- 請求書データの自動抽出と入力
- レポート作成の自動化

### 📊 営業部門の勇者

**「見込み客を探す旅は、魔法の力で効率化できる」**

- LinkedInでの見込み客自動検索
- CRMシステムへのデータ自動登録
- フォローアップメールの自動送信

### 🔍 マーケティング部門の賢者

**「市場調査という迷宮も、魔法があれば道は開ける」**

- 競合サイト情報の自動収集
- SNSのトレンド分析の自動化
- キーワードリサーチの効率化

## 🧪 魔法の研究室（デバッグツール）

魔法がうまく機能しない時のための研究室も完備：

```bash
python debug_bykilt2.py external/samples/search_word.json
```

## 🛠️ 魔法の修復術（最新のアップデート）

### ⚡ 魔法書の安定化呪文

**「混沌に秩序をもたらし、魔法の力を確実なものとせよ」**

最新のアップデートで、2bykiltの魔法書がより安定し、確実に動作するようになりました！

#### 🚨 重要な修復作業完了

**「古き呪文の不調を正し、新たな力を手に入れた」**

- **TypeError退治**: `argument of type 'bool' is not iterable` という邪悪なバグを完全に退治
- **魔法陣の最適化**: 問題を起こしていた複雑な魔法陣（gr.File, gr.Gallery, gr.Video）をシンプルで確実な魔法陣（gr.Textbox）に改良
- **Python 3.12対応**: 最新の魔法環境でも安定動作を実現
- **HTTP 200の証**: サーバーが正常に動作することを確認済み

#### 🧹 魔法の書庫整理

**「不要な巻物を整理し、真に必要な知識のみを残した」**

魔法の書庫から以下の古い巻物を整理しました：
- `bykilt_simplified.py` - 簡易版の試験的巻物
- `test_*.py` - 実験用の一時的な巻物群
- `debug_bykilt.py` - 旧式のデバッグ用巻物

新たに `debug_bykilt2.py` という強力なデバッグツールを作成し、すべての診断機能を統合しました。

#### 🔮 診断魔法の強化

**「魔法が思うように動かない時、その原因を即座に見抜く力を得た」**

```bash
# 魔法の不調を診断する呪文
python debug_bykilt2.py external/samples/search_word.json
```

この新しい診断ツールは：
- ブラウザの状態を詳細に分析
- 環境設定の問題を即座に特定
- 依存関係の不整合を自動検出
- モジュール化された診断機能で再利用可能

#### 📜 賢者の知恵書

**「同じ困難に再び出会った時、迷うことなく解決の道を歩めるように」**

今回の修復作業で得られた知恵を、後世の魔術師たちのために記録しました：

- `FIX_SUMMARY.md` - 技術的な修復の詳細記録
- `CLEANUP_REPORT.md` - 書庫整理の理由と影響
- `LLM_AS_OPTION.prompt.md` - 効率的な問題解決の呪文集（20-30分で解決）

#### ✨ 魔法使いへのメッセージ

**「さらに安定し、確実になった2bykiltで、あなたの業務効率化の冒険を続けてください」**

この修復により：
- 🛡️ より堅牢で信頼できる魔法書に進化
- ⚡ 最小環境でも軽快に動作
- 🎯 すべてのコア機能が正常動作
- 📚 将来の問題解決手順も完備

**「さあ、新たに生まれ変わった2bykiltと共に、業務効率化の冒険を再開しよう！」**

---

<details>
<summary>上級者向け魔法の書（詳細設定）</summary>

## 🔮 上級者向け魔法

### カスタムブラウザの使用

普段使っているブラウザで魔法を使いたい時：

```env
CHROME_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
CHROME_USER_DATA="/Users/YourUsername/Library/Application Support/Google/Chrome"
```

### 魔法の種類

2bykiltでは様々な種類の魔法をサポートしています：

- **browser-control**: ブラウザ操作の基本魔法
- **script**: Pythonスクリプトを実行する上級魔法
- **action_runner_template**: Playwrightコードを直接使う究極魔法
- **unlock-future**: JSON形式で魔法を記述する特殊魔法

### LLM魔導士の選択

お好みのLLM魔導士を選んで協力を仰ぐことができます：

- OpenAI (GPT-4)
- Google (Gemini)
- Anthropic (Claude)
- DeepSeek
- Ollama (ローカルモデル)

</details>

## 🧪 テスト実行

### CSVバッチ処理機能のテスト

CSVバッチ処理機能の包括的なテストを実行するには、以下のコマンドを使用してください：

```bash
# 全バッチ処理統合テストを実行
python -m pytest tests/batch/test_batch_cli_integration.py -v

# 特定のテストを実行
python -m pytest tests/batch/test_batch_cli_integration.py::TestBatchCLIIntegration::test_batch_start_command_creates_batch_from_csv -v

# CSV入力正規化テストを実行
python -m pytest tests/batch/test_csv_normalization.py -v
```

#### テスト対象機能

**CLIコマンドテスト:**

- `python bykilt.py batch start <csv_file>` - CSVファイルからバッチを作成
- `python bykilt.py batch status <batch_id>` - バッチステータスを表示
- `python bykilt.py batch update-job <job_id> <status>` - ジョブステータスを更新

**CSV入力正規化テスト:**

- NamedStringオブジェクト（Gradioファイルアップロード）のサポート
- ファイルライクオブジェクトの処理
- パス文字列の処理
- エラーハンドリング

#### テスト実行例

```bash
# バッチ作成テスト
python -m pytest tests/batch/test_batch_cli_integration.py::TestBatchCLIIntegration::test_batch_start_command_creates_batch_from_csv -v
# → CSVファイルからのバッチ作成機能を評価

# バッチステータス表示テスト
python -m pytest tests/batch/test_batch_cli_integration.py::TestBatchCLIIntegration::test_batch_status_command_shows_batch_details -v
# → バッチとジョブ情報の表示機能を評価

# ジョブ更新テスト
python -m pytest tests/batch/test_batch_cli_integration.py::TestBatchCLIIntegration::test_batch_update_job_command_updates_status -v
# → ジョブステータス更新機能を評価

# NamedStringサポートテスト
python -m pytest tests/batch/test_batch_cli_integration.py::TestCSVInputNormalizationIntegration::test_csv_normalization_with_named_string_mock -v
# → Gradio NamedStringオブジェクトの正規化機能を評価
```

### 全テスト実行

プロジェクト全体のテストを実行するには：

```bash
# 全テスト実行
python -m pytest

# 特定のテストスイート実行
python -m pytest tests/batch/ -v
```

## 🧪 テストガイド (Test Guide)

テスト実行とスキップポリシーの最新情報は `docs/test-execution-guide.md` に集約しました。

クイックリンク:
- 全体: docs/test-execution-guide.md
- 目的別: 
  - フル実行: `pytest -q`
  - スキップ理由一覧: `pytest -rs -q`
  - バッチエンジンのみ: `pytest tests/test_batch_engine.py -v`

現在のスキップ分類 (106 → 31 に削減 済):
- LLM依存 (ENABLE_LLM=false 時 1件)
- local_only (重い/最終検証向け)
- integration (環境依存/ブラウザ)
- git_script_integration (Resolverリファクタ待ち 8件)

環境フラグ:
```
ENABLE_LLM=true                 # LLMテストを有効化
RUN_LOCAL_INTEGRATION=1         # integrationを実行
RUN_LOCAL_FINAL_VERIFICATION=1  # final verification (local_only) 実行
```

クリーンアップ:
```
./scripts/clean_test_artifacts.sh          # 生成アーティファクト最小クリア
./scripts/clean_test_logs.sh --dry-run     # ログ/カバレッジ/キャッシュ確認
./scripts/clean_test_logs.sh               # 実行
```

詳細な手順・将来のマーカー設計(#81)はガイド参照。
