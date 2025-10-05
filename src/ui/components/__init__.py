"""
UI コンポーネント層 (Phase3)

Gradio UI を構成するモジュール化されたコンポーネント群。

Phase3 実装範囲:
- SettingsPanel: フラグ状態と ENABLE_LLM 表示
- RunHistory: 実行履歴タイムライン (フィルタ、統計)
- TraceViewer: トレース ZIP ファイル読み込みと表示

Phase4 拡張予定:
- RecordingsList: 録画済み unlock-future スクリプト一覧
- AnimationPreview: GIF アニメーションプレビュー
- TraceViewer iframe 埋め込み
- RunHistory リアルタイム更新

関連:
- docs/plan/cdp-webui-modernization.md
"""

from .settings_panel import SettingsPanel, create_settings_panel
from .trace_viewer import TraceViewer, create_trace_viewer
from .run_history import RunHistory, create_run_history

__all__ = [
    "SettingsPanel",
    "create_settings_panel",
    "TraceViewer",
    "create_trace_viewer",
    "RunHistory",
    "create_run_history",
]
