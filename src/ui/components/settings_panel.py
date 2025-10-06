"""
SettingsPanel コンポーネント (Phase4 拡張)

フィーチャーフラグ状態、エンジン情報、ENABLE_LLM ステータスを
統合表示し、管理者が UI から直接切り替えられるようにする設定パネル。

Phase4 実装内容:
- ランタイムフィーチャーフラグのトグル (FeatureFlags.set_override)
- エンジン選択ドロップダウン (Playwright/CDP)
- LLM 有効化トグル (Docker サンドボックス)
- UI コンポーネント可視性トグル (TraceViewer/RunHistory/Realtime)
- オーバーライド状況の表示とクリアボタン

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3)
- src/config/feature_flags.py
"""

from __future__ import annotations

from functools import partial
from typing import Optional

import gradio as gr

from src.config.feature_flags import FeatureFlags
from src.llm import get_llm_gateway
from src.ui.services.feature_flag_service import FeatureFlagState, get_feature_flag_service


class SettingsPanel:
    """
    設定パネルコンポーネント
    
    Gradio UI として統合し、フィーチャーフラグや
    ENABLE_LLM 状態を可視化します。
    """
    
    def __init__(self):
        self.flag_service = get_feature_flag_service()
        self.llm_gateway = get_llm_gateway()
    
    def render(self) -> gr.Column:
        """
        Gradio コンポーネントをレンダリング
        
        Returns:
            gr.Column: 設定パネル UI
        """
        if gr is None:
            raise RuntimeError("Gradio is required to render SettingsPanel")

        state = self.flag_service.get_current_state(force_refresh=True)

        with gr.Column(visible=True) as panel:
            gr.Markdown("## ⚙️ 設定 / Settings")

            with gr.Accordion("ブラウザエンジン", open=True):
                engine_info = gr.Markdown(self._format_engine_info(state))
                engine_dropdown = gr.Dropdown(
                    choices=["playwright", "cdp"],
                    value=state.runner_engine,
                    label="エンジン選択",
                    interactive=True,
                )
                engine_dropdown.change(
                    fn=self._on_engine_change,
                    inputs=[engine_dropdown],
                    outputs=[engine_dropdown, engine_info],
                )

            with gr.Accordion("LLM 機能", open=True):
                llm_info = gr.Markdown(self._format_llm_info(state))
                llm_toggle = gr.Checkbox(
                    label="LLM を有効化", value=state.enable_llm, interactive=True
                )
                llm_toggle.change(
                    fn=self._on_llm_toggle,
                    inputs=[llm_toggle],
                    outputs=[llm_toggle, llm_info],
                )

            with gr.Accordion("UI オプション", open=True):
                ui_info = gr.Markdown(self._format_ui_info(state))
                with gr.Row():
                    modern_layout = gr.Checkbox(
                        label="モダンレイアウト", value=state.ui_modern_layout, interactive=True
                    )
                    trace_viewer = gr.Checkbox(
                        label="トレースビューア", value=state.ui_trace_viewer, interactive=True
                    )
                    run_history = gr.Checkbox(
                        label="実行履歴", value=state.ui_run_history, interactive=True
                    )
                    realtime_updates = gr.Checkbox(
                        label="リアルタイム更新", value=state.ui_realtime_updates, interactive=True
                    )

                modern_layout.change(
                    fn=partial(self._on_bool_flag_toggle, "ui.modern_layout"),
                    inputs=[modern_layout],
                    outputs=[modern_layout, ui_info],
                )
                trace_viewer.change(
                    fn=partial(self._on_bool_flag_toggle, "ui.trace_viewer"),
                    inputs=[trace_viewer],
                    outputs=[trace_viewer, ui_info],
                )
                run_history.change(
                    fn=partial(self._on_bool_flag_toggle, "ui.run_history"),
                    inputs=[run_history],
                    outputs=[run_history, ui_info],
                )
                realtime_updates.change(
                    fn=partial(self._on_bool_flag_toggle, "ui.realtime_updates"),
                    inputs=[realtime_updates],
                    outputs=[realtime_updates, ui_info],
                )

                gr.Markdown(
                    "*オーバーライドは FeatureFlags ランタイムに保存され、プロセス停止でリセットされます。*"
                )

                clear_button = gr.Button("全オーバーライドをクリア", variant="secondary")
                clear_button.click(
                    fn=self._clear_overrides,
                    outputs=[
                        engine_dropdown,
                        llm_toggle,
                        modern_layout,
                        trace_viewer,
                        run_history,
                        realtime_updates,
                        engine_info,
                        llm_info,
                        ui_info,
                    ],
                )

        return panel
    
    def get_status_summary(self) -> str:
        """
        設定状態のサマリーを取得（ログやメトリクス用）
        
        Returns:
            str: ステータスサマリー
        """
        state = self.flag_service.get_current_state()
        return (
            f"Engine={state.runner_engine}, "
            f"LLM={'ON' if state.enable_llm else 'OFF'}, "
            f"ModernUI={'ON' if state.ui_modern_layout else 'OFF'}"
        )

    # ------------------------------------------------------------------
    # Callbacks
    # ------------------------------------------------------------------
    def _refresh_state(self) -> FeatureFlagState:
        return self.flag_service.get_current_state(force_refresh=True)

    def _on_engine_change(self, engine: str):
        if engine not in {"playwright", "cdp"}:
            engine = "playwright"
        FeatureFlags.set_override("runner.engine", engine)
        state = self._refresh_state()
        return gr.update(value=state.runner_engine), gr.update(
            value=self._format_engine_info(state)
        )

    def _on_llm_toggle(self, enabled: bool):
        FeatureFlags.set_override("enable_llm", bool(enabled))
        state = self._refresh_state()
        return gr.update(value=state.enable_llm), gr.update(
            value=self._format_llm_info(state)
        )

    def _on_bool_flag_toggle(self, flag_name: str, enabled: bool):
        FeatureFlags.set_override(flag_name, bool(enabled))
        state = self._refresh_state()
        return gr.update(value=bool(enabled)), gr.update(
            value=self._format_ui_info(state)
        )

    def _clear_overrides(self):
        FeatureFlags.clear_all_overrides()
        state = self._refresh_state()
        return (
            gr.update(value=state.runner_engine),
            gr.update(value=state.enable_llm),
            gr.update(value=state.ui_modern_layout),
            gr.update(value=state.ui_trace_viewer),
            gr.update(value=state.ui_run_history),
            gr.update(value=state.ui_realtime_updates),
            gr.update(value=self._format_engine_info(state)),
            gr.update(value=self._format_llm_info(state)),
            gr.update(value=self._format_ui_info(state)),
        )

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------
    def _format_engine_info(self, state) -> str:
        override = FeatureFlags.get_override_source("runner.engine")
        badge = self._format_override_badge(override)
        return (
            f"**現在のエンジン**: `{state.runner_engine}` {badge}\n\n"
            "- **Playwright**: 安定版、フル機能サポート\n"
            "- **CDP**: 実験版、低レベル制御\n"
        )

    def _format_llm_info(self, state) -> str:
        override = FeatureFlags.get_override_source("enable_llm")
        badge = self._format_override_badge(override)
        status_icon = "🟢" if state.enable_llm else "⚪"
        status_text = "有効" if state.enable_llm else "無効"
        return (
            f"{status_icon} **ステータス**: {status_text} {badge}\n\n"
            "- Docker サンドボックスで隔離実行\n"
            "- Secrets Vault から資格情報を取得\n"
        )

    def _format_ui_info(self, state) -> str:
        def badge(name: str) -> str:
            return self._format_override_badge(FeatureFlags.get_override_source(name))

        return (
            "**表示設定:**\n"
            f"- モダンレイアウト: {'✅' if state.ui_modern_layout else '❌'} {badge('ui.modern_layout')}\n"
            f"- トレースビューア: {'✅' if state.ui_trace_viewer else '❌'} {badge('ui.trace_viewer')}\n"
            f"- 実行履歴: {'✅' if state.ui_run_history else '❌'} {badge('ui.run_history')}\n"
            f"- リアルタイム更新: {'✅' if state.ui_realtime_updates else '❌'} {badge('ui.realtime_updates')}\n"
        )

    @staticmethod
    def _format_override_badge(source: Optional[str]) -> str:
        if source == "runtime":
            return "`override:runtime`"
        if source == "environment":
            return "`override:env`"
        return ""


def create_settings_panel() -> SettingsPanel:
    """
    SettingsPanel インスタンスを生成（ファクトリ関数）
    
    Returns:
        SettingsPanel: パネルインスタンス
    """
    return SettingsPanel()
