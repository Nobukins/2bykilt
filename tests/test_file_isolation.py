#!/usr/bin/env python3
"""
File component isolation test - find which File parameter causes the schema error
"""
import logging
import argparse
import os
from dotenv import load_dotenv
load_dotenv()

import gradio as gr
from gradio.themes import Ocean

from src.utils.default_config_settings import default_config

def test_file_component_minimal(config):
    """Test minimal File component"""
    with gr.Blocks(title="File-Test-Minimal", theme=Ocean()) as demo:
        gr.Markdown("# File Component Test - Minimal")
        
        # Minimal File component
        file_input = gr.File(label="Test File")
        
        def handle_file(file):
            return f"File: {file.name if file else 'None'}"
        
        output = gr.Textbox(label="Output")
        file_input.change(fn=handle_file, inputs=file_input, outputs=output)
    
    return demo

def test_file_component_with_types(config):
    """Test File component with file_types"""
    with gr.Blocks(title="File-Test-Types", theme=Ocean()) as demo:
        gr.Markdown("# File Component Test - With file_types")
        
        # File component with file_types (like in the original)
        file_input = gr.File(label="Test File", file_types=[".env"])
        
        def handle_file(file):
            return f"File: {file.name if file else 'None'}"
        
        output = gr.Textbox(label="Output")
        file_input.change(fn=handle_file, inputs=file_input, outputs=output)
    
    return demo

def test_file_component_interactive(config):
    """Test File component with interactive parameter"""
    with gr.Blocks(title="File-Test-Interactive", theme=Ocean()) as demo:
        gr.Markdown("# File Component Test - With interactive")
        
        # File component with interactive parameter
        file_input = gr.File(label="Test File", interactive=True)
        
        def handle_file(file):
            return f"File: {file.name if file else 'None'}"
        
        output = gr.Textbox(label="Output")
        file_input.change(fn=handle_file, inputs=file_input, outputs=output)
    
    return demo

def test_file_component_full(config):
    """Test File component with all parameters like in original"""
    with gr.Blocks(title="File-Test-Full", theme=Ocean()) as demo:
        gr.Markdown("# File Component Test - Full")
        
        # File component exactly like in the original
        file_input = gr.File(label="Load .env File", file_types=[".env"], interactive=True)
        
        def handle_file(file):
            return f"File: {file.name if file else 'None'}"
        
        output = gr.Textbox(label="Output")
        file_input.change(fn=handle_file, inputs=file_input, outputs=output)
    
    return demo

def main():
    parser = argparse.ArgumentParser(description="File Component Isolation Test")
    parser.add_argument("--test", type=str, default="minimal", 
                       choices=["minimal", "types", "interactive", "full"], 
                       help="Test type to run")
    parser.add_argument("--port", type=int, default=7866, help="Port number")
    
    args = parser.parse_args()
    
    logging.basicConfig(level=logging.INFO)
    config = default_config()
    
    # Create UI based on test type
    if args.test == "minimal":
        demo = test_file_component_minimal(config)
        print("Testing minimal File component")
    elif args.test == "types":
        demo = test_file_component_with_types(config)
        print("Testing File component with file_types")
    elif args.test == "interactive":
        demo = test_file_component_interactive(config)
        print("Testing File component with interactive=True")
    elif args.test == "full":
        demo = test_file_component_full(config)
        print("Testing File component with all parameters")
    
    # Run with Gradio directly
    demo.launch(server_name="0.0.0.0", server_port=args.port, share=False)

if __name__ == "__main__":
    main()
