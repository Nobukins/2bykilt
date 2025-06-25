import os
import logging
import traceback
import glob
from typing import Tuple, Optional, Dict, Any

import gradio as gr

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

# 条件付きインポート
if ENABLE_LLM:
    try:
        from browser_use.agent.service import Agent
        from browser_use.agent.views import AgentHistoryList
        from browser_use.browser.browser import Browser, BrowserConfig
        from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize
        
        from src.browser.custom_browser import CustomBrowser
        from src.browser.custom_context import BrowserContextConfig as CustomBrowserContextConfig
        from src.controller.custom_controller import CustomController
        from src.agent.custom_agent import CustomAgent
        from src.agent.custom_prompts import CustomSystemPrompt, CustomAgentMessagePrompt
        
        from src.config.llms_parser import pre_evaluate_prompt, extract_params, resolve_sensitive_env_variables
        
        LLM_AGENT_AVAILABLE = True
        print("✅ LLM agent modules loaded successfully")
    except ImportError as e:
        print(f"⚠️ Warning: LLM agent imports failed: {e}")
        LLM_AGENT_AVAILABLE = False
else:
    LLM_AGENT_AVAILABLE = False
    print("ℹ️ LLM functionality is disabled (ENABLE_LLM=false)")

# 常に利用可能なモジュール
from src.utils.utils import get_latest_files
from src.script.script_manager import run_script
from src.browser.browser_manager import prepare_recording_path
from src.utils import utils
from src.utils.globals_manager import get_globals, _global_browser, _global_browser_context, _global_agent, _global_agent_state

# LLM非依存のプロンプト評価機能をインポート
from src.config.standalone_prompt_evaluator import (
    pre_evaluate_prompt_standalone, 
    extract_params_standalone, 
    resolve_sensitive_env_variables_standalone
)

# Configure logging
logger = logging.getLogger(__name__)

def evaluate_prompt_unified(prompt: str) -> Optional[Dict[str, Any]]:
    """
    統一されたプロンプト評価機能
    LLM有効/無効に関わらず、事前登録されたコマンドの評価を行う
    """
    # まず、LLM非依存の評価を実行（常に実行）
    standalone_result = pre_evaluate_prompt_standalone(prompt)
    if standalone_result:
        print(f"✅ Command found via standalone evaluator: {standalone_result.get('name')}")
        return standalone_result
    
    # LLM機能が有効で、standaloneで見つからなかった場合のみLLM評価を実行
    if ENABLE_LLM and LLM_AGENT_AVAILABLE:
        try:
            llm_result = pre_evaluate_prompt(prompt)
            if llm_result:
                print(f"✅ Command found via LLM evaluator: {llm_result.get('name')}")
                return llm_result
        except Exception as e:
            print(f"⚠️ LLM evaluation failed: {e}")
    
    return None

def extract_params_unified(prompt: str, param_names) -> Dict[str, str]:
    """
    統一されたパラメータ抽出機能
    """
    # まず、LLM非依存の抽出を実行
    standalone_params = extract_params_standalone(prompt, param_names)
    if standalone_params:
        return standalone_params
    
    # LLM機能が有効な場合のみLLM抽出を実行
    if ENABLE_LLM and LLM_AGENT_AVAILABLE:
        try:
            return extract_params(prompt, param_names)
        except Exception as e:
            print(f"⚠️ LLM parameter extraction failed: {e}")
    
    return {}

def resolve_env_variables_unified(text: str) -> str:
    """
    統一された環境変数解決機能
    """
    # まず、LLM非依存の解決を実行
    result = resolve_sensitive_env_variables_standalone(text)
    
    # LLM機能が有効な場合のみLLM解決を実行
    if ENABLE_LLM and LLM_AGENT_AVAILABLE:
        try:
            return resolve_sensitive_env_variables(result)
        except Exception as e:
            print(f"⚠️ LLM environment variable resolution failed: {e}")
    
    return result

