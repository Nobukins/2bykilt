"""
BrowserEngine 抽象クラスとデータモデル定義

このモジュールは browser engine の契約仕様を Python コードとして実装します。
詳細な設計意図については docs/engine/browser-engine-contract.md を参照してください。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone


class EngineType(Enum):
    """サポートするエンジンタイプ"""
    PLAYWRIGHT = "playwright"
    CDP = "cdp"
    # 将来拡張: FIREFOX_MARIONETTE = "firefox"


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
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class EngineMetrics:
    """エンジン実行メトリクス"""
    engine_type: str
    total_actions: int = 0
    successful_actions: int = 0
    failed_actions: int = 0
    avg_latency_ms: float = 0.0
    artifacts_captured: int = 0
    started_at: Optional[datetime] = None
    shutdown_at: Optional[datetime] = None


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


class BrowserEngine(ABC):
    """
    ブラウザエンジン抽象クラス
    
    すべてのエンジンアダプター（PlaywrightEngine, CDPEngine等）は
    このインターフェースを実装する必要があります。
    
    使用例:
        engine = EngineLoader.load_engine("playwright")
        try:
            await engine.launch(LaunchContext(headless=True))
            result = await engine.navigate("https://example.com")
            if result.success:
                artifacts = await engine.capture_artifacts(["screenshot"])
        finally:
            await engine.shutdown()
    """
    
    def __init__(self, engine_type: EngineType):
        self.engine_type = engine_type
        self._context = None
        self._page = None
        self._browser = None
        self._metrics = EngineMetrics(
            engine_type=engine_type.value,
            started_at=datetime.now(timezone.utc)
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
    
    def _update_metrics(self, result: ActionResult) -> None:
        """実行結果からメトリクスを更新（内部ヘルパー）"""
        self._metrics.total_actions += 1
        if result.success:
            self._metrics.successful_actions += 1
        else:
            self._metrics.failed_actions += 1
        
        # 平均レイテンシ更新
        n = self._metrics.total_actions
        prev_avg = self._metrics.avg_latency_ms
        self._metrics.avg_latency_ms = (prev_avg * (n - 1) + result.duration_ms) / n
        
        if result.artifacts:
            self._metrics.artifacts_captured += len(result.artifacts)
