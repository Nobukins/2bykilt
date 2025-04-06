import gradio as gr
from .app_logger import logger, LOG_LEVELS

def create_log_tab():
    """Create a Gradio tab for log display and management."""
    with gr.Tab("ログ"):
        log_output = gr.TextArea(
            label="アプリケーションログ",
            value="\n".join(logger.get_gradio_logs()),
            lines=20,
            interactive=False
        )
        log_level = gr.Dropdown(
            choices=["ALL"] + list(LOG_LEVELS.keys()),
            value="ALL",
            label="ログレベル"
        )
        refresh_btn = gr.Button("更新")
        clear_btn = gr.Button("クリア")

        def update_logs(level):
            if level == "ALL":
                return "\n".join(logger.get_gradio_logs())
            return "\n".join(logger.get_gradio_logs(level=level))

        def clear_logs():
            logger.clear_gradio_logs()
            return ""

        log_level.change(update_logs, inputs=[log_level], outputs=[log_output])
        refresh_btn.click(update_logs, inputs=[log_level], outputs=[log_output])
        clear_btn.click(clear_logs, outputs=[log_output])

    return log_output
