#!/usr/bin/env python3
"""
Minimal test for Gradio DataFrame issue
"""
import os
import pytest
import gradio as gr
from src.ui.command_helper import CommandHelper

@pytest.mark.local_only
def test_dataframe():
    """Test DataFrame component that's causing the schema issue"""
    print("Testing DataFrame component...")
    
    # Test the CommandHelper data first
    helper = CommandHelper()
    commands_data = helper.get_commands_for_display()
    print(f"Commands data: {commands_data}")
    
    # Test DataFrame creation
    try:
        # Create a simple DataFrame
        df = gr.DataFrame(
            headers=["Command", "Description", "Usage"],
            label="Available Commands",
            interactive=False,
            value=commands_data  # This might be the problem
        )
        print("DataFrame creation: OK")
        return df
    except Exception as e:
        print(f"DataFrame creation error: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_minimal_ui():
    """Create minimal UI to isolate the problem"""
    with gr.Blocks(title="Minimal Test") as demo:
        gr.Markdown("# Minimal Test for DataFrame Issue")
        
        # Test problematic component
        test_df = test_dataframe()
        
        if test_df is None:
            # Fallback without the problematic component
            gr.Markdown("DataFrame creation failed - using fallback")
            test_output = gr.Textbox(label="Commands", value="DataFrame failed to initialize")
        else:
            test_output = test_df
            
        gr.Button("Test Button")
    
    return demo

if __name__ == "__main__":
    demo = create_minimal_ui()
    demo.launch(server_name="127.0.0.1", server_port=7789, share=False)
