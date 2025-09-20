# 録画パス設定ガイド

## 概要

2Bykiltでは、ブラウザ自動化時の録画ファイルを統一された方法で管理しています。このガイドでは、録画パスの設定方法と構成の基本情報について説明します。

## 録画パスの優先順位

録画パスは以下の優先順位で決定されます：

1. **明示的なパラメータ** - コードやUIで直接指定されたパス
2. **環境変数** `RECORDING_PATH` - 空でない値が設定されている場合
3. **統一フラグ** `artifacts.unified_recording_path` - Trueの場合
4. **レガシーフォールバック** - `./tmp/record_videos`

### デフォルト動作

環境変数や明示的な設定がない場合、録画ファイルは以下の構造で保存されます：

```
artifacts/runs/{実行ID}-art/videos/
├── recording_001.webm
├── recording_002.webm
└── ...
```

## 設定方法

### 1. 環境変数を使用する

最も簡単な方法は、環境変数 `RECORDING_PATH` を設定することです：

```bash
# カスタムパスを指定
export RECORDING_PATH="/path/to/my/recordings"
python bykilt.py

# または1行で実行
RECORDING_PATH=/path/to/my/recordings python bykilt.py
```

### 2. UIから設定する

Webインターフェースの「Browser Settings」タブから設定できます：

1. アプリケーションを起動
2. 「Browser Settings」タブを選択
3. 「録画保存パス」フィールドにパスを入力
4. 設定を保存

### 3. 設定ファイルを使用する

`config/` ディレクトリの設定ファイルで指定できます：

```yaml
# config/base.yml
storage:
  save_recording_path: "/custom/recording/path"
```

## 実行タイプ別の動作

### Script タイプ

pytest を使用したスクリプト実行時の録画：

```bash
# 環境変数で指定
RECORDING_PATH=/tmp/script_recordings python -m pytest myscript/search_script.py

# またはスクリプト内で指定
from src.utils.recording_dir_resolver import create_or_get_recording_dir
recording_path = str(create_or_get_recording_dir())
```

### Browser-Control タイプ

ブラウザ制御スクリプト実行時の録画：

```python
# 自動的に統一パスが使用される
script_info = {
    "type": "browser-control",
    "flow": [...],
    # save_recording_path は自動的に設定される
}
```

### Git-Script タイプ

Git リポジトリから取得したスクリプト実行時の録画：

```python
# 環境変数 RECORDING_PATH が使用される
script_info = {
    "type": "git-script",
    "git": "https://github.com/example/repo.git",
    "script_path": "automation_script.py"
}
```

## 高度な設定

### 機能フラグの使用

`src/config/feature_flags.py` で高度な設定が可能です：

```python
# artifacts.unified_recording_path を有効化
FeatureFlags.set_override("artifacts.unified_recording_path", True)

# 録画保持期間を設定
FeatureFlags.set_override("artifacts.video_retention_days", 30)
```

### プログラムからの制御

Python コードから直接制御する場合：

```python
from src.utils.recording_dir_resolver import create_or_get_recording_dir
from pathlib import Path

# 明示的なパスを指定
explicit_path = Path("/custom/path/recordings")
recording_dir = create_or_get_recording_dir(str(explicit_path))

# 環境変数を設定
import os
os.environ['RECORDING_PATH'] = '/tmp/test_recordings'
recording_dir = create_or_get_recording_dir()
```

## トラブルシューティング

### 録画ファイルが見つからない

**問題**: 録画ファイルが期待された場所に保存されていない

**解決策**:

1. 環境変数 `RECORDING_PATH` が正しく設定されているか確認
2. ディレクトリの書き込み権限を確認
3. ログファイルでエラーメッセージを確認

### パスが反映されない

**問題**: 設定したパスが反映されない

**解決策**:

1. アプリケーションの再起動を試す
2. 環境変数のスペルミスを確認
3. 設定ファイルの構文を確認

### 古いパスが使用される

**問題**: `./tmp/record_videos` が使用され続ける

**解決策**:

1. 環境変数 `RECORDING_PATH` を明示的に設定
2. 機能フラグ `artifacts.unified_recording_path` を有効化
3. 設定ファイルでパスを明示的に指定

## 関連ファイル

- `src/utils/recording_dir_resolver.py` - 統一録画パスリゾルバ
- `src/utils/default_config_settings.py` - デフォルト設定
- `src/config/config_adapter.py` - 設定アダプタ
- `src/core/artifact_manager.py` - アーティファクト管理

## 技術仕様

### サポートされるフォーマット

- WebM (デフォルト)
- MP4 (変換オプションあり)

### ディレクトリ構造

```bash
{recording_path}/
├── {timestamp}_{test_name}.webm
├── {timestamp}_{test_name}.mp4  # 変換時
└── metadata.json               # 録画メタデータ
```

### 環境変数

| 変数名 | 説明 | デフォルト値 |
|--------|------|--------------|
| `RECORDING_PATH` | 録画保存先パス | artifacts/runs/{run_id}-art/videos |
| `ARTIFACTS_UNIFIED_RECORDING_PATH` | 統一パス有効化 | true |

---

このガイドは 2Bykilt の録画パス設定に関する包括的な情報を提供します。追加の質問がある場合は、開発チームまでお問い合わせください。
