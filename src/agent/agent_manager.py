import os
import logging
import traceback
import glob
from typing import Tuple, Optional, Dict, Any

import gradio as gr
from browser_use.agent.service import Agent
from browser_use.agent.views import AgentHistoryList
from browser_use.browser.browser import Browser, BrowserConfig
from browser_use.browser.context import BrowserContextConfig, BrowserContextWindowSize

from src.browser.custom_browser import CustomBrowser
from src.browser.custom_context import BrowserContextConfig as CustomBrowserContextConfig
from src.controller.custom_controller import CustomController
from src.agent.custom_agent import CustomAgent
from src.agent.custom_prompts import CustomSystemPrompt, CustomAgentMessagePrompt
from src.utils.utils import get_latest_files
from src.config.llms_parser import pre_evaluate_prompt, extract_params, resolve_sensitive_env_variables
from src.script.script_manager import run_script
from src.browser.browser_manager import prepare_recording_path
from src.utils import utils
from src.utils.globals_manager import get_globals, _global_browser, _global_browser_context, _global_agent, _global_agent_state

# Configure logging
logger = logging.getLogger(__name__)

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
        max_actions_per_step, tool_calling_method
) -> Tuple[str, str, str, str, Optional[str], Optional[str]]:
    """
    Run the original agent from browser-use library
    
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
        _global_agent = None
        if not keep_browser_open:
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
    max_steps, use_vision, max_actions_per_step, tool_calling_method
):
    """
    Main function to run browser agent based on specified parameters
    """
    # Get agent state from globals
    globals_dict = get_globals()
    agent_state = globals_dict["agent_state"]
    agent_state.clear_stop()

    try:
        # Pre-evaluate prompt for script matching
        script_info = pre_evaluate_prompt(task)
        if script_info:
            params = extract_params(task, script_info.get('params', ''))
            script_output, script_path = await run_script(script_info, params, headless=headless, 
                                                         save_recording_path=save_recording_path if enable_recording else None)
            return (
                script_output,
                "",
                f"Executed script: {script_path}",
                "",
                script_path if enable_recording else None,
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
        task = resolve_sensitive_env_variables(task)
        llm = utils.get_llm_model(
            provider=llm_provider, model_name=llm_model_name, num_ctx=llm_num_ctx,
            temperature=llm_temperature, base_url=llm_base_url, api_key=llm_api_key,
        )
        
        # Run appropriate agent type
        if agent_type == "org":
            final_result, errors, model_actions, model_thoughts, trace_file, history_file = await run_org_agent(
                llm=llm, use_own_browser=use_own_browser, keep_browser_open=keep_browser_open, headless=headless,
                disable_security=disable_security, window_w=window_w, window_h=window_h,
                save_recording_path=recording_path, save_agent_history_path=save_agent_history_path,
                save_trace_path=save_trace_path, task=task, max_steps=max_steps, use_vision=use_vision,
                max_actions_per_step=max_actions_per_step, tool_calling_method=tool_calling_method
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
