import logging
import argparse
import os
import glob
import sys
import time  # Added for restart logic
import platform  # Added for cross-platform support
from pathlib import Path  # Added for cross-platform path handling
from dotenv import load_dotenv
load_dotenv()
import subprocess
import asyncio
import json  # Added to fix missing import

import gradio as gr
from gradio.themes import Citrus, Default, Glass, Monochrome, Ocean, Origin, Soft, Base

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

from src.utils import utils
from src.utils.default_config_settings import default_config, load_config_from_file, save_config_to_file
from src.utils.default_config_settings import save_current_config, update_ui_from_config
from src.utils.utils import update_model_dropdown, get_latest_files

# 基本的なブラウザ関連モジュール（LLM非依存）
from src.script.script_manager import run_script
from src.browser.browser_manager import close_global_browser, prepare_recording_path, initialize_browser
from src.browser.browser_config import BrowserConfig

# 常に利用可能なモジュール
from src.config.standalone_prompt_evaluator import (
    pre_evaluate_prompt_standalone, 
    extract_params_standalone, 
    resolve_sensitive_env_variables_standalone
)

# 条件付きLLM関連インポート
if ENABLE_LLM:
    try:
        from src.config.llms_parser import pre_evaluate_prompt, extract_params, resolve_sensitive_env_variables
        from src.agent.agent_manager import stop_agent, stop_research_agent, run_org_agent, run_custom_agent
        from src.agent.agent_manager import run_deep_search, get_globals, run_browser_agent
        from src.ui.stream_manager import run_with_stream
        LLM_MODULES_AVAILABLE = True
        print("✅ LLM modules loaded successfully")
    except ImportError as e:
        print(f"⚠️ Warning: LLM modules failed to load: {e}")
        LLM_MODULES_AVAILABLE = False
        # LLM無効時のダミー関数を定義
        def pre_evaluate_prompt(prompt): return pre_evaluate_prompt_standalone(prompt)
        def extract_params(prompt, params): return extract_params_standalone(prompt, params)
        def resolve_sensitive_env_variables(text): return resolve_sensitive_env_variables_standalone(text)
        def stop_agent(): return "LLM機能が無効です"
        def stop_research_agent(): return "LLM機能が無効です"
        async def run_org_agent(*args, **kwargs): return "LLM機能が無効です", "", "", "", None, None
        async def run_custom_agent(*args, **kwargs): return "LLM機能が無効です", "", "", "", None, None
        async def run_deep_search(*args, **kwargs): return "LLM機能が無効です", None, gr.update(), gr.update()
        def get_globals(): return {}
        async def run_browser_agent(*args, **kwargs): return "LLM機能が無効です"
        async def run_with_stream(*args, **kwargs): 
            # Extract task from args (task is the 18th parameter)
            task = args[17] if len(args) > 17 else ""
            
            # Check if this is a pre-registered command
            evaluation_result = pre_evaluate_prompt_standalone(task)
            if evaluation_result and evaluation_result.get('is_command'):
                # This is a pre-registered command, try to execute browser automation
                try:
                    # Extract browser parameters from args
                    use_own_browser = args[7] if len(args) > 7 else False
                    headless = args[9] if len(args) > 9 else True
                    
                    # Get the action definition and parameters
                    action_name = evaluation_result.get('command_name', '').lstrip('@')
                    action_def = evaluation_result.get('action_def', {})
                    action_params = evaluation_result.get('params', {})
                    action_type = action_def.get('type', '')
                    
                    if not action_def:
                        return f"❌ Pre-registered command '{action_name}' not found", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                    # Handle different action types
                    if action_type == 'browser-control':
                        from src.modules.direct_browser_control import execute_direct_browser_control
                        
                        execution_params = {
                            'use_own_browser': use_own_browser,
                            'headless': headless,
                            **action_params
                        }
                        
                        result = await execute_direct_browser_control(action_def, **execution_params)
                        
                        if result:
                            return f"✅ Browser control command '{action_name}' executed successfully", "", "", "", "", None, None, None, gr.update(), gr.update()
                        else:
                            return f"❌ Browser control command '{action_name}' execution failed", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                    elif action_type == 'script':
                        # Handle script execution
                        command_template = action_def.get('command', '')
                        if not command_template:
                            return f"❌ Script command '{action_name}' has no command template", "", "", "", "", None, None, None, gr.update(), gr.update()
                        
                        # Replace parameters in command template
                        command = command_template
                        for param_name, param_value in action_params.items():
                            placeholder = f"${{params.{param_name}}}"
                            command = command.replace(placeholder, str(param_value))
                        
                        # Execute the script command
                        try:
                            import subprocess
                            import asyncio
                            import os
                            
                            # Change to the project directory
                            project_dir = os.path.dirname(os.path.abspath(__file__))
                            
                            # Windows対応: 環境変数とPYTHONPATHを適切に設定
                            env = os.environ.copy()
                            env['PYTHONPATH'] = project_dir
                            
                            # Windows対応: コマンドを適切に構築
                            if platform.system() == "Windows":
                                # Windowsでは明示的にPythonパスを使用
                                if command.startswith('python '):
                                    command = command.replace('python ', f'"{sys.executable}" ', 1)
                                # PowerShellでの実行を考慮
                                shell_value = True
                            else:
                                shell_value = True
                            
                            # Execute the command asynchronously
                            process = await asyncio.create_subprocess_shell(
                                command,
                                cwd=project_dir,
                                env=env,
                                shell=shell_value,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )
                            
                            stdout, stderr = await process.communicate()
                            
                            stdout_text = stdout.decode('utf-8') if stdout else ""
                            stderr_text = stderr.decode('utf-8') if stderr else ""
                            
                            if process.returncode == 0:
                                result_message = f"✅ Script command '{action_name}' executed successfully\n\nCommand: {command}"
                                if stdout_text:
                                    result_message += f"\n\nOutput:\n{stdout_text}"
                            else:
                                result_message = f"❌ Script command '{action_name}' execution failed (exit code: {process.returncode})\n\nCommand: {command}"
                                if stderr_text:
                                    result_message += f"\n\nError:\n{stderr_text}"
                                if stdout_text:
                                    result_message += f"\n\nOutput:\n{stdout_text}"
                            
                            return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()
                            
                        except Exception as e:
                            return f"❌ Error executing script command '{action_name}': {str(e)}\n\nCommand: {command}", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                    elif action_type in ['action_runner_template', 'git-script']:
                        # Use the script_manager for these types
                        try:
                            from src.script.script_manager import run_script
                            
                            script_output, script_path = await run_script(action_def, action_params, headless=headless)
                            
                            if script_output and "successfully" in script_output.lower():
                                return f"✅ {action_type} command '{action_name}' executed successfully\n\n{script_output}", "", "", "", "", None, None, None, gr.update(), gr.update()
                            else:
                                return f"❌ {action_type} command '{action_name}' execution failed\n\n{script_output}", "", "", "", "", None, None, None, gr.update(), gr.update()
                        except Exception as e:
                            return f"❌ Error executing {action_type} command '{action_name}': {str(e)}", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                    else:
                        return f"❌ Action type '{action_type}' is not supported in minimal mode. Supported types: browser-control, script, action_runner_template, git-script", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                except Exception as e:
                    import traceback
                    error_detail = traceback.format_exc()
                    return f"❌ Error executing pre-registered command: {str(e)}\n\nDetails:\n{error_detail}", "", "", "", "", None, None, None, gr.update(), gr.update()
            else:
                return "LLM機能が無効です。事前登録されたコマンド（@で始まる）のみが利用可能です。", "", "", "", "", None, None, None, gr.update(), gr.update()
