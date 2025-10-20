"""
メイン UI 統合モジュール (Phase3)

各 UI コンポーネントを統合して Gradio インターフェースを構築。

Phase3 スコープ:
- コンポーネントの統合 (SettingsPanel, TraceViewer, RunHistory)
- タブレイアウト構成
- フィーチャーフラグによる表示制御

Phase4 拡張予定:
- リアルタイム実行監視
- WebSocket 統合 (進捗通知)
- カスタムテーマ適用

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3: UI Modularization)
"""

from typing import Optional, TYPE_CHECKING
import logging

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore

if TYPE_CHECKING:
    import gradio as gradio_typing
else:  # pragma: no cover - runtime-only fallback
    gradio_typing = None  # type: ignore

def _sync_gradio_module(gr_module):
    """Ensure all UI modules share the same Gradio reference (mockable in tests)."""
    global gr
    gr = gr_module  # align local reference
    try:
        from src.ui.components import settings_panel, run_panel, run_history, trace_viewer
        from src.ui import stream_manager

        settings_panel.gr = gr_module
        run_panel.gr = gr_module
        run_history.gr = gr_module
        trace_viewer.gr = gr_module
        stream_manager.gr = gr_module
    except Exception:
        # During import-time failures we keep best-effort; actual usage will raise later.
        pass

from .components import (
    create_run_panel,
    create_settings_panel,
    create_trace_viewer,
    create_run_history,
)
from .services.feature_flag_service import get_feature_flag_service

logger = logging.getLogger(__name__)


