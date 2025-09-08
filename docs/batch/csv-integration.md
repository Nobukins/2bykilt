# CSV連携処理ドキュメント

## 概要

CSV連携処理は、2Bykiltのバッチ実行エンジンのコア機能であり、CSVファイルを処理してブラウザ自動化タスクのバッチジョブを生成します。この機能は、大量のデータを効率的に処理し、並列実行を可能にするためのものです。

## 主な機能

### CSVファイル処理

- **自動デリミタ検出**: CSVファイルのデリミタを自動的に検出
- **エンコーディング対応**: UTF-8、Shift-JIS、CP932などの各種エンコーディングに対応
- **大規模ファイル処理**: メモリ効率の良いチャンク処理で大規模ファイルを処理
- **セキュリティチェック**: パストラバーサル攻撃の防止と機密ディレクトリへのアクセス制限

### バッチジョブ管理

- **ジョブ生成**: CSVの各行から個別のジョブファイルを生成
- **マニフェスト管理**: バッチ実行の全体像を管理するマニフェストファイルの作成
- **ステータス追跡**: 各ジョブの実行状態（pending, running, completed, failed）を追跡
- **エラーハンドリング**: 包括的なエラー処理とログ記録

### 設定オプション

- **ファイルサイズ制限**: 処理可能なCSVファイルの最大サイズを設定
- **チャンクサイズ**: メモリ効率のための処理チャンクサイズ
- **エンコーディング**: ファイル読み込み時のエンコーディング指定
- **セキュリティ設定**: パストラバーサル防止の有効/無効

## 設定

### 環境変数による設定

以下の環境変数を使用して設定をカスタマイズできます：

```bash
# 最大ファイルサイズ（MB）
export BATCH_MAX_FILE_SIZE_MB=500

# チャンクサイズ（行数）
export BATCH_CHUNK_SIZE=1000

# ファイルエンコーディング
export BATCH_ENCODING=utf-8

# デリミタフォールバック
export BATCH_DELIMITER_FALLBACK=,

# パストラバーサル許可
export BATCH_ALLOW_PATH_TRAVERSAL=false

# ヘッダー検証
export BATCH_VALIDATE_HEADERS=true

# 空行スキップ
export BATCH_SKIP_EMPTY_ROWS=true

# ログレベル
export BATCH_LOG_LEVEL=INFO
```

### プログラム内設定

BatchEngineの初期化時に設定を渡すことも可能です：

```python
from src.batch.engine import BatchEngine, start_batch

# カスタム設定
config = {
    'max_file_size_mb': 200,
    'encoding': 'utf-8',
    'allow_path_traversal': False,
    'log_level': 'DEBUG'
}

# エンジン作成
engine = BatchEngine(run_context, config)

# または直接バッチ開始
manifest = start_batch('data.csv', config=config)
```

## 使用方法

### 基本的な使用例

```python
from src.batch.engine import start_batch

# シンプルな使用例
manifest = start_batch('customers.csv')
print(f"バッチ {manifest.batch_id} が作成されました")
print(f"総ジョブ数: {manifest.total_jobs}")
```

### 詳細な使用例

```python
from src.batch.engine import BatchEngine
from src.runtime.run_context import RunContext

# ランタイムコンテキストの作成
run_context = RunContext.get()

# カスタム設定
config = {
    'max_file_size_mb': 100,
    'encoding': 'utf-8',
    'allow_path_traversal': False
}

# エンジンの作成
engine = BatchEngine(run_context, config)

# CSVファイルの処理
try:
    manifest = engine.create_batch_jobs('data.csv')
    print(f"バッチID: {manifest.batch_id}")
    print(f"ジョブ数: {manifest.total_jobs}")

    # 各ジョブの確認
    for job in manifest.jobs:
        print(f"ジョブ {job.job_id}: {job.status}")

except Exception as e:
    print(f"エラー: {e}")
```

### CLIからの使用

コマンドラインからバッチ処理を実行することも可能です：

```bash
# 基本的なバッチ実行
python bykilt.py batch start data.csv

# カスタム設定での実行
python bykilt.py batch start data.csv --config max_file_size_mb=200,encoding=utf-8
```

## APIリファレンス

### BatchEngineクラス

#### コンストラクタ

```python
BatchEngine(run_context: RunContext, config: Optional[Dict[str, Any]] = None)
```

#### 主なメソッド

##### parse_csv(csv_path: str, chunk_size: int = 1000) -> List[Dict[str, Any]]

CSVファイルを解析して行データのリストを返します。

**パラメータ:**

- `csv_path`: CSVファイルのパス
- `chunk_size`: メモリ効率のためのチャンクサイズ

**戻り値:** CSV行の辞書リスト

##### create_batch_jobs(csv_path: str) -> BatchManifest

CSVファイルからバッチジョブを作成します。

**パラメータ:**

- `csv_path`: 処理するCSVファイルのパス

**戻り値:** 作成されたバッチのマニフェスト

##### get_batch_status(batch_id: str) -> Optional[BatchManifest]

バッチの実行状態を取得します。

