#!/usr/bin/env python3
"""
Ultra minimal test to isolate the Gradio schema issue
"""
import os
import gradio as gr

# Set ENABLE_LLM to false
os.environ["ENABLE_LLM"] = "false"

def create_ultra_minimal_ui():
    """Create ultra minimal UI to isolate the problem"""
    with gr.Blocks(title="Ultra Minimal Test") as demo:
        gr.Markdown("# Ultra Minimal Test")
        
        # Test the most basic components first
        text_input = gr.Textbox(label="Test Input", value="test")
        button = gr.Button("Test Button")
        
        # Try adding one component at a time
        # checkbox = gr.Checkbox(label="Test Checkbox", value=True)  # Test this first
        
    return demo

if __name__ == "__main__":
    demo = create_ultra_minimal_ui()
    demo.launch(server_name="127.0.0.1", server_port=7791, share=False)
