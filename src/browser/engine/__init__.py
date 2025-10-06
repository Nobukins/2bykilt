"""
Browser Engine 抽象化レイヤー

2bykilt の Runner が複数のブラウザ自動化エンジン（Playwright, CDP-use 等）を
透過的に利用するための基盤インターフェースを提供します。

フェーズ1で実装:
- BrowserEngine 抽象クラス
- EngineLoader（フィーチャーフラグベース）
- PlaywrightEngine アダプター

フェーズ2で実装:
- CDPEngine アダプター
- パフォーマンステレメトリー拡張

関連:
- ドキュメント: docs/engine/browser-engine-contract.md
- Issue: #53 (CDP エンジン調査と統合)
"""

from .browser_engine import (
    BrowserEngine,
    EngineType,
    LaunchContext,
    ActionResult,
    EngineMetrics,
    EngineError,
    EngineLaunchError,
    ActionExecutionError,
    ArtifactCaptureError,
)
from .telemetry import EngineTelemetryRecorder

__all__ = [
    "BrowserEngine",
    "EngineType",
    "LaunchContext",
    "ActionResult",
    "EngineMetrics",
    "EngineError",
    "EngineLaunchError",
    "ActionExecutionError",
    "ArtifactCaptureError",
    "EngineTelemetryRecorder",
]

__version__ = "1.0.0-alpha"
