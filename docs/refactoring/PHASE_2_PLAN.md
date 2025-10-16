# Phase 2: test_batch_engine.py 分割計画

**Issue**: #327  
**親Issue**: #264  
**対象ファイル**: tests/test_batch_engine.py (2303行)  
**作成日**: 2025-10-16

---

## 📋 現状分析

### ファイルサイズ
- **総行数**: 2303行
- **テストクラス数**: 5クラス
- **テストメソッド数**: 86メソッド

### テストクラスの構成

| クラス | テスト数 | 主な責務 | 行範囲（概算） |
|--------|---------|---------|---------------|
| `TestBatchJob` | 3 | BatchJobデータクラス | 42-85 (~43行) |
| `TestBatchManifest` | 2 | Manifestデータクラス | 87-129 (~42行) |
| `TestBatchEngine` | 67 | BatchEngineコア機能 | 131-801 (~670行) |
| `TestBatchEngineLogging` | 7 | ロギング機能 | 802-984 (~182行) |
| `TestStartBatch` | 3 | start_batch関数 | 986-1078 (~92行) |
| `TestBatchRetry` | 3 | リトライ機能 | 1080-2153 (~1073行) |
| `TestExecuteBatchJobs` | 4 | ジョブ実行 | 2155-2303 (~148行) |

**注**: `TestBatchRetry`が非常に大きい（1073行、40%超）

---

## 🎯 分割戦略

### 提案: 機能別5モジュール

```
tests/test_batch_engine.py (2303行)
  ↓
tests/batch/
  ├── __init__.py                      (共通fixture、helper)
  ├── test_batch_data_models.py        (~100行) TestBatchJob + TestBatchManifest
  ├── test_batch_core.py               (~700行) TestBatchEngineのCSV/Job操作系
  ├── test_batch_lifecycle.py          (~400行) TestBatchEngineのライフサイクル系
  ├── test_batch_retry.py              (~1100行) TestBatchRetry + リトライ関連
  └── test_batch_execution.py          (~300行) TestStartBatch + TestExecuteBatchJobs + ロギング
```

### 分割の根拠

#### 1. test_batch_data_models.py (~100行)
**責務**: データモデルの単体テスト

**含むテスト**:
- `TestBatchJob` (3テスト)
  - test_batch_job_creation
  - test_batch_job_to_dict
  - test_batch_job_from_dict
- `TestBatchManifest` (2テスト)
  - test_batch_manifest_creation
  - test_batch_manifest_serialization

**特徴**:
- 依存が少なく、独立性が高い
- データクラスのシリアライゼーション検証
- 高速実行（モックなし）

---

#### 2. test_batch_core.py (~700行)
**責務**: BatchEngineのコア機能（CSV解析、ジョブ作成、設定）

**含むテスト**:
- `TestBatchEngine`から抽出（~35テスト）
  - CSV解析系（15テスト）:
    - test_parse_csv_basic
    - test_parse_csv_empty_rows
    - test_parse_csv_file_not_found
    - test_parse_csv_empty_file
    - test_parse_csv_no_data_rows
    - test_parse_csv_special_characters
    - test_parse_csv_large_file
    - test_parse_csv_custom_config
    - test_parse_csv_file_too_large
    - test_parse_csv_path_traversal_prevention
    - test_parse_csv_invalid_delimiter_detection
    - test_parse_csv_malformed_csv
    - test_parse_csv_file_processing_error_empty_content
    - test_parse_csv_security_error_path_traversal
    - test_parse_csv_security_error_sensitive_directory_access
    - test_parse_csv_security_error_sensitive_directory_access_allowed
  
  - 設定検証系（8テスト）:
    - test_config_validation_valid
    - test_config_validation_invalid_max_file_size
    - test_config_validation_invalid_chunk_size
    - test_config_validation_invalid_encoding
    - test_config_validation_invalid_delimiter
    - test_config_validation_invalid_boolean
    - test_config_validation_invalid_log_level
    - test_config_validation_env_vars
  
  - ジョブ作成系（2テスト）:
    - test_create_batch_jobs
    - test_create_batch_jobs_empty_csv
  
  - アーティファクト系（7テスト）:
    - test_add_row_artifact_text
    - test_add_row_artifact_json_infer_ext
    - test_add_row_artifact_binary_content
    - test_add_row_artifact_extension_override
    - test_add_row_artifact_job_not_found
    - test_add_row_artifact_job_not_in_manifest
    - test_add_row_artifact_invalid_params
  
  - ユーティリティ系（3テスト）:
    - test_to_portable_relpath_success
    - test_to_portable_relpath_fallback
    - test_configure_logging_success
    - test_configure_logging_invalid_level

