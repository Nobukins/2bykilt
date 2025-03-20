import logging
import argparse
import os
import glob
from dotenv import load_dotenv
load_dotenv()

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

# The run_browser_agent function has been moved to agent_manager.py

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
                            max_steps, use_vision, max_actions_per_step, tool_calling_method, dev_mode
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
    args = parser.parse_args()

    config_dict = default_config()
    demo = create_ui(config_dict, theme_name=args.theme)
    demo.launch(server_name=args.ip, server_port=args.port)

if __name__ == '__main__':
    main()

async def run_custom_agent():
    """Run the custom agent."""
    globals_dict = get_globals()
    use_own_browser = globals_dict["use_own_browser_config"]

    # Use centralized browser initialization
    browser = await initialize_browser(use_own_browser, window_w=1024, window_h=768)
    globals_dict["browser"] = browser
    # ...existing code...