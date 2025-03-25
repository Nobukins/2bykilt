import asyncio
import logging
import traceback
from typing import Dict, Any, List, Optional, Union, Callable, Awaitable

import gradio as gr

from src.agent.agent_manager import get_globals, run_browser_agent
from src.utils.utils import capture_screenshot

# Configure logging
logger = logging.getLogger(__name__)

async def run_with_stream(
    agent_type: str,
    llm_provider: str,
    llm_model_name: str,
    llm_num_ctx: int,
    llm_temperature: float,
    llm_base_url: str,
    llm_api_key: str,
    use_own_browser: bool,
    keep_browser_open: bool,
    headless: bool,
    disable_security: bool,
    window_w: int,
    window_h: int,
    save_recording_path: str,
    save_agent_history_path: str,
    save_trace_path: str,
    enable_recording: bool,
    task: str,
    add_infos: str,
    max_steps: int,
    use_vision: bool,
    max_actions_per_step: int,
    tool_calling_method: str,
    dev_mode: bool = False,
    maintain_browser_session: bool = False,  # Added parameter
    tab_selection_strategy: str = "new_tab"  # Add parameter with default
):
    """
    Run browser agent with UI streaming of results
    
    This function handles both headless and non-headless modes, providing
    appropriate streaming of results to the UI.
    """
    globals_dict = get_globals()
    agent_state = globals_dict["agent_state"]
    agent_state.clear_stop()
    
    stream_vw = 80
    stream_vh = int(80 * window_h // window_w)
    
    # Handle non-headless mode (direct execution without streaming)
    if not headless:
        result = await run_browser_agent(
            agent_type=agent_type, llm_provider=llm_provider, llm_model_name=llm_model_name, llm_num_ctx=llm_num_ctx,
            llm_temperature=llm_temperature, llm_base_url=llm_base_url, llm_api_key=llm_api_key,
            use_own_browser=use_own_browser, keep_browser_open=keep_browser_open, headless=headless,
            disable_security=disable_security, window_w=window_w, window_h=window_h,
            save_recording_path=save_recording_path, save_agent_history_path=save_agent_history_path,
            save_trace_path=save_trace_path, enable_recording=enable_recording, task=task, add_infos=add_infos,
            max_steps=max_steps, use_vision=use_vision, max_actions_per_step=max_actions_per_step,
            tool_calling_method=tool_calling_method, maintain_browser_session=maintain_browser_session,  # Pass parameter
            tab_selection_strategy=tab_selection_strategy  # Pass the parameter
        )
        html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Using browser...</h1>"
        yield [html_content] + list(result)
    else:
        # Handle headless mode with periodic UI updates
        try:
            agent_state.clear_stop()
            agent_task = asyncio.create_task(
                run_browser_agent(
                    agent_type=agent_type, llm_provider=llm_provider, llm_model_name=llm_model_name,
                    llm_num_ctx=llm_num_ctx, llm_temperature=llm_temperature, llm_base_url=llm_base_url,
                    llm_api_key=llm_api_key, use_own_browser=use_own_browser, keep_browser_open=keep_browser_open,
                    headless=headless, disable_security=disable_security, window_w=window_w, window_h=window_h,
                    save_recording_path=save_recording_path, save_agent_history_path=save_agent_history_path,
                    save_trace_path=save_trace_path, enable_recording=enable_recording, task=task, add_infos=add_infos,
                    max_steps=max_steps, use_vision=use_vision, max_actions_per_step=max_actions_per_step,
                    tool_calling_method=tool_calling_method, maintain_browser_session=maintain_browser_session,  # Pass parameter
                    tab_selection_strategy=tab_selection_strategy  # Pass the parameter
                )
            )

            # Initialize UI elements
            html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Using browser...</h1>"
            final_result = errors = model_actions = model_thoughts = ""
            latest_videos = trace = history_file = None

            # Periodically update UI while agent is running
            while not agent_task.done():
                try:
                    browser_context = globals_dict["browser_context"]
                    encoded_screenshot = await capture_screenshot(browser_context)
                    if encoded_screenshot is not None:
                        html_content = f'<img src="data:image/jpeg;base64,{encoded_screenshot}" style="width:{stream_vw}vw; height:{stream_vh}vh; border:1px solid #ccc;">'
                    else:
                        html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>"
                except Exception as e:
                    html_content = f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>"

                # Check if stop was requested
                if agent_state and agent_state.is_stop_requested():
                    yield [
                        html_content, final_result, errors, model_actions, model_thoughts, latest_videos, trace, history_file,
                        gr.update(value="Stopping...", interactive=False), gr.update(interactive=False),
                    ]
                    break
                else:
                    yield [
                        html_content, final_result, errors, model_actions, model_thoughts, latest_videos, trace, history_file,
                        gr.update(value="Stop", interactive=True), gr.update(interactive=True)
                    ]
                await asyncio.sleep(0.05)

            # Once the agent task completes, get results
            try:
                result = await agent_task
                final_result, errors, model_actions, model_thoughts, latest_videos, trace, history_file, stop_button, run_button = result
            except gr.Error:
                final_result = ""
                model_actions = ""
                model_thoughts = ""
                latest_videos = trace = history_file = None
                stop_button = gr.update(value="Stop", interactive=True)
                run_button = gr.update(interactive=True)
            except Exception as e:
                errors = f"Agent error: {str(e)}"
                stop_button = gr.update(value="Stop", interactive=True)
                run_button = gr.update(interactive=True)

            yield [
                html_content, final_result, errors, model_actions, model_thoughts, latest_videos, trace, history_file,
                stop_button, run_button
            ]
        except Exception as e:
            yield [
                f"<h1 style='width:{stream_vw}vw; height:{stream_vh}vh'>Waiting for browser session...</h1>",
                "", f"Error: {str(e)}\n{traceback.format_exc()}", "", "", None, None, None,
                gr.update(value="Stop", interactive=True), gr.update(interactive=True)
            ]