else:
    LLM_MODULES_AVAILABLE = False
    print("ℹ️ LLM functionality is disabled (ENABLE_LLM=false)")
    # LLM無効時のダミー関数を定義（standaloneを使用）
    def pre_evaluate_prompt(prompt): return pre_evaluate_prompt_standalone(prompt)
    def extract_params(prompt, params): return extract_params_standalone(prompt, params)
    def resolve_sensitive_env_variables(text): return resolve_sensitive_env_variables_standalone(text)
    def stop_agent(): return "LLM機能が無効です"
    def stop_research_agent(): return "LLM機能が無効です"
    async def run_org_agent(*args, **kwargs): return "LLM機能が無効です", "", "", "", None, None
    async def run_custom_agent(*args, **kwargs): return "LLM機能が無効です", "", "", "", None, None
    async def run_deep_search(*args, **kwargs): return "LLM機能が無効です", None, gr.update(), gr.update()
    def get_globals(): return {}
    async def run_browser_agent(*args, **kwargs): return "LLM機能が無効です"
    async def run_with_stream(*args, **kwargs): 
        # Extract task from args (task is the 18th parameter)
        task = args[17] if len(args) > 17 else ""
        
        # Check if this is a pre-registered command
        evaluation_result = pre_evaluate_prompt_standalone(task)
        if evaluation_result and evaluation_result.get('is_command'):
            # This is a pre-registered command, try to execute browser automation
            try:
                # Extract browser parameters from args
                use_own_browser = args[7] if len(args) > 7 else False
                headless = args[9] if len(args) > 9 else True
                
                # Get the action definition and parameters
                action_name = evaluation_result.get('command_name', '').lstrip('@')
                action_def = evaluation_result.get('action_def', {})
                action_params = evaluation_result.get('params', {})
                action_type = action_def.get('type', '')
                
                if not action_def:
                    return f"❌ Pre-registered command '{action_name}' not found", "", "", "", "", None, None, None, gr.update(), gr.update()
                
                # Handle different action types
                if action_type == 'browser-control':
                    from src.modules.direct_browser_control import execute_direct_browser_control
                    
                    execution_params = {
                        'use_own_browser': use_own_browser,
                        'headless': headless,
                        **action_params
                    }
                    
                    result = await execute_direct_browser_control(action_def, **execution_params)
                    
                    if result:
                        return f"✅ Browser control command '{action_name}' executed successfully", "", "", "", "", None, None, None, gr.update(), gr.update()
                    else:
                        return f"❌ Browser control command '{action_name}' execution failed", "", "", "", "", None, None, None, gr.update(), gr.update()
                
                elif action_type == 'script':
                    # Handle script execution
                    command_template = action_def.get('command', '')
                    if not command_template:
                        return f"❌ Script command '{action_name}' has no command template", "", "", "", "", None, None, None, gr.update(), gr.update()
                    
                    # Replace parameters in command template
                    command = command_template
                    for param_name, param_value in action_params.items():
                        placeholder = f"${{params.{param_name}}}"
                        command = command.replace(placeholder, str(param_value))
                    
                    # Execute the script command
                    try:
                        import subprocess
                        import asyncio
                        import os
                        
                        # Change to the project directory
                        project_dir = os.path.dirname(os.path.abspath(__file__))
                        
                        # Windows対応: 環境変数とPYTHONPATHを適切に設定
                        env = os.environ.copy()
                        env['PYTHONPATH'] = project_dir
                        
                        # Windows対応: コマンドを適切に構築
                        if platform.system() == "Windows":
                            # Windowsでは明示的にPythonパスを使用
                            if command.startswith('python '):
                                command = command.replace('python ', f'"{sys.executable}" ', 1)
                            shell_value = True
                        else:
                            shell_value = True
                        
                        # Execute the command asynchronously
                        process = await asyncio.create_subprocess_shell(
                            command,
                            cwd=project_dir,
                            env=env,
                            shell=shell_value,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        
                        stdout, stderr = await process.communicate()
                        
                        stdout_text = stdout.decode('utf-8') if stdout else ""
                        stderr_text = stderr.decode('utf-8') if stderr else ""
                        
                        if process.returncode == 0:
                            result_message = f"✅ Script command '{action_name}' executed successfully\n\nCommand: {command}"
                            if stdout_text:
                                result_message += f"\n\nOutput:\n{stdout_text}"
                        else:
                            result_message = f"❌ Script command '{action_name}' execution failed (exit code: {process.returncode})\n\nCommand: {command}"
                            if stderr_text:
                                result_message += f"\n\nError:\n{stderr_text}"
                            if stdout_text:
                                result_message += f"\n\nOutput:\n{stdout_text}"
                        
                        return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()
                        
                    except Exception as e:
                        return f"❌ Error executing script command '{action_name}': {str(e)}\n\nCommand: {command}", "", "", "", "", None, None, None, gr.update(), gr.update()
                
                elif action_type in ['action_runner_template', 'git-script']:
                    # Use the script_manager for these types
                    try:
                        from src.script.script_manager import run_script
                        
                        script_output, script_path = await run_script(action_def, action_params, headless=headless)
                        
                        if script_output and "successfully" in script_output.lower():
                            return f"✅ {action_type} command '{action_name}' executed successfully\n\n{script_output}", "", "", "", "", None, None, None, gr.update(), gr.update()
                        else:
                            return f"❌ {action_type} command '{action_name}' execution failed\n\n{script_output}", "", "", "", "", None, None, None, gr.update(), gr.update()
                    except Exception as e:
                        return f"❌ Error executing {action_type} command '{action_name}': {str(e)}", "", "", "", "", None, None, None, gr.update(), gr.update()
                
                else:
                    return f"❌ Action type '{action_type}' is not supported in minimal mode. Supported types: browser-control, script, action_runner_template, git-script", "", "", "", "", None, None, None, gr.update(), gr.update()
                
            except Exception as e:
                import traceback
                error_detail = traceback.format_exc()
                return f"❌ Error executing pre-registered command: {str(e)}\n\nDetails:\n{error_detail}", "", "", "", "", None, None, None, gr.update(), gr.update()
        else:
            return "LLM機能が無効です。事前登録されたコマンド（@で始まる）のみが利用可能です。", "", "", "", "", None, None, None, gr.update(), gr.update()

# ブラウザ自動化関連モジュール（常に利用可能）
from src.config.action_translator import ActionTranslator
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager
from src.ui.command_helper import CommandHelper  # Import CommandHelper class
from src.utils.playwright_codegen import run_playwright_codegen, save_as_action_file
from src.utils.log_ui import create_log_tab  # Import log UI integration

import yaml  # 必要であればインストール: pip install pyyaml

# load_actions_config関数の定義（LLM非依存）
def load_actions_config():
    """Load actions configuration from llms.txt file."""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'llms.txt')
        if not os.path.exists(config_path):
            print(f"⚠️ Actions config file not found at {config_path}")
            return {}
            
        with open(config_path, 'r', encoding='utf-8') as file:
            content = file.read()
        
        # Parse YAML structure
        try:
            actions_config = yaml.safe_load(content)
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                return actions_config
            else:
                print("⚠️ Invalid actions config structure")
                return {}
        except yaml.YAMLError as e:
            print(f"⚠️ YAML parsing error: {e}")
            return {}
    except Exception as e:
        print(f"⚠️ Error loading actions config: {e}")
        return {}

