import logging
import os
import re
import sys
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any, TextIO
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from io import StringIO

# new helper
from src.utils.fs_paths import get_logs_dir

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

class OutputCapture:
    """Capture stdout, stderr, and Python logging to a buffer while still showing output."""
    
    def __init__(self):
        self.buffer = StringIO()
        self._original_stdout: Optional[TextIO] = None
        self._original_stderr: Optional[TextIO] = None
        self._capture_active = False
        self._log_handler: Optional[logging.StreamHandler] = None
    
    def start(self):
        """Start capturing output."""
        if not self._capture_active:
            self._original_stdout = sys.stdout
            self._original_stderr = sys.stderr
            sys.stdout = TeeOutput(self._original_stdout, self.buffer)
            sys.stderr = TeeOutput(self._original_stderr, self.buffer)
            
            # Add a handler to capture all logging output
            self._log_handler = logging.StreamHandler(self.buffer)
            self._log_handler.setLevel(logging.DEBUG)
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            self._log_handler.setFormatter(formatter)
            logging.getLogger().addHandler(self._log_handler)
            
            self._capture_active = True
    
    def stop(self) -> str:
        """Stop capturing and return captured content."""
        if self._capture_active:
            sys.stdout = self._original_stdout
            sys.stderr = self._original_stderr
            
            # Remove the logging handler
            if self._log_handler:
                logging.getLogger().removeHandler(self._log_handler)
                self._log_handler = None
            
            self._capture_active = False
        content = self.buffer.getvalue()
        self.buffer = StringIO()  # Reset buffer
        return content

class TeeOutput:
    """Write to both original output and buffer."""
    
    def __init__(self, original: TextIO, buffer: StringIO):
        self.original = original
        self.buffer = buffer
    
    def write(self, text: str):
        self.original.write(text)
        self.buffer.write(text)
    
    def flush(self):
        self.original.flush()

