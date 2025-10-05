"""
UI サービス層 (Phase3)

UI コンポーネントをサポートするサービスクラス群。

Phase3 実装範囲:
- FeatureFlagService: フィーチャーフラグ管理

Phase4 拡張予定:
- ThemeService: カスタムテーマ管理
- NotificationService: WebSocket 経由のリアルタイム通知

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.4: Feature Flag Strategy)
"""

from .feature_flag_service import (
    FeatureFlagService,
    FeatureFlagState,
    get_feature_flag_service,
)

__all__ = [
    "FeatureFlagService",
    "FeatureFlagState",
    "get_feature_flag_service",
]