class ModernUI:
    """
    モダン UI 統合クラス。

    Phase3 実装:
    - 全コンポーネントの統合
    - タブベースのレイアウト
    - フィーチャーフラグによる表示制御

    Attributes:
        _flag_service: FeatureFlagService インスタンス
        _settings_panel: SettingsPanel コンポーネント
        _trace_viewer: TraceViewer コンポーネント
        _run_history: RunHistory コンポーネント
    """

    def __init__(self):
        _sync_gradio_module(gr)
        self._flag_service = get_feature_flag_service()
        self._settings_panel = create_settings_panel()
        self._trace_viewer = create_trace_viewer()
        self._run_history = create_run_history()
        self._run_panel = create_run_panel()

    def build_interface(self) -> Optional["gradio_typing.Blocks"]:
        """
        Gradio Blocks インターフェース構築。

        Returns:
            gr.Blocks: 構築済み Gradio インターフェース

        Phase3 レイアウト:
        - Feature Flag に基づいた動的メニュー構成
        - 必須メニュー: Run Agent, LLMS Config, Browser Settings, Artifacts
        - オプショナルメニュー: 設定フラグで表示/非表示を制御

        Phase4 拡張予定:
        - Tab 5: 録画一覧
        - WebSocket 進捗通知
        - カスタムテーマ
        """
        if gr is None:
            logger.error("Gradio not installed, cannot build UI")
            return None

        # Feature Flag からメニュー設定を取得
        menus = self._flag_service.get_enabled_menus()
        
        with gr.Blocks(
            title="2bykilt - Modern Browser Automation UI",
            theme=gr.themes.Soft(),
        ) as interface:
            gr.Markdown(
                """
                # 2bykilt - ブラウザ自動化プラットフォーム

                Phase3 モダン UI - Feature Flag ベースメニュー
                """
            )

            with gr.Tabs():
                # Run Agent タブ
                if menus.get('run_agent', False):
                    with gr.Tab("🤖 Run Agent"):
                        self._run_panel.render()

                # LLMS Config タブ
                if menus.get('llms_config', False):
                    with gr.Tab("📄 LLMS Config"):
                        # 現在の settings_panel を使用
                        # 今後専用パネルに置き換え可能
                        self._settings_panel.render()

                # Browser Settings タブ
                if menus.get('browser_settings', False):
                    with gr.Tab("🌐 Browser Settings"):
                        self._settings_panel.render()

                # Artifacts タブ
                if menus.get('artifacts', False):
                    with gr.Tab("📦 Artifacts"):
                        # admin/artifacts_panel.py を使用
                        # 未実装の場合は簡易パネルを表示
                        try:
                            from src.ui.admin.artifacts_panel import create_artifacts_panel
                            artifacts_panel = create_artifacts_panel()
                            artifacts_panel.render()
                        except (ImportError, AttributeError):
                            gr.Markdown("📦 Artifacts Panel (coming soon)")

                # 実行履歴タブ（常に表示）
                with gr.Tab("📜 履歴"):
                    self._run_history.render()

                # トレースビューアタブ（常に表示）
                with gr.Tab("🎬 トレース"):
                    self._trace_viewer.render()

                # Feature Flags 管理パネル
                if menus.get('feature_flags_admin', False):
                    with gr.Tab("⚙️ Feature Flags"):
                        try:
                            from src.ui.admin.feature_flags_panel import create_feature_flags_panel
                            flags_panel = create_feature_flags_panel()
                            flags_panel.render()
                        except (ImportError, AttributeError):
                            gr.Markdown("⚙️ Feature Flags Panel (coming soon)")

                # オプショナルメニュー: Results
                if menus.get('results', False):
                    with gr.Tab("📊 Results"):
                        gr.Markdown("📊 Results Panel (coming soon)")

                # オプショナルメニュー: Recordings
                if menus.get('recordings', False):
                    with gr.Tab("🎥 Recordings"):
                        gr.Markdown("🎥 Recordings Panel (coming soon)")

                # オプショナルメニュー: Deep Research
                if menus.get('deep_research', False):
                    with gr.Tab("🧐 Deep Research"):
                        gr.Markdown("🧐 Deep Research Panel (coming soon)")

            # フッター
            gr.Markdown(
                f"""
                ---
                **Phase3 実装範囲:**
                - ✅ FeatureFlagService: メニュー動的管理
                - ✅ Feature Flag 統合: 10+ メニュー項目の表示制御
                - ✅ RunPanel: エージェント実行
                - ✅ SettingsPanel: ブラウザ設定
                - ✅ RunHistory: 実行履歴
                - ✅ TraceViewer: トレース表示

                **アクティブメニュー:** {sum(1 for v in menus.values() if v)}/{len(menus)}
                """
            )

        logger.info("Modern UI interface built successfully with Feature Flag based menus")
        return interface

    def launch(
        self,
        server_name: str = "0.0.0.0",
        server_port: int = 7860,
        share: bool = False,
    ) -> None:
        """
        Gradio サーバー起動。

        Args:
            server_name: バインドアドレス
            server_port: ポート番号
            share: Gradio 共有リンク有効化

        Phase3 実装:
        - 基本起動設定
        - ログ出力

        Phase4 拡張予定:
        - HTTPS 対応
        - 認証レイヤー統合
        """
        interface = self.build_interface()
        if interface is None:
            logger.error("Cannot launch UI: interface build failed")
            return

        logger.info(
            f"Launching Modern UI on {server_name}:{server_port} (share={share})"
        )

        interface.launch(
            server_name=server_name,
            server_port=server_port,
            share=share,
        )


def create_modern_ui() -> ModernUI:
    """
    ModernUI インスタンス作成ファクトリ。

    Returns:
        ModernUI: 新規インスタンス

    使用例:
        ui = create_modern_ui()
        ui.launch()
    """
    return ModernUI()


def main() -> None:
    """
    スタンドアロン起動エントリポイント。

    使用例:
        python -m src.ui.main_ui
    """
    import argparse

    parser = argparse.ArgumentParser(description="2bykilt Modern UI")
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Server bind address (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Server port (default: 7860)",
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Enable Gradio share link",
    )

    args = parser.parse_args()

    ui = create_modern_ui()
    ui.launch(
        server_name=args.host,
        server_port=args.port,
        share=args.share,
    )


if __name__ == "__main__":
    main()
