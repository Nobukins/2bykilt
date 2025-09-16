# 2bykilt 魔法練習場

<img src="../../assets/2bykilt-practice.png" alt="2Bykilt 魔法練習場" width="200"/>

## 🧪 魔法の練習と実験

ここは**2bykilt**の魔法を練習するための特別な空間です。初心者の魔法使いがまず訪れるべき場所であり、自分だけの魔法を作り始めるのに最適です！

## 魔法の詠唱方法

### 基本の呪文

```bash
# RECORDING_PATH環境変数を設定（必須）
export RECORDING_PATH="./record_videos"

python action_runner.py --action <魔法の名前> [オプション]
```

### 環境変数の設定

**RECORDING_PATH (必須)**: 録画ファイルとスクリーンショットの保存先ディレクトリ

```bash
export RECORDING_PATH="/path/to/your/recordings"
```

**BYKILT_BROWSER_TYPE (オプション)**: 使用するブラウザタイプ

```bash
export BYKILT_BROWSER_TYPE="chromium"  # chromium, chrome, msedge, firefox, webkit
```

### 使える呪文オプション

- `--action`: 実行する魔法の名前（拡張子なし）
- `--query`: 検索キーワード（魔法で使用される）
- `--slowmo`: 魔法の速度調整（ミリ秒）
- `--headless`: 目に見えない魔法として実行（画面表示なし）
- `--browser`: ブラウザタイプ（chromium/chrome/msedge/firefox/webkit）

### 魔法の例

1. 特定の魔法を唱える:

```bash
export RECORDING_PATH="./record_videos"
python action_runner.py --action nogtips_search --query "Playwright魔法の使い方"
```

2. 新しい魔法の巻物を作る:

```bash
python action_runner.py --new my_custom_magic
```

## 生成物について

実行後に以下のファイルが生成されます：

- **動画ファイル**: `artifacts/<action_name>/Tab-XX-*.webm`
- **スクリーンショット**: `artifacts/<action_name>/Tab-XX-*.png`
- **マニフェスト**: `artifacts/<action_name>/tab_index_manifest.json`

### マニフェストファイルの例

```json
{
  "action": "nogtips_search",
  "timestamp": "2025-09-16T14:30:00",
  "artifacts": [
    {
      "index": 1,
      "original_name": "recording_001.webm",
      "new_name": "Tab-01-recording_001.webm",
      "path": "/path/to/artifacts/nogtips_search/Tab-01-recording_001.webm",
      "type": "video"
    }
  ],
  "summary": {
    "total_files": 1,
    "videos": 1,
    "screenshots": 0
  }
}
```

## 自分だけの魔法の作り方

1. 新しい魔法の巻物を作成:

```bash
python action_runner.py --new my_magic
```

2. 生成された `actions/my_magic.py` ファイルを編集します。

3. **魔法記録の術**（Playwright Codegen）で魔法を記録:

```bash
playwright codegen
```

4. 記録された魔法を `run_actions` 関数内に貼り付けます。

5. 魔法を唱える:

```bash
python action_runner.py --action my_magic
```

---

「すべての偉大な魔法使いは、最初は練習場から始まった...」
