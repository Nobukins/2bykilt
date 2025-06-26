#!/usr/bin/env python3
"""
Minimal UI test to identify Gradio component configuration issues
"""

import os
from dotenv import load_dotenv
load_dotenv()

import gradio as gr

# LLM機能の有効/無効を制御
ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

def create_minimal_ui():
    """Create a minimal UI to test Gradio component issues"""
    
    # Load default config
    config = {
        'window_width': 1920,
        'window_height': 1080,
        'enable_recording': True,
        'agent_type': 'custom',
        'max_steps': 50,
        'use_vision': False
    }
    
    with gr.Blocks(title="2Bykilt Minimal Test") as demo:
        gr.Markdown("# 🪄🌐 2Bykilt Minimal Test")
        
        with gr.Tabs() as tabs:
            with gr.TabItem("Browser Settings", id=1):
                with gr.Column():
                    gr.Markdown("### Browser Settings")
                    
                    browser_type = gr.Dropdown(
                        choices=["chrome", "edge"], 
                        label="Browser Type", 
                        value="chrome"
                    )
                    
                    use_own_browser = gr.Checkbox(label="Use Own Browser", value=False)
                    headless = gr.Checkbox(label="Headless Mode", value=False)
                    
                    with gr.Row():
                        window_w = gr.Number(
                            value=config.get('window_width', 1920),
                            label="Window Width",
                            precision=0
                        )
                        window_h = gr.Number(
                            value=config.get('window_height', 1080),
                            label="Window Height", 
                            precision=0
                        )
                    
                    enable_recording = gr.Checkbox(
                        label="Enable Recording",
                        value=config.get('enable_recording', True)
                    )
            
            with gr.TabItem("Agent Settings", id=2):
                with gr.Column():
                    gr.Markdown("### Agent Settings")
                    
                    agent_type = gr.Radio(
                        ["org", "custom"], 
                        label="Agent Type", 
                        value=config['agent_type']
                    )
                    
                    max_steps = gr.Slider(
                        minimum=1, 
                        maximum=200, 
                        value=config['max_steps'], 
                        step=1, 
                        label="Max Steps"
                    )
                    
                    use_vision = gr.Checkbox(
                        label="Use Vision", 
                        value=config['use_vision']
                    )
            
            with gr.TabItem("Run Agent", id=3):
                with gr.Column():
                    gr.Markdown("### Run Agent")
                    
                    task_input = gr.Textbox(
                        label="Task",
                        placeholder="Enter your task here...",
                        lines=3
                    )
                    
                    run_button = gr.Button("Run Agent", variant="primary")
                    
                    output = gr.Textbox(
                        label="Output",
                        lines=10,
                        max_lines=20
                    )
                    
                    def run_agent(task):
                        if ENABLE_LLM:
                            return f"LLM enabled - Task: {task}"
                        else:
                            return f"LLM disabled - Basic mode - Task: {task}"
                    
                    run_button.click(
                        fn=run_agent,
                        inputs=[task_input],
                        outputs=[output]
                    )
    
    return demo

if __name__ == "__main__":
    print(f"🔍 ENABLE_LLM: {ENABLE_LLM}")
    
    try:
        demo = create_minimal_ui()
        print("✅ UI created successfully")
        
        demo.launch(
            server_name="127.0.0.1",
            server_port=7791,
            share=False,
            show_error=True
        )
    except Exception as e:
        import traceback
        print(f"❌ Error creating UI: {e}")
        traceback.print_exc()
