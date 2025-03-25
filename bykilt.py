import logging
import argparse
import os
import glob
import sys
import time  # Added for restart logic
from dotenv import load_dotenv
load_dotenv()
import subprocess
import asyncio

import gradio as gr
from gradio.themes import Citrus, Default, Glass, Monochrome, Ocean, Origin, Soft, Base

from src.utils import utils
from src.utils.default_config_settings import default_config, load_config_from_file, save_config_to_file
from src.utils.default_config_settings import save_current_config, update_ui_from_config
from src.utils.utils import update_model_dropdown, get_latest_files

# Import the new modules
from src.script.script_manager import run_script
from src.config.llms_parser import pre_evaluate_prompt, extract_params, resolve_sensitive_env_variables
from src.agent.agent_manager import stop_agent, stop_research_agent, run_org_agent, run_custom_agent
from src.agent.agent_manager import run_deep_search, get_globals, run_browser_agent
from src.ui.stream_manager import run_with_stream
from src.browser.browser_manager import close_global_browser, prepare_recording_path, initialize_browser

# Import the new modules for run_browser_agent
from src.config.action_translator import ActionTranslator
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager

import yaml  # 必要であればインストール: pip install pyyaml

# Configure logging
logger = logging.getLogger(__name__)

def load_actions_config():
    """Load actions configuration from llms.txt file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'llms.txt')
        if not os.path.exists(config_path):
            logger.warning(f"Actions config file not found at {config_path}")
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # デバッグ出力を追加
        logger.info(f"Loading actions from: {config_path}")
        
        # YAMLとして解析を試みる
        try:
            # YAMLパーサーを使用（llms.txtはYAML形式に見える）
            actions_config = yaml.safe_load(content)
            logger.info(f"Parsed config type: {type(actions_config)}")
            
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                logger.info(f"Found {len(actions_config['actions'])} actions")
                logger.info(f"Action names: {[a.get('name') for a in actions_config['actions']]}")
            else:
                logger.warning(f"Unexpected config structure: {list(actions_config.keys()) if isinstance(actions_config, dict) else type(actions_config)}")
            
            return actions_config
            
        except Exception as yaml_err:
            logger.warning(f"YAML parsing failed: {yaml_err}")
            
            # YAMLパースに失敗した場合は元の実装方法を試す
            actions_config = {}
            for line in content.split('\n'):
                if line.strip() and '=' in line:
                    key, value = line.split('=', 1)
                    actions_config[key.strip()] = value.strip()
            
            logger.info(f"Fallback parsing result: {actions_config}")
            return actions_config
            
    except Exception as e:
        logger.error(f"Error loading actions config: {e}")
        return {}

# Define proper mapping for Playwright commands
PLAYWRIGHT_COMMANDS = {
    'navigate': 'goto',
    'click': 'click',
    'fill': 'fill',
    'fill_form': 'fill',
    'keyboard_press': 'press',
    'wait_for_selector': 'wait_for_selector',
    'wait_for_navigation': 'wait_for_load_state',
    'screenshot': 'screenshot',
    'extract_content': 'query_selector_all'  # For content extraction
}

# Map theme names to theme objects
theme_map = {
    "Default": Default(), "Soft": Soft(), "Monochrome": Monochrome(), "Glass": Glass(),
    "Origin": Origin(), "Citrus": Citrus(), "Ocean": Ocean(), "Base": Base()
}

async def run_browser_agent(task, add_infos, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, 
                           llm_base_url, llm_api_key, use_vision, use_own_browser, headless, 
                           maintain_browser_session=False, tab_selection_strategy="new_tab"):
    """
    Run the browser agent using JSON-based execution.
    """
    browser_manager = BrowserDebugManager()
    debug_utils = DebugUtils(browser_manager=browser_manager)
    
    # セッションIDを取得（maintain_browser_sessionがTrueの場合のみ）
    session_id = browser_manager.session_manager.active_session_id if maintain_browser_session else None
    
    try:
        # ブラウザセッションを初期化
        browser_result = await browser_manager.initialize_with_session(
            session_id=session_id,
            use_own_browser=use_own_browser,
            headless=headless
        )
        
        if browser_result.get("status") != "success":
            return {"status": "error", "message": "ブラウザの初期化に失敗しました"}
        
        # 新しいセッションIDを取得
        session_id = browser_result.get("session_id")
        
        # アクションの解析と実行
        action_name, params = pre_evaluate_prompt(task)
        actions_config = load_actions_config()
        
        # JSONに変換
        translator = ActionTranslator()
        json_file_path = translator.translate_to_json(
            action_name, params, actions_config, 
            maintain_session=maintain_browser_session,
            tab_selection_strategy=tab_selection_strategy  # タブ選択戦略を渡す
        )
        
        # JSON実行
        result = await debug_utils.test_llm_response(
            json_file_path, use_own_browser, headless, 
            session_id=session_id,
            tab_selection_strategy=tab_selection_strategy  # タブ選択戦略を渡す
        )
        
        # セッション情報を結果に追加
        result["session_id"] = session_id
        result["session_maintained"] = maintain_browser_session
        
        return result
    finally:
        # セッション維持フラグに基づいてリソースをクリーンアップ
        if not maintain_browser_session:
            await browser_manager.cleanup_resources(session_id=session_id, maintain_session=False)
        else:
            # セッションを維持する場合は現在のブラウザ情報を更新
            browser = browser_manager.global_browser
            if (browser and session_id):
                browser_info = browser_manager._get_browser_info(browser)
                browser_manager.session_manager.update_session(session_id, browser_info)

def chrome_restart_dialog():
    """Chromeの再起動確認ダイアログを表示"""
    with gr.Blocks() as dialog:
        with gr.Box():
            gr.Markdown("### ⚠️ Chromeの再起動が必要です")
            gr.Markdown("Chromeは既に起動していますが、デバッグモードではありません。")
            gr.Markdown("すべてのChromeウィンドウを閉じて、デバッグモードで再起動しますか？")
            gr.Markdown("⚠️ **警告**: この操作により開いているすべてのChromeタブが閉じられます！")
            
            with gr.Row():
                yes_button = gr.Button("はい、Chromeを再起動する", variant="primary")
                no_button = gr.Button("いいえ、新しいウィンドウを試す", variant="secondary")
            
            result = gr.State(None)
            
            def set_yes():
                return "yes"
                
            def set_no():
                return "no"
            
            yes_button.click(fn=set_yes, outputs=result)
            no_button.click(fn=set_no, outputs=result)
    
    return dialog

async def show_restart_dialog():
    """Show a dialog to confirm Chrome restart and execute the restart logic."""
    dialog = chrome_restart_dialog()
    result = await dialog.launch()
    if result == "yes":
        # Implement Chrome restart logic
        try:
            # Kill Chrome process based on platform
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['killall', 'Google Chrome'], stderr=subprocess.DEVNULL)
            elif sys.platform == 'win32':  # Windows
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], stderr=subprocess.DEVNULL)
            else:  # Linux and others
                subprocess.run(['killall', 'chrome'], stderr=subprocess.DEVNULL)
            
            # Wait for Chrome to completely close
            time.sleep(2)
            
            # Start Chrome with debugging port
            chrome_path = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
            chrome_debugging_port = os.getenv("CHROME_DEBUGGING_PORT", "9222")
            chrome_user_data = os.getenv("CHROME_USER_DATA", "")
            
            cmd_args = [
                chrome_path,
                f"--remote-debugging-port={chrome_debugging_port}",
                "--no-first-run",
                "--no-default-browser-check"
            ]
            
            if chrome_user_data and chrome_user_data.strip():
                cmd_args.append(f"--user-data-dir={chrome_user_data}")
            
            # Start Chrome process
            subprocess.Popen(cmd_args)
            return "Chromeを再起動しました"
        except Exception as e:
            return f"再起動中にエラーが発生しました: {str(e)}"
    else:
        return "操作をキャンセルしました"

def create_ui(config, theme_name="Ocean"):
    """Create the Gradio UI with the specified configuration and theme"""
    css = """
    .gradio-container { max-width: 1200px !important; margin: auto !important; padding-top: 20px !important; }
    .header-text { text-align: center; margin-bottom: 30px; }
    .theme-section { margin-bottom: 20px; padding: 15px; border-radius: 10px; }
    """

    with gr.Blocks(title="2Bykilt", theme=theme_map[theme_name], css=css) as demo:
        with gr.Row():
            gr.Markdown("# 🪄🌐 2Bykilt\n### Enhanced Browser Control with AI and human, because for you", elem_classes=["header-text"])

        with gr.Tabs() as tabs:
            with gr.TabItem("⚙️ Agent Settings", id=1):
                with gr.Group():
                    agent_type = gr.Radio(["org", "custom"], label="Agent Type", value=config['agent_type'], info="Select the type of agent to use")
                    with gr.Column():
                        max_steps = gr.Slider(minimum=1, maximum=200, value=config['max_steps'], step=1, label="Max Run Steps", info="Maximum number of steps the agent will take")
                        max_actions_per_step = gr.Slider(minimum=1, maximum=20, value=config['max_actions_per_step'], step=1, label="Max Actions per Step", info="Maximum number of actions the agent will take per step")
                    with gr.Column():
                        use_vision = gr.Checkbox(label="Use Vision", value=config['use_vision'], info="Enable visual processing capabilities")
                        tool_calling_method = gr.Dropdown(label="Tool Calling Method", value=config['tool_calling_method'], interactive=True, allow_custom_value=True, choices=["auto", "json_schema", "function_calling"], info="Tool Calls Function Name", visible=False)

            with gr.TabItem("🔧 LLM Configuration", id=2):
                with gr.Group():
                    llm_provider = gr.Dropdown(choices=[provider for provider, model in utils.model_names.items()], label="LLM Provider", value=config['llm_provider'], info="Select your preferred language model provider")
                    llm_model_name = gr.Dropdown(label="Model Name", choices=utils.model_names['openai'], value=config['llm_model_name'], interactive=True, allow_custom_value=True, info="Select a model from the dropdown or type a custom model name")
                    llm_num_ctx = gr.Slider(minimum=2**8, maximum=2**16, value=config['llm_num_ctx'], step=1, label="Max Context Length", info="Controls max context length model needs to handle (less = faster)", visible=config['llm_provider'] == "ollama")
                    llm_temperature = gr.Slider(minimum=0.0, maximum=2.0, value=config['llm_temperature'], step=0.1, label="Temperature", info="Controls randomness in model outputs")
                    with gr.Row():
                        llm_base_url = gr.Textbox(label="Base URL", value=config['llm_base_url'], info="API endpoint URL (if required)")
                        llm_api_key = gr.Textbox(label="API Key", type="password", value=config['llm_api_key'], info="Your API key (leave blank to use .env)")

                    llm_provider.change(fn=lambda provider: gr.update(visible=provider == "ollama"), inputs=llm_provider, outputs=llm_num_ctx)
                    
                    with gr.Row():
                        dev_mode = gr.Checkbox(
                            label="Dev Mode",
                            value=config['dev_mode'],
                            info="Use LM Studio compatible endpoints"
                        )

            with gr.TabItem("🌐 Browser Settings", id=3):
                with gr.Group():
                    with gr.Row():
                        use_own_browser = gr.Checkbox(label="Use Own Browser", value=config['use_own_browser'], info="Use your existing browser instance")
                        keep_browser_open = gr.Checkbox(label="Keep Browser Open", value=config['keep_browser_open'], info="Keep Browser Open between Tasks")
                        headless = gr.Checkbox(label="Headless Mode", value=config['headless'], info="Run browser without GUI")
                        disable_security = gr.Checkbox(label="Disable Security", value=config['disable_security'], info="Disable browser security features")
                        enable_recording = gr.Checkbox(label="Enable Recording", value=config['enable_recording'], info="Enable saving browser recordings")
                    with gr.Row():
                        window_w = gr.Number(label="Window Width", value=config['window_w'], info="Browser window width")
                        window_h = gr.Number(label="Window Height", value=config['window_h'], info="Browser window height")
                    save_recording_path = gr.Textbox(label="Recording Path", placeholder="e.g. ./tmp/record_videos", value=config['save_recording_path'], info="Path to save browser recordings", interactive=True)
                    save_trace_path = gr.Textbox(label="Trace Path", placeholder="e.g. ./tmp/traces", value=config['save_trace_path'], info="Path to save Agent traces", interactive=True)
                    save_agent_history_path = gr.Textbox(label="Agent History Save Path", placeholder="e.g., ./tmp/agent_history", value=config['save_agent_history_path'], info="Specify the directory where agent history should be saved.", interactive=True)

                    maintain_browser_session = gr.Checkbox(
                        label="Maintain Browser Session",
                        value=False,
                        info="Keep browser session active between commands (for multi-step interactions)"
                    )

                    # Add tab selection strategy control
                    tab_selection_strategy = gr.Radio(
                        choices=["new_tab", "active_tab", "last_tab"],
                        value="active_tab",
                        label="Tab Selection Strategy",
                        info="Choose which browser tab to use for automation when using own browser",
                        visible=True
                    )

                    # Make tab selection strategy depend on use_own_browser
                    use_own_browser.change(
                        fn=lambda enabled: gr.update(visible=enabled),
                        inputs=use_own_browser,
                        outputs=tab_selection_strategy
                    )

                    # 再起動確認セクションを追加
                    with gr.Row():
                        restart_button = gr.Button("ブラウザを再起動", variant="secondary")
                        restart_status = gr.Markdown("")
                        
                        def restart_browser():
                            return asyncio.run(show_restart_dialog())
                        
                        restart_button.click(fn=restart_browser, outputs=restart_status)

            with gr.TabItem("🤖 Run Agent", id=4):
                task = gr.Textbox(label="Task Description", lines=4, placeholder="Enter your task or script name (e.g., search-for-something query=python)", value=config['task'], info="Describe what you want the agent to do or specify a script from llms.txt")
                add_infos = gr.Textbox(label="Additional Information", lines=3, placeholder="Add any helpful context or instructions...", info="Optional hints to help the LLM complete the task")
                with gr.Row():
                    run_button = gr.Button("▶️ Run Agent", variant="primary", scale=2)
                    stop_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                with gr.Row():
                    browser_view = gr.HTML(value="<h1 style='width:80vw; height:50vh'>Waiting for browser session...</h1>", label="Live Browser View")

            with gr.TabItem("🧐 Deep Research", id=5):
                research_task_input = gr.Textbox(label="Research Task", lines=5, value="Compose a report on the use of Reinforcement Learning for training Large Language Models, encompassing its origins, current advancements, and future prospects, substantiated with examples of relevant models and techniques. The report should reflect original insights and analysis, moving beyond mere summarization of existing literature.")
                with gr.Row():
                    max_search_iteration_input = gr.Number(label="Max Search Iteration", value=3, precision=0)
                    max_query_per_iter_input = gr.Number(label="Max Query per Iteration", value=1, precision=0)
                with gr.Row():
                    research_button = gr.Button("▶️ Run Deep Research", variant="primary", scale=2)
                    stop_research_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                markdown_output_display = gr.Markdown(label="Research Report")
                markdown_download = gr.File(label="Download Research Report")

            with gr.TabItem("📊 Results", id=6):
                with gr.Group():
                    recording_display = gr.Video(label="Latest Recording")
                    gr.Markdown("### Results")
                    with gr.Row():
                        with gr.Column():
                            final_result_output = gr.Textbox(label="Final Result", lines=3, show_label=True)
                        with gr.Column():
                            errors_output = gr.Textbox(label="Errors", lines=3, show_label=True)
                    with gr.Row():
                        with gr.Column():
                            model_actions_output = gr.Textbox(label="Model Actions", lines=3, show_label=True)
                        with gr.Column():
                            model_thoughts_output = gr.Textbox(label="Model Thoughts", lines=3, show_label=True)
                    trace_file = gr.File(label="Trace File")
                    agent_history_file = gr.File(label="Agent History")

                    # Connect buttons to functions
                    stop_button.click(fn=stop_agent, inputs=[], outputs=[errors_output, stop_button, run_button])
                    run_button.click(
                        fn=run_with_stream,
                        inputs=[
                            agent_type, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key,
                            use_own_browser, keep_browser_open, headless, disable_security, window_w, window_h,
                            save_recording_path, save_agent_history_path, save_trace_path, enable_recording, task, add_infos,
                            max_steps, use_vision, max_actions_per_step, tool_calling_method, dev_mode, maintain_browser_session,
                            tab_selection_strategy  # Add tab selection strategy parameter
                        ],
                        outputs=[
                            browser_view, final_result_output, errors_output, model_actions_output, model_thoughts_output,
                            recording_display, trace_file, agent_history_file, stop_button, run_button
                        ],
                    )
                    research_button.click(
                        fn=run_deep_search,
                        inputs=[
                            research_task_input, max_search_iteration_input, max_query_per_iter_input,
                            llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, 
                            llm_api_key, use_vision, use_own_browser, headless
                        ],
                        outputs=[markdown_output_display, markdown_download, stop_research_button, research_button]
                    )
                    stop_research_button.click(fn=stop_research_agent, inputs=[], outputs=[stop_research_button, research_button])

            with gr.TabItem("🎥 Recordings", id=7):
                def list_recordings(save_recording_path):
                    if not os.path.exists(save_recording_path):
                        return []
                    recordings = glob.glob(os.path.join(save_recording_path, "*.[mM][pP]4")) + glob.glob(os.path.join(save_recording_path, "*.[wW][eE][bB][mM]"))
                    recordings.sort(key=os.path.getctime)
                    numbered_recordings = [(recording, f"{idx}. {os.path.basename(recording)}") for idx, recording in enumerate(recordings, start=1)]
                    return numbered_recordings

                recordings_gallery = gr.Gallery(label="Recordings", value=list_recordings(config['save_recording_path']), columns=3, height="auto", object_fit="contain")
                refresh_button = gr.Button("🔄 Refresh Recordings", variant="secondary")
                refresh_button.click(fn=list_recordings, inputs=save_recording_path, outputs=recordings_gallery)

            with gr.TabItem("📁 Configuration", id=8):
                with gr.Group():
                    config_file_input = gr.File(label="Load Config File", file_types=[".pkl"], interactive=True)
                    load_config_button = gr.Button("Load Existing Config From File", variant="primary")
                    save_config_button = gr.Button("Save Current Config", variant="primary")
                    config_status = gr.Textbox(label="Status", lines=2, interactive=False)

                    load_config_button.click(
                        fn=update_ui_from_config,
                        inputs=[config_file_input],
                        outputs=[
                            agent_type, max_steps, max_actions_per_step, use_vision, tool_calling_method,
                            llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key,
                            use_own_browser, keep_browser_open, headless, disable_security, enable_recording,
                            window_w, window_h, save_recording_path, save_trace_path, save_agent_history_path,
                            task, config_status
                        ]
                    )
                    save_config_button.click(
                        fn=save_current_config,
                        inputs=[
                            agent_type, max_steps, max_actions_per_step, use_vision, tool_calling_method,
                            llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key,
                            use_own_browser, keep_browser_open, headless, disable_security,
                            enable_recording, window_w, window_h, save_recording_path, save_trace_path,
                            save_agent_history_path, task,
                        ],
                        outputs=[config_status]
                    )

        llm_provider.change(lambda provider, api_key, base_url: update_model_dropdown(provider, api_key, base_url), inputs=[llm_provider, llm_api_key, llm_base_url], outputs=llm_model_name)
        enable_recording.change(lambda enabled: gr.update(interactive=enabled), inputs=enable_recording, outputs=save_recording_path)
        use_own_browser.change(fn=close_global_browser)
        keep_browser_open.change(fn=close_global_browser)

    return demo

def main():
    parser = argparse.ArgumentParser(description="Gradio UI for 2Bykilt Agent")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on")
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    parser.add_argument("--dark-mode", action="store_true", help="Enable dark mode")
    args = parser.parse_args()  # Fix: Use parse_args() to get arguments

    print(f"🔍 DEBUG: Selected theme: {args.theme}")
    print(f"🔍 DEBUG: Dark mode enabled: {args.dark_mode}")

    config_dict = default_config()
    demo = create_ui(config_dict, theme_name=args.theme)
    demo.launch(server_name=args.ip, server_port=args.port)

if __name__ == '__main__':
    main()
    
async def on_run_agent_click(task, add_infos, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key, use_vision, use_own_browser, headless):
    try:
        # bykilt.pyのコマンド処理箇所に追加
        print(f"🔎 入力コマンド解析: {task}")
        action_name, params = pre_evaluate_prompt(task)
        print(f"🔎 解析結果: アクション={action_name}, パラメータ={params}")

        # CommandDispatcherを使用してコマンド実行
        from src.agent.agent_manager import run_command
        result = await run_command(
            prompt=task,
            use_own_browser=use_own_browser,
            headless=headless
        )
        
        if result.get("action_type") == "llm":
            # 既存のLLM処理フローを使用
            return await run_browser_agent(task, add_infos, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key, use_vision, use_own_browser, headless)
        
        # アクション実行結果を表示
        success = result.get("success", False)
        message = f"### アクション実行結果\n\n"
        message += f"**成功**: {'はい' if success else 'いいえ'}\n\n"
        message += f"**アクションタイプ**: {result.get('action_type', '不明')}\n\n"
        
        if "message" in result:
            message += f"**メッセージ**: {result.get('message', '')}\n\n"
        
        if "stdout" in result:
            message += f"**出力**:\n```\n{result.get('stdout', '')}\n```\n\n"
        
        if "stderr" in result and result.get("stderr"):
            message += f"**エラー出力**:\n```\n{result.get('stderr', '')}\n```\n\n"
            
        if "command" in result:
            message += f"**実行コマンド**:\n```\n{result.get('command', '')}\n```\n\n"
            
        if "error" in result and result.get("error"):
            message += f"**エラー**:\n```\n{result.get('error', '')}\n```\n\n"
            
        return message, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
            
    except Exception as e:
        import traceback
        error_msg = f"エラーが発生しました: {e}\n{traceback.format_exc()}"
        return error_msg, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)