# Global state variables are now imported from globals_manager

async def stop_agent():
    """Stop the currently running agent and update UI elements"""
    global _global_agent_state, _global_browser_context, _global_browser, _global_agent
    try:
        _global_agent.stop()
        message = "Stop requested - the agent will halt at the next safe point"
        logger.info(f"🛑 {message}")
        return (
            message,
            gr.update(value="Stopping...", interactive=False),
            gr.update(interactive=False),
        )
    except Exception as e:
        error_msg = f"Error during stop: {str(e)}"
        logger.error(error_msg)
        return (
            error_msg,
            gr.update(value="Stop", interactive=True),
            gr.update(interactive=True)
        )

async def stop_research_agent():
    """Stop the currently running research agent"""
    global _global_agent_state, _global_browser_context, _global_browser
    try:
        _global_agent_state.request_stop()
        message = "Stop requested - the agent will halt at the next safe point"
        logger.info(f"🛑 {message}")
        return (
            gr.update(value="Stopping...", interactive=False),
            gr.update(interactive=False),
        )
    except Exception as e:
        error_msg = f"Error during stop: {str(e)}"
        logger.error(error_msg)
        return (
            gr.update(value="Stop", interactive=True),
            gr.update(interactive=True)
        )

async def run_org_agent(
        llm, use_own_browser, keep_browser_open, headless, disable_security, window_w, window_h,
        save_recording_path, save_agent_history_path, save_trace_path, task, max_steps, use_vision,
        max_actions_per_step, tool_calling_method, maintain_browser_session=False,
        existing_context=None, existing_page=None
) -> Tuple[str, str, str, str, Optional[str], Optional[str]]:
    """
    Run the original agent from browser-use library
    
    Returns:
        Tuple containing (final_result, errors, model_actions, model_thoughts, trace_file, history_file)
    """
    global _global_browser, _global_browser_context, _global_agent_state, _global_agent
    _global_agent_state.clear_stop()

    try:
        # If maintain_browser_session is True and we have existing context/page, use them
        if maintain_browser_session and existing_context and existing_page:
            context = existing_context
            page = existing_page
            # Store these for future use
            _global_browser_context = context
        else:
            # Initialize browser and create a new page as before
            extra_chromium_args = [f"--window-size={window_w},{window_h}"]
            if use_own_browser:
                chrome_path = os.getenv("CHROME_PATH", None)
                if chrome_path == "":
                    chrome_path = None
                chrome_user_data = os.getenv("CHROME_USER_DATA", None)
                if chrome_user_data:
                    extra_chromium_args += [f"--user-data-dir={chrome_user_data}"]
            else:
                chrome_path = None

            if _global_browser is None:
                _global_browser = Browser(
                    config=BrowserConfig(
                        headless=headless, disable_security=disable_security, chrome_instance_path=chrome_path,
                        extra_chromium_args=extra_chromium_args,
                    )
                )

            if _global_browser_context is None:
                _global_browser_context = await _global_browser.new_context(
                    config=BrowserContextConfig(
                        trace_path=save_trace_path if save_trace_path else None,
                        save_recording_path=save_recording_path if save_recording_path else None,
                        no_viewport=False, browser_window_size=BrowserContextWindowSize(width=window_w, height=window_h),
                    )
                )
                page = await _global_browser_context.new_page()

        if _global_agent is None:
            _global_agent = Agent(
                task=task, llm=llm, use_vision=use_vision, browser=_global_browser,
                browser_context=_global_browser_context, max_actions_per_step=max_actions_per_step,
                tool_calling_method=tool_calling_method
            )
        history = await _global_agent.run(max_steps=max_steps)
        history_file = os.path.join(save_agent_history_path, f"{_global_agent.agent_id}.json")
        _global_agent.save_history(history_file)

        final_result = history.final_result()
        errors = history.errors()
        model_actions = history.model_actions()
        model_thoughts = history.model_thoughts()
        trace_file = get_latest_files(save_trace_path)

        return final_result, errors, model_actions, model_thoughts, trace_file.get('.zip'), history_file
    except Exception as e:
        traceback.print_exc()
        errors = str(e) + "\n" + traceback.format_exc()
        return '', errors, '', '', None, None
    finally:
        if not keep_browser_open and not maintain_browser_session:
            if _global_browser_context:
                await _global_browser_context.close()
                _global_browser_context = None
            if _global_browser:
                await _global_browser.close()
                _global_browser = None

