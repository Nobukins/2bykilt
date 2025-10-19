# Test Execution Guide# Test Execution Guide



このガイドは、テストスイートの実行方法、依存関係管理、テスト分離、成果物クリーンアップ、イベントループ管理など、テスト実行における包括的な知識を提供します。This guide documents how to run, filter, and maintain the 2bykilt test suite after the async stabilization & skip reduction work (106 → 31 skips).



## 目次## Quick Start



1. [クイックスタート](#クイックスタート)```bash

2. [環境変数とその影響](#環境変数とその影響)# Run full suite (fastest typical path) – skips env-gated tests automatically

3. [テスト分離と実行順序](#テスト分離と実行順序)pytest -q

4. [依存関係管理](#依存関係管理)

5. [成果物クリーンアップと再現性](#成果物クリーンアップと再現性)# Focus on batch engine (recently refactored async logic)

6. [イベントループ管理](#イベントループ管理)pytest tests/test_batch_engine.py -v

7. [テストレイヤーとマーカー](#テストレイヤーとマーカー)

8. [プッシュ前検証](#プッシュ前検証)# Run Feature Flag tests (Issue #272 - Admin UI & new API methods)

9. [トラブルシューティング決定木](#トラブルシューティング決定木)pytest tests/unit/ui/admin/ tests/unit/config/test_feature_flags_new_methods.py -v

10. [ベストプラクティス](#ベストプラクティス)

# Run only non-LLM unit-ish layers (safe in minimal env)

---pytest -m "not integration and not local_only" -q

```

## クイックスタート

## Environment Flags & Their Effects

```bash

# CI環境シミュレーション（プッシュ前の推奨検証）| Variable | Values | Effect |

unset BYKILT_ENV|----------|--------|--------|

ENABLE_LLM=true pytest -m "ci_safe" --cov=src --cov-report=term -v| ENABLE_LLM | true/false | Enables LLM-dependent tests (currently 1 test skipped when false) |

| RUN_LOCAL_FINAL_VERIFICATION | 1 unset | Enables heavy local verification tests (UI/browser + recording) |

# 特定のテストファイルを実行| RUN_LOCAL_INTEGRATION | 1 unset | Enables broader integration tests (network/browser/profile) |

pytest tests/path/to/test_file.py -v

Unset values are treated as disabled.

# カバレッジレポート付きで実行

pytest tests/path/to/test_file.py --cov=src --cov-report=html## Remaining Skip Categories (Snapshot)



# パターンマッチングでテスト実行| Category | Approx Count | Reason | Re-enable Path |

pytest -k "test_pattern" -v|----------|--------------|--------|----------------|

| LLM-dependent | 1 | Requires model + tokens | Set ENABLE_LLM=true |

# 完全クリーン環境での実行（最も確実）| local_only (final verification) | ~10 | Long-running / interactive | Export RUN_LOCAL_FINAL_VERIFICATION=1 |

./scripts/clean_test_artifacts.sh| integration | ~12 | Browser/env dependent & slower | Export RUN_LOCAL_INTEGRATION=1 |

./scripts/clean_test_logs.sh| git_script_integration (mocking gap) | 8 | Resolver injection not mockable yet | Refactor get_git_script_resolver (planned) |

unset BYKILT_ENV

ENABLE_LLM=true pytest -m "ci_safe" --cov=src --cov-report=term -vExact counts may shift slightly as tests evolve.

```

## Typical Test Layers / Markers (Current State)

---

Project already uses pragmatic environment gating; a future issue (#81) proposes formal marker taxonomy (unit, integration, browser, slow, etc.). Until then:

## 環境変数とその影響

- local_only: Explicitly opt-in heavy / environment sensitive tests

### コア環境変数- integration: Broader multi-component flows

- (future) browser, unit, slow: To be added per #81 acceptance criteria

| 変数 | 値 | 影響 |

|------|-----|------|## Running Specific Layers

| `ENABLE_LLM` | true/false | LLM依存機能とテストの有効化（CI では `true` が必須） |

| `BYKILT_ENV` | unset/dev/staging/prod | 設定環境の選択（CI では未設定 = デフォルト環境） |```bash

| `RUN_LOCAL_INTEGRATION` | 1/unset | 統合テストの実行制御 |# Opt into integration tests

| `RUN_LOCAL_FINAL_VERIFICATION` | 1/unset | 重い検証テストの実行制御 |RUN_LOCAL_INTEGRATION=1 pytest -m integration -v



### 重要な注意事項# Opt into final verification

RUN_LOCAL_FINAL_VERIFICATION=1 pytest -m local_only -v

⚠️ **CI環境との一致**：

- CIでは `BYKILT_ENV` が未設定# Include LLM tests

- ローカルで `BYKILT_ENV=dev` が設定されていると、CI と異なる動作をする可能性があるENABLE_LLM=true pytest -m "not local_only" -v

- **プッシュ前には必ず `unset BYKILT_ENV` を実行**```



```bash### Artifact capture integration checks

# ❌ NG: 環境変数が設定されたままテスト

export BYKILT_ENV=devThe browser automation pipeline now has a focused regression around artifact generation. It exercises both the script-based demo runner and the direct browser-control flow, asserting that screenshots, element captures, and recordings are persisted in the run directory. Run it locally with integration tests enabled:

pytest -m "ci_safe" -v  # CI と異なる動作の可能性

```bash

# ✅ OK: CI環境をシミュレートRUN_LOCAL_INTEGRATION=1 pytest tests/integration/test_artifact_capture.py -vv

unset BYKILT_ENV```

ENABLE_LLM=true pytest -m "ci_safe" -v

```The suite writes to a temp `ARTIFACTS_BASE_DIR`, so existing local artifacts are untouched. On success you should see one `*-art` run folder per test containing `screenshots/`, `elements/`, and `videos/` entries plus the standard `manifest_v2.json`.



### 環境変数の優先順位### Feature Flag Admin UI tests (Issue #272)



1. **環境変数** (`BYKILT_ENV`, `ENABLE_LLM`)The Feature Flag admin UI and API enhancement tests verify:

2. **設定ファイル** (`config/base.yml`, `config/dev/`)- **UI Component**: Gradio panel creation, data loading, filtering, and search functionality

3. **デフォルト値** (コード内のフォールバック)- **API Methods**: `get_all_flags()` and `get_flag_metadata()` with thread-safety, override handling, and consistency checks

- **Coverage**: 21 tests total (11 UI tests, 10 API tests)

---

Run these tests with:

## テスト分離と実行順序

```bash

### なぜテスト順序が重要か# All Feature Flag tests

pytest tests/unit/ui/admin/ tests/unit/config/test_feature_flags_new_methods.py -v

**問題**: ローカルで単体実行すると成功するが、全体実行で失敗するテストが存在する

# UI tests only

**原因**:pytest tests/unit/ui/admin/test_feature_flag_panel.py -v

1. **状態の汚染**: 前のテストが残した状態（ファイル、グローバル変数、モック）が影響

2. **成果物の残存**: `artifacts/runs/` に残ったファイルが後続テストに影響# API method tests only

3. **モックの未クリーンアップ**: `patch()` が適切に解除されていないpytest tests/unit/config/test_feature_flags_new_methods.py -v

4. **イベントループの残存**: 非同期テストのループが正しく閉じられていない```



### テスト分離のベストプラクティスThese tests use the actual feature_flags.yaml configuration and verify:

- Metadata structure (value, default, type, description, source, override_active)

#### 1. フィクスチャスコープの適切な使用- Runtime override behavior

- Thread-safe concurrent access

```python- Consistency between `get_all_flags()` and `get_flag_metadata()`

import pytest- UI filtering and search capabilities



# ❌ NG: テストごとに状態が共有される## Async Test Conventions

@pytest.fixture(scope="module")

def shared_state():All new async tests should:

    return {"count": 0}

1. Be declared with `async def test_*` when awaiting async code directly.

# ✅ OK: 各テストで独立した状態2. Avoid manual event loop creation/closing – rely on pytest-asyncio auto mode.

@pytest.fixture(scope="function")3. Ensure any background tasks (e.g., spawned via `asyncio.create_task`) are awaited or canceled explicitly in the test body or fixture finalizer.

def isolated_state():4. Use temporary directories (`tmp_path`) and avoid persisting state in `artifacts/` unless the test asserts on artifact outputs.

    return {"count": 0}

```## Artifact & Log Cleanup



#### 2. 一時ディレクトリの使用Two cleanup scripts (existing + new) help ensure hermetic test runs:



```python```bash

import pytest# Remove run-specific artifact directories & pytest cache

from pathlib import Path./scripts/clean_test_artifacts.sh



# ✅ OK: pytest が自動クリーンアップする一時ディレクトリ# Remove logs, coverage, htmlcov, and residual run dirs (dry run first)

def test_artifact_creation(tmp_path: Path):./scripts/clean_test_logs.sh --dry-run

    artifact_dir = tmp_path / "artifacts"./scripts/clean_test_logs.sh

    artifact_dir.mkdir()

    # テスト後、tmp_path は自動削除される# Clean Feature Flag artifacts (if test isolation issues occur)

    assert artifact_dir.exists()rm -rf artifacts/runs/*-flags

```

# ❌ NG: 実際の artifacts/ ディレクトリを汚染

def test_artifact_creation_bad():Recommended before large refactors or when investigating flakiness. Note: Feature Flag lazy artifact creation may generate `*-flags` directories during tests; clean these if test isolation issues occur.

    artifact_dir = Path("artifacts/runs/test-run")

    artifact_dir.mkdir(parents=True)## Common Commands

    # テスト後も残り続ける！

``````bash

# Verbose skip reasons (inventory)

#### 3. コンテキストマネージャーでのモックpytest -rs -q



```python# Single test debug

from unittest.mock import patchpytest tests/test_batch_engine.py::TestStartBatch::test_creates_new_batch -vv



# ❌ NG: モックがテスト外で解除される# Fail fast & show locals

def test_config_without_multi_env():pytest -x --showlocals

    with patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False):

        config = default_config()# Only modified tests since main

    # ここでモックは既に解除されているpytest $(git diff --name-only origin/main | grep '^tests/' | tr '\n' ' ')

    assert config['use_multi_env'] is False  # 失敗する可能性```



# ✅ OK: すべての検証をコンテキスト内で実行## Adding New Tests – Checklist

def test_config_without_multi_env():

    with patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False):- [ ] Use deterministic data (no real network unless integration-marked)

        config = default_config()- [ ] Prefer factories/fixtures for complex objects

        assert config['use_multi_env'] is False  # 成功- [ ] Clean up artifacts or write to tmp_path

```- [ ] Avoid real sleeps > 0.1s (use async timeouts / monkeypatch) unless integration

- [ ] If test requires environment asset (browser/profile) – gate with env flag

#### 4. モジュールレベル変数のモック（Issue #340で発見）

## Metrics Related Testing

```python

# src/utils/default_config_settings.pyBatch engine metrics now include `batch_jobs_stopped`. When expanding metrics:

MULTI_ENV_AVAILABLE = is_multi_env_config_available()  # モジュールインポート時に評価

- Provide a `_record_*` helper mirroring `_record_batch_stop_metrics` pattern

# ❌ NG: 文字列ベースの patch は動作しない- Patch/spy metric collector in tests for assertion isolation

def test_default_config():

    with patch('src.utils.default_config_settings.MULTI_ENV_AVAILABLE', False):## Dealing With git_script_integration Skips

        config = default_config()  # MULTI_ENV_AVAILABLE は既に評価済み

Current blockers: Mocking `get_git_script_resolver` and side effects of cloning/copying. Planned approach (post-PR):

# ✅ OK: patch.object() を使用

import src.utils.default_config_settings as config_module- Introduce resolver injection via fixture or parameter

- Provide lightweight in-memory or tempdir fake repo

def test_default_config():- Remove class-level skips incrementally

    with patch.object(config_module, 'MULTI_ENV_AVAILABLE', False):

        config = default_config()  # 正しくモックされる## Failure Triage Flow

```

1. Re-run with `-vv -k failing_test_name` to isolate

### 実行順序の問題を検出する方法2. If async warning appears: ensure the test function is async & awaited

3. If artifacts mismatch: run cleanup scripts and retry

```bash4. If event loop RuntimeError: check for manual loop manipulation or lingering tasks

# 1. 単体で実行（通常は成功）5. If path errors inside simulation: ensure job manifest includes required task/command structure

pytest tests/path/to/test_file.py::test_specific -v

## Roadmap Links

# 2. 全体で実行（失敗する可能性）

pytest tests/path/to/test_file.py -v- Issue #263: Event loop teardown/runtime stabilization (addressed by async refactors & ordering rules)

- Issue #101: Recording stability & generation – baseline stabilized, further refinements future scope

# 3. ランダム順序で実行（順序依存を検出）- Issue #81: Test layering & marker formalization – next structural enhancement

pip install pytest-randomly- Issue #272: Feature Flag Admin UI – Gradio-based management panel with comprehensive test coverage (21 tests)

pytest tests/path/to/test_file.py --randomly-dont-shuffle  # ベースライン

pytest tests/path/to/test_file.py  # ランダム順序## Known Gaps (Post-Work)



# 4. 失敗するテストの前後を特定| Gap | Impact | Planned Remedy |

pytest tests/path/to/test_file.py -v --lf  # 前回の失敗のみ再実行|-----|--------|----------------|

pytest tests/path/to/test_file.py -v -x    # 最初の失敗で停止| Missing formal marker schema | Harder selective CI matrix | Implement per #81 |

```| git_script resolver not injectable | 8 tests skipped | Refactor factory + fixture |

| Single remaining LLM skip | Minor coverage gap | Enable in LLM-capable CI lane |

---

## Suggested CI Profiles (Future)

## 依存関係管理

| Profile | Command | Purpose |

### モジュールレベルでの依存関係|---------|---------|---------|

| fast | `pytest -m "not integration and not local_only"` | PR gating |

**問題**: モジュールインポート時に評価される変数は、テスト内でモックするのが困難| extended | `RUN_LOCAL_INTEGRATION=1 pytest -m "integration and not local_only"` | Nightly/integration |

| full | `ENABLE_LLM=true RUN_LOCAL_*=1 pytest` | Exhaustive / manual release gate |

**例**: Issue #340 で発見された問題

## Appendix – Legacy Cleanup Note

```python

# src/utils/default_config_settings.py (11行目)Simulation tests previously assumed lightweight automation stubs; the engine now executes real automation flow requiring valid task/command fields. Old assumptions were updated; future changes should keep simulation test semantics aligned with engine contract evolution.

MULTI_ENV_AVAILABLE = is_multi_env_config_available()

---

# この変数はモジュールがインポートされた瞬間に評価されるMaintainers: Update this document whenever skip policy, markers, or environment flags change.

# つまり、テスト開始前に既に値が確定している
```

### 解決パターン

#### パターン1: patch.object() の使用

```python
import src.utils.default_config_settings as config_module
from unittest.mock import patch

def test_legacy_config():
    # ✅ モジュールオブジェクトを直接パッチ
    with patch.object(config_module, 'MULTI_ENV_AVAILABLE', False):
        config = default_config()
        assert config['use_multi_env'] is False
```

#### パターン2: 関数化して遅延評価

```python
# ❌ NG: モジュールレベルで即座に評価
MULTI_ENV_AVAILABLE = is_multi_env_config_available()

# ✅ OK: 関数にして呼び出し時に評価
def get_multi_env_available():
    return is_multi_env_config_available()

# 使用時
if get_multi_env_available():
    # ...
```

### 循環インポートの回避

```python
# ❌ NG: 循環インポート
# module_a.py
from module_b import some_function

# module_b.py
from module_a import some_class

# ✅ OK: 遅延インポート
# module_a.py
def use_some_function():
    from module_b import some_function
    return some_function()
```

### LLM依存関係の管理

```python
# ✅ OK: 条件付きインポート
from src.config.env_config import is_llm_enabled

if is_llm_enabled():
    from langchain.llms import OpenAI
    # LLM関連の処理
else:
    # フォールバック処理
    pass

# テスト側
@pytest.mark.skipif(not is_llm_enabled(), reason="LLM機能が無効")
def test_llm_feature():
    # LLM依存のテスト
    pass
```

---

## 成果物クリーンアップと再現性

### なぜクリーンアップが必要か

**問題**: テスト実行時に生成された成果物が残り続け、後続のテストに影響する

**影響を受けやすいケース**:
1. **アーティファクト検証テスト**: 「ディレクトリが空である」ことを期待するテスト
2. **ファイルカウントテスト**: 「N個のファイルが生成される」ことを検証するテスト
3. **マニフェスト検証**: 「特定の構造のJSONが存在する」ことを確認するテスト
4. **録画ファイルテスト**: 「.webm ファイルが存在する」ことを検証するテスト

### クリーンアップスクリプト

#### 1. 成果物クリーンアップ: `scripts/clean_test_artifacts.sh`

```bash
#!/bin/bash
# テスト生成物を削除（キャッシュとアーティファクト）

./scripts/clean_test_artifacts.sh

# 削除対象:
# - artifacts/runs/TESTRUN*-art
# - artifacts/runs/test-art
# - src/artifacts/runs/TEST*-art
# - .pytest_cache
```

**使用タイミング**:
- ✅ プッシュ前の最終検証前
- ✅ テスト失敗時のトラブルシューティング
- ✅ CI環境シミュレーション前

#### 2. ログとカバレッジクリーンアップ: `scripts/clean_test_logs.sh`

```bash
#!/bin/bash
# ログ、カバレッジ、キャッシュを削除

./scripts/clean_test_logs.sh --dry-run  # プレビュー
./scripts/clean_test_logs.sh            # 実行

# 削除対象:
# - logs/*
# - htmlcov/
# - .coverage
# - coverage.xml
# - .pytest_cache
# - tmp/*
```

**使用タイミング**:
- ✅ カバレッジレポートの再生成前
- ✅ ディスク容量の確保
- ✅ クリーンな状態からの開発開始時

### クリーンアップのベストプラクティス

#### プッシュ前の完全クリーンアップワークフロー

```bash
#!/bin/bash
# pre-push-validation.sh

set -e

echo "🧹 Step 1: クリーンアップ"
./scripts/clean_test_artifacts.sh
./scripts/clean_test_logs.sh

echo "🔧 Step 2: 環境設定"
unset BYKILT_ENV
export ENABLE_LLM=true

echo "🧪 Step 3: テスト実行"
pytest -m "ci_safe" --cov=src --cov-report=term -v

echo "✅ すべてのチェック完了！プッシュ可能です"
```

#### テスト内でのクリーンアップ

```python
import pytest
from pathlib import Path
import shutil

@pytest.fixture(autouse=True)
def cleanup_artifacts():
    """各テストの前後でアーティファクトをクリーンアップ"""
    # テスト前のクリーンアップ
    artifact_dir = Path("artifacts/runs/test-art")
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    
    yield  # テスト実行
    
    # テスト後のクリーンアップ
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
```

### Feature Flag アーティファクトのクリーンアップ

```bash
# Feature Flag 遅延生成により *-flags ディレクトリが作成される
rm -rf artifacts/runs/*-flags

# 特定のテスト実行ディレクトリのみ削除
rm -rf artifacts/runs/TESTRUN-*
```

---

## イベントループ管理

### イベントループ問題の背景（Issue #263）

**問題**: 非同期テストで以下のエラーが頻発

```
RuntimeError: This event loop is already running
RuntimeError: Cannot close a running event loop
RuntimeError: Runner is closed
PytestUnhandledCoroutineWarning
```

**根本原因**:
1. **手動ループ管理**: テスト内で `asyncio.get_event_loop()` を手動で作成・閉じている
2. **pytest-asyncio の競合**: `pytest-asyncio` の自動管理とバッティング
3. **バックグラウンドタスクの未完了**: タスクが実行中のままループを閉じようとする
4. **フィクスチャのスコープミス**: モジュールスコープのループを複数テストで共有

### ベストプラクティス: pytest-asyncio に任せる

#### ❌ NG: 手動でイベントループを管理

```python
import asyncio

def test_async_function():
    loop = asyncio.get_event_loop()  # ❌ 手動作成
    result = loop.run_until_complete(my_async_function())
    loop.close()  # ❌ 手動クローズ
    assert result == expected
```

#### ✅ OK: pytest-asyncio の自動管理

```python
import pytest

@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected
```

### pytest-asyncio の設定

```ini
# pytest.ini
[pytest]
asyncio_mode = auto  # 自動的に async def test_* を検出
```

**`auto` モードの利点**:
- `@pytest.mark.asyncio` デコレータが不要
- イベントループの自動作成・破棄
- テスト間の完全な分離

### 非同期フィクスチャのベストプラクティス

```python
import pytest

# ✅ OK: 非同期フィクスチャ
@pytest.fixture
async def async_resource():
    resource = await create_resource()
    yield resource
    await resource.cleanup()

# ✅ OK: 使用例
async def test_with_async_fixture(async_resource):
    result = await async_resource.do_something()
    assert result is not None
```

### バックグラウンドタスクの適切な管理

```python
import asyncio
import pytest

# ❌ NG: タスクを放置
async def test_background_task():
    task = asyncio.create_task(long_running_operation())
    result = await some_other_operation()
    # task が実行中のままテスト終了

# ✅ OK: タスクを適切にキャンセル
async def test_background_task():
    task = asyncio.create_task(long_running_operation())
    try:
        result = await some_other_operation()
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
```

### イベントループデバッグ

```bash
# イベントループ関連のエラーを詳細表示
pytest tests/test_async.py -v --log-cli-level=DEBUG

# 未完了タスクの警告を有効化
PYTHONWARNINGS="default" pytest tests/test_async.py -v
```

---

## テストレイヤーとマーカー

### 現在のマーカー分類

| マーカー | 説明 | 実行条件 |
|---------|------|---------|
| `ci_safe` | CI環境で実行可能 | デフォルト実行対象（1042テスト） |
| `local_only` | ローカル専用（重い検証） | `RUN_LOCAL_FINAL_VERIFICATION=1` |
| `integration` | 統合テスト（ブラウザ依存） | `RUN_LOCAL_INTEGRATION=1` |
| `llm` | LLM機能依存 | `ENABLE_LLM=true` |
| `git_script_integration` | Git スクリプト統合 | リファクタ待ち（8テスト） |

### マーカー使用例

```python
import pytest

@pytest.mark.ci_safe
def test_basic_functionality():
    """CI で実行される基本テスト"""
    assert True

@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("RUN_LOCAL_INTEGRATION") != "1",
    reason="Integration tests require RUN_LOCAL_INTEGRATION=1"
)
def test_browser_integration():
    """ブラウザ統合テスト"""
    pass

@pytest.mark.local_only
def test_heavy_verification():
    """重い検証テスト（ローカル専用）"""
    pass
```

### スキップカテゴリ（31テスト）

| カテゴリ | 概数 | 理由 | 有効化方法 |
|---------|------|------|-----------|
| LLM依存 | 1 | LLM機能が必要 | `ENABLE_LLM=true` |
| local_only | ~10 | 長時間実行/インタラクティブ | `RUN_LOCAL_FINAL_VERIFICATION=1` |
| integration | ~12 | ブラウザ/環境依存 | `RUN_LOCAL_INTEGRATION=1` |
| git_script_integration | 8 | Resolver リファクタ待ち | 計画中 |

### 実行例

```bash
# CI セーフテストのみ（デフォルト）
pytest -m "ci_safe" -v

# 統合テストも含める
RUN_LOCAL_INTEGRATION=1 pytest -m "ci_safe or integration" -v

# すべてのテストを実行
RUN_LOCAL_INTEGRATION=1 RUN_LOCAL_FINAL_VERIFICATION=1 pytest -v

# LLM機能付きで実行
ENABLE_LLM=true pytest -m "ci_safe" -v
```

---

## プッシュ前検証

### 必須チェックリスト

```bash
# ✅ 1. 環境変数のクリーンアップ
unset BYKILT_ENV

# ✅ 2. 成果物のクリーンアップ
./scripts/clean_test_artifacts.sh
./scripts/clean_test_logs.sh

# ✅ 3. CI環境シミュレーション
ENABLE_LLM=true pytest -m "ci_safe" --cov=src --cov-report=term -v

# ✅ 4. 修正したファイルのみテスト（高速チェック）
pytest tests/path/to/modified_test.py -v

# ✅ 5. カバレッジ確認
pytest -m "ci_safe" --cov=src --cov-report=html
open htmlcov/index.html  # カバレッジレポートを確認
```

### プッシュ前の一般的な問題

#### 問題1: ローカルで成功、CI で失敗

**原因**:
- `BYKILT_ENV=dev` が設定されている
- 古い成果物が残っている
- テスト実行順序が異なる

**解決**:
```bash
unset BYKILT_ENV
./scripts/clean_test_artifacts.sh
./scripts/clean_test_logs.sh
ENABLE_LLM=true pytest -m "ci_safe" -v
```

#### 問題2: モジュールレベル変数のモック失敗

**原因**:
- 文字列ベースの `patch()` を使用
- 変数がインポート時に評価済み

**解決**:
```python
# ❌ NG
with patch('module.VARIABLE', False):
    pass

# ✅ OK
import module
with patch.object(module, 'VARIABLE', False):
    pass
```

#### 問題3: インデントエラー（アサーションがコンテキスト外）

**原因**:
- `with` ブロックの外でアサーション
- モックが既に解除されている

**解決**:
```python
# ❌ NG
with patch.object(module, 'VARIABLE', False):
    result = function()
assert result == expected  # モック解除済み

# ✅ OK
with patch.object(module, 'VARIABLE', False):
    result = function()
    assert result == expected  # モック有効
```

### 実行時間の目安

| テスト範囲 | 実行時間（目安） |
|-----------|----------------|
| 単一テストファイル | 5-10秒 |
| ci_safe 全体（1042テスト） | 2-5分 |
| CI 全体実行 | 5-8分 |

**推奨**: プッシュ前に少なくとも修正ファイルのテストを実行

---

## トラブルシューティング決定木

### ステップ1: エラーの分類

```
テスト失敗
├─ ローカルで成功、CI で失敗
│  └─ → 環境変数チェック（BYKILT_ENV, ENABLE_LLM）
│     └─ → 成果物クリーンアップ
│        └─ → テスト順序確認
│
├─ ローカルでも失敗
│  ├─ ImportError / ModuleNotFoundError
│  │  └─ → ENABLE_LLM 確認
│  │     └─ → 依存関係インストール確認
│  │
│  ├─ RuntimeError (event loop)
│  │  └─ → イベントループ管理確認
│  │     └─ → pytest-asyncio 設定確認
│  │
│  ├─ AssertionError
│  │  └─ → モックスコープ確認
│  │     └─ → インデント確認
│  │
│  └─ FileNotFoundError / ディレクトリ関連
│     └─ → 成果物クリーンアップ
│        └─ → tmp_path 使用確認
│
└─ 間欠的失敗
   └─ → テスト順序依存確認
      └─ → pytest-randomly でランダム実行
         └─ → フィクスチャスコープ確認
```

### ステップ2: 診断コマンド

```bash
# 1. 環境変数の確認
env | grep -E "BYKILT|ENABLE_LLM|RUN_LOCAL"

# 2. 成果物の確認
ls -la artifacts/runs/
ls -la .pytest_cache/

# 3. 単体実行で問題を切り分け
pytest tests/path/to/test_file.py::test_specific -xvs

# 4. テスト順序の影響を確認
pytest tests/path/to/test_file.py -v  # 全体
pytest tests/path/to/test_file.py::test_specific -v  # 単体

# 5. モックの状態を確認
pytest tests/path/to/test_file.py -v --log-cli-level=DEBUG

# 6. カバレッジで実行パスを確認
pytest tests/path/to/test_file.py --cov=src --cov-report=term-missing -v
```

### ステップ3: よくある解決パターン

#### パターン1: 環境変数リセット

```bash
# すべての環境変数をクリア
unset BYKILT_ENV
unset RUN_LOCAL_INTEGRATION
unset RUN_LOCAL_FINAL_VERIFICATION

# CI環境を再現
export ENABLE_LLM=true
pytest -m "ci_safe" -v
```

#### パターン2: 完全クリーンアップ

```bash
# すべてをクリーンアップ
./scripts/clean_test_artifacts.sh
./scripts/clean_test_logs.sh
rm -rf artifacts/runs/*
rm -rf .pytest_cache/

# 再実行
pytest -m "ci_safe" -v
```

#### パターン3: 依存関係の再インストール

```bash
# 仮想環境の再作成
deactivate
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
```

---

## ベストプラクティス

### 1. テスト作成時のチェックリスト

- [ ] `tmp_path` を使用してアーティファクトを分離
- [ ] モックは `with` コンテキスト内でアサーション
- [ ] モジュールレベル変数は `patch.object()` を使用
- [ ] 非同期テストは `async def` + pytest-asyncio
- [ ] バックグラウンドタスクは `finally` でキャンセル
- [ ] フィクスチャスコープは最小限（`function`）
- [ ] 適切なマーカー（`ci_safe`, `integration` など）を設定

### 2. プッシュ前のチェックリスト

- [ ] `unset BYKILT_ENV` で環境変数をクリア
- [ ] `./scripts/clean_test_artifacts.sh` で成果物を削除
- [ ] `./scripts/clean_test_logs.sh` でログをクリア
- [ ] `ENABLE_LLM=true pytest -m "ci_safe" -v` で CI シミュレーション
- [ ] 修正したテストファイルを個別に実行して確認
- [ ] カバレッジが 65% 以上であることを確認

### 3. CI失敗時の対応フロー

1. **ローカルでの再現**:
   ```bash
   unset BYKILT_ENV
   ENABLE_LLM=true pytest -m "ci_safe" -v
   ```

2. **失敗テストの切り分け**:
   ```bash
   pytest tests/path/to/failing_test.py::test_name -xvs
   ```

3. **モックとインデントの確認**:
   - すべてのアサーションが `with` ブロック内にあるか
   - `patch.object()` を使用しているか

4. **成果物の影響確認**:
   ```bash
   ./scripts/clean_test_artifacts.sh
   pytest tests/path/to/failing_test.py -v
   ```

5. **修正とコミット**:
   ```bash
   git add tests/path/to/failing_test.py
   git commit -m "fix: correct test isolation issue"
   git push
   ```

### 4. コードレビュー時の確認ポイント

- [ ] テストは CI 環境で実行可能か（`ci_safe` マーカー）
- [ ] `tmp_path` を使用しているか
- [ ] モックのスコープは適切か
- [ ] 非同期テストのイベントループ管理は適切か
- [ ] テスト順序に依存していないか
- [ ] 環境変数の依存は明示されているか

---

## 関連ドキュメント

- **Issue #340**: テストカバレッジ 20% → 65% への改善
- **Issue #263**: イベントループ安定化
- **Issue #101**: 録画機能の安定性
- **Issue #81**: テストマーカーの形式化
- **Issue #272**: Feature Flag Admin UI

- **スクリプト**:
  - `scripts/clean_test_artifacts.sh` - 成果物クリーンアップ
  - `scripts/clean_test_logs.sh` - ログとカバレッジクリーンアップ

- **設定ファイル**:
  - `pytest.ini` - pytest 設定（asyncio_mode = auto）
  - `pyproject.toml` - カバレッジ設定
  - `.github/copilot-instructions.md` - プッシュ前検証ルール

---

## まとめ

このガイドは、2bykilt プロジェクトでのテスト実行における包括的な知識を提供します。

**重要なポイント**:
1. ✅ プッシュ前には必ず `unset BYKILT_ENV` と成果物クリーンアップを実行
2. ✅ モジュールレベル変数は `patch.object()` でモック
3. ✅ すべてのアサーションは `with` コンテキスト内で実行
4. ✅ 非同期テストは pytest-asyncio に任せる
5. ✅ テスト分離のため `tmp_path` を使用

**最終チェック**:
```bash
unset BYKILT_ENV
./scripts/clean_test_artifacts.sh
./scripts/clean_test_logs.sh
ENABLE_LLM=true pytest -m "ci_safe" --cov=src --cov-report=term -v
```

このワークフローに従うことで、ローカルと CI の両方で安定したテスト実行が可能になります。
