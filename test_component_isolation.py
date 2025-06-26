#!/usr/bin/env python3
"""
Component isolation test - systematically add UI components to find the problematic one
"""
import logging
import argparse
import os
import sys
import json
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from gradio.themes import Ocean

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

from src.utils.default_config_settings import default_config

def create_test_ui_stage1(config, theme_name="Ocean"):
    """Stage 1: Basic tabs and text components"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Stage1", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Stage 1")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("🤖 Run Agent", id=1):
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task", 
                    value=config['task']
                )
                
                run_button = gr.Button("▶️ Run Agent", variant="primary")
                result_output = gr.Textbox(label="Result", lines=3)
                
                def simple_run(task_input):
                    return f"Executed: {task_input}"
                
                run_button.click(fn=simple_run, inputs=task, outputs=result_output)
                
            with gr.TabItem("⚙️ Settings", id=2):
                gr.Markdown("## Settings Tab")
                setting1 = gr.Textbox(label="Setting 1", value="test")
                
            with gr.TabItem("📊 Data", id=3):
                gr.Markdown("## Data Tab")
                data_output = gr.Textbox(label="Data", lines=5)
    
    return demo

def create_test_ui_stage2(config, theme_name="Ocean"):
    """Stage 2: Add simple dropdowns and checkboxes"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Stage2", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Stage 2")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("🤖 Run Agent", id=1):
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task", 
                    value=config['task']
                )
                
                # Add simple dropdown
                llm_model = gr.Dropdown(
                    label="LLM Model",
                    choices=["gpt-4", "gpt-3.5-turbo", "claude-3"],
                    value="gpt-4"
                )
                
                # Add checkbox
                headless_mode = gr.Checkbox(label="Headless Mode", value=True)
                
                run_button = gr.Button("▶️ Run Agent", variant="primary")
                result_output = gr.Textbox(label="Result", lines=3)
                
                def simple_run(task_input, model, headless):
                    return f"Executed: {task_input} with {model}, headless={headless}"
                
                run_button.click(
                    fn=simple_run, 
                    inputs=[task, llm_model, headless_mode], 
                    outputs=result_output
                )
                
            with gr.TabItem("⚙️ Settings", id=2):
                gr.Markdown("## Settings Tab")
                setting1 = gr.Textbox(label="Setting 1", value="test")
                
            with gr.TabItem("📊 Data", id=3):
                gr.Markdown("## Data Tab")
                data_output = gr.Textbox(label="Data", lines=5)
    
    return demo

def create_test_ui_stage3(config, theme_name="Ocean"):
    """Stage 3: Add more complex dropdowns with more options"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Stage3", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Stage 3")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("🤖 Run Agent", id=1):
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task", 
                    value=config['task']
                )
                
                # Add dropdown with more choices
                llm_model = gr.Dropdown(
                    label="LLM Model",
                    choices=["gpt-4", "gpt-3.5-turbo", "claude-3", "gemini-pro", "llama-2"],
                    value="gpt-4"
                )
                
                # Add browser choice dropdown
                browser_choice = gr.Dropdown(
                    label="Browser",
                    choices=["chromium", "firefox", "webkit"],
                    value="chromium"
                )
                
                headless_mode = gr.Checkbox(label="Headless Mode", value=True)
                
                run_button = gr.Button("▶️ Run Agent", variant="primary")
                result_output = gr.Textbox(label="Result", lines=3)
                
                def simple_run(task_input, model, browser, headless):
                    return f"Executed: {task_input} with {model} on {browser}, headless={headless}"
                
                run_button.click(
                    fn=simple_run, 
                    inputs=[task, llm_model, browser_choice, headless_mode], 
                    outputs=result_output
                )
                
            with gr.TabItem("⚙️ Settings", id=2):
                gr.Markdown("## Settings Tab")
                setting1 = gr.Textbox(label="Setting 1", value="test")
                
            with gr.TabItem("📊 Data", id=3):
                gr.Markdown("## Data Tab")
                data_output = gr.Textbox(label="Data", lines=5)
    
    return demo

def create_test_ui_stage4(config, theme_name="Ocean"):
    """Stage 4: Add DataFrame component (likely culprit)"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Stage4", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Stage 4")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("🤖 Run Agent", id=1):
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task", 
                    value=config['task']
                )
                
                llm_model = gr.Dropdown(
                    label="LLM Model",
                    choices=["gpt-4", "gpt-3.5-turbo", "claude-3"],
                    value="gpt-4"
                )
                
                headless_mode = gr.Checkbox(label="Headless Mode", value=True)
                
                run_button = gr.Button("▶️ Run Agent", variant="primary")
                result_output = gr.Textbox(label="Result", lines=3)
                
                def simple_run(task_input, model, headless):
                    return f"Executed: {task_input} with {model}, headless={headless}"
                
                run_button.click(
                    fn=simple_run, 
                    inputs=[task, llm_model, headless_mode], 
                    outputs=result_output
                )
                
            with gr.TabItem("📊 Commands", id=2):
                gr.Markdown("## Commands Tab with DataFrame")
                
                # Add the DataFrame that might be causing the issue
                commands_table = gr.DataFrame(
                    headers=["Command", "Type", "Status"],
                    datatype=["str", "str", "str"],
                    label="Commands Table",
                    interactive=True
                )
                
                # Test data for DataFrame
                test_data = [
                    ["navigate_url", "browser", "completed"],
                    ["extract_content", "data", "pending"],
                    ["form_input", "interaction", "ready"]
                ]
                
                def load_test_data():
                    return test_data
                
                load_button = gr.Button("Load Test Data")
                load_button.click(fn=load_test_data, outputs=commands_table)
                
            with gr.TabItem("⚙️ Settings", id=3):
                gr.Markdown("## Settings Tab")
                setting1 = gr.Textbox(label="Setting 1", value="test")
    
    return demo