async def run_custom_agent(
        llm, use_own_browser, keep_browser_open, headless, disable_security, window_w, window_h,
        save_recording_path, save_agent_history_path, save_trace_path, task, add_infos, max_steps,
        use_vision, max_actions_per_step, tool_calling_method
) -> Tuple[str, str, str, str, Optional[str], Optional[str]]:
    """
    Run the custom agent with extended capabilities
    
    Returns:
        Tuple containing (final_result, errors, model_actions, model_thoughts, trace_file, history_file)
    """
    global _global_browser, _global_browser_context, _global_agent_state, _global_agent
    _global_agent_state.clear_stop()

    try:
        extra_chromium_args = [f"--window-size={window_w},{window_h}"]
        if use_own_browser:
            chrome_path = os.getenv("CHROME_PATH", None)
            if chrome_path == "":
                chrome_path = None
            chrome_user_data = os.getenv("CHROME_USER_DATA", None)
            if chrome_user_data:
                extra_chromium_args += [f"--user-data-dir={chrome_user_data}"]
        else:
            chrome_path = None

        controller = CustomController()
        if _global_browser is None:
            _global_browser = CustomBrowser(
                config=BrowserConfig(
                    headless=headless, disable_security=disable_security, chrome_instance_path=chrome_path,
                    extra_chromium_args=extra_chromium_args,
                )
            )

        if _global_browser_context is None:
            _global_browser_context = await _global_browser.new_context(
                config=CustomBrowserContextConfig(
                    trace_path=save_trace_path if save_trace_path else None,
                    save_recording_path=save_recording_path if save_recording_path else None,
                    no_viewport=False, browser_window_size=BrowserContextWindowSize(width=window_w, height=window_h),
                )
            )

        if _global_agent is None:
            _global_agent = CustomAgent(
                task=task, add_infos=add_infos, use_vision=use_vision, llm=llm, browser=_global_browser,
                browser_context=_global_browser_context, controller=controller, system_prompt_class=CustomSystemPrompt,
                agent_prompt_class=CustomAgentMessagePrompt, max_actions_per_step=max_actions_per_step,
                tool_calling_method=tool_calling_method
            )
        history = await _global_agent.run(max_steps=max_steps)
        history_file = os.path.join(save_agent_history_path, f"{_global_agent.agent_id}.json")
        _global_agent.save_history(history_file)

        final_result = history.final_result()
        errors = history.errors()
        model_actions = history.model_actions()
        model_thoughts = history.model_thoughts()
        trace_file = get_latest_files(save_trace_path)

        return final_result, errors, model_actions, model_thoughts, trace_file.get('.zip'), history_file
    except Exception as e:
        traceback.print_exc()
        errors = str(e) + "\n" + traceback.format_exc()
        return '', errors, '', '', None, None
    finally:
        _global_agent = None
        if not keep_browser_open:
            if _global_browser_context:
                await _global_browser_context.close()
                _global_browser_context = None
            if _global_browser:
                await _global_browser.close()
                _global_browser = None