**特徴**:
- CSV処理の包括的テスト
- セキュリティ検証（パストラバーサル防止）
- 設定バリデーション

---

#### 3. test_batch_lifecycle.py (~400行)
**責務**: BatchEngineのライフサイクル管理（状態更新、マニフェスト操作、停止）

**含むテスト**:
- `TestBatchEngine`から抽出（~25テスト）
  - ステータス更新系（6テスト）:
    - test_update_job_status
    - test_update_job_status_with_error
    - test_update_job_status_not_found
    - test_update_job_status_batch_not_found
    - test_update_job_status_job_not_found_in_manifest
    - test_update_single_job_status_completed
    - test_update_single_job_status_failed
  
  - マニフェスト操作系（12テスト）:
    - test_load_manifest_by_batch_id_success
    - test_load_manifest_by_batch_id_not_found
    - test_load_manifest_from_current_context_success
    - test_load_manifest_from_current_context_not_found
    - test_search_batch_manifest_in_artifacts_success
    - test_search_batch_manifest_in_artifacts_no_artifacts_dir
    - test_load_and_check_manifest_success
    - test_load_and_check_manifest_job_not_found
    - test_find_manifest_file_for_job_not_found
    - test_load_manifest_success
    - test_load_manifest_file_not_found
    - test_save_manifest_success
    - test_find_manifest_file_for_batch_success
    - test_find_manifest_file_for_batch_not_found
  
  - ジョブ検索系（2テスト）:
    - test_find_job_by_id_success
    - test_find_job_by_id_not_found
  
  - バッチ完了判定系（2テスト）:
    - test_is_batch_complete_true
    - test_is_batch_complete_false
  
  - バッチ停止系（2テスト）:
    - test_stop_batch_marks_pending_jobs_stopped
    - test_stop_batch_invalid_id
  
  - サマリー生成系（4テスト）:
    - test_get_batch_summary_success
    - test_get_batch_summary_not_found
    - test_get_batch_summary_with_summary_generator_import_error
    - test_generate_batch_summary_success
    - test_generate_batch_summary_import_error
  
  - 失敗行エクスポート系（2テスト）:
    - test_export_failed_rows_success
    - test_export_failed_rows_no_failed_jobs

**特徴**:
- ステートマシン的な振る舞いのテスト
- マニフェストファイルI/O
- ジョブライフサイクル管理

---

#### 4. test_batch_retry.py (~1100行)
**責務**: リトライ機能の包括的テスト

**含むテスト**:
- `TestBatchRetry` (全テスト ~40テスト)
  - リトライ実行系:
    - test_retry_batch_jobs_success
    - test_retry_batch_jobs_not_found
    - test_retry_batch_jobs_invalid_job_id
    - test_retry_batch_jobs_no_failed_jobs
    - test_retry_batch_jobs_custom_parameters
    - test_retry_batch_jobs_input_validation
    - test_execute_job_with_retry_success
    - test_execute_job_with_retry_input_validation
  
  - リトライパラメータ検証系:
    - test_validate_retry_parameters_success
    - test_validate_retry_parameters_default_max_delay
    - test_validate_retry_parameters_invalid_max_retries
    - test_validate_retry_parameters_invalid_retry_delay
    - test_validate_retry_parameters_invalid_backoff_factor
    - test_validate_retry_parameters_invalid_max_retry_delay
  
  - メトリクス記録系:
    - test_record_retry_metrics_success
    - test_record_retry_metrics_no_collector
    - test_record_batch_stop_metrics_success
    - test_record_batch_stop_metrics_no_collector
    - test_retry_metrics_still_available_after_stop_batch_addition
    - test_record_failed_rows_export_metric
    - test_record_failed_rows_export_metric_no_collector
  
  - 設定ロード系:
    - test_load_config_from_env_partial_coverage

**特徴**:
- 最大の独立モジュール（1073行）
- 複雑なリトライロジックの網羅的テスト
- メトリクス収集の検証

---

#### 5. test_batch_execution.py (~300行)
**責務**: バッチ実行とロギング

**含むテスト**:
- `TestStartBatch` (3テスト)
  - test_start_batch_with_new_context
  - test_start_batch_with_provided_context
  - test_start_batch_with_config

- `TestExecuteBatchJobs` (4テスト)
  - test_execute_batch_jobs_with_progress_callback
  - test_execute_batch_jobs_without_progress_callback
  - test_execute_batch_jobs_progress_callback_exception_handling
  - test_execute_batch_jobs_incremental_manifest_updates

