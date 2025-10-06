#!/bin/bash
# CDP動作確認用のリアルタイムログ監視スクリプト

echo "🔍 CDP動作確認ログモニター開始"
echo "================================"
echo ""
echo "✅ チェックポイント:"
echo "  1. 🔧 一時user-data-dir作成"
echo "  2. 🚀 chromeプロセス起動"
echo "  3. ✅ ポート9222でブラウザ実行中"
echo "  4. 🔗 CDP接続試行"
echo "  5. ✅ chromeプロセスへの接続成功"
echo ""
echo "ログを監視中... (Ctrl+C で終了)"
echo "================================"
echo ""

# ログファイルが存在する場合
if [ -f "logs/runner.log" ]; then
    tail -f logs/runner.log | grep --line-buffered -E "(browser_debug_manager|CDP|chrome|接続|user-data-dir|ポート|9222)" | while read line; do
        # 成功メッセージを緑色で表示
        if echo "$line" | grep -q "✅"; then
            echo -e "\033[0;32m$line\033[0m"
        # エラーメッセージを赤色で表示
        elif echo "$line" | grep -q "❌\|ERROR"; then
            echo -e "\033[0;31m$line\033[0m"
        # 警告を黄色で表示
        elif echo "$line" | grep -q "⚠️\|WARNING"; then
            echo -e "\033[0;33m$line\033[0m"
        # その他の情報
        else
            echo "$line"
        fi
    done
else
    echo "⚠️ logs/runner.log が見つかりません"
    echo "Modern UIを起動してからこのスクリプトを実行してください"
fi
