# スクリーンショット & DOM 抽出デモ (Issue #34)

## 🎯 ゴール

- Playwright ベースの自動化フローでスクリーンショットと DOM テキスト/HTML を同時に保存する。
- `ArtifactManager` による `artifacts/runs/<run_id>-art/` へのアーティファクト出力を確認する。
- `llms.txt` に登録された `demo-artifact-capture` スクリプトをワンクリックで再生できるようにする。

Issue #34 で導入された非同期キャプチャ API (`async_capture_page_screenshot` / `async_capture_element_value`) とブラウザ制御フローの統合を体験するガイドです。

## 📋 前提条件

1. Python 3.11 以上
1. 依存パッケージと Playwright をセットアップ済み

    ```bash
    pip install -r requirements-minimal.txt
    playwright install
    ```

1. ルートディレクトリで作業していること（例: `2bykilt/`）。

> 💡 `RunContext` が実行ごとに `artifacts/runs/<run_id>-art/` を自動作成し、各種キャプチャを整理します。

## 🛠️ 新規スクリプトの概要

`myscript/bin/demo_artifact_capture.py` が新しく追加されました。主なポイントは以下の通りです。

- `async_playwright` を使った非同期フロー。
- `async_capture_page_screenshot` で全画面キャプチャを保存。
- `async_capture_element_value` で指定セレクタのテキスト/HTML を抽出。
- 基本設定は Wikipedia トップページの言語カードを対象。
- CLI から URL、セレクタ、キャプチャフィールドを上書き可能。

```bash
python myscript/bin/demo_artifact_capture.py \
  --url https://www.wikipedia.org \
  --selector ".central-featured-lang strong" \
  --fields text html
```

オプションを省略した場合はデフォルト値が利用されます。`llms.txt` から呼び出された際に未展開の `${params.*}` が渡っても自動で無視されるため、安全に再利用できます。

## 🚀 すぐ試す: `demo-artifact-capture`

`llms.txt` の最後に登録された `demo-artifact-capture` アクションは、上記スクリプトをそのまま呼び出します。LLM アクションランナーや UI から同名のスクリプトを選択するだけで、以下を実行します。

1. Chromium を起動し、対象ページへ遷移。
2. 画面全体のスクリーンショットを保存。
3. 指定セレクタのテキストと HTML を抽出し、テキストファイルに保存。
4. ログに保存先パスを出力。

> 🧪 UI から実行できない場合は、手動で `python myscript/bin/demo_artifact_capture.py` を呼び出して挙動を確認してください。

## 📂 生成されるアーティファクト

実行すると新しい Run ID が割り当てられ、`artifacts/runs/<run_id>-art/` に下記ファイルが作成されます。

```text
artifacts/
  runs/
    20250214-123456-abc123-art/
      manifest_v2.json
      screenshots/
        demo_capture_20250214_123456_789012.png
      elements/
        demo_capture_element_20250214_123457_123456.txt
        element_20250214_123457123456.json
```

- `screenshots/*.png` … 実際のブラウザ画面。
- `elements/*.txt` … 指定セレクタのテキスト/HTML。`
- `elements/*.json` … `ArtifactManager.save_element_capture` により出力されるメタデータ。
- `manifest_v2.json` … 生成物の一覧。`type: "screenshot"` や `type: "element_capture"` のエントリが追加されています。

## 🧭 手順詳細

### 1. 既存フローでのキャプチャ

`llms.txt` の `search-nogtips` フロー（Issue #34 の適用例）では次のアクションが挿入されています。

- `action: screenshot` … `async_capture_page_screenshot` を使用。
- `action: extract_content` … 複数セレクタを `async_capture_element_value` で保存。

このフローをブラウザコントロール経由で実行すると、同じように `screenshots/` と `elements/` にアーティファクトが残ります。`demo_artifact_capture.py` と合わせて挙動を比較すると理解が深まります。

### 2. 保存先の確認

`artifact_manager.py` は `RunContext` の Run ID をもとに、コンポーネント別ディレクトリ（`*-art/`）を作成します。スクリーンショットは `screenshots/`、要素抽出は `elements/` に格納され、`manifest_v2.json` に自動登録されます。

### 3. フィールド選択

`--fields` オプションでキャプチャ対象を調整できます。

- `text` … `element.inner_text()`
- `html` … `element.inner_html()`
- `value` … `element.input_value()`

複数指定すると `TEXT: ...` / `HTML:` / `VALUE:` のブロックが `.txt` に追記されます。未指定の場合は `text` のみ。

## 🔄 カスタマイズのヒント

- `--browser` … `chromium` / `firefox` / `webkit` を切り替え。
- `--headless` … 付与するとヘッドレスモードで実行。
- `--prefix` … 保存ファイル名の先頭を任意に変更（同時に `.txt` / `.png` のラベルも変わります）。
- `--selector` … 複数の要素を順にキャプチャしたい場合は、スクリプトを複製してセレクタを配列化すると便利です。

## 🧩 関連モジュール

- `src/core/screenshot_manager.py` … `_persist_screenshot` / `async_capture_page_screenshot`
- `src/core/element_capture.py` … `_persist_capture` / `async_capture_element_value`
- `src/browser/engine/playwright_engine.py` … `screenshot` / `extract_content` アクションの統合ポイント
- `src/modules/direct_browser_control.py` … ブラウザ制御ワークフローのコマンド実装

Issue #34 の対応により、上記の各モジュールが非同期 API を通じて統一された振る舞いを行います。

## ✅ 次のステップ

1. `demo-artifact-capture` を実行し、生成ファイルと `manifest_v2.json` を確認する。
2. `--fields value` や異なるセレクタで再試行し、テキスト差分を比較する。
3. 既存の `myscript/` スクリプトにも `async_capture_*` 呼び出しを組み込み、Issue #34 の成果を広げていきましょう。
