# Chrome/Edge 最新版対応: 新しいプロファイル指定方 法

## 背景

2024年5月以降のChrome/Edgeの最新バージョンでは、従来の `--user-data-dir` の指定方法では正常に動作しない場合があります。

## 問題の症状

- `DevToolsActivePort file doesn't exist`
- `Chrome failed to start: crashed`
- `V8 OOM (Out of Memory)`
- `TargetClosedError: Target page, context or browser has been closed`

## 新しい作法（2024年5月以降対応）

### 従来の方法（非推奨）
```bash
--user-data-dir="/Users/username/Library/Application Support/Google/Chrome"
--user-data-dir="/Users/username/Library/Application Support/Microsoft Edge"
```

### 新しい方法（推奨）
```bash
# Chrome/Edgeのユーザーデータディレクトリ内に新しいフォルダを作成
--user-data-dir="/Users/username/Library/Application Support/Google/Chrome/SeleniumProfile"
--user-data-dir="/Users/username/Library/Application Support/Microsoft Edge/SeleniumProfile"
```

## 実装方針

1. **プロファイルディレクトリの新しい構造**
   ```
   Chrome User Data/
   ├── Default/                 # 元のプロファイル
   ├── Profile 1/               # 追加プロファイル
   └── SeleniumProfile/         # 自動化用プロファイル
       └── Default/             # SeleniumProfile内のメインプロファイル
   ```

2. **重要なプロファイルデータのコピー**
   - 元の `Default` プロファイルから重要なファイルをコピー
   - 認証情報、クッキー、セッションデータなど
   - 拡張機能の設定（必要に応じて）

3. **プロファイル競合の回避**
   - 元のブラウザプロセスとの競合を避ける
   - 独立したプロファイルインスタンスの使用

## 重要な技術資料と対策

### 日本語技術記事からの重要な知見
Source: https://note.com/syogaku/n/nb0d442ed1d81

**2024年5月以降のChrome/Edge Automation対応:**
1. **プロファイル専用サブディレクトリの必須化**
   - メインの User Data ディレクトリを直接指定すると失敗
   - 必ずサブディレクトリ（例: SeleniumProfile）を作成して使用

2. **重要ファイルの手動コピーが必要**
   ```
   Default/Preferences → SeleniumProfile/Default/Preferences
   Default/Secure Preferences → SeleniumProfile/Default/Secure Preferences
   Default/Login Data → SeleniumProfile/Default/Login Data
   Default/Web Data → SeleniumProfile/Default/Web Data
   Default/Cookies → SeleniumProfile/Default/Cookies
   Local State → SeleniumProfile/Local State
   Default/Bookmarks → SeleniumProfile/Default/Bookmarks
   Default/History → SeleniumProfile/Default/History
   ```

3. **実行前の必須条件**
   - **すべてのブラウザプロセスを完全終了**
   - プロファイルのロック状態をクリア
   - 一時ファイルのクリーンアップ

4. **追加で必要な引数**
   ```bash
   --no-first-run
   --no-default-browser-check
   --disable-default-apps
   --disable-dev-shm-usage
   --disable-extensions-except
   --load-extension
   ```

### Microsoft 公式ドキュメントの要点
Source: https://learn.microsoft.com/ja-jp/deployedge/microsoft-edge-browser-policies/userdatadir

1. **UserDataDir ポリシーの制約**
   - データの損失やエラーを避けるために、ボリュームルートやシステムディレクトリは使用禁止
   - Microsoft Edge がコンテンツを管理するため、直接の書き込みは非推奨

2. **推奨されるディレクトリ構造**
   - 専用のサブディレクトリ使用
   - プロファイル競合の回避
   - 独立したインスタンス管理

## 参考資料

- **日本語技術記事**: https://note.com/syogaku/n/nb0d442ed1d81
- **Microsoft Edge ポリシー文書**: https://learn.microsoft.com/ja-jp/deployedge/microsoft-edge-browser-policies/userdatadir

## 実装状況

### ✅ 完了
- Chrome での新しい作法の実装と検証

### 🔄 進行中
- Edge での新しい作法の実装
- script_manager.py でのプロファイル作成ロジック更新

### ⏳ 予定
- 全ブラウザタイプでの統一対応
- プロファイル自動クリーンアップ機能
