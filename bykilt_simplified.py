#!/usr/bin/env python3
"""
Simplified bykilt.py to isolate the Gradio schema issue
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

def create_simplified_ui(config, theme_name="Ocean"):
    """Create simplified UI to isolate the problem"""
    theme_map = {"Ocean": Ocean()}
    
    with gr.Blocks(title="2Bykilt-Simplified", theme=theme_map[theme_name]) as demo:
        gr.Markdown("# 🪄🌐 2Bykilt - Simplified")
        
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
    
    return demo

from src.api.app import create_fastapi_app, run_app

def main():
    parser = argparse.ArgumentParser(description="Simplified Gradio UI for 2Bykilt")
    parser.add_argument("--ip", type=str, default="127.0.0.1")
    parser.add_argument("--port", type=int, default=7793)
    parser.add_argument("--theme", type=str, default="Ocean")
    args = parser.parse_args()

    config_dict = default_config()
    demo = create_simplified_ui(config_dict, theme_name=args.theme)
    
    app = create_fastapi_app(demo, args)
    run_app(app, args)

if __name__ == '__main__':
    main()
