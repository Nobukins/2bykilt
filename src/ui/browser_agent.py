"""Browser agent execution functions for UI.

This module contains functions for running the browser agent and managing Chrome.
"""
import os
import sys
import time
import subprocess
import gradio as gr


async def run_browser_agent(task, add_infos, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, 
                           llm_base_url, llm_api_key, use_vision, use_own_browser, headless, 
                           maintain_browser_session=False, tab_selection_strategy="new_tab"):
    """Run the browser agent using JSON-based execution.
    
    Args:
        task: Task description or URL
        add_infos: Additional information
        llm_provider: LLM provider name
        llm_model_name: Model name
        llm_num_ctx: Context window size
        llm_temperature: Temperature setting
        llm_base_url: Base URL for LLM API
        llm_api_key: API key
        use_vision: Enable vision capabilities
        use_own_browser: Use existing browser
        headless: Run in headless mode
        maintain_browser_session: Keep browser session alive
        tab_selection_strategy: Tab selection strategy (new_tab/reuse_tab)
    
    Returns:
        dict: Execution result with status, message, and errors
    """
    # Import here to avoid circular dependencies
    from src.browser.browser_debug_manager import BrowserDebugManager
    from src.utils.debug_utils import DebugUtils
    from src.ui.helpers import load_actions_config
    
    # Check if LLM is enabled
    try:
        from src.config.feature_flags import is_llm_enabled
        ENABLE_LLM = is_llm_enabled()
    except Exception:
        ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"
    
    # Check if LLM modules are available
    try:
        from src.modules.llm_factory import LLMFactory
        LLM_MODULES_AVAILABLE = True
    except ImportError:
        LLM_MODULES_AVAILABLE = False
    
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
    from src.config.standalone_prompt_evaluator import pre_evaluate_prompt
    from src.modules.action_translator import ActionTranslator
    
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
