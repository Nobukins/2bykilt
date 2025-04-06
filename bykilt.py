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
import json  # Added to fix missing import

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
from src.browser.browser_config import BrowserConfig

# Import the new modules for run_browser_agent
from src.config.action_translator import ActionTranslator
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager
from src.ui.command_helper import CommandHelper  # Import CommandHelper class
from src.utils.playwright_codegen import run_playwright_codegen, save_as_action_file
from src.utils.log_ui import create_log_tab  # Import log UI integration

import yaml  # 必要であればインストール: pip install pyyaml

# Configure logging
logger = logging.getLogger(__name__)

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
            no_button.click(fn=set_no(), outputs=result)
    
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

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

browser_config = BrowserConfig()

def create_ui(config, theme_name="Ocean"):
    """Create the Gradio UI with the specified configuration and theme"""
    # Load CSS from external file
    css_path = os.path.join(os.path.dirname(__file__), "assets", "css", "styles.css")
    with open(css_path, 'r', encoding='utf-8') as f:
        css = f.read()

    # 追加: カスタムヘッダーにCSP設定を含める
    custom_head = """
    <meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; font-src * data:;">
    <script>
    console.log('カスタムヘッダー読み込み完了');
    </script>
    """

    with gr.Blocks(title="2Bykilt", theme=theme_map[theme_name], css=css, head=custom_head) as demo:
        # ======================================================
        # Define shared variables for all tabs
        # ======================================================
        window_w = gr.Number(value=config.get('window_width', 1920), label="ブラウザウィンドウ幅", precision=0, visible=False)
        window_h = gr.Number(value=config.get('window_height', 1080), label="ブラウザウィンドウ高さ", precision=0, visible=False)
        enable_recording = gr.Checkbox(label="録画を有効にする", value=config.get('enable_recording', True), visible=False)
        maintain_browser_session = gr.Checkbox(label="ブラウザセッションを維持", value=config.get('maintain_browser_session', False), visible=False)
        tab_selection_strategy = gr.Radio(["new_tab", "reuse_tab"], label="タブ選択戦略", 
                                           value=config.get('tab_selection_strategy', "new_tab"), visible=False)
        save_recording_path = gr.Textbox(label="録画保存パス", value=config.get('save_recording_path', './tmp/record_videos'), visible=False)
        save_trace_path = gr.Textbox(label="トレース保存パス", value=config.get('save_trace_path', './tmp/traces'), visible=False)
        save_agent_history_path = gr.Textbox(label="エージェント履歴パス", value=config.get('save_agent_history_path', './tmp/agent_history'), visible=False)

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
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### ブラウザー設定")
                        
                        browser_type = gr.Dropdown(
                            choices=["chrome", "edge"], 
                            label="使用するブラウザ", 
                            value=browser_config.config.get("current_browser", "chrome"),
                            info="Chrome または Edge を選択してください"
                        )
                        
                        use_own_browser = gr.Checkbox(label="既存のブラウザを使用", value=False)
                        headless = gr.Checkbox(label="ヘッドレスモード", value=False)
                        keep_browser_open = gr.Checkbox(label="ブラウザを開いたままにする", value=False)
                        disable_security = gr.Checkbox(
                            label="セキュリティを無効化", 
                            value=browser_config.get_browser_settings()["disable_security"],
                            info="ブラウザのセキュリティ機能を無効化します"
                        )
                        
                        # Directly render components instead of using .update()
                        with gr.Row():
                            window_w = gr.Number(value=config.get('window_width', 1920), 
                                                 label="ブラウザウィンドウ幅", 
                                                 precision=0)
                            window_h = gr.Number(value=config.get('window_height', 1080), 
                                                 label="ブラウザウィンドウ高さ", 
                                                 precision=0)
                        
                        enable_recording = gr.Checkbox(label="録画を有効にする", 
                                                       value=config.get('enable_recording', True))
                        maintain_browser_session = gr.Checkbox(label="ブラウザセッションを維持", 
                                                               value=config.get('maintain_browser_session', False))
                        tab_selection_strategy = gr.Radio(["new_tab", "reuse_tab"], 
                                                           label="タブ選択戦略",
                                                           value=config.get('tab_selection_strategy', "new_tab"))
                        save_recording_path = gr.Textbox(label="録画保存パス", 
                                                         value=config.get('save_recording_path', './tmp/record_videos'))
                        save_trace_path = gr.Textbox(label="トレース保存パス", 
                                                     value=config.get('save_trace_path', './tmp/traces'))
                        save_agent_history_path = gr.Textbox(label="エージェント履歴パス", 
                                                             value=config.get('save_agent_history_path', './tmp/agent_history'))
                        
                        browser_path_info = gr.Markdown(
                            value=f"**現在のブラウザパス**: {browser_config.get_browser_settings()['path']}", 
                            visible=True
                        )
                        user_data_info = gr.Markdown(
                            value=f"**ユーザーデータパス**: {browser_config.get_browser_settings()['user_data']}",
                            visible=True
                        )
                        
                        update_browser_btn = gr.Button("ブラウザ設定を更新", variant="primary")
                        browser_update_result = gr.Markdown("")
                        
                        def update_browser_settings(browser_selection, disable_security_flag):
                            """Update browser settings and return results."""
                            try:
                                browser_config.set_current_browser(browser_selection)
                                settings = browser_config.get_browser_settings()
                                settings["disable_security"] = disable_security_flag
                                
                                browser_path = f"**現在のブラウザパス**: {settings['path']}"
                                user_data = f"**ユーザーデータパス**: {settings['user_data']}"
                                
                                return (
                                    browser_path,
                                    user_data,
                                    f"✅ ブラウザ設定を {browser_selection.upper()} に更新しました"
                                )
                            except Exception as e:
                                return (
                                    browser_path_info.value,
                                    user_data_info.value,
                                    f"❌ エラーが発生しました: {str(e)}"
                                )
                        
                        browser_type.change(
                            fn=update_browser_settings,
                            inputs=[browser_type, disable_security],
                            outputs=[browser_path_info, user_data_info, browser_update_result]
                        )
                        
                        update_browser_btn.click(
                            fn=update_browser_settings,
                            inputs=[browser_type, disable_security],
                            outputs=[browser_path_info, user_data_info, browser_update_result]
                        )

            with gr.TabItem("🤖 Run Agent", id=4):
                # Add command helper integration
                with gr.Accordion("📋 Available Commands", open=False):
                    commands_table = gr.DataFrame(
                        headers=["Command", "Description", "Usage"],
                        label="Available Commands",
                        interactive=False
                    )
                    
                    def load_commands_table():
                        """Load commands into the table"""
                        helper = CommandHelper()
                        return helper.get_commands_for_display()
                    
                    refresh_commands = gr.Button("🔄 Refresh Commands")
                    refresh_commands.click(fn=load_commands_table, outputs=commands_table)
                
                # Update task input with placeholder for command usage
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task or use @command format (e.g., @search query=python)", 
                    value=config['task'],
                    info="Describe the task or use a command (@name or /name)"
                )
                
                # Add command table click-to-insert functionality
                def insert_command(evt: gr.SelectData):
                    """コマンドテンプレートをタスク入力に挿入"""
                    helper = CommandHelper()
                    commands = helper.get_all_commands()
                    
                    # 表示用コマンドリストを取得
                    display_commands = helper.get_commands_for_display()
                    
                    if evt.index[0] < len(display_commands):
                        # 選択されたコマンド名を取得
                        selected_command_name = display_commands[evt.index[0]][0]
                        
                        # 完全なコマンド情報を取得
                        command = next((cmd for cmd in commands if cmd['name'] == selected_command_name), None)
                        
                        if command:
                            # コマンドテンプレートを生成
                            command_text = f"@{command['name']}"
                            
                            # 必須パラメータがあれば追加
                            if command.get('params'):
                                required_params = [p for p in command['params'] if p.get('required', False)]
                                if required_params:
                                    param_str = " ".join([f"{p['name']}=" for p in required_params])
                                    command_text += f" {param_str}"
                            
                            return command_text
                    
                    return ""  # 何も選択されなかった場合
                
                commands_table.select(fn=insert_command, outputs=task)
                
                # Load commands into the table initially
                commands_table.value = load_commands_table()
                
                add_infos = gr.Textbox(label="Additional Information", lines=3, placeholder="Add any helpful context or instructions...")
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

            with gr.TabItem("🎭 Playwright Codegen", id=8):
                with gr.Group():
                    gr.Markdown("### 🎮 ブラウザ操作スクリプト自動生成")
                    gr.Markdown("URLを入力してPlaywright codegenを起動し、ブラウザ操作を記録。生成されたスクリプトはアクションファイルとして保存できます。")
                    
                    with gr.Row():
                        url_input = gr.Textbox(
                            label="ウェブサイトURL", 
                            placeholder="記録するURLを入力（例: https://example.com）",
                            info="Playwrightが記録を開始するURL"
                        )
                        run_codegen_button = gr.Button("▶️ Playwright Codegenを実行", variant="primary")
                        
                    codegen_status = gr.Markdown("")
                    
                    with gr.Accordion("生成されたスクリプト", open=True):
                        generated_script = gr.Code(
                            label="生成スクリプト",
                            language="python",
                            value="# ここに生成されたスクリプトが表示されます",
                            interactive=False,
                            lines=15
                        )
                        copy_script_button = gr.Button("📋 クリップボードにコピー")
                        
                    with gr.Accordion("アクションとして保存", open=True):
                        with gr.Row():
                            action_file_name = gr.Textbox(
                                label="ファイル名", 
                                placeholder="ファイル名を入力（.pyは不要）",
                                info="保存するアクションファイル名（actionsフォルダに保存されます）"
                            )
                            action_command_name = gr.Textbox(
                                label="コマンド名", 
                                placeholder="llms.txtに登録するコマンド名（空白の場合はファイル名を使用）",
                                info="llms.txtに登録するコマンド名（空白の場合はファイル名を使用）"
                            )
                        
                        save_action_button = gr.Button("💾 アクションファイルとして保存", variant="primary")
                        save_status = gr.Markdown("")
                        
                    # Playwright codegen操作のハンドラ関数
                    def handle_run_codegen(url):
                        if not url or url.strip() == "":
                            return "⚠️ 有効なURLを入力してください", "# URLを入力してスクリプトを生成してください"
                        
                        success, result = run_playwright_codegen(url)
                        if success:
                            return "✅ スクリプトが正常に生成されました", result
                        else:
                            return f"❌ エラー: {result}", "# スクリプト生成中にエラーが発生しました"
                    
                    def handle_save_action(script, file_name, command_name):
                        if not script or script.strip() == "# ここに生成されたスクリプトが表示されます" or script.strip() == "# URLを入力してスクリプトを生成してください" or script.strip() == "# スクリプト生成中にエラーが発生しました":
                            return "⚠️ 保存する有効なスクリプトがありません。まずスクリプトを生成してください。"
                        
                        if not file_name or file_name.strip() == "":
                            return "⚠️ 有効なファイル名を入力してください。"
                        
                        success, message = save_as_action_file(script, file_name, command_name)
                        if success:
                            return f"✅ {message}"
                        else:
                            return f"❌ {message}"
                    
                    # UI要素と関数の連携
                    run_codegen_button.click(
                        fn=handle_run_codegen,
                        inputs=[url_input],
                        outputs=[codegen_status, generated_script]
                    )
                    
                    save_action_button.click(
                        fn=handle_save_action,
                        inputs=[generated_script, action_file_name, action_command_name],
                        outputs=[save_status]
                    )
                    
                    # クリップボード機能のためのJavaScript
                    copy_script_button.click(fn=None, js="""
                    () => {
                        const codeBlock = document.querySelector('.gradio-container [data-testid="code"] pre code');
                        if (codeBlock) {
                            const text = codeBlock.textContent;
                            navigator.clipboard.writeText(text);
                            const button = document.querySelector('button:contains("クリップボードにコピー")');
                            const originalText = button.textContent;
                            button.textContent = "✓ コピーしました！";
                            setTimeout(() => { button.textContent = originalText; }, 2000);
                        }
                        return null;
                    }
                    """)

            with gr.TabItem("📁 Configuration", id=9):
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

        # JavaScriptファイル読み込み部分を強化
        try:
            # コマンドデータ取得を強化
            helper = CommandHelper()
            commands_json = helper.get_all_commands()
            
            # デバッグ出力を追加
            print(f"コマンドデータ取得: {len(commands_json)}件")
            for cmd in commands_json[:3]:  # 最初の3つだけ表示
                print(f"  - {cmd.get('name', 'No name')}: {cmd.get('description', 'No description')}")
            
            # JSONシリアライズを例外処理でラップ
            try:
                commands_json_str = json.dumps(commands_json)
                print(f"JSONシリアライズ成功: {len(commands_json_str)}バイト")
            except Exception as json_err:
                print(f"JSONシリアライズエラー: {json_err}")
                commands_json_str = "[]"  # 空の配列をフォールバックとして使用
            
            # HTMLとJavaScriptを結合
            combined_html = f"""
            <script>
            // コマンドデータをグローバル変数として設定
            console.log("コマンドデータを埋め込みます");
            window.embeddedCommands = {commands_json_str};
            console.log("埋め込みコマンド数:", window.embeddedCommands ? window.embeddedCommands.length : 0);
            
            // コマンドサジェスト機能クラス
            class CommandSuggest {{
                constructor() {{
                    this.commands = window.embeddedCommands || [];
                    this.initialized = false;
                    this.suggestionsContainer = null;
                    this.activeTextarea = null;
                    console.log("CommandSuggest初期化:", this.commands.length + "個のコマンド");
                    this.initialize();
                }}
                
                initialize() {{
                    // テキストエリアを検索
                    setTimeout(() => this.findTextArea(), 1000);
                }}
                
                findTextArea() {{
                    const textareas = document.querySelectorAll('textarea[placeholder*="task" i], textarea[placeholder*="description" i]');
                    if (textareas.length > 0) {{
                        this.activeTextarea = textareas[0];
                        console.log("テキストエリアを検出:", this.activeTextarea);
                        this.setupListeners();
                        this.createSuggestionsContainer();
                        this.initialized = true;
                    }} else {{
                        console.log("テキストエリアが見つかりません。再試行します...");
                        setTimeout(() => this.findTextArea(), 1000);
                    }}
                }}
                
                setupListeners() {{
                    // テキストエリアにイベントリスナーを設定
                    this.activeTextarea.addEventListener('input', (e) => this.handleInput(e));
                    this.activeTextarea.addEventListener('keydown', (e) => this.handleKeydown(e));
                }}
                
                createSuggestionsContainer() {{
                    // コマンド候補表示用のコンテナを作成
                    this.suggestionsContainer = document.createElement('div');
                    this.suggestionsContainer.className = 'command-suggestions';
                    this.suggestionsContainer.style.position = 'absolute';
                    this.suggestionsContainer.style.zIndex = '9999';
                    this.suggestionsContainer.style.backgroundColor = 'white';
                    this.suggestionsContainer.style.border = '1px solid #ddd';
                    this.suggestionsContainer.style.borderRadius = '4px';
                    this.suggestionsContainer.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
                    this.suggestionsContainer.style.maxHeight = '200px';
                    this.suggestionsContainer.style.overflow = 'auto';
                    this.suggestionsContainer.style.width = 'auto';
                    this.suggestionsContainer.style.minWidth = '300px';
                    this.suggestionsContainer.style.display = 'none';
                    document.body.appendChild(this.suggestionsContainer);
                }}
                
                handleInput(e) {{
                    const text = e.target.value;
                    const cursorPos = e.target.selectionStart;
                    
                    // @または/の入力を検出
                    const lastAtPos = text.lastIndexOf('@', cursorPos - 1);
                    const lastSlashPos = text.lastIndexOf('/', cursorPos - 1);
                    
                    const triggerPos = Math.max(lastAtPos, lastSlashPos);
                    
                    if (triggerPos !== -1 && triggerPos < cursorPos) {{
                        const commandPart = text.substring(triggerPos + 1, cursorPos);
                        
                        // スペースがなければコマンド入力中と判断
                        if (!commandPart.includes(' ') && !commandPart.includes('\\n')) {{
                            this.showSuggestions(commandPart, triggerPos);
                            return;
                        }}
                    }}
                    
                    // サジェストを非表示
                    if (this.suggestionsContainer) {{
                        this.suggestionsContainer.style.display = 'none';
                    }}
                }}
                
                showSuggestions(inputText, triggerPos) {{
                    // コマンド候補をフィルタリング
                    const filtered = this.commands.filter(cmd => 
                        cmd.name.toLowerCase().startsWith(inputText.toLowerCase())
                    );
                    
                    // 結果がなければ非表示
                    if (filtered.length === 0) {{
                        this.suggestionsContainer.style.display = 'none';
                        return;
                    }}
                    
                    // 位置調整
                    const rect = this.activeTextarea.getBoundingClientRect();
                    this.suggestionsContainer.style.top = `${{rect.bottom + window.scrollY}}px`;
                    this.suggestionsContainer.style.left = `${{rect.left + window.scrollX}}px`;
                    
                    // サジェスト項目の生成
                    this.suggestionsContainer.innerHTML = '';
                    filtered.forEach(cmd => {{
                        const item = document.createElement('div');
                        item.className = 'suggestion-item';
                        item.dataset.command = cmd.name;
                        item.style.padding = '8px 12px';
                        item.style.cursor = 'pointer';
                        
                        const nameSpan = document.createElement('span');
                        nameSpan.textContent = cmd.name;
                        nameSpan.style.fontWeight = 'bold';
                        item.appendChild(nameSpan);
                        
                        if (cmd.description) {{
                            const descSpan = document.createElement('span');
                            descSpan.style.color = '#666';
                            descSpan.style.marginLeft = '10px';
                            descSpan.textContent = cmd.description;
                        }}
                        
                        // クリックイベント
                        item.addEventListener('click', () => {{
                            this.insertCommand(cmd, triggerPos);
                        }});
                        
                        this.suggestionsContainer.appendChild(item);
                    }});
                    
                    // 表示
                    this.suggestionsContainer.style.display = 'block';
                }}
                
                handleKeydown(e) {{
                    // キーボード操作の処理
                    if (this.suggestionsContainer && this.suggestionsContainer.style.display === 'block') {{
                        const items = this.suggestionsContainer.querySelectorAll('.suggestion-item');
                        let activeItem = this.suggestionsContainer.querySelector('.suggestion-item.active');
                        
                        switch(e.key) {{
                            case 'Enter':
                                if (activeItem) {{
                                    e.preventDefault();
                                    const cmdName = activeItem.dataset.command;
                                    const cmd = this.commands.find(c => c.name === cmdName);
                                    if (cmd) {{
                                        this.insertCommand(cmd, parseInt(this.activeTextarea.dataset.triggerPos));
                                    }}
                                }}
                                break;
                            case 'Escape':
                                this.suggestionsContainer.style.display = 'none';
                                break;
                        }}
                    }}
                }}
                
                insertCommand(cmd, triggerPos) {{
                    // コマンドを挿入
                    const textarea = this.activeTextarea;
                    const text = textarea.value;
                    
                    let newText = text.substring(0, triggerPos + 1) + cmd.name;
                    
                    // 必須パラメータがあれば追加
                    if (cmd.params && cmd.params.length > 0) {{
                        const requiredParams = cmd.params.filter(p => p.required);
                        if (requiredParams.length > 0) {{
                            newText += ' ' + requiredParams.map(p => `${{p.name}}=`).join(' ');
                        }}
                    }}
                    
                    // カーソル以降のテキスト
                    newText += text.substring(textarea.selectionStart);
                    
                    textarea.value = newText;
                    textarea.focus();
                    
                    // サジェスト非表示
                    this.suggestionsContainer.style.display = 'none';
                }}
                
                showDebugInfo() {{
                    console.log("=== コマンドサジェスト状態 ===");
                    console.log("初期化完了:", this.initialized);
                    console.log("コマンド数:", this.commands.length);
                    if (this.commands.length > 0) {{
                        console.log("コマンド例:", this.commands[0]);
                    }}
                    console.log("テキストエリア:", this.activeTextarea ? "検出済み" : "未検出");
                    console.log("サジェストコンテナ:", this.suggestionsContainer ? "作成済み" : "未作成");
                    console.log("========================");
                }}
            }}
            
            // ページ読み込み完了時に初期化
            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    console.log("CommandSuggest初期化を開始");
                    window.CommandSuggest = new CommandSuggest();
                    window.commandSuggestLoaded = true;
                }}, 1000);
            }});
            </script>
            
            <div style="margin: 10px 0; text-align: center;">
                <button onclick="console.log('デバッグボタンがクリックされました'); console.log('window.embeddedCommandsの状態:', window.embeddedCommands ? ('存在します(' + window.embeddedCommands.length + '件)') : '存在しません'); console.log('window.CommandSuggestの状態:', window.CommandSuggest ? '初期化済み' : '未初期化'); window.CommandSuggest && window.CommandSuggest.showDebugInfo(); return false;" 
                        style="padding: 8px 12px; background: #0078d7; color: white; border: none; border-radius: 4px; cursor: pointer;">
                    コマンドサジェスト詳細デバッグ
                </button>
            </div>
            """
            
            # 結合したHTMLを埋め込み
            gr.HTML(combined_html)
            
        except Exception as e:
            import traceback
            print(f"JavaScriptファイル読み込みエラー: {e}")
            print(traceback.format_exc())
            gr.HTML(f'''
            <div style="color: red; padding: 10px; border: 1px solid red; margin: 10px 0;">
                <h3>JavaScript読み込みエラー</h3>
                <p>{str(e)}</p>
                <pre>{traceback.format_exc()}</pre>
            </div>
            ''')

        # Add log display tab
        create_log_tab()

    return demo

