# Phase 3: batch/engine.py 分割 - 分析と計画

**Issue**: #328  
**作成日**: 2025-10-16  
**Phase**: 3/4 (Parent: #264)  
**依存**: Phase 2 (#327) 完了後

---

## 📋 エグゼクティブサマリー

### 現状
- **ファイル**: `src/batch/engine.py`
- **規模**: 2,111行（Phase 1完了後も巨大）
- **構成要素**:
  - 4つの例外クラス
  - 2つのデータクラス (BatchJob, BatchManifest)
  - 1つのメインクラス (BatchEngine) - 47メソッド
  - 1つのエントリーポイント関数 (start_batch)

### Phase位置づけ

```
Phase 1 (#326) ✅ 完了
├─ bykilt.py分割 (1908行 → 1310行, 31%削減)
└─ 5モジュール作成

Phase 2 (#327) ✅ 完了  
├─ test_batch_engine.py分割 (2303行 → 5モジュール)
└─ 62テスト抽出、81テスト全成功

Phase 3 (#328) ⏳ 次のステップ ← ここ
├─ src/batch/engine.py分割 (2111行)
├─ Phase 2のテストが品質保証
└─ Phase 1のパターン適用

Phase 4 (#329) ⏳ 計画中
└─ 残りのリファクタリング
```

---

## 🎯 分割目標と期待効果

### 目標
1. **責任の分離**: 単一責任原則に従った明確なモジュール分割
2. **保守性向上**: 各モジュール500-800行以内
3. **テスト容易性**: Phase 2で作成した62テストがそのまま使用可能
4. **段階的移行**: 既存コードの互換性維持

### 期待効果

#### 1. 保守性の向上
- **Before**: 2,111行の巨大ファイル、47メソッド
- **After**: 5-7モジュール、各500-800行
- **効果**: 
  - 変更範囲の明確化
  - コードレビューの効率化（1モジュール30分→全体2時間）
  - バグ修正の局所化

#### 2. 並行開発の促進
- **Before**: 1ファイルでコンフリクト頻発
- **After**: 機能別モジュールで並行開発可能
- **効果**:
  - マージコンフリクト70%削減
  - 複数開発者の同時作業可能

#### 3. テスト効率の向上
- **Before**: 全2,111行を理解してテスト作成
- **After**: 関連モジュールのみ理解すれば十分
- **効果**:
  - Phase 2の62テストが品質保証（変更時の回帰テスト）
  - 新規テスト作成時間50%削減
  - テストカバレッジの向上（70% → 85%目標）

#### 4. 再利用性の向上
- **Before**: BatchEngineクラスからの部分利用困難
- **After**: 各機能が独立モジュールとして利用可能
- **効果**:
  - CSV parsingのみ使用するケース対応
  - 他プロジェクトへの部分移植容易

---

## 📊 現状分析

### ファイル構造

```python
src/batch/engine.py (2,111行)
├─ Imports & Constants (1-86)
├─ Exception Classes (50-78)
│  ├─ BatchEngineError
│  ├─ ConfigurationError
│  ├─ FileProcessingError
│  └─ SecurityError
├─ Data Classes (89-149)
│  ├─ BatchJob (89-118)
│  └─ BatchManifest (121-149)
└─ BatchEngine Class (152-2035)
   ├─ Initialization (183-241)
   ├─ Configuration (262-342)
   ├─ CSV Processing (344-500)
   ├─ Job Management (502-579)
   ├─ Status & Summary (616-758)
   ├─ Artifact Management (761-865)
   ├─ Metrics (866-926, 1067-1087)
   ├─ Retry Logic (1088-1298)
   ├─ Batch Control (1299-1379)
   ├─ Execution (1423-1653)
   ├─ Job Execution (1654-1707)
   ├─ Simulation & Extraction (1708-2034)
   └─ start_batch function (2037-2111)
```

### メソッド分析（47メソッド）

#### Core機能 (8メソッド)
- `__init__`: 初期化
- `_configure_logging`: ログ設定
- `_load_config_from_env`: 環境変数読込
- `_validate_config`: 設定検証
- `_validate_file_type`: ファイルタイプ検証
- `_to_portable_relpath`: パス変換
- `parse_csv`: CSV解析（メイン機能）
- `create_batch_jobs`: バッチジョブ作成

#### Manifest管理 (10メソッド)
- `_load_manifest_from_current_context`
- `_search_batch_manifest_in_artifacts`
- `_load_manifest_by_batch_id`
- `_find_manifest_file_for_job`
- `_find_manifest_file_for_batch`
- `_load_and_check_manifest`
- `_load_manifest`
- `_save_manifest`
- `_find_job_by_id`
- `_is_batch_complete`

#### Status & Summary (4メソッド)
- `get_batch_summary`
- `update_job_status`
- `_update_single_job_status`
- `_generate_batch_summary`

#### Artifact管理 (2メソッド)
- `add_row_artifact`
- `_export_failed_rows`

#### Retry機能 (3メソッド)
- `_validate_retry_parameters`
- `retry_batch_jobs`
- `execute_job_with_retry`

#### Batch制御 (2メソッド)
- `stop_batch`
- `execute_batch_jobs`

#### Job実行 (5メソッド)
- `_execute_single_job`
- `_simulate_job_execution`
- `_execute_field_extraction`
- `_get_mock_page_content`
- `_parse_row_index_from_job_id`

#### Metrics (7メソッド)
- `_record_batch_creation_metrics`
- `_record_job_metrics`
- `_record_failed_rows_export_metric`
- `_record_retry_metrics`
- `_record_batch_stop_metrics`
- `_record_batch_execution_metrics`
- `_record_extraction_metrics`

---

## 🏗️ 提案される分割構造

### オプション A: 機能別分割（推奨）

```
src/batch/
├── __init__.py (re-exports)
├── exceptions.py (~50行)
│   ├─ BatchEngineError
│   ├─ ConfigurationError
│   ├─ FileProcessingError
│   └─ SecurityError
├── models.py (~150行)
│   ├─ BatchJob
│   └─ BatchManifest
├── config.py (~300行)
│   ├─ Configuration loading
│   ├─ Validation
│   └─ Environment variable handling
├── csv_parser.py (~400行)
│   ├─ CSV parsing logic
│   ├─ File validation
│   └─ Security checks
├── manifest_manager.py (~500行)
│   ├─ Manifest CRUD operations
│   ├─ Job searching
│   └─ File persistence
├── job_manager.py (~350行)
│   ├─ Job creation
│   ├─ Status updates
│   └─ Summary generation
├── artifact_manager.py (~200行)
│   ├─ Row-level artifacts
│   └─ Failed rows export
├── retry_handler.py (~300行)
│   ├─ Retry logic
│   ├─ Exponential backoff
│   └─ Parameter validation
├── executor.py (~450行)
│   ├─ Job execution
│   ├─ Batch execution
│   └─ Simulation
└── metrics_recorder.py (~250行)
    └─ All metrics recording

Total: ~2,950行 (元2,111行 + 新規コード/ドキュメント)
```

### オプション B: レイヤー別分割

```
src/batch/
├── core/
│   ├── exceptions.py
│   ├── models.py
│   └── config.py
├── io/
│   ├── csv_parser.py
│   └── manifest_io.py
├── services/
│   ├── job_service.py
│   ├── artifact_service.py
│   └── retry_service.py
└── execution/
    ├── executor.py
    └── metrics.py
```

---

## 🔗 依存関係

### Phase 2への依存

**強い依存 - 必須**:
1. **テストスイートの存在**
   - Phase 2で作成した62テスト（5モジュール）
   - 分割後の回帰テスト保証
   - テストが失敗 = 分割NG

2. **テストカバレッジ**
   - 現在70% coverage on engine.py
   - 分割時の品質保証基準
   - カバレッジ低下は許容しない

**Phase 2からの利点**:
```python
# Phase 2で作成したテストがそのまま使える
tests/batch/
├── test_batch_data_models.py (5 tests) ✅
├── test_batch_core.py (29 tests) ✅
├── test_batch_lifecycle.py (11 tests) ✅
├── test_batch_retry.py (16 tests) ✅
└── test_batch_execution.py (10 tests) ✅

→ Phase 3の分割後も全テスト成功が条件
→ import文の調整のみで動作保証
```

### Phase 1への関連

**弱い関連 - 参考**:
- Phase 1のbykilt.py分割パターンを参考
- 同じ品質基準を適用
- ただし、engine.pyは構造が異なるため独自戦略必要

### 外部依存

**影響を受けるモジュール**:
```python
# 直接import
from src.batch.engine import (
    BatchEngine,
    BatchJob,
    BatchManifest,
    start_batch,
    # ... exceptions
)

# 影響範囲
src/cli/batch_commands.py: BatchEngine使用
src/batch/summary.py: BatchManifest使用
tests/: 全62テスト
```

**移行戦略**:
```python
# src/batch/__init__.py で互換性維持
from .models import BatchJob, BatchManifest
from .engine import BatchEngine  # → executor.py or engine.py (facade)
from .exceptions import *
from .api import start_batch

__all__ = [
    'BatchEngine',
    'BatchJob', 
    'BatchManifest',
    'start_batch',
    # ... exceptions
]
```

---

## 📈 実装計画

### Step 1: 準備（1-2時間）
- [ ] Phase 2テストの全成功確認
- [ ] 現在のimport依存関係調査
- [ ] 分割戦略の最終決定（Option A vs B）

### Step 2: 段階的分割（8-12時間）

#### 2.1 基礎モジュール作成
- [ ] `exceptions.py` 作成（30分）
- [ ] `models.py` 作成（1時間）
- [ ] テスト実行確認

#### 2.2 独立機能の分離
- [ ] `config.py` 作成（2時間）
- [ ] `csv_parser.py` 作成（2時間）
- [ ] テスト実行確認

#### 2.3 中核機能の分離
- [ ] `manifest_manager.py` 作成（2時間）
- [ ] `job_manager.py` 作成（1.5時間）
- [ ] テスト実行確認

#### 2.4 高度機能の分離
- [ ] `retry_handler.py` 作成（1.5時間）
- [ ] `artifact_manager.py` 作成（1時間）
- [ ] `executor.py` 作成（2時間）
- [ ] テスト実行確認

#### 2.5 サポート機能
- [ ] `metrics_recorder.py` 作成（1時間）
- [ ] `__init__.py` 整備（30分）

### Step 3: 統合とテスト（2-3時間）
- [ ] 全62テスト実行（Phase 2のテスト）
- [ ] カバレッジ確認（70%維持）
- [ ] import文の調整
- [ ] 既存コードの互換性確認

### Step 4: ドキュメント（1-2時間）
- [ ] 各モジュールのdocstring
- [ ] MIGRATION.md作成
- [ ] README更新

### Step 5: レビューとマージ（1-2時間）
- [ ] コードレビュー
- [ ] PR作成
- [ ] Issue #328クローズ

**Total: 15-20時間 (2-3日)**

---

## ✅ 成功基準

### 必須条件
1. ✅ **全テスト成功**: Phase 2の62テスト全て成功
2. ✅ **カバレッジ維持**: 70%以上のカバレッジ維持
3. ✅ **後方互換性**: 既存のimportが動作
4. ✅ **行数削減**: 各モジュール800行以内

### 望ましい条件
1. 🎯 **カバレッジ向上**: 70% → 75-80%
2. 🎯 **ドキュメント**: 各モジュールに詳細docstring
3. 🎯 **パフォーマンス**: 実行速度の維持または向上
4. 🎯 **型ヒント**: 完全な型アノテーション

---

## ⚠️ リスクと緩和策

### リスク 1: テスト失敗
**影響**: 高  
**確率**: 中  
**緩和策**:
- 各ステップでテスト実行
- import文の慎重な調整
- Phase 2のテストがsafety net

### リスク 2: 循環依存
**影響**: 高  
**確率**: 中  
**緩和策**:
- 依存関係グラフの事前作成
- models.pyとexceptions.pyを最初に分離
- TYPE_CHECKINGの活用

### リスク 3: パフォーマンス劣化
**影響**: 中  
**確率**: 低  
**緩和策**:
- ベンチマークテストの実施
- 不要なimportの最小化
- lazy importの活用

### リスク 4: 開発時間超過
**影響**: 低  
**確率**: 中  
**緩和策**:
- 段階的な実装
- 各ステップの時間制限
- 必要に応じてスコープ調整

---

## 🎯 次のアクション

### 即座に実行
1. [ ] Phase 2テストの全成功確認
2. [ ] 現在のimport依存関係の完全マップ作成
3. [ ] 分割戦略の承認取得（Option A推奨）

### 実装前
4. [ ] 詳細な実装計画の作成
5. [ ] チェックポイントの設定
6. [ ] ロールバック戦略の準備

### 実装中
7. [ ] 各ステップでのテスト実行
8. [ ] 進捗の定期的な記録
9. [ ] 問題発生時の即座の対応

---

## 📚 参考資料

### Phase 1 & 2の学び
- Phase 1: bykilt.py分割で31%削減成功
- Phase 2: test分割で62テスト抽出、全成功
- パターン: 段階的分割 + 各ステップでのテスト

### 推奨リーディング
- Python Module Design Patterns
- Dependency Injection in Python
- Testing Strategies for Refactoring

---

**作成者**: GitHub Copilot  
**最終更新**: 2025-10-16  
**ステータス**: Phase 3 実装計画承認待ち
