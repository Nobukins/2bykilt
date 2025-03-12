import logging
from typing import Dict, Any

class FlowLogger:
    def __init__(self):
        self.logger = logging.getLogger("flow_logger")
        self._setup_logger()
        
    def _setup_logger(self):
        """ロガーの初期設定"""
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # コンソール出力
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # ファイル出力
        file_handler = logging.FileHandler('flow_analysis.log')
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        
        self.logger.setLevel(logging.INFO)

    def log_prompt_analysis(self, prompt: str, analysis: Dict[str, Any]):
        """プロンプト解析のログ"""
        self.logger.info("=== Prompt Analysis ===")
        self.logger.info(f"Input: {prompt}")
        self.logger.info(f"Analysis: {analysis}")

    def log_llm_input(self, context: Dict[str, Any]):
        """LLMへの入力情報のログ"""
        self.logger.info("=== LLM Input ===")
        for key, value in context.items():
            self.logger.info(f"{key}: {value}")

    def log_playwright_commands(self, commands: list):
        """Playwrightコマンドのログ"""
        self.logger.info("=== Playwright Commands ===")
        for cmd in commands:
            self.logger.info(f"Command: {cmd}")

    def log_execution_result(self, result: Dict[str, Any]):
        """実行結果のログ"""
        self.logger.info("=== Execution Result ===")
        self.logger.info(f"Result: {result}")
