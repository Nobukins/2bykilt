"""
UI モジュール (Phase3)

Gradio ベースの Web UI 層。

Phase3 実装範囲:
- services: FeatureFlagService
- components: SettingsPanel, TraceViewer, RunHistory
- main_ui: ModernUI 統合インターフェース

Phase4 拡張予定:
- WebSocket 統合
- カスタムテーマ
- リアルタイム進捗通知

関連:
- docs/plan/cdp-webui-modernization.md (Section 5: Architecture)
"""

from .main_ui import ModernUI, create_modern_ui

__all__ = [
    "ModernUI",
    "create_modern_ui",
]