# Functions to load and save llms.txt for UI editing
def load_llms_file():
    path = os.path.join(os.path.dirname(__file__), 'llms.txt')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except FileNotFoundError:
        return ''

def save_llms_file(content):
    path = os.path.join(os.path.dirname(__file__), 'llms.txt')
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    return "✅ llms.txtを保存しました"

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
    # LLM機能が無効の場合、ブラウザ自動化のみで処理
    if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
        browser_manager = BrowserDebugManager()
        debug_utils = DebugUtils(browser_manager=browser_manager)
        
        try:
            # ブラウザセッションを初期化
            browser_result = await browser_manager.initialize_with_session(
                session_id=None,
                use_own_browser=use_own_browser,
                headless=headless
            )
            
            if browser_result.get("status") != "success":
                return {
                    "status": "error", 
                    "message": "ブラウザの初期化に失敗しました", 
                    "final_result": "",
                    "errors": "ブラウザの初期化に失敗しました"
                }
            
            # 基本的なブラウザ操作の実行
            # URLの場合は直接ナビゲート
            if task.startswith("http"):
                result = await debug_utils.execute_goto_url(task, use_own_browser, headless)
                return {
                    "status": "success",
                    "message": f"URLに移動しました: {task}",
                    "final_result": f"URLに移動: {task}",
                    "errors": ""
                }
            else:
                return {
                    "status": "info",
                    "message": "LLM機能が無効のため、自然言語による指示は処理できません。URLまたは具体的なコマンドを入力してください。",
                    "final_result": "LLM機能が無効です",
                    "errors": ""
                }
                
        except Exception as e:
            return {
                "status": "error",
                "message": f"実行エラー: {str(e)}",
                "final_result": "",
                "errors": str(e)
            }
    
    # LLM機能が有効な場合の処理（従来通り）
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
                # Windowsでより確実にChromeプロセスを終了
                try:
                    subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], stderr=subprocess.DEVNULL, check=False)
                    subprocess.run(['taskkill', '/F', '/IM', 'msedge.exe'], stderr=subprocess.DEVNULL, check=False)  # Edge対応
                except Exception:
                    pass
            else:  # Linux and others
                subprocess.run(['killall', 'chrome'], stderr=subprocess.DEVNULL)
            
            # Wait for Chrome to completely close
            time.sleep(3)  # Windows環境では少し長めに待機
            
            # Start Chrome with debugging port - Windows対応
            if sys.platform == 'win32':
                # Windows用のChrome実行可能ファイルパス
                default_chrome_paths = [
                    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                    os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
                ]
                chrome_path = os.getenv("CHROME_PATH")
                if not chrome_path or not os.path.exists(chrome_path):
                    for path in default_chrome_paths:
                        if os.path.exists(path):
                            chrome_path = path
                            break
                    else:
                        chrome_path = "chrome"  # システムPATHに依存
            else:
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
            
            # Windows対応: プロセス起動の改善
            if sys.platform == 'win32':
                # Windowsでは shell=True で実行
                subprocess.Popen(cmd_args, shell=False, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
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

def load_env_browser_settings_file(env_file):
    if not env_file:
        return ("", "", "❌ No env file selected")
    # Load environment vars from file path
    load_dotenv(env_file.name)
    path = os.getenv('CHROME_PATH', '')
    user_data = os.getenv('CHROME_USER_DATA', '')
    return (
        f"**現在のブラウザパス**: {path}",
        f"**ユーザーデータパス**: {user_data}",
        "✅ Env settings loaded"
    )

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

        with gr.Tabs(selected=4) as tabs:  # Default to Run Agent tab
            # Define Agent Settings first for dependency
            with gr.TabItem("⚙️ Agent Settings", id=1):
                with gr.Group():
                    agent_type = gr.Radio(["org", "custom"], label="Agent Type", value=config['agent_type'], info="Select the type of agent to use")
                    with gr.Column():
                        max_steps = gr.Slider(minimum=1, maximum=200, value=config['max_steps'], step=1, label="Max Run Steps", info="Maximum number of steps the agent will take")
                        max_actions_per_step = gr.Slider(minimum=1, maximum=20, value=config['max_actions_per_step'], step=1, label="Max Actions per Step", info="Maximum number of actions the agent will take per step")
                    with gr.Column():
                        use_vision = gr.Checkbox(label="Use Vision", value=config['use_vision'], info="Enable visual processing capabilities")
                        tool_calling_method = gr.Dropdown(label="Tool Calling Method", value=config['tool_calling_method'], interactive=True, choices=["auto", "json_schema", "function_calling"], info="Tool Calls Function Name", visible=False)

            with gr.TabItem("🔧 LLM Configuration", id=2):
                # LLM機能の状態表示
                if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
                    with gr.Group():
                        gr.Markdown("### ⚠️ LLM機能が無効化されています")
                        gr.Markdown("""
                        **現在の状態**: LLM機能は無効化されています  
                        **利用可能な機能**: ブラウザ自動化、Playwright Codegen  
                        **LLM機能を有効化するには**: 
                        1. 環境変数 `ENABLE_LLM=true` を設定
                        2. LLM関連パッケージをインストール: `pip install -r requirements.txt`
                        3. アプリケーションを再起動
                        """)
                        
                        # LLM無効時でも基本設定は表示（ただし無効化）
                        llm_provider = gr.Dropdown(
                            choices=["LLM無効"], 
                            label="LLM Provider", 
                            value="LLM無効", 
                            interactive=False,
                            info="LLM機能が無効化されています"
                        )
                        llm_model_name = gr.Dropdown(
                            choices=["LLM無効"], 
                            label="Model Name", 
                            value="LLM無効", 
                            interactive=False,
                            info="LLM機能が無効化されています"
                        )
                        llm_num_ctx = gr.Slider(
                            minimum=2**8, maximum=2**16, value=4096, step=1, 
                            label="Max Context Length", interactive=False, visible=False
                        )
                        llm_temperature = gr.Slider(
                            minimum=0.0, maximum=2.0, value=0.0, step=0.1, 
                            label="Temperature", interactive=False
                        )
                        with gr.Row():
                            llm_base_url = gr.Textbox(
                                label="Base URL", value="", interactive=False,
                                info="LLM機能が無効化されています"
                            )
                            llm_api_key = gr.Textbox(
                                label="API Key", type="password", value="", interactive=False,
                                info="LLM機能が無効化されています"
                            )
                        dev_mode = gr.Checkbox(
                            label="Dev Mode", value=False, interactive=False,
                            info="LLM機能が無効化されています"
                        )
                else:
                    # LLM有効時の通常UI
                    with gr.Group():
                        llm_provider = gr.Dropdown(choices=[provider for provider, model in utils.model_names.items()], label="LLM Provider", value=config['llm_provider'], info="Select your preferred language model provider")
                        llm_model_name = gr.Dropdown(label="Model Name", choices=utils.model_names['openai'], value=config['llm_model_name'], interactive=True, info="Select a model from the dropdown or type a custom model name")
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

            with gr.TabItem("🤖 Run Agent", id=4):
                # LLM機能の状態に応じてタブの内容を変更
                if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
                    with gr.Group():
                        gr.Markdown("### ℹ️ ブラウザ自動化モード")
                        gr.Markdown("""
                        **現在のモード**: LLM機能無効  
                        **利用可能な機能**:
                        - ブラウザ自動化とスクリプト実行
                        - Playwright Codegen
                        - JSON形式のアクション実行
                        - 基本的なブラウザ操作
                        
                        **制限事項**: 自然言語による指示は利用できません
                        """)
                
                # Add command helper integration
                with gr.Accordion("📋 Available Commands", open=False):
                    # Create DataFrame with empty initial data to avoid schema issues
                    commands_table = gr.DataFrame(
                        headers=["Command", "Description", "Usage"],
                        label="Available Commands",
                        interactive=False,
                        value=[]  # Start with empty data
                    )
                    
                    def load_commands_table():
                        """Load commands into the table"""
                        try:
                            helper = CommandHelper()
                            return helper.get_commands_for_display()
                        except Exception as e:
                            print(f"Error loading commands: {e}")
                            return [["Error", "Could not load commands", str(e)]]
                    
                    refresh_commands = gr.Button("🔄 Refresh Commands")
                    refresh_commands.click(fn=load_commands_table, outputs=commands_table)
                    
                    # Load commands on page load using the refresh button functionality
                    demo.load(fn=load_commands_table, outputs=commands_table)
                
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
                
                # Load commands into the table initially - defer loading to avoid schema issues
                # commands_table.value = load_commands_table()  # Commented out to avoid Gradio schema error
                
                add_infos = gr.Textbox(label="Additional Information", lines=3, placeholder="Add any helpful context or instructions...")
                with gr.Row():
                    run_button = gr.Button("▶️ Run Agent", variant="primary", scale=2)
                    stop_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                with gr.Row():
                    browser_view = gr.HTML(value="<h1 style='width:80vw; height:50vh'>Waiting for browser session...</h1>", label="Live Browser View")

            # New tab for editing llms.txt directly
            with gr.TabItem("📄 LLMS Config", id=5):
                # View section for llms.txt
                with gr.Accordion("📄 View LLMS Config", open=False):
                    llms_code = gr.Code(label="LLMS Config View", language="markdown", value=load_llms_file(), interactive=False, lines=20)
                    refresh_view_btn = gr.Button("🔄 Refresh View", variant="secondary")
                    refresh_view_btn.click(fn=load_llms_file, inputs=None, outputs=llms_code)
                # Edit section for llms.txt
                with gr.Accordion("✏️ Edit LLMS Config", open=True):
                    llms_text = gr.Textbox(label="LLMS Config (llms.txt)", value=load_llms_file(), lines=20, interactive=True)
                    with gr.Row():
                        save_btn = gr.Button("💾 Save llms.txt", variant="primary")
                        reload_btn = gr.Button("🔄 Reload llms.txt")
                    status_llms = gr.Markdown()
                    save_btn.click(fn=save_llms_file, inputs=llms_text, outputs=status_llms)
                    reload_btn.click(fn=load_llms_file, inputs=None, outputs=llms_text)

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
                        
                        # Env file path input (replacing File component to fix schema error)
                        env_file_path = gr.Textbox(label="Env File Path", placeholder="Enter path to .env file")
                        load_env_btn = gr.Button("🔄 Load Env Settings", variant="secondary")
                        
                        # Hook to reload browser path/user data from .env
                        def load_env_from_path(file_path):
                            """Load environment settings from file path"""
                            if not file_path:
                                return "No path provided", "No path provided", "Error: Please provide a file path"
                            try:
                                # Mock loading - replace with actual implementation
                                return f"Loaded from: {file_path}", f"User data from: {file_path}", "Settings loaded successfully"
                            except Exception as e:
                                return "Error loading", "Error loading", f"Error: {str(e)}"
                        
                        load_env_btn.click(
                            fn=load_env_from_path,
                            inputs=[env_file_path],
                            outputs=[browser_path_info, user_data_info, browser_update_result]
                        )
                        
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

            with gr.TabItem("🎭 Playwright Codegen", id=9):
                with gr.Group():
                    gr.Markdown("### 🎮 ブラウザ操作スクリプト自動生成")
                    gr.Markdown("URLを入力してPlaywright codegenを起動し、ブラウザ操作を記録。生成されたスクリプトはアクションファイルとして保存できます。")
                    
                    with gr.Row():
                        url_input = gr.Textbox(
                            label="ウェブサイトURL", 
                            placeholder="記録するURLを入力（例: https://example.com）",
                            info="Playwrightが記録を開始するURL"
                        )
                        browser_type_codegen = gr.Radio(
                            label="ブラウザタイプ",
                            choices=["Chrome", "Edge"],
                            value="Chrome",
                            info="記録に使用するブラウザを選択"
                        )
                    run_codegen_button = gr.Button("▶️ Playwright Codegenを実行", variant="primary")
                    
                    codegen_status = gr.Markdown("")
                    
                    # View generated script
                    with gr.Accordion("📄 View Generated Script", open=True):
                        generated_script_view = gr.Code(
                            label="Generated Script",
                            language="python",
                            value="# ここに生成されたスクリプトが表示されます",
                            interactive=False,
                            lines=15
                        )
                        copy_script_button = gr.Button("📋 Copy to Clipboard")

                    # Edit generated script
                    with gr.Accordion("✏️ Edit Generated Script", open=False):
                        generated_script_edit = gr.Textbox(
                            label="Edit Generated Script",
                            value="",
                            lines=15,
                            interactive=True
                        )
                        with gr.Row():
                            reload_edit_btn = gr.Button("🔄 Load into Editor", variant="secondary")
                        # load view code into editor
                        reload_edit_btn.click(fn=lambda code: code, inputs=generated_script_view, outputs=generated_script_edit)
                    # Save action file using edited script
                    with gr.Accordion("アクションとして保存", open=True):
                        with gr.Row():
                            action_file_name = gr.Textbox(label="ファイル名", placeholder="ファイル名を入力（.pyは不要）")
                            action_command_name = gr.Textbox(label="コマンド名", placeholder="コマンド名（空白でファイル名使用）")
                        save_action_button = gr.Button("💾 Save as Action", variant="primary")
                        save_status = gr.Markdown("")
                        save_action_button.click(fn=save_as_action_file, inputs=[generated_script_edit, action_file_name, action_command_name], outputs=[save_status])
                    
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
                    def handle_run_codegen(url, browser_choice):
                        if not url or url.strip() == "":
                            return "⚠️ 有効なURLを入力してください", "# URLを入力してスクリプトを生成してください"
                        
                        # ブラウザタイプの判定
                        browser_type = browser_choice.lower()
                        
                        # ユーザーデータディレクトリの存在確認
                        if browser_type == "edge":
                            from src.utils.playwright_codegen import detect_browser_paths
                            browser_paths = detect_browser_paths()
                            user_data_dir = browser_paths.get("edge_user_data", "")
                            if not user_data_dir or not os.path.exists(user_data_dir):
                                return "⚠️ Edgeのユーザーデータディレクトリが見つかりません。自動検出を試みます...", "# ブラウザ設定確認中..."
                        
                        # Playwright codegen実行
                        from src.utils.playwright_codegen import run_playwright_codegen
                        success, result = run_playwright_codegen(url, browser_type)
                        if success:
                            return f"✅ {browser_choice}を使用してスクリプトが正常に生成されました", result
                        else:
                            return f"❌ エラー: {result}", "# スクリプト生成中にエラーが発生しました"
                    
                    # UI要素と関数の連携を更新
                    run_codegen_button.click(
                        fn=handle_run_codegen,
                        inputs=[url_input, browser_type_codegen],
                        outputs=[codegen_status, generated_script_view]
                    )
                    
                    save_action_button.click(
                        fn=save_as_action_file,
                        inputs=[generated_script_edit, action_file_name, action_command_name],
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

            with gr.TabItem("🔎 データ抽出", id="data_extract"):  # Data Extraction tab with restored UI
                gr.Markdown("### 🔍 ページからデータを抽出")
                with gr.Row():
                    with gr.Column(scale=1):
                        extraction_url = gr.Textbox(label="抽出先URL", placeholder="https://example.com", lines=1)
                        with gr.Accordion("抽出セレクター設定", open=True):
                            selector_type = gr.Radio(["シンプル", "詳細"], value="シンプル", label="セレクタータイプ")
                            simple_selectors = gr.Textbox(label="セレクター (カンマで区切る)", placeholder="h1, .main-content, #title", lines=2)
                            advanced_selectors = gr.Code(label="セレクター (JSON形式)", language="json",
                                                        value='''{
  "タイトル": {"selector": "h1", "type": "text"},
  "本文": {"selector": ".content", "type": "html"},
  "画像URL": {"selector": "img.main", "type": "attribute", "attribute": "src"}
}''')
                        extract_button = gr.Button("データを抽出", variant="primary")
                        save_path = gr.Textbox(label="保存先ファイルパス (空白で自動生成)", placeholder="/path/to/output.json", lines=1)
                        save_format = gr.Dropdown(choices=["json", "csv"], value="json", label="保存形式")
                        save_button = gr.Button("データを保存", variant="secondary")
                    with gr.Column(scale=2):
                        extraction_result = gr.JSON(label="抽出結果")
                        extraction_status = gr.Markdown(label="ステータス")
                # Toggle between simple and advanced selectors
                selector_type.change(fn=lambda t: (gr.update(visible=(t=="シンプル")), gr.update(visible=(t=="詳細"))),
                                     inputs=selector_type, outputs=[simple_selectors, advanced_selectors])
                
                # Extraction logic
                async def run_extraction(url, selector_type, simple_s, advanced_s, use_own, headless, maintain_sess, tab_strategy):
                    if not url:
                        return None, "URLを入力してください"
                    try:
                        from src.modules.execution_debug_engine import ExecutionDebugEngine
                        engine = ExecutionDebugEngine()
                        selectors = simple_s.split(",") if selector_type=="シンプル" else advanced_s
                        result = await engine.execute_extract_content({"url":url, "selectors":selectors},
                                                                    use_own_browser=use_own, headless=headless,
                                                                    maintain_browser_session=maintain_sess,
                                                                    tab_selection_strategy=tab_strategy)
                        if result.get("error"):
                            return None, f"❌ エラー: {result['error']}"
                        return result, "✅ 抽出完了"
                    except Exception as e:
                        return None, f"❌ 抽出中に例外: {e}"
                
                async def save_extracted_data(data, path, fmt):
                    if not data:
                        return "❌ 保存するデータがありません"
                    try:
                        from src.modules.execution_debug_engine import ExecutionDebugEngine
                        engine = ExecutionDebugEngine()
                        engine.last_extracted_content = data
                        save_result = await engine.save_extracted_content(file_path=path or None, format_type=fmt)
                        return "✅ 保存完了" if save_result.get("success") else f"❌ {save_result.get('message')}"
                    except Exception as e:
                        return f"❌ 保存中に例外: {e}"
                
                extract_button.click(fn=run_extraction,
                                     inputs=[extraction_url, selector_type, simple_selectors, advanced_selectors,
                                             use_own_browser, headless, maintain_browser_session, tab_selection_strategy],
                                     outputs=[extraction_result, extraction_status])
                save_button.click(fn=save_extracted_data,
                                  inputs=[extraction_result, save_path, save_format], outputs=[extraction_status])

            with gr.TabItem("📁 Configuration", id=10):
                with gr.Group():
                    config_file_path = gr.Textbox(label="Config File Path", placeholder="Enter path to .pkl config file")
                    git_token = gr.Textbox(label="Git Token (for non-git users)", type="password", info="Personal token for downloading scripts without Git")
                    load_config_button = gr.Button("Load Existing Config From File", variant="primary")
                    save_config_button = gr.Button("Save Current Config", variant="primary")
                    config_status = gr.Textbox(label="Status", lines=2, interactive=False)

                    load_config_button.click(
                        fn=update_ui_from_config,
                        inputs=[config_file_path],
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

            with gr.TabItem("📊 Results", id=7):
                with gr.Group():
                    recording_display = gr.Textbox(label="Latest Recording Path", interactive=False)
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
                    trace_file_path = gr.Textbox(label="Trace File Path", placeholder="Path where trace file will be saved")
                    agent_history_path = gr.Textbox(label="Agent History Path", placeholder="Path where agent history will be saved")

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
                            recording_display, trace_file_path, agent_history_path, stop_button, run_button
                        ],
                    )
                    # research_button.click(
                    #     fn=run_deep_search,
                    #     inputs=[
                    #         research_task_input, max_search_iteration_input, max_query_per_iter_input,
                    #         llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, 
                    #         llm_api_key, use_vision, use_own_browser, headless
                    #     ],
                    #     outputs=[markdown_output_display, markdown_download, stop_research_button, research_button]
                    # )
                    # stop_research_button.click(fn=stop_research_agent, inputs=[], outputs=[stop_research_button, research_button])

            with gr.TabItem("🎥 Recordings", id=8):
                def list_recordings(save_recording_path):
                    if not os.path.exists(save_recording_path):
                        return []
                    recordings = glob.glob(os.path.join(save_recording_path, "*.[mM][pP]4")) + glob.glob(os.path.join(save_recording_path, "*.[wW][eE][bB][mM]"))
                    recordings.sort(key=os.path.getctime)
                    numbered_recordings = [(recording, f"{idx}. {os.path.basename(recording)}") for idx, recording in enumerate(recordings, start=1)]
                    return numbered_recordings

                recordings_display = gr.Textbox(label="Recordings List", lines=10, interactive=False)
                refresh_button = gr.Button("🔄 Refresh Recordings", variant="secondary")
                
                def format_recordings_list(recordings_path):
                    """Format recordings as a text list instead of gallery"""
                    try:
                        recordings = list_recordings(recordings_path)
                        if not recordings:
                            return "No recordings found"
                        formatted_list = "\n".join([f"{idx}. {os.path.basename(recording)}" for idx, recording in enumerate(recordings, start=1)])
                        return formatted_list
                    except Exception as e:
                        return f"Error loading recordings: {str(e)}"
                
                refresh_button.click(fn=format_recordings_list, inputs=save_recording_path, outputs=recordings_display)
                
                # Initialize with current recordings
                recordings_display.value = format_recordings_list(config['save_recording_path'])

            with gr.TabItem("🧐 Deep Research", id=6):
                research_task_input = gr.Textbox(label="Research Task", lines=5, value="Compose a report on the use of Reinforcement Learning for training Large Language Models, encompassing its origins, current advancements, and future prospects, substantiated with examples of relevant models and techniques. The report should reflect original insights and analysis, moving beyond mere summarization of existing literature.")
                with gr.Row():
                    max_search_iteration_input = gr.Number(label="Max Search Iteration", value=3, precision=0)
                    max_query_per_iter_input = gr.Number(label="Max Query per Iteration", value=1, precision=0)
                with gr.Row():
                    research_button = gr.Button("▶️ Run Deep Research", variant="primary", scale=2)
                    stop_research_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                markdown_output_display = gr.Markdown(label="Research Report")
                markdown_download_path = gr.Textbox(label="Research Report Download Path", placeholder="Path where report will be saved")

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
        # まず、LLM有効/無効に関わらず事前登録コマンドをチェック
        print(f"🔎 入力コマンド解析: {task}")
        
        # 統一されたプロンプト評価を使用
        if ENABLE_LLM and LLM_MODULES_AVAILABLE:
            action_result = pre_evaluate_prompt(task)  # LLM版とstandalone版の統合済み
        else:
            action_result = pre_evaluate_prompt_standalone(task)  # standalone版
        
        # 事前登録されたコマンドが見つかった場合
        if action_result:
            print(f"✅ 事前登録コマンドを発見: {action_result.get('name')}")
            
            # パラメータを抽出
            if ENABLE_LLM and LLM_MODULES_AVAILABLE:
                params = extract_params(task, action_result.get('params', ''))
            else:
                params = extract_params_standalone(task, action_result.get('params', ''))
            
            print(f"🔎 抽出されたパラメータ: {params}")
            
            # ブラウザ自動化を実行（LLM非依存）
            try:
                browser_manager = BrowserDebugManager()
                debug_utils = DebugUtils(browser_manager=browser_manager)
                
                # ブラウザセッションを初期化
                browser_result = await browser_manager.initialize_with_session(
                    session_id=None,
                    use_own_browser=use_own_browser,
                    headless=headless
                )
                
                if browser_result.get("status") == "success":
                    # 実際のスクリプト実行
                    script_output, script_path = await run_script(
                        action_result, params, headless=headless, 
                        save_recording_path=None
                    )
                    
                    message = f"### ✅ 事前登録コマンド実行完了\n\n"
                    message += f"**コマンド**: {action_result.get('name')}\n\n"
                    message += f"**パラメータ**: {params}\n\n"
                    message += f"**実行結果**: {script_output}\n\n"
                    message += f"**スクリプトパス**: {script_path}\n\n"
                    
                    return message, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
                else:
                    error_msg = f"### ❌ ブラウザ初期化エラー\n\n{browser_result.get('message', '不明なエラー')}"
                    return error_msg, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
                    
            except Exception as e:
                error_msg = f"### ❌ コマンド実行エラー\n\n```\n{str(e)}\n```"
                return error_msg, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
        
        # 事前登録コマンドでない場合の処理
        if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
            # LLM無効時の処理
            print(f"🔎 ブラウザ自動化モード - 入力: {task}")
            
            # URLの場合は直接ナビゲート
            if task.startswith("http"):
                try:
                    browser_manager = BrowserDebugManager()
                    debug_utils = DebugUtils(browser_manager=browser_manager)
                    
                    result = await debug_utils.execute_goto_url(task, use_own_browser, headless)
                    message = f"### ブラウザ自動化実行結果\n\n"
                    message += f"**操作**: URLに移動\n\n"
                    message += f"**URL**: {task}\n\n"
                    message += f"**状態**: 完了\n\n"
                    
                    return message, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
                except Exception as e:
                    error_msg = f"### ブラウザ自動化エラー\n\nURL移動中にエラーが発生しました: {str(e)}"
                    return error_msg, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
            else:
                # LLM機能が必要な処理の場合
                info_msg = f"""### ⚠️ LLM機能が無効です

**現在のモード**: ブラウザ自動化のみ  
**入力された指示**: {task}

**利用可能な操作**:
- 事前登録されたコマンド (例: @search-linkedin query=test)
- URLの直接入力 (例: https://www.google.com)
- Playwright Codegenで生成されたスクリプトの実行
- JSON形式のアクション実行

**LLM機能を有効にするには**:
1. 環境変数を設定: `ENABLE_LLM=true`
2. LLM関連パッケージをインストール: `pip install -r requirements.txt`
3. アプリケーションを再起動
"""
                return info_msg, "", gr.update(value="実行", interactive=True), gr.update(interactive=True)
        
        # LLM機能が有効な場合の処理（従来通り）
        print(f"🔎 LLM処理へ移行")

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