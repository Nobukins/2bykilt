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
        - Tab 1: メイン実行画面 (unlock-future UI - 既存)
        - Tab 2: 設定パネル (SettingsPanel)
        - Tab 3: 実行履歴 (RunHistory)
        - Tab 4: トレースビューア (TraceViewer)

        Phase4 拡張予定:
        - Tab 5: 録画一覧
        - WebSocket 進捗通知
        - カスタムテーマ
        """
        if gr is None:
            logger.error("Gradio not installed, cannot build UI")
            return None

        with gr.Blocks(
            title="2bykilt - Modern Browser Automation UI",
            theme=gr.themes.Soft(),
        ) as interface:
            gr.Markdown(
                """
                # 2bykilt - ブラウザ自動化プラットフォーム

                Phase3 モダン UI - CDP/WebUI 統合版
                """
            )

            with gr.Tabs():
                # Tab 1: メイン実行画面 (既存 UI - ここでは省略)
                with gr.Tab("🚀 実行画面"):
                    self._run_panel.render()

                # Tab 2: 設定パネル
                with gr.Tab("⚙️ 設定"):
                    self._settings_panel.render()

                # Tab 3: 実行履歴
                with gr.Tab("📜 履歴"):
                    self._run_history.render()

                # Tab 4: トレースビューア
                with gr.Tab("🎬 トレース"):
                    self._trace_viewer.render()

            # フッター
            gr.Markdown(
                """
                ---
                **Phase3 実装範囲:**
                - ✅ FeatureFlagService: バックエンド/UI フラグ同期
                - ✅ SettingsPanel: エンジン状態、LLM 分離状態表示
                - ✅ RunHistory: 実行履歴タイムライン (フィルタ、統計)
                - ✅ TraceViewer: トレース ZIP 読み込み (Phase4 で再生機能追加)

                **Phase4 実装予定:**
                - Playwright Trace Viewer 埋め込み
                - リアルタイム実行監視
                - CDP サンドボックス統合
                - セキュリティレビュー
                """
            )

        logger.info("Modern UI interface built successfully")
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
