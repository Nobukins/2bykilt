"""
RunAgentPanel コンポーネント (Phase4 拡張)

レガシー UI の Run Agent タブをモジュール化し、モダン UI へ再利用可能な
コンポーネントとして提供する。既存の `bykilt.py` に実装されていた実行
フロー (run_with_stream, stop_agent, コマンドヘルパー) を整理し、
共通の設定値およびフィーチャーフラグと連動する。

主な責務:
- unlock-future / browser-control ランコマンドの入力フォーム
- コマンド一覧表示とタスク入力補助
- 実行/停止ボタンとストリーミング結果表示
- ENABLE_LLM フラグに応じた LLM 設定の有効/無効化

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3)
- src/ui/stream_manager.py
- src/agent/agent_manager.py
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import gradio as gr

from src.config.feature_flags import FeatureFlags, is_llm_enabled
from src.ui.command_helper import CommandHelper
from src.ui.services.feature_flag_service import FeatureFlagState, get_feature_flag_service
from src.ui.stream_manager import run_with_stream
from src.utils.default_config_settings import default_config
from src.utils import utils

# Conditional import for LLM agent functionality
try:
    from src.agent.agent_manager import stop_agent
except ImportError:
    # Stub function when LLM is disabled
    def stop_agent():
        """Stub: Agent functionality not available when ENABLE_LLM=false"""
        return "Agent functionality is disabled (ENABLE_LLM=false)", gr.update(), gr.update()

logger = logging.getLogger(__name__)


@dataclass
class _RunPanelDefaults:
    """UI 構築時に使用するデフォルト値のコンテナ。"""

    config: Dict[str, Any]
    flag_state: FeatureFlagState
    llm_provider_choices: List[str]
    llm_model_choices: List[str]
    llm_provider_value: str
    llm_model_value: str


class RunAgentPanel:
    """Run Agent UI を提供する Gradio コンポーネント。"""

    def __init__(self) -> None:
        self._flag_service = get_feature_flag_service()
        self._command_helper = CommandHelper()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def render(self) -> gr.Column:
        """Gradio Column として Run Agent パネルを描画する。"""
        if gr is None:  # pragma: no cover - defensive (Gradio 未インストール)
            raise RuntimeError("Gradio is required to render RunAgentPanel")

        defaults = self._prepare_defaults()
        cfg = defaults.config
        flags = defaults.flag_state

        with gr.Column() as panel:
            gr.Markdown(
                """
                ### 🤖 Run Agent
                unlock-future / browser-control のタスクを実行します。コマンド一覧から
                `@command` テンプレートを選択するか、自由入力で指示を与えてください。
                """
            )
            with gr.Row():
                engine_dropdown = gr.Dropdown(
                    choices=["playwright", "cdp"],
                    value=flags.runner_engine,
                    label="Runner Engine",
                    interactive=True,
                )
                engine_status = gr.Markdown(self._format_engine_status(flags))

            gr.Markdown(self._format_llm_status(flags))

            engine_dropdown.change(
                fn=self._handle_engine_change,
                inputs=engine_dropdown,
                outputs=[engine_dropdown, engine_status],
            )

            with gr.Accordion("🛠️ CDP Validation Guide", open=flags.runner_engine == "cdp"):
                gr.Markdown(
                    """
                    - CDP エンジン有効時は unlock-future の全操作が `cdp-use` アダプターを経由します。
                    - 実行ログに `CDPEngine` の初期化と DevTools セッション接続ログが出力されることを確認してください。
                    - Playwright に戻す場合は Runner Engine ドロップダウンで `playwright` を選択し、設定が即時反映されることを確認します。
                    """
                )

            # コマンド補助
            with gr.Accordion("📋 Available Commands", open=False):
                commands_table = gr.DataFrame(
                    headers=["Command", "Description", "Usage"],
                    value=self._load_commands_table(),
                    interactive=False,
                    label="Command catalog",
                )
                refresh_commands = gr.Button("🔄 Refresh Commands", variant="secondary")
                refresh_commands.click(
                    fn=self._load_commands_table,
                    outputs=commands_table,
                )

            # タスク入力とオプション
            with gr.Row():
                task = gr.Textbox(
                    label="Task Description",
                    placeholder="Enter task or @command",
                    value=cfg.get("task", ""),
                    lines=4,
                )
                additional_info = gr.Textbox(
                    label="Additional Instructions",
                    placeholder="Optional context for the agent",
                    value="",
                    lines=4,
                )

            commands_table.select(
                fn=self._handle_command_selection,
                outputs=task,
            )

            # 実行設定
            with gr.Accordion("⚙️ Agent Options", open=False):
                with gr.Row():
                    agent_type = gr.Radio(
                        choices=["org", "custom"],
                        value=cfg.get("agent_type", "custom"),
                        label="Agent Type",
                    )
                    tool_calling_method = gr.Dropdown(
                        choices=["auto", "json_schema", "function_calling"],
                        value=cfg.get("tool_calling_method", "auto"),
                        label="Tool Calling",
                    )
                    dev_mode = gr.Checkbox(
                        label="Dev Mode",
                        value=cfg.get("dev_mode", False),
                    )

                with gr.Row():
                    max_steps = gr.Slider(
                        minimum=1,
                        maximum=200,
                        value=int(cfg.get("max_steps", 100)),
                        step=1,
                        label="Max Steps",
                    )
                    max_actions_per_step = gr.Slider(
                        minimum=1,
                        maximum=20,
                        value=int(cfg.get("max_actions_per_step", 10)),
                        step=1,
                        label="Max Actions / Step",
                    )
                    use_vision = gr.Checkbox(
                        label="Use Vision",
                        value=bool(cfg.get("use_vision", True)),
                    )

            # LLM 設定
            llm_enabled = flags.enable_llm and is_llm_enabled()
            with gr.Accordion("🧠 LLM Settings", open=False):
                llm_help = "✅ ENABLE_LLM が有効です" if llm_enabled else "ℹ️ LLM 機能は無効です"
                gr.Markdown(llm_help)

                provider_choices = defaults.llm_provider_choices
                provider_value = defaults.llm_provider_value
                model_choices = defaults.llm_model_choices
                model_value = defaults.llm_model_value

                llm_provider = gr.Dropdown(
                    choices=provider_choices,
                    value=provider_value,
                    label="Provider",
                    interactive=llm_enabled,
                )
                llm_model_name = gr.Dropdown(
                    choices=model_choices,
                    value=model_value,
                    label="Model",
                    interactive=llm_enabled,
                )
                llm_num_ctx = gr.Slider(
                    minimum=2**8,
                    maximum=2**16,
                    value=int(cfg.get("llm_num_ctx", 32000)),
                    step=256,
                    label="Max Context",
                    interactive=llm_enabled,
                )
                llm_temperature = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=float(cfg.get("llm_temperature", 1.0)),
                    step=0.1,
                    label="Temperature",
                    interactive=llm_enabled,
                )
                llm_base_url = gr.Textbox(
                    label="Base URL",
                    value=cfg.get("llm_base_url", ""),
                    interactive=llm_enabled,
                )
                llm_api_key = gr.Textbox(
                    label="API Key",
                    value=cfg.get("llm_api_key", ""),
                    type="password",
                    interactive=llm_enabled,
                )

                llm_provider.change(
                    fn=self._handle_llm_provider_change,
                    inputs=llm_provider,
                    outputs=llm_model_name,
                )

            # ブラウザ設定
            with gr.Accordion("🌐 Browser", open=False):
                with gr.Row():
                    browser_type = gr.Dropdown(
                        choices=["chrome", "edge"],
                        value=cfg.get("browser_type", "chrome"),
                        label="Browser",
                    )
                    use_own_browser = gr.Checkbox(
                        label="Use existing browser profile",
                        value=bool(cfg.get("use_own_browser", False)),
                    )
                    keep_browser_open = gr.Checkbox(
                        label="Keep browser open",
                        value=bool(cfg.get("keep_browser_open", False)),
                    )
                with gr.Row():
                    headless = gr.Checkbox(
                        label="Headless",
                        value=bool(cfg.get("headless", False)),
                    )
                    disable_security = gr.Checkbox(
                        label="Disable security",
                        value=bool(cfg.get("disable_security", True)),
                    )
                    maintain_browser_session = gr.Checkbox(
                        label="Maintain session",
                        value=bool(cfg.get("maintain_browser_session", False)),
                    )
                    tab_selection_strategy = gr.Radio(
                        choices=["new_tab", "reuse_tab"],
                        value=cfg.get("tab_selection_strategy", "new_tab"),
                        label="Tab strategy",
                    )

                with gr.Row():
                    window_w = gr.Number(
                        value=int(cfg.get("window_w", cfg.get("window_width", 1280))),
                        label="Window width",
                        precision=0,
                    )
                    window_h = gr.Number(
                        value=int(cfg.get("window_h", cfg.get("window_height", 1100))),
                        label="Window height",
                        precision=0,
                    )

                enable_recording = gr.Checkbox(
                    label="Enable recording",
                    value=bool(cfg.get("enable_recording", True)),
                )
                save_recording_path = gr.Textbox(
                    label="Recording path",
                    value=cfg.get("save_recording_path", "artifacts/runs/<run>-art/videos"),
                )
                save_trace_path = gr.Textbox(
                    label="Trace path",
                    value=cfg.get("save_trace_path", "./tmp/traces"),
                )
                save_agent_history_path = gr.Textbox(
                    label="Agent history path",
                    value=cfg.get("save_agent_history_path", "./tmp/agent_history"),
                )

            # 実行/停止と結果表示
            with gr.Row():
                run_button = gr.Button("▶️ Run Agent", variant="primary", scale=2)
                stop_button = gr.Button("⏹️ Stop", variant="stop", scale=1)

            browser_view = gr.HTML(
                value="<h3>Waiting for browser session...</h3>",
                label="Live Browser View",
            )
            with gr.Row():
                final_result_output = gr.Textbox(label="Final Result", lines=3)
                errors_output = gr.Textbox(label="Errors", lines=3)
            with gr.Row():
                model_actions_output = gr.Textbox(label="Model Actions", lines=3)
                model_thoughts_output = gr.Textbox(label="Model Thoughts", lines=3)
            recording_display = gr.Textbox(label="Latest Recording", interactive=False)
            trace_file_path = gr.Textbox(label="Trace File", interactive=False)
            agent_history_path = gr.Textbox(label="Agent History", interactive=False)

            stop_button.click(
                fn=stop_agent,
                inputs=None,
                outputs=[errors_output, stop_button, run_button],
            )

            run_button.click(
                fn=run_with_stream,
                inputs=[
                    agent_type,
                    llm_provider,
                    llm_model_name,
                    llm_num_ctx,
                    llm_temperature,
                    llm_base_url,
                    llm_api_key,
                    use_own_browser,
                    keep_browser_open,
                    headless,
                    disable_security,
                    window_w,
                    window_h,
                    save_recording_path,
                    save_agent_history_path,
                    save_trace_path,
                    enable_recording,
                    task,
                    additional_info,
                    max_steps,
                    use_vision,
                    max_actions_per_step,
                    tool_calling_method,
                    dev_mode,
                    maintain_browser_session,
                    tab_selection_strategy,
                    browser_type,
                ],
                outputs=[
                    browser_view,
                    final_result_output,
                    errors_output,
                    model_actions_output,
                    model_thoughts_output,
                    recording_display,
                    trace_file_path,
                    agent_history_path,
                    stop_button,
                    run_button,
                ],
            )

        return panel

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _prepare_defaults(self) -> _RunPanelDefaults:
        config = default_config().copy()
        flag_state = self._flag_service.get_current_state(force_refresh=True)

        provider_choices, provider_value, model_choices, model_value = self._resolve_llm_defaults(
            enable_llm=flag_state.enable_llm,
            config=config,
        )

        return _RunPanelDefaults(
            config=config,
            flag_state=flag_state,
            llm_provider_choices=provider_choices,
            llm_model_choices=model_choices,
            llm_provider_value=provider_value,
            llm_model_value=model_value,
        )

    def _resolve_llm_defaults(
        self, *, enable_llm: bool, config: Dict[str, Any]
    ) -> Tuple[List[str], str, List[str], str]:
        provider_choices = sorted(utils.model_names.keys()) or [config.get("llm_provider", "openai")]
        provider_value = config.get("llm_provider", provider_choices[0])
        if provider_value not in provider_choices:
            provider_value = provider_choices[0]

        model_choices = utils.model_names.get(provider_value, [])
        if not model_choices:
            model_choices = [config.get("llm_model_name", provider_value)]
        model_value = config.get("llm_model_name", model_choices[0])
        if model_value not in model_choices:
            model_value = model_choices[0]

        if not enable_llm:
            # LLM 無効時でも backend 呼び出しに必要な値を確保する
            provider_choices = [provider_value]
            model_choices = [model_value]

        return provider_choices, provider_value, model_choices, model_value

    def _load_commands_table(self) -> List[List[str]]:
        try:
            return self._command_helper.get_commands_for_display()
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to load commands", exc_info=exc)
            return [["Error", "Could not load commands", str(exc)]]

    def _handle_command_selection(self, evt: gr.SelectData) -> str:
        try:
            if evt is None or evt.index is None:
                return ""
            row_idx = evt.index[0]
            commands = self._command_helper.get_commands_for_display()
            if row_idx >= len(commands):
                return ""
            command_name = commands[row_idx][0]
            template = self._command_helper.generate_command_template(command_name)
            return f"@{template}" if not template.startswith("@") else template
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.warning("Failed to handle command selection", exc_info=exc)
            return ""

    def _handle_llm_provider_change(self, provider: str) -> gr.Dropdown:
        choices = utils.model_names.get(provider, [])
        if not choices:
            return gr.Dropdown.update(choices=[], value="", interactive=True)
        return gr.Dropdown.update(choices=choices, value=choices[0], interactive=True)

    def _format_engine_status(self, state: FeatureFlagState) -> str:
        source = FeatureFlags.get_override_source("runner.engine")
        badge = f"`override:{source}`" if source else ""
        engine = state.runner_engine
        hints = "✅ CDP engine active" if engine == "cdp" else "🟢 Playwright engine"
        return (
            f"{hints} {badge}\n\n"
            "- `playwright`: 既存の安定ルート\n"
            "- `cdp`: DevTools セッション直接制御"
        )

    def _format_llm_status(self, state: FeatureFlagState) -> str:
        source = FeatureFlags.get_override_source("enable_llm")
        badge = f"`override:{source}`" if source else ""
        if state.enable_llm and is_llm_enabled():
            return f"🧠 **LLM**: 有効 {badge}\n\n- LLM ストリーミング出力と自動コマンド補完が利用できます"
        return f"⚪ **LLM**: 無効 {badge}\n\n- ブラウザ制御とコマンド実行のみ利用可能"

    def _handle_engine_change(self, engine: str):
        if engine not in {"playwright", "cdp"}:
            engine = "playwright"
        FeatureFlags.set_override("runner.engine", engine)
        state = self._flag_service.get_current_state(force_refresh=True)
        return gr.update(value=state.runner_engine), gr.update(
            value=self._format_engine_status(state)
        )


def create_run_panel() -> RunAgentPanel:
    """RunAgentPanel インスタンスを生成するファクトリ。"""
    return RunAgentPanel()
