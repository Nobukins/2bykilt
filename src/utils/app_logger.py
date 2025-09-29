import logging
import os
import sys
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

LOG_LEVELS = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Add emoji mapping
EMOJI_MAP = {
    "DEBUG": "🔍",
    "INFO": "ℹ️",
    "WARNING": "⚠️",
    "ERROR": "❌",
    "CRITICAL": "🚨"
}

class AppLogger:
    _instance = None
    _lock = threading.Lock()
    _gradio_logs = []
    _max_buffer_size = 1000  # Limit for Gradio logs
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppLogger, cls).__new__(cls)
                cls._instance._initialize_logger()
            return cls._instance
    
    def _initialize_logger(self):
        self.logger = logging.getLogger('app_logger')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        # Prefer writing logs to the repository root `logs/` directory when
        # possible. This prevents accidental writes into `src/logs/` when the
        # module lives under `src/` (common source layout). If we cannot
        # discover a repository root, fall back to the current working
        # directory's `logs/` to preserve previous behavior in tests.
        def _find_repo_root() -> Optional[str]:
            # Prefer scanning from the current working directory upwards so
            # tests that create a temporary repo layout (tmp_path) are
            # detected when the test changes CWD. Fall back to scanning the
            # module's file parents if nothing is found from CWD.
            markers = ("pyproject.toml", ".git", "artifacts")
            try:
                cwd = Path.cwd().resolve()
                for parent in (cwd, *cwd.parents):
                    for m in markers:
                        if (parent / m).exists():
                            return str(parent)
            except Exception:
                pass

            try:
                p = Path(__file__).resolve()
            except Exception:
                return None
            candidate = None
            for parent in p.parents:
                for m in markers:
                    if (parent / m).exists():
                        candidate = parent
                        break
                if candidate:
                    break
            return str(candidate) if candidate is not None else None

        repo_root = _find_repo_root()
        if repo_root:
            log_dir = os.path.join(repo_root, 'logs')
        else:
            log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        # Expose chosen log dir for tests and debugging
        self._log_dir = log_dir

        log_file = os.path.join(self._log_dir, f'app_{datetime.now().strftime("%Y%m%d")}.log')
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def get_gradio_logs(self, max_logs: int = 100, level: Optional[str] = None) -> List[str]:
        with self._lock:
            if level and level.upper() in LOG_LEVELS:
                filtered_logs = [log for log in self._gradio_logs if f"[{level.upper()}]" in log]
                return filtered_logs[-max_logs:] if max_logs > 0 else filtered_logs
            return self._gradio_logs[-max_logs:] if max_logs > 0 else self._gradio_logs.copy()
    
    def set_level(self, level: str):
        if level.upper() in LOG_LEVELS:
            self.logger.setLevel(LOG_LEVELS[level.upper()])
    
    def _log(self, level: int, message: str, emoji: bool = True, save_for_gradio: bool = True):
        """Internal logging method with emoji support."""
        level_name = logging.getLevelName(level)
        if emoji and level_name in EMOJI_MAP:
            message = f"{EMOJI_MAP[level_name]} {message}"
        self.logger.log(level, message)
        if save_for_gradio:
            with self._lock:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._gradio_logs.append(f"[{timestamp}] [{level_name}] {message}")
                # Limit buffer size
                if len(self._gradio_logs) > self._max_buffer_size:
                    self._gradio_logs = self._gradio_logs[-self._max_buffer_size:]
    
    def clear_gradio_logs(self):
        """Clear Gradio logs."""
        with self._lock:
            self._gradio_logs.clear()
    
    def debug(self, message: str, save_for_gradio: bool = True):
        self._log(logging.DEBUG, message, save_for_gradio=save_for_gradio)
    
    def info(self, message: str, save_for_gradio: bool = True):
        self._log(logging.INFO, message, save_for_gradio=save_for_gradio)
    
    def warning(self, message: str, save_for_gradio: bool = True):
        self._log(logging.WARNING, message, save_for_gradio=save_for_gradio)
    
    def error(self, message: str, save_for_gradio: bool = True):
        self._log(logging.ERROR, message, save_for_gradio=save_for_gradio)
    
    def critical(self, message: str, save_for_gradio: bool = True):
        self._log(logging.CRITICAL, message, save_for_gradio=save_for_gradio)
    
    def log_prompt_analysis(self, prompt: str, analysis: Dict[str, Any]):
        self.info("=== Prompt Analysis ===")
        self.info(f"Input: {prompt}")
        self.info(f"Analysis: {analysis}")
    
    def log_llm_input(self, context: Dict[str, Any]):
        self.info("=== LLM Input ===")
        for key, value in context.items():
            self.info(f"{key}: {value}")

    def log_playwright_commands(self, commands: list):
        self.info("=== Playwright Commands ===")
        for cmd in commands:
            self.info(f"Command: {cmd}")

    def log_execution_result(self, result: Dict[str, Any]):
        self.info("=== Execution Result ===")
        self.info(f"Result: {result}")

def bootstrap_app_logger(log_dir: Optional[str] = None, level: str = "DEBUG", force: bool = False) -> AppLogger:
    """Initialize or return the singleton AppLogger.

    - log_dir: explicit path to logs (overrides repo-root detection)
    - level: logging level name
    - force: if True, re-create instance even if one exists (useful for tests)
    """
    with AppLogger._lock:
        if AppLogger._instance is None or force:
            AppLogger._instance = AppLogger(log_dir=log_dir)
        return AppLogger._instance


def get_app_logger() -> AppLogger:
    """Return the initialized AppLogger; bootstrap with defaults if missing."""
    if AppLogger._instance is None:
        return bootstrap_app_logger()
    return AppLogger._instance


class _LazyLogger:
    """Proxy object so existing `from ... import logger` usages keep working.

    Attribute access is forwarded to the real AppLogger instance (created on
    first use via get_app_logger()). This keeps import-time behavior safe
    while allowing tests to control initialization via bootstrap_app_logger().
    """
    def __getattr__(self, name: str):
        inst = get_app_logger()
        return getattr(inst, name)

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return f"<LazyLogger proxy to {get_app_logger()!r}>"


# Module-level exported logger (backwards-compatible). Use bootstrap_app_logger()
# at startup (bykilt.py) to control log directory and options. Tests can call
# bootstrap_app_logger(..., force=True) to reinitialize under test CWD.
logger = _LazyLogger()