from src.api.app import create_fastapi_app, run_app

def main():
    parser = argparse.ArgumentParser(description="Gradio UI for 2Bykilt Agent")
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on")
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    parser.add_argument("--dark-mode", action="store_true", help="Enable dark mode")
    args = parser.parse_args()

    print(f"🔍 DEBUG: Selected theme: {args.theme}")
    print(f"🔍 DEBUG: Dark mode enabled: {args.dark_mode}")

    config_dict = default_config()
    demo = create_ui(config_dict, theme_name=args.theme)
    
    # Create the asset directories if they don't exist
    assets_dir = os.path.join(os.path.dirname(__file__), "assets")
    css_dir = os.path.join(assets_dir, "css")
    js_dir = os.path.join(assets_dir, "js")
    fonts_dir = os.path.join(assets_dir, "fonts")
    
    os.makedirs(css_dir, exist_ok=True)
    os.makedirs(js_dir, exist_ok=True)
    os.makedirs(fonts_dir, exist_ok=True)
    
    # Create font family directories
    for family in ["ui-sans-serif", "system-ui"]:
        family_dir = os.path.join(fonts_dir, family)
        os.makedirs(family_dir, exist_ok=True)
        
        # Create placeholder font files if they don't exist
        for weight in ["Regular", "Bold"]:
            font_path = os.path.join(family_dir, f"{family}-{weight}.woff2")
            if not os.path.exists(font_path):
                # Create an empty file as placeholder
                with open(font_path, 'wb') as f:
                    pass
    
    # GradioとFastAPIを統合 - モジュール化版
    app = create_fastapi_app(demo, args)
    run_app(app, args)

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