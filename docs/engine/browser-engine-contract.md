# Browser Engine 契約仕様

- **バージョン**: 1.0.0-draft
- **作成日**: 2025-10-06
- **関連 Issue**: [#53](https://github.com/Nobukins/2bykilt/issues/53)
- **ステータス**: フェーズ0 ドラフト

## 1. 概要

本ドキュメントは 2bykilt の Runner が複数のブラウザ自動化エンジン（Playwright, CDP-use 等）を透過的に利用するための抽象化契約を定義します。

### 1.1 設計原則

- **エンジン非依存**: アクション定義（JSON 形式の `unlock-future` 等）はエンジン実装の詳細に依存しない。
- **段階的移行**: フィーチャーフラグで既存 Playwright と新規 CDP を切替可能にし、ロールバックを容易にする。
- **可観測性**: エンジンごとのレイテンシ、成功率、アーティファクト生成を統一的に収集。
- **拡張性**: 将来の新エンジン追加（Firefox 専用、native desktop 等）に対応可能な設計。

## 2. インターフェース定義

### 2.1 BrowserEngine 抽象クラス

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

class EngineType(Enum):
    """サポートするエンジンタイプ"""
    PLAYWRIGHT = "playwright"
    CDP = "cdp"
    # 将来: FIREFOX_MARIONETTE = "firefox"

@dataclass
class LaunchContext:
    """エンジン起動時のコンテキスト"""
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    viewport: Optional[Dict[str, int]] = None
    user_agent: Optional[str] = None
    proxy: Optional[Dict[str, str]] = None
    timeout_ms: int = 30000
    trace_enabled: bool = False
    sandbox_mode: bool = True
    extra_args: Optional[List[str]] = None

@dataclass
class ActionResult:
    """アクション実行結果"""
    success: bool
    action_type: str
    duration_ms: float
    error: Optional[str] = None
    artifacts: Optional[Dict[str, Any]] = None  # screenshots, traces, logs
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class EngineMetrics:
    """エンジン実行メトリクス"""
    engine_type: str
    total_actions: int
    successful_actions: int
    failed_actions: int
    avg_latency_ms: float
    artifacts_captured: int

class BrowserEngine(ABC):
    """ブラウザエンジン抽象クラス"""
    
    def __init__(self, engine_type: EngineType):
        self.engine_type = engine_type
        self._context = None
        self._metrics = EngineMetrics(
            engine_type=engine_type.value,
            total_actions=0,
            successful_actions=0,
            failed_actions=0,
            avg_latency_ms=0.0,
            artifacts_captured=0
        )
    
    @abstractmethod
    async def launch(self, context: LaunchContext) -> None:
        """
        エンジンを起動しブラウザコンテキストを初期化
        
        Args:
            context: 起動パラメータ
            
        Raises:
            EngineLaunchError: 起動失敗時
        """
        pass
    
    @abstractmethod
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> ActionResult:
        """
        指定URLへ遷移
        
        Args:
            url: 遷移先URL
            wait_until: 待機条件 (load, domcontentloaded, networkidle)
            
        Returns:
            ActionResult: 実行結果
        """
        pass
    
    @abstractmethod
    async def dispatch(self, action: Dict[str, Any]) -> ActionResult:
        """
        汎用アクション実行（click, type, scroll, evaluate等）
        
        Args:
            action: アクション定義（JSON形式）
                例: {"type": "click", "selector": "#button", "timeout": 5000}
                
        Returns:
            ActionResult: 実行結果
        """
        pass
    
    @abstractmethod
    async def capture_artifacts(self, artifact_types: List[str]) -> Dict[str, Any]:
        """
        アーティファクトを取得（スクリーンショット、トレース、ログ等）
        
        Args:
            artifact_types: 取得するアーティファクトのリスト
                例: ["screenshot", "trace", "console_logs"]
                
        Returns:
            Dict[str, Any]: アーティファクトデータ（キーはタイプ、値はバイナリまたはパス）
        """
        pass
    
    @abstractmethod
    async def shutdown(self, capture_final_state: bool = True) -> None:
        """
        エンジンをシャットダウンし、リソースをクリーンアップ
        
        Args:
            capture_final_state: 終了時に最終状態をキャプチャするか
        """
        pass
    
    def get_metrics(self) -> EngineMetrics:
        """実行メトリクスを取得"""
        return self._metrics
    
    def supports_action(self, action_type: str) -> bool:
        """
        指定アクションタイプをサポートしているか確認
        
        Args:
            action_type: アクションタイプ (click, type, evaluate, etc.)
            
        Returns:
            bool: サポート可否
        """
        # サブクラスでオーバーライド可能
        return True
```

### 2.2 共通例外クラス

```python
class EngineError(Exception):
    """エンジン実行エラーの基底クラス"""
    pass

class EngineLaunchError(EngineError):
    """エンジン起動失敗"""
    pass

class ActionExecutionError(EngineError):
    """アクション実行失敗"""
    def __init__(self, action_type: str, message: str, original_error: Optional[Exception] = None):
        self.action_type = action_type
        self.original_error = original_error
        super().__init__(f"Action '{action_type}' failed: {message}")

class ArtifactCaptureError(EngineError):
    """アーティファクト取得失敗"""
    pass
```

## 3. アダプター実装ガイドライン

### 3.1 PlaywrightEngine

既存の `modules/execution_debug_engine.py` と `script/script_manager.py` から Playwright ロジックを抽出し、`BrowserEngine` インターフェースを実装。

**実装パス**: `src/browser/engine/playwright_engine.py`

**主要メソッド実装**:

- `launch()`: `playwright.chromium.launch()` をラップ、LaunchContext から browser/context を生成。
- `navigate()`: `page.goto()` を実行し、待機条件を適用。
- `dispatch()`: アクションタイプに応じて `page.click()`, `page.fill()`, `page.evaluate()` 等を呼び出し。
- `capture_artifacts()`: `page.screenshot()`, `context.tracing.stop()` で取得。

**互換性維持**:

- 既存の unlock-future JSON 定義を変更せず、アダプター内で変換。
- フラグ `runner.engine=playwright` 時に既存挙動を完全再現。

### 3.2 CDPEngine

新規実装として `cdp-use>=0.6.0` を利用した CDP ネイティブアダプターを追加。

**実装パス**: `src/browser/engine/cdp_engine.py`

**主要メソッド実装**:

- `launch()`: CDP クライアントを初期化し、ブラウザプロセスを起動。
- `navigate()`: `Page.navigate` CDP コマンドを送信。
- `dispatch()`: CDP の `Runtime.evaluate`, `Input.dispatchMouseEvent` 等を直接呼び出し。
- `capture_artifacts()`: `Page.captureScreenshot`, Tracing API を利用。

**フェーズ2 スコープ**:

- 最小アクションセット（navigate, click, type, screenshot）のみ実装。
- ネットワークインターセプトやファイルアップロードはフェーズ4 で拡張。

### 3.3 エンジンローダー

**実装パス**: `src/browser/engine/loader.py`

```python
from typing import Optional
from .browser_engine import BrowserEngine, EngineType
from .playwright_engine import PlaywrightEngine
from .cdp_engine import CDPEngine

class EngineLoader:
    """フィーチャーフラグに基づいてエンジンをロード"""
    
    @staticmethod
    def load_engine(engine_type: Optional[str] = None) -> BrowserEngine:
        """
        エンジンインスタンスを生成
        
        Args:
            engine_type: "playwright" or "cdp" (Noneの場合は環境変数から取得)
            
        Returns:
            BrowserEngine: ロードされたエンジン
            
        Raises:
            ValueError: 未サポートのエンジンタイプ
        """
        if engine_type is None:
            import os
            engine_type = os.getenv("RUNNER_ENGINE", "playwright")
        
        if engine_type == EngineType.PLAYWRIGHT.value:
            return PlaywrightEngine()
        elif engine_type == EngineType.CDP.value:
            return CDPEngine()
        else:
            raise ValueError(f"Unsupported engine type: {engine_type}")
```

## 4. unlock-future 統合

### 4.1 JSON アクション変換

既存の unlock-future JSON 定義を `BrowserEngine.dispatch()` へ変換するアダプター層を追加。

**実装パス**: `src/browser/unlock_future_adapter.py`

```python
from typing import Dict, Any
from .engine.browser_engine import BrowserEngine, ActionResult

class UnlockFutureAdapter:
    """unlock-future JSON を BrowserEngine へ変換"""
    
    def __init__(self, engine: BrowserEngine):
        self.engine = engine
    
    async def execute_unlock_future_action(self, action_json: Dict[str, Any]) -> ActionResult:
        """
        unlock-future アクションを実行
        
        Args:
            action_json: unlock-future形式のアクション定義
            
        Returns:
            ActionResult: 実行結果
        """
        action_type = action_json.get("action", "unknown")
        
        if action_type == "navigate":
            return await self.engine.navigate(action_json["url"])
        elif action_type == "click":
            return await self.engine.dispatch({
                "type": "click",
                "selector": action_json["selector"],
                "timeout": action_json.get("timeout", 30000)
            })
        elif action_type == "type":
            return await self.engine.dispatch({
                "type": "fill",
                "selector": action_json["selector"],
                "text": action_json["text"]
            })
        else:
            # 汎用dispatchへフォールバック
            return await self.engine.dispatch(action_json)
```

### 4.2 execution_debug_engine.py との統合

`modules/execution_debug_engine.py` 内で `EngineLoader` を呼び出し、フラグに応じてエンジンを切替。

```python
# modules/execution_debug_engine.py の一部（擬似コード）

from src.browser.engine.loader import EngineLoader
from src.browser.unlock_future_adapter import UnlockFutureAdapter

async def execute_unlock_future_script(script_path: str):
    # フィーチャーフラグからエンジンを決定
    engine_type = get_feature_flag("runner.cdp_engine", default="playwright")
    
    # エンジンロード
    engine = EngineLoader.load_engine(engine_type)
    adapter = UnlockFutureAdapter(engine)
    
    # スクリプト実行
    try:
        await engine.launch(LaunchContext(headless=True, trace_enabled=True))
        
        # JSONアクション読み込み
        actions = load_unlock_future_json(script_path)
        
        for action in actions:
            result = await adapter.execute_unlock_future_action(action)
            if not result.success:
                logger.error(f"Action failed: {result.error}")
                break
        
        # アーティファクト取得
        artifacts = await engine.capture_artifacts(["screenshot", "trace"])
        save_artifacts(artifacts)
        
    finally:
        await engine.shutdown()
```

## 5. フィーチャーフラグ定義

`feature_flags/FLAGS.md` へ追加:

```yaml
runner:
  cdp_engine:
    type: enum
    values: [playwright, cdp]
    default: playwright
    description: "ブラウザ自動化エンジンの選択"
    rollout:
      dev: cdp  # 開発環境では CDP を優先
      staging: playwright
      production: playwright
```

## 6. テスト戦略

### 6.1 ユニットテスト

**テストパス**: `tests/unit/browser/engine/`

- `test_playwright_engine.py`: PlaywrightEngine の各メソッド動作確認（モック利用）。
- `test_cdp_engine.py`: CDPEngine の CDP コマンド送信ロジック検証。
- `test_engine_loader.py`: フラグに応じた正しいエンジンロードを確認。

### 6.2 統合テスト

**テストパス**: `tests/integration/browser/engine/`

- `test_unlock_future_with_playwright.py`: 既存 unlock-future スクリプトを Playwright エンジンで実行。
- `test_unlock_future_with_cdp.py`: 同じスクリプトを CDP エンジンで実行し、結果を比較。
- `test_engine_switching.py`: フラグ切替後に正しいエンジンが使われることを確認。

### 6.3 パフォーマンスベンチマーク

**テストパス**: `tests/benchmarks/engine_comparison.py`

Issue #53 の手法を踏襲し、以下を測定:

- ページ遷移レイテンシ（navigate）。
- 要素操作レイテンシ（click, type）。
- アーティファクト生成時間（screenshot, trace）。
- メモリ消費量（実行前後の差分）。

## 7. マイグレーションパス

### 7.1 既存コードへの影響

- **変更不要**: unlock-future JSON 定義、既存スクリプトはそのまま動作。
- **変更推奨**: `execution_debug_engine.py` および `script_manager.py` でエンジンを直接呼び出している箇所を `EngineLoader` 経由に変更。
- **非推奨化**: Playwright API を直接利用している箇所は、将来的に `BrowserEngine` インターフェース経由へ移行を推奨。

### 7.2 段階的ロールアウト

1. **フェーズ1**: Playwright エンジンのみ実装し、リファクタリング効果を検証。
2. **フェーズ2**: CDP エンジン追加、dev 環境で試験運用。
3. **フェーズ3**: ステージング環境で A/B テスト（50% Playwright, 50% CDP）。
4. **フェーズ4**: 性能・安定性が確認されれば CDP をデフォルトへ昇格。

## 8. 未解決事項

- [ ] Firefox 専用エンジン（Marionette）は Phase2 以降に検討するか。
- [ ] WebSocket 経由の CDP 接続がプロキシ環境で動作するか検証必要。
- [ ] CDP エンジンで Playwright のトレース形式（.zip）を再現する方法を確認。
- [ ] エンジン切替時に既存アーティファクトの互換性を保証する方法。

## 9. 次のステップ

1. 本ドキュメントのレビューを実施し、インターフェース設計を確定。
2. Issue #53 へフェーズ0 完了報告とフェーズ1 着手宣言をコメント。
3. フェーズ1 のブランチ `feature/phase1-playwright-extraction` を作成。
4. `src/browser/engine/` ディレクトリを作成し、`browser_engine.py` を commit。

---

**改訂履歴**:

- 2025-10-06: 初版ドラフト作成（フェーズ0）
