# LLM Dependency Detailed Analysis - Issue #43

**作成日**: 2025-10-16  
**目的**: ENABLE_LLM=false 時に requirements-minimal.txt のみで動作させるための完全なLLM依存排除

## 🎯 達成目標

### 必須条件
1. ✅ ENABLE_LLM=false で LLM関連パッケージが一切不要
2. ✅ requirements-minimal.txt のみで起動・動作
3. ✅ 遅延インポート (lazy import) による条件付き読み込み
4. ✅ 静的解析で検証可能な完全分離

## 📦 LLM関連パッケージ (排除対象)

### Tier 1: コアLLMライブラリ
- `langchain` / `langchain-*` (全バリエーション)
- `openai`
- `anthropic`
- `deepseek`
- `ollama`

### Tier 2: 拡張機能
- `browser-use` (LLMエージェント機能)
- `mem0ai` (メモリ管理)
- `faiss-cpu` (ベクトル検索)

## 📋 ファイル別LLM依存状況

### 🔴 Critical - 完全遅延ロード必須

#### 1. `src/utils/llm.py` (136 lines)
**現状**: 無条件で全LLMライブラリをインポート
```python
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.globals import get_llm_cache
from langchain_ollama import ChatOllama
# ... 多数のlangchain imports
```

**対応**: ファイル全体を条件付きインポート化
- Option A: ファイル冒頭で `if not ENABLE_LLM: raise ImportError("LLM disabled")`
- Option B: 全関数を遅延インポート化
- **推奨**: Option A (シンプル)

**影響範囲**: 
- `src/agent/custom_agent.py`
- `src/agent/agent_manager.py`
- その他 LLM 機能を使用する全モジュール

---

#### 2. `src/utils/deep_research.py` (426 lines)
**現状**: 一部条件付きインポート実装済み（行19-37）
```python
if ENABLE_LLM:
    try:
        from src.agent.custom_agent import CustomAgent
        # ... LLM関連インポート
        LLM_RESEARCH_AVAILABLE = True
    except ImportError:
        LLM_RESEARCH_AVAILABLE = False
else:
    LLM_RESEARCH_AVAILABLE = False
```

**問題**: `browser-use` のインポートが無条件（行41-44）
```python
from browser_use.browser.browser import BrowserConfig, Browser
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller, DoneAction
```

**対応**: `browser-use` も条件付き化
```python
if ENABLE_LLM and LLM_RESEARCH_AVAILABLE:
    from browser_use.browser.browser import BrowserConfig, Browser
    # ...
```

---

#### 3. `src/agent/` ディレクトリ (全ファイル)
**ファイル一覧**:
- `custom_agent.py`
- `custom_message_manager.py`
- `custom_prompts.py`
- `custom_views.py`
- `agent_manager.py`

**現状**: LLM機能の中核モジュール、langchain に全面依存

**対応**: 
- モジュールレベルで条件付きインポートガード
- 各ファイル冒頭に追加:
```python
import os
from src.config.feature_flags import is_llm_enabled

if not is_llm_enabled():
    raise ImportError(
        "LLM functionality is disabled. "
        "Set ENABLE_LLM=true to use agent features."
    )
```

---

#### 4. `src/llm/docker_sandbox.py`
**現状**: LLM用サンドボックス機能

**対応**: 同様に条件付きインポートガード

---

#### 5. `src/controller/custom_controller.py`
**現状**: `browser-use` に依存
```python
from browser_use.agent.views import ActionResult
from browser_use.browser.context import BrowserContext
from browser_use.controller.service import Controller, DoneAction
```

**対応**: 条件付きインポートガード

---

#### 6. `src/browser/custom_browser.py`, `custom_context.py`
**現状**: `browser-use` の Browser, BrowserContext をラップ

**対応**: 条件付きインポートガード

---

### 🟡 Medium - 条件分岐追加

#### 7. `src/ui/components/run_panel.py`
**現状**: UI要素に LLM 関連タブが含まれる可能性

**対応**: 
- LLM機能の UI 要素を条件表示
- Gradio タブの動的生成

```python
def create_run_panel():
    components = [...]
    
    if is_llm_enabled():
        # LLM関連タブを追加
        components.append(create_llm_tab())
    
    return gr.TabbedInterface(components)
```

---

#### 8. `src/config/config_adapter.py`
**現状**: LLM設定の読み込み

**対応**: LLM設定の条件読み込み
```python
def load_config():
    config = load_base_config()
    
    if is_llm_enabled():
        config.update(load_llm_config())
    
    return config
```

---

#### 9. `src/security/secret_masker.py`, `secrets_vault.py`
**現状**: LLM API キーのマスキング処理を含む可能性

**対応**: LLM関連秘密情報の条件処理

---

#### 10. `src/utils/utils.py`
**現状**: ユーティリティ関数集

