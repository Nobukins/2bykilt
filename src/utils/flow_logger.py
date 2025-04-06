from typing import Dict, Any
from .app_logger import logger

class FlowLogger:
    """Compatibility wrapper for AppLogger."""
    def log_prompt_analysis(self, prompt: str, analysis: Dict[str, Any]):
        logger.log_prompt_analysis(prompt, analysis)

    def log_llm_input(self, context: Dict[str, Any]):
        logger.log_llm_input(context)

    def log_playwright_commands(self, commands: list):
        logger.log_playwright_commands(commands)

    def log_execution_result(self, result: Dict[str, Any]):
        logger.log_execution_result(result)
