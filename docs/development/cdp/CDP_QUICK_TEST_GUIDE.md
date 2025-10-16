# CDP 動作確認 - クイックガイド

## 🚀 現在の状態

✅ **Modern UI起動中**: http://0.0.0.0:7860  
✅ **Chromeプロセス終了済み**  
✅ **CDP接続ロジック実装完了**

## 📋 実施すべきテスト

### 1. unlock-future モードのCDP実行テスト（優先度: 🔴 最高）

#### 手順

1. ブラウザで http://0.0.0.0:7860 を開く
2. **Run Agent** タブを選択
3. 設定:
   - **Runner Engine**: `cdp`
   - **Use existing browser profile**: OFF
   - **Keep browser open**: ON
4. **Task Description**:
   ```
   @nogtips-jsonpayload query=CDP
   ```
5. **▶️ Run Agent** をクリック

#### 期待される動作

- Chromeが自動起動（`chrome_debug_cdp_` プロファイル）
- https://nogtips.wordpress.com/ に遷移
- Cookie同意ボタンをクリック
- 検索フォームに "CDP" を入力

#### 確認ポイント

```bash
# ターミナルで以下のログを確認:
tail -f logs/runner.log | grep "browser_debug_manager\|CDP\|chrome"
```

期待されるログ:
```
INFO [browser_debug_manager] 🔧 CDP用の一時user-data-dirを作成
INFO [browser_debug_manager] 🚀 chromeプロセスを起動
INFO [browser_debug_manager] ✅ ポート9222でブラウザが実行中
INFO [browser_debug_manager] ✅ chromeプロセスへの接続成功
```

### 2. browser-control モードのCDP実行テスト（優先度: 🟡 中）

#### 前提

browser-controlモードも内部的に`BrowserDebugManager`を使用しているため、理論上はCDP接続が可能。

#### 手順

1. `llms.txt` から browser-control タイプのアクションを選択（例: `click-jsonpayload`）
2. 同じCDP設定でコマンド実行:
   ```
   @click-jsonpayload selector=#example
   ```

#### 期待される動作

- unlock-futureと同様にCDP接続
- ただし、`use_own_browser`パラメータが正しく渡されるか要確認

### 3. script モードのCDP実行テスト（優先度: 🟢 低）

#### 前提

scriptモードはレガシー実装のため、CDP対応には追加の実装が必要な可能性あり。

#### 手順

1. `llms.txt` から script タイプのアクションを選択（例: `script-nogtips`）
2. 同じCDP設定でコマンド実行

## 🔍 デバッグコマンド

### CDP接続確認

```bash
# ポート9222が使用中かチェック
lsof -i :9222

# CDP バージョンエンドポイント確認
curl http://localhost:9222/json/version

# Chromeプロセス確認
ps aux | grep -i chrome | grep -i debug
```

### ログ確認

```bash
# リアルタイムログ監視
./scripts/monitor_cdp_test.sh

# または直接tail
tail -f logs/runner.log | grep --color -E "(browser_debug_manager|CDP|chrome|✅|❌)"
```

### 成果物確認

```bash
# 最新の実行結果を確認
ls -lth artifacts/runs/ | head -5

# スクリーンショット確認
find artifacts/runs -name "*.png" -mtime -1
```

## 🐛 よくある問題と解決策

### 問題: "Port 9222 not in use" エラー

**解決策**:
```bash
# 全てのChromeを終了
killall "Google Chrome"
# 2秒待機
sleep 2
# 再実行
```

### 問題: "既存のブラウザ セッションで開いています"

**解決策**:
- `Use existing browser profile` が OFF になっていることを再確認
- 個人プロファイルを使おうとしている可能性

### 問題: CDP接続成功後、自動操作が実行されない

**解決策**:
- セレクタが正しいか確認
- `slowmo` パラメータを増やす（1000 → 2000）
- `ExecutionDebugEngine` のログを確認

## 📊 テスト結果記録テンプレート

```markdown
## テスト実施日時: 2025-10-06 14:30

### unlock-future モード
- [ ] Chrome自動起動: ✅ / ❌
- [ ] CDP接続成功: ✅ / ❌
- [ ] 自動操作実行: ✅ / ❌
- [ ] スクリーンショット保存: ✅ / ❌
- エラーログ: ___________

### browser-control モード
- [ ] CDP接続: ✅ / ❌ / ⏭️ スキップ
- [ ] 自動操作: ✅ / ❌ / ⏭️ スキップ
- エラーログ: ___________

### script モード
- [ ] CDP接続: ✅ / ❌ / ⏭️ スキップ
- [ ] 自動操作: ✅ / ❌ / ⏭️ スキップ
- エラーログ: ___________

### 総合評価
- 成功: ____ / 失敗: ____ / スキップ: ____
- CDP MVP実装の完成度: ____%
```

## 🎯 次のアクション

### テスト成功時

1. ✅ テスト結果を記録
2. ✅ browser-control/script モードの動作確認
3. ✅ 統合テストスイート作成
4. ✅ チュートリアル最終化
5. ✅ PR作成

### テスト失敗時

1. ❌ エラーログ全文をコピー
2. ❌ `chrome://version` のコマンドライン確認
3. ❌ 問題の特定と修正
4. ❌ 再テスト

## 📝 重要な注意事項

1. **個人プロファイルは使用しない**
   - `Use existing browser profile` は必ず OFF
   - 一時プロファイルで動作確認

2. **Runner Engine ドロップダウンは表示専用（現時点）**
   - 実際の切り替えは `Use existing browser profile` で制御
   - Phase5+ で本来の機能を実装予定

3. **セッション再利用機能**
   - 2回目の実行時は既存ブラウザを再利用
   - `Keep browser open = ON` の時に有効

---

**ドキュメント**: `docs/CDP_TEST_PROCEDURE.md` に詳細手順あり  
**実装サマリー**: `docs/CDP_MVP_IMPLEMENTATION_SUMMARY.md` 参照  
**Feature Flag**: `docs/tutorial/CDP_FLAG_MAPPING.md` 参照
