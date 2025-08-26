# LLM機能のオプション化について

## 概要

2bykiltはLLM機能を完全にオプション化し、軽量なブラウザ自動化ツールとしても利用できるようになりました。

## インストールオプション

### 🔧 軽量インストール（推奨）
```bash
# 基本パッケージのみインストール
pip install -r requirements-minimal.txt
playwright install

# LLM機能を無効化して起動
export ENABLE_LLM=false
python bykilt.py
```

### 🧙‍♂️ フル機能インストール
```bash
# 全パッケージインストール
pip install -r requirements.txt
playwright install

# LLM機能を有効化して起動
export ENABLE_LLM=true
python bykilt.py
```

## 機能比較

| 機能 | 軽量モード | フルモード |
|------|------------|------------|
| ブラウザ自動化 | ✅ | ✅ |
| Playwright Codegen | ✅ | ✅ |
| スクリプト実行 | ✅ | ✅ |
| JSON形式のアクション実行 | ✅ | ✅ |
| 自然言語による指示 | ❌ | ✅ |
| LLMプロバイダー連携 | ❌ | ✅ |
| 高度なAI機能 | ❌ | ✅ |

## 環境変数

| 変数名 | 値 | 説明 |
|--------|-----|------|
| ENABLE_LLM | false | LLM機能を無効化（軽量モード） |
| ENABLE_LLM | true | LLM機能を有効化（フルモード） |

## セキュリティ調査対応

軽量モードでは以下のLLM関連パッケージが除外され、セキュリティ調査の対象から除外されます：

- langchain-*
- anthropic
- openai
- google-generativeai
- fireworks-ai
- ollama
- browser-use（LLM依存部分）

## テスト

```bash
# 軽量モードのテスト
./test_minimal_mode.sh

# 軽量版パッケージをインストールしてテスト
./test_minimal_mode.sh --install-minimal
```