async def run_deep_search(research_task, max_search_iteration_input, max_query_per_iter_input, 
                         llm_provider, llm_model_name, llm_num_ctx, llm_temperature, 
                         llm_base_url, llm_api_key, use_vision, use_own_browser, headless):
    """Run deep research with the given parameters"""
    from src.utils.deep_research import deep_research
    from src.utils import utils
    
    global _global_agent_state
    _global_agent_state.clear_stop()
    
    # Create LLM model from parameters
    llm = utils.get_llm_model(
        provider=llm_provider, 
        model_name=llm_model_name, 
        num_ctx=llm_num_ctx,
        temperature=llm_temperature, 
        base_url=llm_base_url, 
        api_key=llm_api_key,
    )
    
    markdown_content, file_path = await deep_research(
        research_task, llm, _global_agent_state,
        max_search_iterations=max_search_iteration_input,
        max_query_num=max_query_per_iter_input,
        use_vision=use_vision, 
        headless=headless,
        use_own_browser=use_own_browser
    )
    
    return markdown_content, file_path, gr.update(value="Stop", interactive=True), gr.update(interactive=True)

async def run_browser_agent(
    agent_type, llm_provider, llm_model_name, llm_num_ctx, llm_temperature, llm_base_url, llm_api_key,
    use_own_browser, keep_browser_open, headless, disable_security, window_w, window_h,
    save_recording_path, save_agent_history_path, save_trace_path, enable_recording, task, add_infos,
    max_steps, use_vision, max_actions_per_step, tool_calling_method, maintain_browser_session=False,
    tab_selection_strategy="active_tab"  # Add parameter with default
):
    """
    Main function to run browser agent based on specified parameters

    Args:
        agent_type: Type of agent to run (org or custom)
        llm_provider: Provider of the LLM model
        llm_model_name: Name of the LLM model
        llm_num_ctx: Number of context tokens for the LLM model
        llm_temperature: Temperature setting for the LLM model
        llm_base_url: Base URL for the LLM model API
        llm_api_key: API key for the LLM model
        use_own_browser: Whether to use own browser instance
        keep_browser_open: Whether to keep the browser open after task completion
        headless: Whether to run the browser in headless mode
        disable_security: Whether to disable browser security settings
        window_w: Width of the browser window
        window_h: Height of the browser window
        save_recording_path: Path to save browser recordings
        save_agent_history_path: Path to save agent history
        save_trace_path: Path to save browser trace files
        enable_recording: Whether to enable browser recording
        task: Task to be executed by the agent
        add_infos: Additional information for the custom agent
        max_steps: Maximum number of steps for the agent
        use_vision: Whether to use vision capabilities
        max_actions_per_step: Maximum number of actions per step
        tool_calling_method: Method for calling tools
        maintain_browser_session: Whether to maintain the browser session between tasks
        tab_selection_strategy: Strategy for tab selection ("active_tab", "new_tab" or "last_tab")
    """
    # Get agent state from globals
    globals_dict = get_globals()
    agent_state = globals_dict["agent_state"]
    agent_state.clear_stop()

    try:
        # 統一されたプロンプト評価を使用（LLM有効/無効に関わらず動作）
        script_info = evaluate_prompt_unified(task)
        if script_info:
            print(f"🎯 Executing registered command: {script_info.get('command_name')}")
            
            # Get the action definition and parameters from the script_info
            action_def = script_info.get('action_def', {})
            params = script_info.get('params', {})
            
            print(f"📋 Action definition: {action_def}")
            print(f"🔧 Parameters: {params}")
            
            script_output, script_path = await run_script(action_def, params, headless=headless, 
                                                         save_recording_path=save_recording_path if enable_recording else None)
            return (
                script_output,
                "",
                f"✅ Executed registered command: {script_info.get('command_name')}",
                f"Script path: {script_path}",
                script_path if enable_recording else None,
                None,
                None,
                gr.update(value="Stop", interactive=True),
                gr.update(interactive=True)
            )

        # LLM機能が無効で、登録済みコマンドでもない場合は制限的な動作
        if not ENABLE_LLM or not LLM_AGENT_AVAILABLE:
            return (
                "⚠️ LLM機能が無効のため、自然言語による指示は処理できません。\n\n" +
                "以下のオプションを使用してください:\n" +
                "1. 事前登録されたコマンド（例: @search-linkedin query=test）\n" +
                "2. 直接URL（例: https://www.google.com）\n" +
                "3. JSON形式のアクション定義",
                "LLM機能が無効です",
                "制限モードで動作中",
                "LLM機能を有効にするには ENABLE_LLM=true を設定してください",
                None,
                None,
                None,
                gr.update(value="Stop", interactive=True),
                gr.update(interactive=True)
            )

        # Prepare recording path
        recording_path = prepare_recording_path(enable_recording, save_recording_path)
        existing_videos = set()
        if recording_path:
            existing_videos = set(glob.glob(os.path.join(recording_path, "*.[mM][pP]4")) + 
                                 glob.glob(os.path.join(recording_path, "*.[wW][eE][bB][mM]")))

        # Resolve sensitive variables and initialize LLM
        task = resolve_env_variables_unified(task)
        llm = utils.get_llm_model(
            provider=llm_provider, model_name=llm_model_name, num_ctx=llm_num_ctx,
            temperature=llm_temperature, base_url=llm_base_url, api_key=llm_api_key,
        )
        
        # Check for existing browser context if maintain_browser_session is True
        existing_context = None
        existing_page = None
        if maintain_browser_session:
            # Try to get existing browser context and page
            if "_global_browser_context" in globals_dict and globals_dict["_global_browser_context"]:
                existing_context = globals_dict["_global_browser_context"]
                # Get the first page if available
                if hasattr(existing_context, 'pages') and existing_context.pages:
                    existing_page = existing_context.pages[0]
        
        # Pass existing_context and existing_page to the agent functions
        if agent_type == "org":
            final_result, errors, model_actions, model_thoughts, trace_file, history_file = await run_org_agent(
                llm=llm, use_own_browser=use_own_browser, keep_browser_open=keep_browser_open, headless=headless,
                disable_security=disable_security, window_w=window_w, window_h=window_h,
                save_recording_path=recording_path, save_agent_history_path=save_agent_history_path,
                save_trace_path=save_trace_path, task=task, max_steps=max_steps, use_vision=use_vision,
                max_actions_per_step=max_actions_per_step, tool_calling_method=tool_calling_method,
                maintain_browser_session=maintain_browser_session,
                existing_context=existing_context,
                existing_page=existing_page
            )
        elif agent_type == "custom":
            final_result, errors, model_actions, model_thoughts, trace_file, history_file = await run_custom_agent(
                llm=llm, use_own_browser=use_own_browser, keep_browser_open=keep_browser_open, headless=headless,
                disable_security=disable_security, window_w=window_w, window_h=window_h,
                save_recording_path=recording_path, save_agent_history_path=save_agent_history_path,
                save_trace_path=save_trace_path, task=task, add_infos=add_infos, max_steps=max_steps,
                use_vision=use_vision, max_actions_per_step=max_actions_per_step, tool_calling_method=tool_calling_method
            )
        else:
            raise ValueError(f"Invalid agent type: {agent_type}")

        # Check for new videos after agent run
        latest_video = None
        if recording_path:
            new_videos = set(glob.glob(os.path.join(recording_path, "*.[mM][pP]4")) + 
                           glob.glob(os.path.join(recording_path, "*.[wW][eE][bB][mM]")))
            if new_videos - existing_videos:
                latest_video = list(new_videos - existing_videos)[0]

        return (
            final_result, errors, model_actions, model_thoughts, latest_video, trace_file, history_file,
            gr.update(value="Stop", interactive=True), gr.update(interactive=True)
        )
    except gr.Error:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        errors = str(e) + "\n" + traceback.format_exc()
        logger.error(errors)
        return (
            '', errors, '', '', None, None, None,
            gr.update(value="Stop", interactive=True), gr.update(interactive=True)
        )
