# 2Bykilt 軽量版 (LLM-Free Edition)

**LLM依存を完全に排除した、ブラウザ自動化に特化した軽量版**

## 🎯 特徴

- **🪶 軽量**: LLM関連の依存関係を完全に排除
- **⚡ 高速**: AI処理のオーバーヘッドなし  
- **🔧 実用的**: 事前登録されたコマンドでブラウザ自動化
- **🎭 Codegen**: Playwright Codegenでスクリプト自動生成

## 📦 インストール

### 自動インストール (推奨)
```bash
./install-minimal.sh
```

### 手動インストール
```bash
# 仮想環境作成
python3 -m venv venv-minimal
source venv-minimal/bin/activate

# 依存関係インストール
pip install -r requirements-minimal.txt
playwright install
```

## 🚀 起動

```bash
source venv-minimal/bin/activate
ENABLE_LLM=false python bykilt.py --port 7789
```

ブラウザで http://127.0.0.1:7789 にアクセス

## 🛠️ 利用可能な機能

### ✅ 使える機能
- **ブラウザ自動化**: Playwrightベースの自動化
- **事前登録コマンド**: `@コマンド名` で実行
- **Playwright Codegen**: 操作記録からスクリプト生成
- **スクリプト実行**: シェルコマンド、Python実行
- **JSONアクション**: 構造化されたブラウザ操作

### ❌ 使えない機能  
- **自然言語処理**: LLMによる指示解釈
- **深層学習研究**: AI機能
- **動的プロンプト**: LLMベースの応答生成

## 📋 事前登録コマンド例

```bash
# LinkedIn検索
@search-linkedin query=python

# サイト内検索  
@phrase-search site=example.com query=tutorial

# ブラウザ操作の実行
@action-runner-nogtips action=click_button
```

## 🎭 Playwright Codegen使用法

1. **Playwright Codegen**タブを開く
2. URLを入力して「実行」
3. ブラウザで操作を記録
4. 生成されたスクリプトを保存

## 📁 ディレクトリ構造

```
2bykilt/
├── bykilt.py                 # メインアプリケーション
├── requirements-minimal.txt  # 軽量版依存関係
├── install-minimal.sh       # 自動インストール
├── llms.txt                 # 事前登録コマンド定義
└── src/                     # ソースコード
    ├── browser/             # ブラウザ自動化
    ├── config/              # 設定・評価器
    ├── utils/               # ユーティリティ
    └── script/              # スクリプト実行
```

## ⚙️ 設定

### 環境変数 (.env)
```bash
ENABLE_LLM=false
CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
CHROME_DEBUGGING_PORT=9222
```

### ブラウザ設定
- **ヘッドレスモード**: UI非表示で実行
- **既存ブラウザ使用**: デバッグモードで接続
- **セッション維持**: ブラウザウィンドウを保持

## 🔧 トラブルシューティング

### Chrome接続エラー
```bash
# Chromeをデバッグモードで起動
open -a "Chrome" --args --remote-debugging-port=9222
```

### 依存関係エラー
```bash
# 仮想環境を再作成
rm -rf venv-minimal
./install-minimal.sh
```

### ポート競合
```bash
# 別のポートで起動
python bykilt.py --port 8888
```

## 🆚 フル版との比較

| 機能 | 軽量版 | フル版 |
|------|--------|--------|
| ブラウザ自動化 | ✅ | ✅ |
| 事前登録コマンド | ✅ | ✅ |
| Playwright Codegen | ✅ | ✅ |
| 自然言語処理 | ❌ | ✅ |
| LLM統合 | ❌ | ✅ |
| インストールサイズ | ~100MB | ~2GB |
| 起動時間 | ~3秒 | ~15秒 |

## 🤝 コントリビューション

軽量版の改善や新機能の提案は、GitHubのIssueまでお願いします。

## 📄 ライセンス

MIT License

---

**2Bykilt軽量版** - シンプル、高速、実用的なブラウザ自動化ツール
