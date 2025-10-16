# CDP 動作確認手順書

## 📅 テスト日時: 2025年10月6日

## 🎯 テスト目的

Modern UI経由でCDP接続が正常に動作し、unlock-futureコマンド（`@nogtips-jsonpayload query=CDP`）が正常実行されることを検証する。

## ✅ 事前準備（完了済み）

- [x] 全てのChromeプロセスを終了
- [x] Modern UIサーバー起動（http://0.0.0.0:7860）

## 🔧 テスト手順（オプションA: 自動起動モード）

### ステップ1: ブラウザでUIを開く

1. ブラウザ（Safari推奨、またはFirefox）で以下のURLを開く:
   ```
   http://0.0.0.0:7860
   ```

2. **Run Agent** タブが表示されることを確認

### ステップ2: CDP設定を行う

1. **Runner Engine** ドロップダウンを見つける
   - 現在の値を確認（おそらく `playwright`）
   - `cdp` に変更

2. **🌐 Browser** アコーディオンをクリックして展開

3. 以下の設定を行う:
   - [ ] **Use existing browser profile**: **OFF**（チェックを外す）
   - [ ] **Keep browser open**: **ON**（チェックを入れる）
   - **Browser Type**: `chrome`（デフォルトのまま）

### ステップ3: unlock-futureコマンドを実行

1. **Task Description** フィールドに以下を入力:
   ```
   @nogtips-jsonpayload query=CDP
   ```

2. **▶️ Run Agent** ボタンをクリック

3. 実行開始を待つ（数秒）

### ステップ4: 動作確認

#### 4.1 Chromeの自動起動確認

- [ ] Chromeが自動的に起動する
- [ ] 新しいタブが開かれる
- [ ] `https://nogtips.wordpress.com/` に自動遷移する

#### 4.2 自動操作の確認

- [ ] Cookie同意ボタンが自動クリックされる
- [ ] 検索フォームが自動的にフォーカスされる
- [ ] "CDP" という文字が検索ボックスに入力される

#### 4.3 ブラウザの状態確認

実行完了後、Chromeで以下を確認:

1. `chrome://version` を新しいタブで開く
2. **コマンドライン** セクションを確認
3. 以下が含まれていることを確認:
   ```
   --remote-debugging-port=9222
   --user-data-dir=/var/folders/.../chrome_debug_cdp_XXXXX
   ```

### ステップ5: ターミナルログの確認

ターミナル（Modern UI起動中のウィンドウ）に戻り、以下のログパターンが出力されていることを確認:

#### ✅ 成功時のログパターン

```text
INFO [browser_debug_manager] 🔍 UIで選択されたブラウザタイプを使用: chrome
INFO [browser_debug_manager] 🔗 外部chromeプロセスに接続を試行
INFO [browser_debug_manager] 🔧 CDP用の一時user-data-dirを作成: /var/folders/.../chrome_debug_cdp_XXXXX
INFO [browser_debug_manager] 🚀 chromeプロセスを起動
INFO [browser_debug_manager] ✅ ポート9222でブラウザが実行中
INFO [browser_debug_manager] 🔗 CDP接続試行 1/3
INFO [browser_debug_manager] ✅ chromeプロセスへの接続成功
```

#### ❌ エラー時のログパターン（期待されない）

```text
ERROR [browser_debug_manager] ❌ ブラウザプロセス起動後もポート9222が利用できません
ERROR [browser_debug_manager] ❌ CDP接続が 3 回失敗しました
```

### ステップ6: 成果物の確認

1. `artifacts/runs/` ディレクトリを確認:
   ```bash
   ls -la artifacts/runs/
   ```

2. 最新の実行結果フォルダを開く:
   ```bash
   ls -la artifacts/runs/$(ls -t artifacts/runs/ | head -1)/
   ```

3. 以下のファイルが存在することを確認:
   - [ ] スクリーンショット（.png）
   - [ ] JSONコマンドファイル
   - [ ] Feature Flags解決結果（*-flags/feature_flags_resolved.json）

## 🔄 追加テスト: セッション再利用

### 目的

2回目のコマンド実行時に既存ブラウザが再利用されることを確認。

### 手順

1. Chromeを閉じずにそのまま開いたままにする

2. Modern UIで再度 **Task Description** に入力:
   ```
   @nogtips-jsonpayload query=Playwright
   ```

3. **▶️ Run Agent** をクリック

4. ターミナルログで以下を確認:
   ```text
   INFO [browser_debug_manager] ✅ 既存のCDPブラウザを再利用
   ```

5. 新しいChromeウィンドウが立ち上がらないことを確認

6. 既存のChromeで新しいタブが開かれ、自動操作が実行されることを確認

## 📊 テスト結果記録

### 基本動作テスト

| 項目 | 期待結果 | 実際の結果 | ステータス |
|------|---------|-----------|----------|
| Chrome自動起動 | CDP対応で起動 | | ⬜️ 未実施 |
| 一時プロファイル使用 | `chrome_debug_cdp_` プレフィックス | | ⬜️ 未実施 |
| CDP接続成功 | ✅ ログ出力 | | ⬜️ 未実施 |
| ページ遷移 | nogtips.wordpress.com | | ⬜️ 未実施 |
| 自動クリック | Cookie同意ボタン | | ⬜️ 未実施 |
| フォーム入力 | "CDP" 検索 | | ⬜️ 未実施 |
| スクリーンショット保存 | artifacts/runs/ | | ⬜️ 未実施 |

### セッション再利用テスト

| 項目 | 期待結果 | 実際の結果 | ステータス |
|------|---------|-----------|----------|
| 既存ブラウザ再利用 | 新規起動なし | | ⬜️ 未実施 |
| タブ作成 | 既存ウィンドウに新タブ | | ⬜️ 未実施 |
| 2回目の自動操作 | 正常実行 | | ⬜️ 未実施 |

## 🐛 トラブルシューティング

### 問題1: "Port 9222 not in use" エラー

**原因**: Chromeが起動しなかった

**対処**:
1. 全てのChromeを終了: `killall "Google Chrome"`
2. ターミナルでエラーメッセージを確認
3. 必要に応じて `browser_debug_manager.py` のログレベルを上げる

### 問題2: "既存のブラウザ セッションで開いています" メッセージ

**原因**: 個人プロファイルが既に使用中

**対処**:
1. `Use existing browser profile` が **OFF** になっていることを再確認
2. 全てのChromeを完全終了
3. 再度実行

### 問題3: 自動操作が実行されない

**原因**: CDP接続は成功したが、コマンド実行に失敗

**対処**:
1. `ExecutionDebugEngine` のログを確認
2. セレクタの有効性を確認（nogtips.wordpress.com の構造変更の可能性）
3. `slowmo` パラメータを増やして動作を遅くする

## 📝 次のステップ

テスト完了後、以下を実施:

1. テスト結果を記録
2. エラーがあれば原因を特定
3. browser-control モードのCDP対応に進む
4. script モードのCDP対応に進む
5. 統合テストとドキュメント最終化

## 📞 サポート

テスト中に問題が発生した場合:

1. ターミナルログ全体をコピー
2. `chrome://version` のコマンドライン情報をコピー
3. エラーメッセージをスクリーンショット
4. 上記をまとめて報告

---

**開始時刻**: __________  
**完了時刻**: __________  
**テスト実施者**: __________  
**総合評価**: ⬜️ 成功 / ⬜️ 部分成功 / ⬜️ 失敗
