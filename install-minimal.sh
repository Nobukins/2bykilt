#!/bin/bash

# 2Bykilt 軽量版インストールスクリプト
# LLM機能なしでブラウザ自動化のみを提供

echo "🚀 2Bykilt 軽量版インストールを開始します..."

# Python仮想環境の作成
echo "📦 Python仮想環境を作成しています..."
python3 -m venv venv-minimal
source venv-minimal/bin/activate

# 依存関係のインストール
echo "📥 軽量版依存関係をインストールしています..."
pip install --upgrade pip
pip install -r requirements-minimal.txt

# Playwrightブラウザのインストール
echo "🌐 Playwrightブラウザをインストールしています..."
playwright install

# 環境変数設定
echo "⚙️ 環境変数を設定しています..."
echo "ENABLE_LLM=false" > .env.minimal
echo "CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" >> .env.minimal
echo "CHROME_DEBUGGING_PORT=9222" >> .env.minimal

echo "✅ 軽量版インストールが完了しました！"
echo ""
echo "🚀 起動方法:"
echo "  source venv-minimal/bin/activate"
echo "  ENABLE_LLM=false python bykilt.py --port 7789"
echo ""
echo "🌐 ブラウザでアクセス: http://127.0.0.1:7789"
echo ""
echo "📖 利用可能な機能:"
echo "  - ブラウザ自動化 (Playwright)"
echo "  - 事前登録コマンド実行"
echo "  - Playwright Codegen"
echo "  - スクリプト実行"
echo "  - JSON形式のアクション"
echo ""
echo "⚠️ 注意: LLM機能は無効化されています"