- `TestBatchEngineLogging` (7テスト)
  - test_parse_csv_mime_type_warning
  - test_parse_csv_file_size_warning
  - test_parse_csv_delimiter_detection_warning
  - test_parse_csv_row_processing_debug
  - test_create_batch_jobs_logging
  - test_create_batch_jobs_manifest_save_logging
  - test_security_check_exception_logging

**特徴**:
- エントリーポイント（start_batch）のテスト
- 実行フロー全体の統合テスト
- ロギング動作の検証

---

## 🔧 実装手順

### Step 1: 共通ファイルの作成
```bash
mkdir -p tests/batch
touch tests/batch/__init__.py
```

### Step 2: 共通fixture/helperの抽出
`tests/batch/__init__.py`に以下を移動:
- `_run_async` ヘルパー関数
- 共通fixture（`engine`, `temp_dir`, `run_context`など）

### Step 3: 各モジュールの作成（優先順位順）

1. **test_batch_data_models.py** (最小依存)
   - BatchJob, BatchManifestのテストを抽出
   - インポート: dataclasses, pytest
   
2. **test_batch_core.py** (コア機能)
   - CSV解析、設定、アーティファクトのテストを抽出
   - インポート: BatchEngine, 共通fixture
   
3. **test_batch_lifecycle.py** (ライフサイクル)
   - マニフェスト操作、ステータス管理のテストを抽出
   - インポート: BatchEngine, 共通fixture
   
4. **test_batch_retry.py** (最大モジュール)
   - TestBatchRetry全体を移動
   - インポート: BatchEngine, 共通fixture, メトリクス関連
   
5. **test_batch_execution.py** (統合)
   - start_batch, execute系, ロギングのテストを抽出
   - インポート: start_batch, BatchEngine, 共通fixture

### Step 4: 元ファイルの削除
全テストが新モジュールに移動後、`tests/test_batch_engine.py`を削除

### Step 5: テストの検証
```bash
# 個別モジュールのテスト
pytest tests/batch/test_batch_data_models.py -v
pytest tests/batch/test_batch_core.py -v
pytest tests/batch/test_batch_lifecycle.py -v
pytest tests/batch/test_batch_retry.py -v
pytest tests/batch/test_batch_execution.py -v

# 全バッチテストの実行
pytest tests/batch/ -v

# カバレッジ確認
pytest tests/batch/ --cov=src/batch --cov-report=term-missing
```

---

## ✅ 成功基準

- [ ] 全86テストが新モジュールに移行
- [ ] 各モジュール < 500行（test_batch_retry.py除く）
- [ ] test_batch_retry.py < 1200行
- [ ] 全テストがpass（86/86 passed）
- [ ] テスト実行時間の変化を記録（並列化の効果）
- [ ] カバレッジ維持（src/batch/engine.py）
- [ ] インポートエラーなし
- [ ] 共通fixtureが適切に共有されている

---

## 📊 期待効果

### 並列実行の改善
```bash
# Before: 単一ファイル
pytest tests/test_batch_engine.py  # ~60秒

# After: 5並列
pytest tests/batch/ -n 5  # ~15秒（予想）
```

### 保守性の向上
- テスト失敗時の原因特定が容易
- 機能別のテスト追加が明確
- モジュール間の依存が可視化

### コードレビューの改善
- 小さな単位でのPR作成が可能
- 変更影響範囲の明確化
- レビュアーの負担軽減

---

## 🚨 リスクと緩和策

### リスク1: 共通fixtureの管理
**問題**: fixture共有が複雑化  
**緩和**: `conftest.py`または`__init__.py`で一元管理

### リスク2: テスト実行順序の依存
**問題**: 暗黙的な順序依存が発覚  
**緩和**: 各テストの独立性を検証（`pytest --random-order`）

### リスク3: インポート循環
**問題**: 新モジュール間で循環参照  
**緩和**: 依存関係を明確化、共通部分を`__init__.py`に集約

---

## 📝 実装メモ

### Phase 1の教訓
- PEP 8準拠のインポート整理
- 型ヒントの追加
- docstringの充実
- カバレッジ≥80%の維持

### Phase 2での適用
- 各テストモジュールにモジュールdocstring追加
- fixtureにもdocstring追加
- テスト名の一貫性確保
- セットアップ/ティアダウンの明確化

---

## 🔗 関連ドキュメント

- 親Issue: #264
- Phase 1完了: #326 (PR #330)
- Phase 1計画: docs/refactoring/BYKILT_PY_SPLIT_PLAN.md
- メトリクス: docs/metrics/LARGE_FILES_REPORT.md

---

**Plan Status**: ✅ Complete  
**Next Action**: 実装開始（Step 1から順次実行）
