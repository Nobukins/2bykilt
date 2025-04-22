<img src="./assets/2bykilt-ai.png" alt="2Bykilt - 業務効率化魔法「2bykilt」" width="full"/>

<br/>

[![GitHub stars](https://img.shields.io/github/stars/Nobukins/2bykilt?style=social)](https://github.com/Nobukins/2bykilt/stargazers)
[![Documentation](https://img.shields.io/badge/Documentation-📕-blue)](https://docs.browser-use.com)

# 💫 2bykilt - 伝説の業務効率化の魔法

**「呪文を唱えよ。さすれば扉は開かれん」**

業務の冒険者たちよ、もはや複雑な作業に時間を費やす必要はない。**2bykilt**（ツーバイキルト）は、あなたの日々の作業を自動化する伝説の魔法道具だ。ブラウザ操作を簡単に録画し、再生し、共有できる。まるで伝説の魔法書のように。

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

### 🧙‍♂️ 最後の砦としてのAI魔導士

**「迷った時は、魔導士に相談せよ。道を示してくれるだろう」**

- 定型作業は自動化スクリプトで処理
- 複雑な判断が必要な場合はLLM（魔導士）が対応
- 人間とAIの最適な協力関係を実現

### 🔮 魔法の書からの知識抽出

**「賢者は必要な知識のみを集め、混沌から秩序を生み出す」**

- **魔法の目**: ウェブ上の情報を正確に見定め抽出
- **知識の結晶化**: 集めた情報を整理して保存
- **魔術の応用**: 抽出データを様々な形式で再利用

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
python debug_bykilt.py external/samples/search_word.json
```

## 🌟 2bykiltを使う3つの理由

1. **魔法の習得が容易** - 特別な知識不要で、今日から使える
2. **魔法の再現性が高い** - 一度作った魔法は何度でも同じように動作
3. **魔法の応用が無限** - あらゆる業務に適用可能

## 🏹 魔法の旅を始めよう

```bash
python bykilt.py
```

そしてブラウザで `http://127.0.0.1:7788` にアクセス。

**「さあ、業務効率化の冒険に出発だ！」**

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
