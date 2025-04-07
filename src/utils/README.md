# Playwright Codegenモジュール

## 概要

このモジュールは、2Bykiltアプリケーション内でPlaywrightのcodegen機能を使用してブラウザ操作を記録し、Python形式でエクスポートする機能を提供します。Google ChromeとMicrosoft Edgeの両方のブラウザをサポートしています。

## 主な機能

- Google Chrome または Microsoft Edgeを使用したブラウザ操作の録画
- 録画したブラウザ操作をPythonスクリプトとして出力
- 生成されたスクリプトをアクションファイルとして保存

## 使用方法

1. 2Bykiltアプリケーションを起動
2. 「🎭 Playwright Codegen」タブを選択
3. 「ブラウザタイプ」で「Chrome」または「Edge」を選択
4. 「ウェブサイトURL」に録画を開始するURLを入力
5. 「▶️ Playwright Codegenを実行」ボタンをクリック
6. 選択したブラウザが起動し、Playwrightの録画インターフェースが表示される
7. 操作が完了したら、生成されたコードを確認
8. 必要に応じて「アクションとして保存」セクションでファイル名とアクション名を入力し、保存

## 環境設定

`.env`ファイルで以下の設定が可能です：

```
# Chrome設定
CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome
CHROME_USER_DATA=~/Library/Application Support/Google/Chrome

# Edge設定
EDGE_PATH=/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge
EDGE_USER_DATA=~/Library/Application Support/Microsoft Edge
```

設定しない場合は、アプリケーション起動時に自動検出を試みます。

## 注意事項

- Playwrightが最新バージョンであることを確認してください（`pip install -U playwright`）。
- 録画中は選択したブラウザの他のウィンドウやタブは操作しないでください。