def create_test_ui_stage5(config, theme_name="Ocean"):
    """Stage 5: Add File components"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Stage5", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Stage 5")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("🤖 Run Agent", id=1):
                task = gr.Textbox(
                    label="Task Description", 
                    lines=4, 
                    placeholder="Enter your task", 
                    value=config['task']
                )
                
                run_button = gr.Button("▶️ Run Agent", variant="primary")
                result_output = gr.Textbox(label="Result", lines=3)
                
                def simple_run(task_input):
                    return f"Executed: {task_input}"
                
                run_button.click(fn=simple_run, inputs=task, outputs=result_output)
                
            with gr.TabItem("📊 Commands", id=2):
                gr.Markdown("## Commands Tab with DataFrame")
                
                commands_table = gr.DataFrame(
                    headers=["Command", "Type", "Status"],
                    datatype=["str", "str", "str"],
                    label="Commands Table",
                    interactive=True
                )
                
            with gr.TabItem("📁 Files", id=3):
                gr.Markdown("## File Operations")
                
                # Add File components
                env_file_input = gr.File(label="Load .env File", file_types=[".env"], interactive=True)
                config_file_input = gr.File(label="Load Config File", file_types=[".pkl"], interactive=True)
                trace_file = gr.File(label="Trace File")
                agent_history_file = gr.File(label="Agent History")
                markdown_download = gr.File(label="Download Research Report")
                
                def handle_file_upload(file):
                    if file:
                        return f"File uploaded: {file.name}"
                    return "No file uploaded"
                
                env_file_input.change(fn=handle_file_upload, inputs=env_file_input, outputs=result_output)
                
            with gr.TabItem("⚙️ Settings", id=4):
                gr.Markdown("## Settings Tab")
                setting1 = gr.Textbox(label="Setting 1", value="test")
    
    return demo

def main():
    parser = argparse.ArgumentParser(description="Component Isolation Test for 2Bykilt")
    parser.add_argument("--stage", type=int, default=1, choices=[1,2,3,4,5], help="Test stage to run")
    parser.add_argument("--port", type=int, default=7860, help="Port number")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    
    config = default_config()
    
    # Create UI based on stage
    if args.stage == 1:
        demo = create_test_ui_stage1(config)
        print("Testing Stage 1: Basic tabs and text components")
    elif args.stage == 2:
        demo = create_test_ui_stage2(config)
        print("Testing Stage 2: Adding simple dropdowns and checkboxes")
    elif args.stage == 3:
        demo = create_test_ui_stage3(config)
        print("Testing Stage 3: More complex dropdowns")
    elif args.stage == 4:
        demo = create_test_ui_stage4(config)
        print("Testing Stage 4: Adding DataFrame component")
    elif args.stage == 5:
        demo = create_test_ui_stage5(config)
        print("Testing Stage 5: Adding File components")
    
    # Run with Gradio directly
    demo.launch(server_name=args.host, server_port=args.port, share=False)

if __name__ == "__main__":
    main()
