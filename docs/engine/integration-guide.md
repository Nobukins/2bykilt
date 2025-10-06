# Phase1-2 統合ガイド

本ドキュメントでは、BrowserEngine と LLMServiceGateway の統合方法を説明します。

## 1. BrowserEngine の利用方法

### 1.1 基本的な使用例

```python
from src.browser.engine.loader import EngineLoader
from src.browser.engine.browser_engine import LaunchContext

async def main():
    # フィーチャーフラグから自動選択（環境変数 RUNNER_ENGINE=playwright|cdp）
    engine = EngineLoader.load_engine()
    
    try:
        # エンジン起動
        await engine.launch(LaunchContext(
            headless=True,
            trace_enabled=True,
            browser_type="chromium"
        ))
        
        # ナビゲーション
        result = await engine.navigate("https://example.com")
        print(f"Navigate: {result.success}, duration={result.duration_ms}ms")
        
        # クリックアクション
        result = await engine.dispatch({
            "type": "click",
            "selector": "#button"
        })
        
        # アーティファクト取得
        artifacts = await engine.capture_artifacts(["screenshot", "trace"])
        print(f"Artifacts: {artifacts}")
        
    finally:
        await engine.shutdown()
```

### 1.2 unlock-future 互換実行

```python
from src.browser.engine.loader import EngineLoader
from src.browser.unlock_future_adapter import UnlockFutureAdapter

async def run_unlock_future():
    engine = EngineLoader.load_engine("playwright")  # または "cdp"
    adapter = UnlockFutureAdapter(engine)
    
    try:
        await engine.launch(LaunchContext(headless=False))
        
        # unlock-future JSON 形式のコマンド
        commands = [
            {"action": "command", "args": ["https://example.com"]},
            {"action": "fill_form", "args": ["#search", "test query"]},
            {"action": "click", "args": ["#submit"]},
            {"action": "screenshot", "args": ["result.png"]}
        ]
        
        results = await adapter.execute_unlock_future_commands(commands)
        
        for i, result in enumerate(results):
            print(f"Command {i+1}: {result.success}, {result.duration_ms}ms")
        
    finally:
        await engine.shutdown()
```

## 2. LLMServiceGateway の利用方法

### 2.1 基本的な使用例

```python
from src.llm import get_llm_gateway

async def use_llm():
    gateway = get_llm_gateway()
    
    try:
        await gateway.initialize()
        
        if gateway.is_enabled():
            response = await gateway.invoke_llm(
                prompt="Explain browser automation",
                config={"model": "gpt-4", "temperature": 0.7}
            )
            print(f"LLM Response: {response['text']}")
        else:
            print("LLM is disabled (ENABLE_LLM=false)")
    
    finally:
        await gateway.shutdown()
```

### 2.2 ENABLE_LLM フラグ制御

```bash
# LLM 無効（デフォルト）
export ENABLE_LLM=false
python run_task.py

# LLM 有効（Phase3 でサンドボックス実装後に動作）
export ENABLE_LLM=true
python run_task.py
```

## 3. フィーチャーフラグ設定

### 3.1 環境変数

```bash
# ブラウザエンジン選択
export RUNNER_ENGINE=playwright  # または cdp

# LLM 機能トグル
export ENABLE_LLM=false  # または true

# 実行
python -m src.script.script_manager execute-unlock-future sample.json
```

### 3.2 設定ファイル（将来拡張）

`config/feature_flags.yaml` (Phase3 で実装予定):

```yaml
runner:
  engine: playwright  # playwright | cdp
  
llm:
  enabled: false
  sandbox_mode: docker  # docker | firecracker | none (Phase3)
  
ui:
  modern_layout: false
  trace_viewer: false
```

## 4. テスト実行

### 4.1 ユニットテスト

```bash
# すべてのエンジンテスト
pytest tests/unit/browser/engine/ -v

# 特定のテストファイル
pytest tests/unit/browser/engine/test_playwright_engine.py -v

# カバレッジ付き
pytest tests/unit/browser/engine/ --cov=src/browser/engine --cov-report=html
```

### 4.2 統合テスト（Phase2 後半で追加）

```bash
# unlock-future 互換テスト
pytest tests/integration/browser/engine/test_unlock_future_compat.py -v

# エンジン切替テスト
RUNNER_ENGINE=playwright pytest tests/integration/browser/engine/test_engine_switching.py -v
RUNNER_ENGINE=cdp pytest tests/integration/browser/engine/test_engine_switching.py -v
```

## 5. トラブルシューティング

### 5.1 CDP エンジンが利用できない

**症状**: `EngineLoader.load_engine("cdp")` で ValueError

**原因**: cdp-use パッケージ未インストール

**解決策**:
```bash
pip install cdp-use>=0.6.0
```

### 5.2 LLM 機能が動作しない

**症状**: `gateway.is_enabled()` が False を返す

**原因**: ENABLE_LLM 環境変数が未設定または false

**解決策**:
```bash
export ENABLE_LLM=true
```

Phase3 でサンドボックス実装が完成するまでは、有効化してもスタブレスポンスのみ返されます。

### 5.3 トレースファイルが生成されない

**症状**: `capture_artifacts(["trace"])` で trace が空

**原因**: LaunchContext で `trace_enabled=False`

**解決策**:
```python
context = LaunchContext(trace_enabled=True)
await engine.launch(context)
```

## 6. 次のステップ

- **Phase3**: UI モジュール化と LLM サンドボックス実装
- **Phase4**: CDP 高度な機能、セキュリティレビュー、本番展開

詳細は `docs/plan/cdp-webui-modernization.md` を参照してください。