**対応**: LLM機能チェック関数の追加
```python
def is_llm_available() -> bool:
    """Check if LLM functionality is available."""
    try:
        from src.config.feature_flags import is_llm_enabled
        return is_llm_enabled()
    except ImportError:
        return False

def require_llm():
    """Decorator to guard LLM-requiring functions."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if not is_llm_available():
                raise RuntimeError(
                    f"{func.__name__} requires LLM functionality. "
                    "Set ENABLE_LLM=true and install full requirements."
                )
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

### 🟢 Low - 参照のみ、修正不要

#### 11. `src/ui/browser_agent.py`, `stream_manager.py`
**現状**: LLM機能を呼び出す側

**対応**: すでに条件分岐されている可能性。要確認。

---

## 🛠️ 実装戦略

### Phase 1: コアモジュールの遅延ロード化

#### Step 1.1: `src/utils/llm.py` の完全分離
```python
# src/utils/llm.py - 新しい冒頭
"""
LLM utility functions.
Requires ENABLE_LLM=true and full requirements.txt installation.
"""
import os
from src.config.feature_flags import is_llm_enabled

if not is_llm_enabled():
    raise ImportError(
        "LLM functionality is disabled. "
        "Set ENABLE_LLM=true and install requirements.txt (not requirements-minimal.txt) "
        "to use LLM features."
    )