**パラメータ:**

- `batch_id`: バッチID

**戻り値:** バッチマニフェスト（見つからない場合はNone）

##### update_job_status(job_id: str, status: str, error_message: Optional[str] = None)

ジョブのステータスを更新します。

**パラメータ:**

- `job_id`: ジョブID
- `status`: 新しいステータス（'completed', 'failed' など）
- `error_message`: エラーメッセージ（失敗時）

### start_batch関数

```python
start_batch(csv_path: str, run_context: Optional[RunContext] = None, config: Optional[Dict[str, Any]] = None) -> BatchManifest
```

CSVファイルからバッチ処理を開始する便利関数です。

**パラメータ:**

- `csv_path`: CSVファイルのパス
- `run_context`: オプションのランタイムコンテキスト
- `config`: オプションの設定辞書

**戻り値:** バッチマニフェスト

### データ構造

#### BatchJob

個別のバッチジョブを表すデータクラス：

```python
@dataclass
class BatchJob:
    job_id: str
    run_id: str
    row_data: Dict[str, Any]
    status: str = "pending"
    error_message: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None
```

#### BatchManifest

バッチ全体のマニフェストを表すデータクラス：

```python
@dataclass
class BatchManifest:
    batch_id: str
    run_id: str
    csv_path: str
    total_jobs: int
    completed_jobs: int = 0
    failed_jobs: int = 0
    created_at: Optional[str] = None
    jobs: Optional[List[BatchJob]] = None
```

## エラーハンドリング

### 例外クラス

#### FileProcessingError

ファイル処理中に発生するエラー：

- CSV解析エラー
- ファイルエンコーディングの問題
- ファイルサイズ制限超過
- ファイルが見つからない
- 不正なファイル形式

#### ConfigurationError

設定関連のエラー：

- 無効な設定値
- 必須設定の欠如
- 設定値の範囲外

#### SecurityError

セキュリティ関連のエラー：

- パストラバーサル攻撃の検出
- 機密ディレクトリへのアクセス試行

### エラーハンドリング例

```python
from src.batch.engine import start_batch, FileProcessingError, ConfigurationError, SecurityError

try:
    manifest = start_batch('data.csv')
except FileProcessingError as e:
    print(f"ファイル処理エラー: {e}")
except ConfigurationError as e:
    print(f"設定エラー: {e}")
except SecurityError as e:
    print(f"セキュリティエラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")
```

## トラブルシューティング

### よくある問題と解決方法

#### 1. CSVファイルが読み込めない

**症状:** FileNotFoundError または FileProcessingError

**解決方法:**

- ファイルパスが正しいか確認
- ファイルが存在するか確認
- 読み取り権限があるか確認
- ファイルが空でないか確認

#### 2. エンコーディングエラー

**症状:** UnicodeDecodeError

**解決方法:**

- ファイルがUTF-8で保存されているか確認
- 必要に応じてエンコーディング設定を変更：

```python
config = {'encoding': 'cp932'}  # Shift-JISの場合
```

#### 3. メモリ不足

**症状:** 大規模ファイルの処理でメモリエラー

**解決方法:**

- チャンクサイズを小さくする：

```python
config = {'chunk_size': 500}
```

- ファイルサイズ制限を確認

#### 4. デリミタ検出の問題

**症状:** CSVの列が正しく分割されない

**解決方法:**

- デリミタを手動で指定：

```python
config = {'delimiter_fallback': ';'}
```

#### 5. セキュリティエラー

**症状:** SecurityError

**解決方法:**

- パストラバーサルを許可する場合：

```python
config = {'allow_path_traversal': True}
```

- 機密ディレクトリへのアクセスは避ける

### ログの確認

デバッグ情報を得るためにログレベルを変更：

```python
config = {'log_level': 'DEBUG'}
```

ログファイルは `artifacts/logs/` ディレクトリに保存されます。

### パフォーマンスチューニング

大規模ファイルを処理する場合の推奨設定：

```python
config = {
    'max_file_size_mb': 1000,
    'chunk_size': 1000,
    'log_level': 'INFO'
}
```

## テスト

CSV連携処理のテストは `tests/test_batch_engine.py` に含まれています：

```bash
# テスト実行
python -m pytest tests/test_batch_engine.py -v

# カバレッジレポート付き
python -m pytest tests/test_batch_engine.py --cov=src.batch.engine
```

## 関連ドキュメント

- [バッチ実行エンジン概要](../engineering/batch-engine-overview.md)
- [ランタイムコンテキスト](../engineering/runtime-context.md)
- [設定管理](../config/configuration-management.md)
- [セキュリティガイドライン](../security/security-guidelines.md)

## バージョン履歴

- **v1.0.0**: 初期実装
  - 基本的なCSV処理機能
  - バッチジョブ管理
  - セキュリティチェック
- **v1.1.0**: 機能拡張
  - 環境変数による設定
  - エラーハンドリングの改善
  - パフォーマンス最適化
- **v1.2.0**: CLI統合
  - コマンドラインインターフェースの追加
  - 設定ファイル対応
