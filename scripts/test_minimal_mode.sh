#!/bin/bash

# 2bykilt LLM機能オプション化テストスクリプト

echo "🧪 2bykilt LLM機能オプション化テスト"
echo "=================================="

echo ""
echo "📋 テスト1: LLM機能無効でのアプリケーション起動テスト"
echo "ENABLE_LLM=false を設定して起動..."

# 環境変数を設定
export ENABLE_LLM=false

# 軽量版requirements.txtのインストール（オプション）
if [ "$1" = "--install-minimal" ]; then
    echo "📦 軽量版パッケージをインストール中..."
    pip install -r requirements-minimal.txt
    echo "✅ 軽量版パッケージのインストール完了"
fi

echo ""
echo "🧪 事前登録コマンドの動作テスト"
echo "Testing standalone prompt evaluation..."
python -c "
from src.config.standalone_prompt_evaluator import pre_evaluate_prompt_standalone, extract_params_standalone
prompt = '@search-linkedin query=test'
result = pre_evaluate_prompt_standalone(prompt)
print(f'✅ Command evaluation result: {result is not None}')
if result:
    params = extract_params_standalone(prompt, result.get('params', ''))
    print(f'✅ Parameter extraction: {params}')
"

echo ""
echo "🌐 アプリケーションを起動しています..."
echo "以下のことを確認してください："
echo "1. ✅ アプリケーションが正常に起動すること"
echo "2. ✅ LLM Configurationタブで「LLM機能が無効化されています」と表示されること"
echo "3. ✅ Run Agentタブで「ブラウザ自動化モード」と表示されること"
echo "4. ✅ URLの直接入力（例: https://www.google.com）が動作すること"
echo "5. ✅ 事前登録コマンド（例: @search-linkedin query=test）が動作すること"
echo "6. ✅ Playwright Codegenが利用可能であること"

echo ""
echo "🚀 アプリケーション起動中... (Ctrl+Cで停止)"
echo "ブラウザで http://127.0.0.1:7788 にアクセスしてください"

# Python アプリケーションを起動
python bykilt.py --theme Ocean