# 既存の import 文はそのまま
from openai import OpenAI
from langchain_openai import ChatOpenAI
# ...
```

#### Step 1.2: `src/agent/*` の完全分離
各ファイルに同様のガードを追加

#### Step 1.3: `src/utils/deep_research.py` の修正
`browser-use` インポートを条件化:
```python
if ENABLE_LLM and LLM_RESEARCH_AVAILABLE:
    from browser_use.browser.browser import BrowserConfig, Browser
    from browser_use.agent.views import ActionResult
    from browser_use.browser.context import BrowserContext
    from browser_use.controller.service import Controller, DoneAction
else:
    # Stub classes
    class BrowserConfig: pass
    class Browser: pass
    class ActionResult: pass
    class BrowserContext: pass
    class Controller: pass
    class DoneAction: pass
```

---

### Phase 2: UI/設定の条件分岐

#### Step 2.1: UI コンポーネントの動的構築
`src/ui/components/run_panel.py`:
```python
def create_tabs():
    tabs = []
    tabs.append(create_base_tabs())  # 基本タブ
    
    if is_llm_enabled():
        tabs.append(create_llm_tabs())  # LLMタブ
    
    return tabs
```

#### Step 2.2: 設定の条件読み込み
`src/config/config_adapter.py`:
```python
def load_full_config():
    config = load_minimal_config()
    
    if is_llm_enabled():
        try:
            config.update(load_llm_config())
        except ImportError as e:
            logger.warning(f"LLM config skipped: {e}")
    
    return config
```

---

### Phase 3: 静的解析とテスト

#### Step 3.1: 検証スクリプト作成
```python
# scripts/verify_llm_isolation.py
import subprocess
import sys

def test_minimal_imports():
    """Test that minimal env can start without LLM packages."""
    code = """
import sys
import os
os.environ['ENABLE_LLM'] = 'false'

# Try importing main modules
from src.config import config_adapter
from src.utils import utils
from src.browser import browser_config
# Skip: from src.agent import custom_agent  # Should not import

print("✅ Minimal imports successful")
"""
    
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ Minimal import test failed:\n{result.stderr}")
        return False
    
    print(result.stdout)
    return True

def verify_no_llm_packages():
    """Verify LLM packages are not imported in minimal mode."""
    forbidden = [
        'langchain', 'openai', 'anthropic', 
        'browser-use', 'mem0', 'ollama'
    ]
    
    code = """
import sys
import os
os.environ['ENABLE_LLM'] = 'false'

# Import main app
from src import bykilt

# Check loaded modules
llm_modules = [m for m in sys.modules if any(pkg in m for pkg in {forbidden})]
if llm_modules:
    print(f"❌ LLM modules found: {llm_modules}")
    sys.exit(1)
else:
    print("✅ No LLM modules loaded")
""".format(forbidden=forbidden)
    
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True
    )
    
    return result.returncode == 0

if __name__ == "__main__":
    tests = [
        ("Minimal imports", test_minimal_imports),
        ("No LLM packages", verify_no_llm_packages),
    ]
    
    failed = []
    for name, test_func in tests:
        print(f"\n🔍 Running: {name}")
        if not test_func():
            failed.append(name)
    
    if failed:
        print(f"\n❌ Failed tests: {', '.join(failed)}")
        sys.exit(1)
    else:
        print("\n✅ All verification tests passed!")
        sys.exit(0)
```

#### Step 3.2: テストスイート拡張
```python
# tests/integration/test_minimal_env.py
import pytest
import os
import subprocess
import sys

@pytest.fixture
def minimal_env():
    """Setup minimal environment."""
    env = os.environ.copy()
    env['ENABLE_LLM'] = 'false'
    return env

def test_app_starts_without_llm(minimal_env):
    """Test that app can start with ENABLE_LLM=false."""
    code = """
import os
os.environ['ENABLE_LLM'] = 'false'
from src.config.feature_flags import is_llm_enabled
assert not is_llm_enabled()
print("✅ App started in minimal mode")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=minimal_env,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "✅" in result.stdout

def test_llm_imports_raise_error(minimal_env):
    """Test that LLM imports raise appropriate errors."""
    code = """
import os
os.environ['ENABLE_LLM'] = 'false'
try:
    from src.utils import llm
    print("❌ Should have raised ImportError")
    exit(1)
except ImportError as e:
    assert "LLM functionality is disabled" in str(e)
    print("✅ Correct ImportError raised")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=minimal_env,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
    assert "✅" in result.stdout

def test_no_forbidden_packages_loaded(minimal_env):
    """Ensure no LLM packages are loaded in minimal mode."""
    code = """
import sys
import os
os.environ['ENABLE_LLM'] = 'false'

# Import main application
# (Add actual import path)

forbidden = ['langchain', 'openai', 'anthropic', 'browser_use', 'mem0', 'ollama']
loaded_forbidden = [m for m in sys.modules if any(pkg in m for pkg in forbidden)]

if loaded_forbidden:
    print(f"❌ Forbidden packages loaded: {loaded_forbidden}")
    exit(1)
else:
    print("✅ No forbidden packages loaded")
"""
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=minimal_env,
        capture_output=True,
        text=True
    )
    assert result.returncode == 0
```

---

## 📊 影響範囲マトリクス

| モジュール | LLM依存 | 対応優先度 | 対応方法 | 工数 |
|-----------|---------|-----------|---------|------|
| `src/utils/llm.py` | 完全 | P0 | インポートガード | 0.5h |
| `src/agent/*` (5files) | 完全 | P0 | インポートガード | 1h |
| `src/llm/*` | 完全 | P0 | インポートガード | 0.5h |
| `src/utils/deep_research.py` | 部分 | P0 | browser-use条件化 | 1h |
| `src/controller/custom_controller.py` | 完全 | P0 | インポートガード | 0.5h |
| `src/browser/custom_*.py` | 完全 | P0 | インポートガード | 0.5h |
| `src/ui/components/run_panel.py` | 参照 | P1 | 条件分岐 | 1h |
| `src/config/config_adapter.py` | 参照 | P1 | 条件分岐 | 0.5h |
| `src/security/*` | 参照 | P2 | 条件分岐 | 0.5h |
| `src/utils/utils.py` | なし | P1 | ヘルパー追加 | 0.5h |
| `scripts/verify_llm_isolation.py` | - | P0 | 新規作成 | 2h |
| `tests/integration/test_minimal_env.py` | - | P0 | 新規作成 | 2h |
| ドキュメント更新 | - | P1 | 更新 | 1h |

**総工数見積もり**: 約 12-15時間 (1.5-2日)

---

## ✅ 検証チェックリスト

### Phase 1完了時
- [ ] `src/utils/llm.py` がENABLE_LLM=false時にImportError
- [ ] `src/agent/*` 全ファイルが条件付きインポート化
- [ ] `src/utils/deep_research.py` のbrowser-use条件化
- [ ] 全LLM関連モジュールにガード実装

### Phase 2完了時
- [ ] UI コンポーネントの条件表示実装
- [ ] 設定ローダーの条件分岐実装
- [ ] セキュリティモジュールの条件処理実装

### Phase 3完了時
- [ ] `scripts/verify_llm_isolation.py` 作成・実行成功
- [ ] `tests/integration/test_minimal_env.py` 全テスト通過
- [ ] requirements-minimal.txt のみでアプリ起動成功
- [ ] `sys.modules` に langchain/openai/anthropic 等が含まれないことを確認

### 最終確認
- [ ] 静的解析スクリプトがCI統合済み
- [ ] ドキュメント更新完了
- [ ] PR作成・レビュー依頼
- [ ] Issue #43 クローズ

---

## 🎓 学習リソース

### Python 遅延インポートのベストプラクティス
- モジュールレベルガード: 最もシンプル、推奨
- 関数内インポート: 細かい制御が可能だが複雑
- `TYPE_CHECKING`: 型ヒントのみの場合に有効

### 参考コード
```python
# パターン1: モジュールレベルガード (推奨)
if not ENABLE_FEATURE:
    raise ImportError("Feature disabled")

# パターン2: 関数内遅延インポート
def feature_function():
    if ENABLE_FEATURE:
        from expensive_module import ExpensiveClass
        return ExpensiveClass()
    else:
        raise RuntimeError("Feature disabled")

# パターン3: TYPE_CHECKING (型ヒントのみ)
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from expensive_module import ExpensiveClass
```

---

## 📚 次のステップ

1. ✅ **この分析ドキュメントをレビュー**
2. → **Phase 1.1 開始**: `src/utils/llm.py` のインポートガード実装
3. → **Phase 1.2**: `src/agent/*` の条件化
4. → **Phase 1.3**: その他コアモジュールの条件化
5. → **Phase 2**: UI/設定の条件分岐
6. → **Phase 3**: 検証・テスト
7. → **PR作成**

---

**作成者**: GitHub Copilot  
**レビュー待ち**: Yes  
**関連Issue**: #43