class AppLogger:
    _instance = None
    # Use a re-entrant lock to allow bootstrap_app_logger to call into
    # AppLogger.__new__ while holding the lock without deadlocking.
    _lock = threading.RLock()
    _gradio_logs = []
    _max_buffer_size = 1000  # Limit for Gradio logs
    
    def __new__(cls, *args, log_dir: Optional[str] = None, **kwargs):
        # Accept optional init kwargs so callers can create the singleton
        # with configuration (used by bootstrap_app_logger). Store the
        # provided log_dir on the instance before running initialization.
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(AppLogger, cls).__new__(cls)
                # Stash any provided log_dir for _initialize_logger to pick up
                setattr(cls._instance, '_provided_log_dir', log_dir)
                cls._instance._initialize_logger()
            return cls._instance
    
    def _initialize_logger(self):  # noqa: PLR0915 - initialization orchestrates multiple concerns
        self.logger = logging.getLogger('app_logger')
        self.logger.setLevel(logging.DEBUG)
        self.logger.handlers = []
        # Allow tests or callers to inject an explicit log dir via
        # self._provided_log_dir (set by __new__ when bootstrap_app_logger
        # creates the instance). If provided, honoring it here overrides
        # repo-root detection.
        if hasattr(self, '_provided_log_dir') and self._provided_log_dir:
            log_dir = Path(self._provided_log_dir).expanduser().resolve()
            log_dir.mkdir(parents=True, exist_ok=True)
        else:
            # prefer centralized logs under repo-root or env override
            log_dir = get_logs_dir()
        os.makedirs(log_dir, exist_ok=True)
        # Expose chosen log dir for tests and debugging
        self._log_dir = log_dir
        log_file = Path(self._log_dir) / f'app_{datetime.now().strftime("%Y%m%d")}.log'
        # Use timed rotating handler to avoid unbounded growth
        file_handler = TimedRotatingFileHandler(str(log_file), when='midnight', backupCount=14, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] [%(filename)s:%(lineno)d] - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

        # Dedicated directory for persisted browser execution logs
        self._execution_log_dir = Path(self._log_dir) / "browser_runs"
        self._execution_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Subdirectories for summary and detailed logs
        self._summary_log_dir = self._execution_log_dir / "summary"
        self._summary_log_dir.mkdir(parents=True, exist_ok=True)
        
        self._detail_log_dir = self._execution_log_dir / "detail"
        self._detail_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Output capture for detailed logs (captures stdout/stderr)
        self._output_capture = OutputCapture()
    
    def get_gradio_logs(self, max_logs: int = 100, level: Optional[str] = None) -> List[str]:
        with self._lock:
            if level and level.upper() in LOG_LEVELS:
                filtered_logs = [log for log in self._gradio_logs if f"[{level.upper()}]" in log]
                return filtered_logs[-max_logs:] if max_logs > 0 else filtered_logs
            return self._gradio_logs[-max_logs:] if max_logs > 0 else self._gradio_logs.copy()
    
    def set_level(self, level: str):
        if level.upper() in LOG_LEVELS:
            self.logger.setLevel(LOG_LEVELS[level.upper()])
    
    def _log(
        self,
        level: int,
        message: str,
        *args,
        emoji: bool = True,
        save_for_gradio: bool = True,
        exc_info: bool = False,
        stacklevel: int = 3,
        **kwargs,
    ):
        """Internal logging method with emoji support and %-style formatting."""
        # Backwards compatibility: allow positional bool to toggle Gradio buffering
        if args and len(args) == 1 and isinstance(args[0], bool) and "%" not in message and "{" not in message:
            save_for_gradio = bool(args[0])
            args = ()

        formatted_message = message
        if args:
            try:
                formatted_message = message % args
            except Exception:  # pragma: no cover - safety fallback
                extra_parts = " ".join(str(arg) for arg in args)
                formatted_message = f"{message} {extra_parts}" if extra_parts else message

        level_name = logging.getLevelName(level)
        if emoji and level_name in EMOJI_MAP:
            formatted_message = f"{EMOJI_MAP[level_name]} {formatted_message}"

        log_kwargs = {"exc_info": exc_info, "stacklevel": stacklevel}
        extra = kwargs.get("extra")
        if extra is not None:
            log_kwargs["extra"] = extra

        self.logger.log(level, formatted_message, **log_kwargs)

        if save_for_gradio:
            with self._lock:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self._gradio_logs.append(f"[{timestamp}] [{level_name}] {formatted_message}")
                # Limit buffer size
                if len(self._gradio_logs) > self._max_buffer_size:
                    self._gradio_logs = self._gradio_logs[-self._max_buffer_size:]
    
    def clear_gradio_logs(self):
        """Clear Gradio logs."""
        with self._lock:
            self._gradio_logs.clear()
    
    def debug(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(logging.DEBUG, message, *args, save_for_gradio=save_for_gradio, **kwargs)
    
    def info(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(logging.INFO, message, *args, save_for_gradio=save_for_gradio, **kwargs)
    
    def warning(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(logging.WARNING, message, *args, save_for_gradio=save_for_gradio, **kwargs)
    
    def error(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(logging.ERROR, message, *args, save_for_gradio=save_for_gradio, **kwargs)
    
    def critical(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(logging.CRITICAL, message, *args, save_for_gradio=save_for_gradio, **kwargs)

    def exception(self, message: str, *args, save_for_gradio: bool = True, **kwargs):
        self._log(
            logging.ERROR,
            message,
            *args,
            save_for_gradio=save_for_gradio,
            exc_info=True,
            **kwargs,
        )
    
    def persist_action_run_log(
        self,
        action_name: str,
        content: str,
        *,
        command: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Persist automation execution summary to a timestamped log file in summary/ directory."""
        # REVIEW NOTE: Following PR #301 review (discussion_r2412687742), we tighten
        # sanitization to avoid leading '.' (hidden files) and sequences of dots which
        # add little semantic value and could confuse users when scanning the logs dir.
        # Policy:
        #   * Allow only [A-Za-z0-9_-]
        #   * Replace any disallowed run with a single '_'
        #   * Collapse consecutive '_' to one
        #   * Strip leading/trailing '_' (fallback to 'unnamed' if empty)
        # This intentionally disallows '.' inside the action slug; the timestamp already
        # separates the slug from the extension (.log) so extra dots are unnecessary.
        raw = action_name or "unnamed"
        safe_action = re.sub(r"[^A-Za-z0-9_-]+", "_", raw)
        # Collapse duplicate underscores and hyphens separately for cleaner slugs
        safe_action = re.sub(r"_+", "_", safe_action)
        safe_action = re.sub(r"-+", "-", safe_action).strip("_-")
        if not safe_action:
            safe_action = "unnamed"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = self._summary_log_dir / f"{timestamp}-{safe_action}.log"

        header_lines = [
            f"timestamp: {datetime.now().isoformat()}",
            f"action: {action_name}",
        ]

        if command:
            header_lines.append(f"command: {command}")

        if metadata:
            for key, value in metadata.items():
                header_lines.append(f"{key}: {value}")

        header_lines.append("")
        header = "\n".join(header_lines)
        body = content if content.endswith("\n") else f"{content}\n"

        log_path.write_text(f"{header}{body}", encoding="utf-8")
        return log_path
    
    def start_execution_log_capture(self):
        """Start capturing stdout/stderr for detailed execution log."""
        self._output_capture.start()
    
    def stop_execution_log_capture(self) -> str:
        """Stop capturing and return the captured output."""
        return self._output_capture.stop()
    
    def persist_detailed_action_log(
        self,
        action_name: str,
        captured_output: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Path:
        """Persist detailed execution logs to detail/ directory."""
        raw = action_name or "unnamed"
        safe_action = re.sub(r"[^A-Za-z0-9_-]+", "_", raw)
        safe_action = re.sub(r"_+", "_", safe_action)
        safe_action = re.sub(r"-+", "-", safe_action).strip("_-")
        if not safe_action:
            safe_action = "unnamed"
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        log_path = self._detail_log_dir / f"{timestamp}-{safe_action}.log"

        header_lines = [
            f"timestamp: {datetime.now().isoformat()}",
            f"action: {action_name}",
        ]

        if metadata:
            for key, value in metadata.items():
                header_lines.append(f"{key}: {value}")

        header_lines.append("")
        header_lines.append("=== Detailed Execution Log ===")
        header_lines.append("")
        
        header = "\n".join(header_lines)
        body = captured_output if captured_output.endswith("\n") else f"{captured_output}\n"

        log_path.write_text(f"{header}{body}", encoding="utf-8")
        return log_path

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
    # Avoid taking the same re-entrant lock here to prevent lock-ordering
    # issues during initialization. The creation race is acceptable during
    # single-threaded startup; tests can use `force=True` to reinitialize.
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
