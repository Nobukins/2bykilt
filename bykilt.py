"""
2Bykilt - Enhanced Browser Control with AI

Main UI module providing Gradio interface for browser automation.
This module orchestrates the web UI, integrating various services including
browser control, LLM integration, batch processing, and configuration management.
"""

# Standard library imports
import asyncio
import json
import logging
import os
import platform
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

# Third-party imports
from dotenv import load_dotenv
import gradio as gr
# Gradio 4.x has limited themes: Base, Default, Glass, Monochrome, Soft
# Gradio 5.x adds: Citrus, Ocean, Origin
try:
    from gradio.themes import Base, Citrus, Default, Glass, Monochrome, Ocean, Origin, Soft
except ImportError:
    # Gradio 4.x fallbacks
    from gradio.themes import Base, Default, Glass, Monochrome, Soft
    Citrus = Default  # Fallback: Citrus → Default
    Ocean = Glass     # Fallback: Ocean → Glass  
    Origin = Soft     # Fallback: Origin → Soft

# Environment setup
load_dotenv(override=True)

# Application imports - utilities
from src.utils.app_logger import get_app_logger
from src.utils import utils
from src.utils.default_config_settings import (
    default_config,
    load_config_from_file,
    save_config_to_file,
    save_current_config,
    update_ui_from_config,
)
from src.utils.utils import update_model_dropdown, get_latest_files
from src.utils.recording_dir_resolver import create_or_get_recording_dir

# Application imports - CLI
from src.cli.batch_commands import handle_batch_commands

# Application imports - browser
from src.browser.browser_manager import close_global_browser, prepare_recording_path, initialize_browser
from src.browser.browser_config import BrowserConfig

# Application imports - services
from src.services import list_recordings as list_recordings_service, ListParams
from src.script.script_manager import run_script

# Application imports - configuration
from src.config.standalone_prompt_evaluator import (
    pre_evaluate_prompt_standalone,
    extract_params_standalone,
    resolve_sensitive_env_variables_standalone,
)

# Application imports - UI
from src.ui.helpers import (
    load_actions_config,
    load_llms_file,
    save_llms_file,
    discover_and_preview_llmstxt,
    import_llmstxt_actions,
    preview_merge_llmstxt,
    load_env_browser_settings_file,
)
from src.ui.browser_agent import run_browser_agent, chrome_restart_dialog, show_restart_dialog

# Check for batch commands BEFORE full initialization
handle_batch_commands()

# Feature flags integration with backward compatibility
try:
    from src.config.feature_flags import FeatureFlags, is_llm_enabled
except Exception:
    # Fallback for early bootstrap
    def is_llm_enabled():
        return os.getenv("ENABLE_LLM", "false").lower() == "true"

    class FeatureFlags:  # type: ignore
        @staticmethod
        def set_override(name, value, ttl_seconds=None):
            pass


# Runtime LLM flag (evaluated at import time)
ENABLE_LLM = is_llm_enabled()

# ============================================================================
# Conditional LLM Module Imports
# ============================================================================
# When LLM is enabled, import full AI agent capabilities.
# Otherwise, use standalone fallbacks for basic browser control.

if ENABLE_LLM:
    try:
        # LLM configuration and prompt processing
        from src.config.llms_parser import pre_evaluate_prompt, extract_params, resolve_sensitive_env_variables

        # AI agent management
        from src.agent.agent_manager import (
            stop_agent,
            stop_research_agent,
            run_org_agent,
            run_custom_agent,
            run_deep_search,
            get_globals,
            run_browser_agent,
        )

        # Stream management for real-time output
        from src.ui.stream_manager import run_with_stream

        LLM_MODULES_AVAILABLE = True
        print("✅ LLM modules loaded successfully")

    except ImportError as e:
        print(f"⚠️ Warning: LLM modules failed to load: {e}")
        LLM_MODULES_AVAILABLE = False

        # Define fallback functions for non-LLM mode
        def pre_evaluate_prompt(prompt):
            return pre_evaluate_prompt_standalone(prompt)

        def extract_params(prompt, params):
            return extract_params_standalone(prompt, params)

        def resolve_sensitive_env_variables(text):
            return resolve_sensitive_env_variables_standalone(text)

        def stop_agent():
            return "LLM機能が無効です"

        def stop_research_agent():
            return "LLM機能が無効です"

        async def run_org_agent(*args, **kwargs):
            return "LLM機能が無効です", "", "", "", None, None

        async def run_custom_agent(*args, **kwargs):
            return "LLM機能が無効です", "", "", "", None, None

        async def run_deep_search(*args, **kwargs):
            return "LLM機能が無効です", None, gr.update(), gr.update()

        def get_globals():
            return {}

        async def run_browser_agent(*args, **kwargs):
            return "LLM機能が無効です"

        async def run_with_stream(*args, **kwargs):
            # Extract parameters from args
            task = args[17] if len(args) > 17 else ""  # task is the 18th parameter (0-indexed)
            use_own_browser = args[7] if len(args) > 7 else False  # use_own_browser is the 8th parameter
            headless = args[9] if len(args) > 9 else True  # headless is the 10th parameter
            browser_type = args[26] if len(args) > 26 else None  # browser_type is the 27th parameter (last added)

            # Start capturing output before command evaluation for browser-control type
            # This ensures we capture all logs from the beginning
            get_app_logger().start_execution_log_capture()

            # Check if this is a pre-registered command
            evaluation_result = pre_evaluate_prompt_standalone(task)
            if evaluation_result and evaluation_result.get("is_command"):
                # This is a pre-registered command, try to execute browser automation
                try:
                    # Get the action definition and parameters
                    action_name = evaluation_result.get("command_name", "").lstrip("@")
                    action_def = evaluation_result.get("action_def", {})
                    action_params = evaluation_result.get("params", {})
                    action_type = action_def.get("type", "")

                    if not action_def:
                        # Stop capture on error
                        get_app_logger().stop_execution_log_capture()
                        return (
                            f"❌ Pre-registered command '{action_name}' not found",
                            "",
                            "",
                            "",
                            "",
                            None,
                            None,
                            None,
                            gr.update(),
                            gr.update(),
                        )

                    # Handle different action types
                    if action_type == "browser-control":
                        from src.modules.direct_browser_control import execute_direct_browser_control

                        execution_params = {"use_own_browser": use_own_browser, "headless": headless, **action_params}

                        result = await execute_direct_browser_control(action_def, **execution_params)

                        # Stop capturing and retrieve logs (already started at function entry)
                        captured_output = get_app_logger().stop_execution_log_capture()

                        project_dir = os.path.dirname(os.path.abspath(__file__))
                        if result:
                            result_message = f"✅ Browser control command '{action_name}' executed successfully"
                            logger.info(f"Browser control command '{action_name}' executed successfully")

                            # Save summary log
                            summary_log_path = get_app_logger().persist_action_run_log(
                                action_name,
                                result_message,
                                metadata={"action_type": "browser-control", "status": "success"},
                            )

                            # Save detailed log
                            detail_log_path = get_app_logger().persist_detailed_action_log(
                                action_name,
                                captured_output,
                                metadata={"action_type": "browser-control", "status": "success"},
                            )

                            relative_summary_path = os.path.relpath(summary_log_path, project_dir)
                            relative_detail_path = os.path.relpath(detail_log_path, project_dir)
                            result_message += f"\n\nSummary log: {relative_summary_path}"
                            result_message += f"\nDetailed log: {relative_detail_path}"
                            logger.info(f"Summary log saved to: {summary_log_path}")
                            logger.info(f"Detailed log saved to: {detail_log_path}")
                            return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()
                        else:
                            result_message = f"❌ Browser control command '{action_name}' execution failed"
                            logger.error(f"Browser control command '{action_name}' execution failed")

                            # Save summary log
                            summary_log_path = get_app_logger().persist_action_run_log(
                                action_name,
                                result_message,
                                metadata={"action_type": "browser-control", "status": "failure"},
                            )

                            # Save detailed log
                            detail_log_path = get_app_logger().persist_detailed_action_log(
                                action_name,
                                captured_output,
                                metadata={"action_type": "browser-control", "status": "failure"},
                            )

                            relative_summary_path = os.path.relpath(summary_log_path, project_dir)
                            relative_detail_path = os.path.relpath(detail_log_path, project_dir)
                            result_message += f"\n\nSummary log: {relative_summary_path}"
                            result_message += f"\nDetailed log: {relative_detail_path}"
                            logger.info(f"Summary log saved to: {summary_log_path}")
                            logger.info(f"Detailed log saved to: {detail_log_path}")
                            return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()

                    elif action_type == "script":
                        # Stop capture for non-browser-control types
                        get_app_logger().stop_execution_log_capture()

                        # Handle script execution
                        command_template = action_def.get("command", "")
                        if not command_template:
                            return (
                                f"❌ Script command '{action_name}' has no command template",
                                "",
                                "",
                                "",
                                "",
                                None,
                                None,
                                None,
                                gr.update(),
                                gr.update(),
                            )

                        # Replace parameters in command template
                        command = command_template
                        for param_name, param_value in action_params.items():
                            placeholder = f"${{params.{param_name}}}"
                            command = command.replace(placeholder, str(param_value))

                        # Execute the script command
                        try:
                            import subprocess
                            import asyncio

                            # Change to the project directory
                            project_dir = os.path.dirname(os.path.abspath(__file__))

                            # Windows対応: 環境変数とPYTHONPATHを適切に設定
                            env = os.environ.copy()
                            env["PYTHONPATH"] = project_dir

                            # Windows対応: コマンドを適切に構築
                            # Always prefer the current Python interpreter over bare 'python'
                            if command.startswith("python "):
                                command = command.replace("python ", f'"{sys.executable}" ', 1)
                            # Run in shell for template convenience
                            shell_value = True

                            # Execute the command asynchronously
                            process = await asyncio.create_subprocess_shell(
                                command,
                                cwd=project_dir,
                                env=env,
                                shell=shell_value,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                            )

                            stdout, stderr = await process.communicate()

                            # Windows対応: エンコーディングの自動検出とフォールバック
                            def safe_decode(data):
                                if not data:
                                    return ""

                                # 複数のエンコーディングを試行
                                encodings = ["utf-8", "cp932", "shift_jis", "latin1"]
                                for encoding in encodings:
                                    try:
                                        return data.decode(encoding)
                                    except UnicodeDecodeError:
                                        continue
                                # すべて失敗した場合はエラーを無視してデコード
                                return data.decode("utf-8", errors="replace")

                            stdout_text = safe_decode(stdout)
                            stderr_text = safe_decode(stderr)

                            if process.returncode == 0:
                                result_message = (
                                    f"✅ Script command '{action_name}' executed successfully\n\nCommand: {command}"
                                )
                                if stdout_text:
                                    result_message += f"\n\nOutput:\n{stdout_text}"
                                logger.info(f"Script command '{action_name}' executed successfully")
                            else:
                                result_message = f"❌ Script command '{action_name}' execution failed (exit code: {process.returncode})\n\nCommand: {command}"
                                if stderr_text:
                                    result_message += f"\n\nError:\n{stderr_text}"
                                    logger.error(f"Script command '{action_name}' failed with stderr: {stderr_text}")
                                if stdout_text:
                                    result_message += f"\n\nOutput:\n{stdout_text}"
                                logger.error(f"Script command '{action_name}' failed (exit code: {process.returncode})")

                            execution_log_path = get_app_logger().persist_action_run_log(
                                action_name,
                                result_message,
                                command=command,
                                metadata={"returncode": str(process.returncode)},
                            )
                            relative_log_path = os.path.relpath(execution_log_path, project_dir)
                            result_message += f"\n\nExecution log saved to: {relative_log_path}"
                            logger.info(f"Execution log saved to: {execution_log_path}")

                            return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()

                        except Exception as e:
                            error_msg = (
                                f"❌ Error executing script command '{action_name}': {str(e)}\n\nCommand: {command}"
                            )
                            logger.error(f"Exception in script command '{action_name}': {str(e)}")
                            execution_log_path = get_app_logger().persist_action_run_log(
                                action_name,
                                error_msg,
                                command=command,
                                metadata={"exception": str(e)},
                            )
                            relative_log_path = os.path.relpath(execution_log_path, project_dir)
                            error_msg += f"\n\nExecution log saved to: {relative_log_path}"
                            logger.info(f"Execution log saved to: {execution_log_path}")
                            return error_msg, "", "", "", "", None, None, None, gr.update(), gr.update()

                    elif action_type in ["action_runner_template", "git-script"]:
                        # Stop capture for non-browser-control types
                        get_app_logger().stop_execution_log_capture()

                        # Use the script_manager for these types
                        try:
                            from src.script.script_manager import run_script

                            script_output, script_path = await run_script(action_def, action_params, headless=headless)

                            if script_output and "successfully" in script_output.lower():
                                return (
                                    f"✅ {action_type} command '{action_name}' executed successfully\n\n{script_output}",
                                    "",
                                    "",
                                    "",
                                    "",
                                    None,
                                    None,
                                    None,
                                    gr.update(),
                                    gr.update(),
                                )
                            else:
                                return (
                                    f"❌ {action_type} command '{action_name}' execution failed\n\n{script_output}",
                                    "",
                                    "",
                                    "",
                                    "",
                                    None,
                                    None,
                                    None,
                                    gr.update(),
                                    gr.update(),
                                )
                        except Exception as e:
                            return (
                                f"❌ Error executing {action_type} command '{action_name}': {str(e)}",
                                "",
                                "",
                                "",
                                "",
                                None,
                                None,
                                None,
                                gr.update(),
                                gr.update(),
                            )

                    else:
                        # Stop capture for unsupported types
                        get_app_logger().stop_execution_log_capture()
                        return (
                            f"❌ Action type '{action_type}' is not supported in minimal mode. Supported types: browser-control, script, action_runner_template, git-script",
                            "",
                            "",
                            "",
                            "",
                            None,
                            None,
                            None,
                            gr.update(),
                            gr.update(),
                        )

                except Exception as e:
                    # Stop capture on exception
                    get_app_logger().stop_execution_log_capture()
                    import traceback

                    error_detail = traceback.format_exc()
                    return (
                        f"❌ Error executing pre-registered command: {str(e)}\n\nDetails:\n{error_detail}",
                        "",
                        "",
                        "",
                        "",
                        None,
                        None,
                        None,
                        gr.update(),
                        gr.update(),
                    )
                finally:
                    # Ensure capture is always stopped, even if an unhandled exception occurs
                    # This handles edge cases where exceptions are not caught by the except block above
                    # The stop method is idempotent (safe to call multiple times)
                    get_app_logger().stop_execution_log_capture()
            else:
                # Stop capture if not a command
                get_app_logger().stop_execution_log_capture()
                return (
                    "LLM機能が無効です。事前登録されたコマンド（@で始まる）のみが利用可能です。",
                    "",
                    "",
                    "",
                    "",
                    None,
                    None,
                    None,
                    gr.update(),
                    gr.update(),
                )

else:
    LLM_MODULES_AVAILABLE = False
    print("ℹ️ LLM functionality is disabled (ENABLE_LLM=false)")

    # LLM無効時のダミー関数を定義（standaloneを使用）
    def pre_evaluate_prompt(prompt):
        return pre_evaluate_prompt_standalone(prompt)

    def extract_params(prompt, params):
        return extract_params_standalone(prompt, params)

    def resolve_sensitive_env_variables(text):
        return resolve_sensitive_env_variables_standalone(text)

    def stop_agent():
        return "LLM機能が無効です"

    def stop_research_agent():
        return "LLM機能が無効です"

    async def run_org_agent(*args, **kwargs):
        return "LLM機能が無効です", "", "", "", None, None

    async def run_custom_agent(*args, **kwargs):
        return "LLM機能が無効です", "", "", "", None, None

    async def run_deep_search(*args, **kwargs):
        return "LLM機能が無効です", None, gr.update(), gr.update()

    def get_globals():
        return {}

    async def run_browser_agent(*args, **kwargs):
        return "LLM機能が無効です"

    async def run_with_stream(*args, **kwargs):
        # Extract task from args (task is the 18th parameter)
        task = args[17] if len(args) > 17 else ""

        # Start capturing output before command evaluation
        get_app_logger().start_execution_log_capture()

        # Check if this is a pre-registered command
        evaluation_result = pre_evaluate_prompt_standalone(task)
        if evaluation_result and evaluation_result.get("is_command"):
            # This is a pre-registered command, try to execute browser automation
            try:
                # Extract browser parameters from args
                use_own_browser = args[7] if len(args) > 7 else False
                headless = args[9] if len(args) > 9 else True

                # Get the action definition and parameters
                action_name = evaluation_result.get("command_name", "").lstrip("@")
                action_def = evaluation_result.get("action_def", {})
                action_params = evaluation_result.get("params", {})
                action_type = action_def.get("type", "")

                if not action_def:
                    get_app_logger().stop_execution_log_capture()
                    return (
                        f"❌ Pre-registered command '{action_name}' not found",
                        "",
                        "",
                        "",
                        "",
                        None,
                        None,
                        None,
                        gr.update(),
                        gr.update(),
                    )

                # Handle different action types
                if action_type == "browser-control":
                    from src.modules.direct_browser_control import execute_direct_browser_control

                    execution_params = {"use_own_browser": use_own_browser, "headless": headless, **action_params}

                    # Add browser_type if available
                    if len(args) > 26 and args[26] is not None:
                        execution_params["browser_type"] = args[26]

                    result = await execute_direct_browser_control(action_def, **execution_params)

                    # Stop capturing and retrieve output
                    captured_output = get_app_logger().stop_execution_log_capture()

                    project_dir = os.path.dirname(os.path.abspath(__file__))
                    if result:
                        result_message = f"✅ Browser control command '{action_name}' executed successfully"
                        logger.info(f"Browser control command '{action_name}' executed successfully")

                        # Save summary log
                        summary_log_path = get_app_logger().persist_action_run_log(
                            action_name,
                            result_message,
                            metadata={"action_type": "browser-control", "status": "success"},
                        )

                        # Save detailed log
                        detail_log_path = get_app_logger().persist_detailed_action_log(
                            action_name,
                            captured_output,
                            metadata={"action_type": "browser-control", "status": "success"},
                        )

                        relative_summary_path = os.path.relpath(summary_log_path, project_dir)
                        relative_detail_path = os.path.relpath(detail_log_path, project_dir)
                        result_message += f"\n\nSummary log: {relative_summary_path}"
                        result_message += f"\nDetailed log: {relative_detail_path}"
                        logger.info(f"Summary log saved to: {summary_log_path}")
                        logger.info(f"Detailed log saved to: {detail_log_path}")
                        return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()
                    else:
                        result_message = f"❌ Browser control command '{action_name}' execution failed"
                        logger.error(f"Browser control command '{action_name}' execution failed")

                        # Save summary log
                        summary_log_path = get_app_logger().persist_action_run_log(
                            action_name,
                            result_message,
                            metadata={"action_type": "browser-control", "status": "failure"},
                        )

                        # Save detailed log
                        detail_log_path = get_app_logger().persist_detailed_action_log(
                            action_name,
                            captured_output,
                            metadata={"action_type": "browser-control", "status": "failure"},
                        )

                        relative_summary_path = os.path.relpath(summary_log_path, project_dir)
                        relative_detail_path = os.path.relpath(detail_log_path, project_dir)
                        result_message += f"\n\nSummary log: {relative_summary_path}"
                        result_message += f"\nDetailed log: {relative_detail_path}"
                        logger.info(f"Summary log saved to: {summary_log_path}")
                        logger.info(f"Detailed log saved to: {detail_log_path}")
                        return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()

                elif action_type == "script":
                    # Stop capture for non-browser-control types
                    get_app_logger().stop_execution_log_capture()
                    # Handle script execution
                    command_template = action_def.get("command", "")
                    if not command_template:
                        return (
                            f"❌ Script command '{action_name}' has no command template",
                            "",
                            "",
                            "",
                            "",
                            None,
                            None,
                            None,
                            gr.update(),
                            gr.update(),
                        )

                    # Replace parameters in command template
                    command = command_template
                    for param_name, param_value in action_params.items():
                        placeholder = f"${{params.{param_name}}}"
                        command = command.replace(placeholder, str(param_value))

                    # Execute the script command
                    try:
                        import subprocess
                        import asyncio

                        # Change to the project directory
                        project_dir = os.path.dirname(os.path.abspath(__file__))

                        # Windows対応: 環境変数とPYTHONPATHを適切に設定
                        env = os.environ.copy()
                        env["PYTHONPATH"] = project_dir

                        # Windows対応: コマンドを適切に構築
                        if platform.system() == "Windows":
                            # Windowsでは明示的にPythonパスを使用
                            if command.startswith("python "):
                                command = command.replace("python ", f'"{sys.executable}" ', 1)
                            shell_value = True
                        else:
                            shell_value = True

                        # Execute the command asynchronously
                        process = await asyncio.create_subprocess_shell(
                            command,
                            cwd=project_dir,
                            env=env,
                            shell=shell_value,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE,
                        )

                        stdout, stderr = await process.communicate()

                        # Windows対応: エンコーディングの自動検出とフォールバック
                        def safe_decode(data):
                            if not data:
                                return ""

                            # 複数のエンコーディングを試行
                            encodings = ["utf-8", "cp932", "shift_jis", "latin1"]
                            for encoding in encodings:
                                try:
                                    return data.decode(encoding)
                                except UnicodeDecodeError:
                                    continue
                            # すべて失敗した場合はエラーを無視してデコード
                            return data.decode("utf-8", errors="replace")

                        stdout_text = safe_decode(stdout)
                        stderr_text = safe_decode(stderr)

                        if process.returncode == 0:
                            result_message = (
                                f"✅ Script command '{action_name}' executed successfully\n\nCommand: {command}"
                            )
                            if stdout_text:
                                result_message += f"\n\nOutput:\n{stdout_text}"
                            logger.info(f"Script command '{action_name}' executed successfully")
                        else:
                            result_message = f"❌ Script command '{action_name}' execution failed (exit code: {process.returncode})\n\nCommand: {command}"
                            if stderr_text:
                                result_message += f"\n\nError:\n{stderr_text}"
                                logger.error(f"Script command '{action_name}' failed with stderr: {stderr_text}")
                            if stdout_text:
                                result_message += f"\n\nOutput:\n{stdout_text}"
                            logger.error(f"Script command '{action_name}' failed (exit code: {process.returncode})")

                        execution_log_path = get_app_logger().persist_action_run_log(
                            action_name,
                            result_message,
                            command=command,
                            metadata={"returncode": str(process.returncode)},
                        )
                        relative_log_path = os.path.relpath(execution_log_path, project_dir)
                        result_message += f"\n\nExecution log saved to: {relative_log_path}"
                        logger.info(f"Execution log saved to: {execution_log_path}")

                        return result_message, "", "", "", "", None, None, None, gr.update(), gr.update()

                    except Exception as e:
                        error_msg = f"❌ Error executing script command '{action_name}': {str(e)}\n\nCommand: {command}"
                        logger.error(f"Exception in script command '{action_name}': {str(e)}")
                        execution_log_path = get_app_logger().persist_action_run_log(
                            action_name,
                            error_msg,
                            command=command,
                            metadata={"exception": str(e)},
                        )
                        relative_log_path = os.path.relpath(execution_log_path, project_dir)
                        error_msg += f"\n\nExecution log saved to: {relative_log_path}"
                        logger.info(f"Execution log saved to: {execution_log_path}")
                        return error_msg, "", "", "", "", None, None, None, gr.update(), gr.update()

                elif action_type in ["action_runner_template", "git-script"]:
                    # Stop capture for non-browser-control types
                    get_app_logger().stop_execution_log_capture()

                    # Use the script_manager for these types
                    try:
                        from src.script.script_manager import run_script

                        # Pass browser_type to script_manager
                        browser_type_arg = args[26] if len(args) > 26 else None
                        script_output, script_path = await run_script(
                            action_def, action_params, headless=headless, browser_type=browser_type_arg
                        )

                        if script_output and "successfully" in script_output.lower():
                            return (
                                f"✅ {action_type} command '{action_name}' executed successfully\n\n{script_output}",
                                "",
                                "",
                                "",
                                "",
                                None,
                                None,
                                None,
                                gr.update(),
                                gr.update(),
                            )
                        else:
                            return (
                                f"❌ {action_type} command '{action_name}' execution failed\n\n{script_output}",
                                "",
                                "",
                                "",
                                "",
                                None,
                                None,
                                None,
                                gr.update(),
                                gr.update(),
                            )
                    except Exception as e:
                        return (
                            f"❌ Error executing {action_type} command '{action_name}': {str(e)}",
                            "",
                            "",
                            "",
                            "",
                            None,
                            None,
                            None,
                            gr.update(),
                            gr.update(),
                        )

                else:
                    get_app_logger().stop_execution_log_capture()
                    return (
                        f"❌ Action type '{action_type}' is not supported in minimal mode. Supported types: browser-control, script, action_runner_template, git-script",
                        "",
                        "",
                        "",
                        "",
                        None,
                        None,
                        None,
                        gr.update(),
                        gr.update(),
                    )

            except Exception as e:
                get_app_logger().stop_execution_log_capture()
                import traceback

                error_detail = traceback.format_exc()
                return (
                    f"❌ Error executing pre-registered command: {str(e)}\n\nDetails:\n{error_detail}",
                    "",
                    "",
                    "",
                    "",
                    None,
                    None,
                    None,
                    gr.update(),
                    gr.update(),
                )
            finally:
                # Ensure capture is always stopped, even if an unhandled exception occurs
                # This handles edge cases where exceptions are not caught by the except block above
                # The stop method is idempotent (safe to call multiple times)
                get_app_logger().stop_execution_log_capture()
        else:
            get_app_logger().stop_execution_log_capture()
            return (
                "LLM機能が無効です。事前登録されたコマンド（@で始まる）のみが利用可能です。",
                "",
                "",
                "",
                "",
                None,
                None,
                None,
                gr.update(),
                gr.update(),
            )


# ============================================================================
# Browser Automation Modules (Always Available)
# ============================================================================
# These modules provide browser control independent of LLM functionality
import yaml

from src.config.action_translator import ActionTranslator
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager
from src.ui.command_helper import CommandHelper
from src.utils.playwright_codegen import run_playwright_codegen, save_as_action_file
from src.utils.log_ui import create_log_tab
from src.modules.yaml_parser import InstructionLoader
from src.ui.admin.feature_flag_panel import create_feature_flag_admin_panel
from src.ui.admin.artifacts_panel import create_artifacts_panel

# FastAPI integration
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# ============================================================================
# Module Configuration
# ============================================================================

# Configure logging
logger = logging.getLogger(__name__)

# Playwright command mapping for browser automation
PLAYWRIGHT_COMMANDS = {
    "navigate": "goto",
    "click": "click",
    "fill": "fill",
    "fill_form": "fill",
    "keyboard_press": "press",
    "wait_for_selector": "wait_for_selector",
    "wait_for_navigation": "wait_for_load_state",
    "screenshot": "screenshot",
    "extract_content": "query_selector_all",
}

# Gradio theme configuration
theme_map = {
    "Default": Default(),
    "Soft": Soft(),
    "Monochrome": Monochrome(),
    "Glass": Glass(),
    "Origin": Origin(),
    "Citrus": Citrus(),
    "Ocean": Ocean(),
    "Base": Base(),
}

# Browser configuration singleton
browser_config = BrowserConfig()

# ============================================================================
# Main UI Function
# ============================================================================
# Main UI Function
# ============================================================================


def create_ui(config: Dict[str, Any], theme_name: str = "Ocean") -> gr.Blocks:
    """
    Create the Gradio UI with the specified configuration and theme.

    This function constructs the complete web interface including:
    - Agent settings and LLM configuration
    - Browser control and automation
    - Batch processing capabilities
    - Recording playback and management
    - Admin panels for feature flags and artifacts

    Args:
        config: Configuration dictionary with application settings
        theme_name: Name of Gradio theme to use (default: "Ocean")

    Returns:
        gr.Blocks: Configured Gradio application interface
    """
    # Load CSS from external file
    css_path = os.path.join(os.path.dirname(__file__), "assets", "css", "styles.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css = f.read()

    # 追加: カスタムヘッダーにCSP設定を含める
    custom_head = """
    <meta http-equiv="Content-Security-Policy" content="default-src * 'unsafe-inline' 'unsafe-eval'; img-src * data:; font-src * data:;">
    <script>
    console.log('カスタムヘッダー読み込み完了');
    </script>
    """

    with gr.Blocks(title="2Bykilt", theme=theme_map[theme_name], css=css, head=custom_head) as demo:
        # ======================================================
        # Define shared variables for all tabs
        # ======================================================
        window_w = gr.Number(
            value=config.get("window_width", 1920), label="ブラウザウィンドウ幅", precision=0, visible=False
        )
        window_h = gr.Number(
            value=config.get("window_height", 1080), label="ブラウザウィンドウ高さ", precision=0, visible=False
        )
        enable_recording = gr.Checkbox(
            label="録画を有効にする", value=config.get("enable_recording", True), visible=False
        )
        maintain_browser_session = gr.Checkbox(
            label="ブラウザセッションを維持", value=config.get("maintain_browser_session", False), visible=False
        )
        tab_selection_strategy = gr.Radio(
            ["new_tab", "reuse_tab"],
            label="タブ選択戦略",
            value=config.get("tab_selection_strategy", "new_tab"),
            visible=False,
        )
        # Resolve recording path via unified resolver (Issue #353 - unified artifacts only)
        try:
            default_recording_path = str(create_or_get_recording_dir())
        except Exception as e:
            logger.warning(f"Failed to resolve recording directory: {e}. Using fallback.", exc_info=e)
            # Fallback: Use environment variable or raise (Issue #353 - no ./tmp fallback)
            default_recording_path = os.getenv("RECORDING_PATH", "artifacts/runs/<run>-art/videos")

        save_recording_path = gr.Textbox(
            label="録画保存パス", value=config.get("save_recording_path", default_recording_path), visible=False
        )
        # Windows対応: トレースと履歴パスを設定
        default_trace_path = "./tmp/traces"
        default_history_path = "./tmp/agent_history"
        if platform.system() == "Windows":
            default_trace_path = str(Path.cwd() / "tmp" / "traces")
            default_history_path = str(Path.cwd() / "tmp" / "agent_history")

        save_trace_path = gr.Textbox(
            label="トレース保存パス", value=config.get("save_trace_path", default_trace_path), visible=False
        )
        save_agent_history_path = gr.Textbox(
            label="エージェント履歴パス",
            value=config.get("save_agent_history_path", default_history_path),
            visible=False,
        )

        with gr.Row():
            gr.Markdown(
                "# 🪄🌐 2Bykilt\n### Enhanced Browser Control with AI and human, because for you",
                elem_classes=["header-text"],
            )

        with gr.Tabs(selected=4) as tabs:  # Default to Run Agent tab
            # Define Agent Settings first for dependency
            with gr.TabItem("⚙️ Agent Settings", id=1):
                with gr.Group():
                    agent_type = gr.Radio(
                        ["org", "custom"],
                        label="Agent Type",
                        value=config["agent_type"],
                        info="Select the type of agent to use",
                    )
                    with gr.Column():
                        max_steps = gr.Slider(
                            minimum=1,
                            maximum=200,
                            value=config["max_steps"],
                            step=1,
                            label="Max Run Steps",
                            info="Maximum number of steps the agent will take",
                        )
                        max_actions_per_step = gr.Slider(
                            minimum=1,
                            maximum=20,
                            value=config["max_actions_per_step"],
                            step=1,
                            label="Max Actions per Step",
                            info="Maximum number of actions the agent will take per step",
                        )
                    with gr.Column():
                        use_vision = gr.Checkbox(
                            label="Use Vision", value=config["use_vision"], info="Enable visual processing capabilities"
                        )
                        tool_calling_method = gr.Dropdown(
                            label="Tool Calling Method",
                            value=config["tool_calling_method"],
                            interactive=True,
                            choices=["auto", "json_schema", "function_calling"],
                            info="Tool Calls Function Name",
                            visible=False,
                        )

            with gr.TabItem("🔧 LLM Configuration", id=2):
                # Runtime toggle (feature flag override) - always show at top
                with gr.Row():
                    llm_toggle = gr.Checkbox(
                        label="Enable LLM (feature flag)",
                        value=ENABLE_LLM,
                        info="Toggle runtime feature flag 'enable_llm'. Some modules may require restart to fully load.",
                    )
                    llm_toggle_status = gr.Markdown(
                        value=("✅ LLM flag enabled" if ENABLE_LLM else "ℹ️ LLM flag disabled")
                    )
                llm_toggle_advice = gr.Markdown(visible=True, value="")

                def _toggle_llm(flag_value: bool):
                    """Set runtime override for 'enable_llm'. Return status & advisory.

                    NOTE: If enabling when previously disabled, a full restart is needed
                    to import heavy LLM modules. We do not attempt hot-reload here.
                    """
                    try:
                        FeatureFlags.set_override("enable_llm", bool(flag_value))
                        # Provide user guidance
                        if flag_value:
                            msg = (
                                "✅ LLM flag set ON (enable_llm=true)\n\n"
                                "Restart the application to load full LLM modules, or continue in browser-only mode until restart."
                            )
                        else:
                            msg = (
                                "ℹ️ LLM flag set OFF (enable_llm=false)\n\n"
                                "LLM-dependent UI elements will hide after restart; current session may still have imported modules."
                            )
                        return (gr.update(value=("✅ LLM flag enabled" if flag_value else "ℹ️ LLM flag disabled")), msg)
                    except Exception as e:  # noqa: BLE001
                        return (gr.update(), f"❌ Failed to set flag: {e}")

                llm_toggle.change(_toggle_llm, inputs=llm_toggle, outputs=[llm_toggle_status, llm_toggle_advice])

                # LLM機能の状態表示 (post-toggle evaluation NOT live refreshed for heavy imports)
                if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
                    with gr.Group():
                        gr.Markdown("### ⚠️ LLM機能が無効化されています")
                        gr.Markdown(
                            """
                        **現在の状態**: LLM機能は無効化されています
                        **利用可能な機能**: ブラウザ自動化、Playwright Codegen
                        **LLM機能を有効化するには**:
                        1. この画面上部の "Enable LLM (feature flag)" を ON にする もしくは 環境変数 `ENABLE_LLM=true` を設定
                        2. LLM関連パッケージをインストール: `pip install -r requirements.txt`
                        3. アプリケーションを再起動 (ホットリロードは未対応)
                        """
                        )

                        # LLM無効時でも基本設定は表示（ただし無効化）
                        llm_provider = gr.Dropdown(
                            choices=["LLM無効"],
                            label="LLM Provider",
                            value="LLM無効",
                            interactive=False,
                            info="LLM機能が無効化されています",
                        )
                        llm_model_name = gr.Dropdown(
                            choices=["LLM無効"],
                            label="Model Name",
                            value="LLM無効",
                            interactive=False,
                            info="LLM機能が無効化されています",
                        )
                        llm_num_ctx = gr.Slider(
                            minimum=2**8,
                            maximum=2**16,
                            value=4096,
                            step=1,
                            label="Max Context Length",
                            interactive=False,
                            visible=False,
                        )
                        llm_temperature = gr.Slider(
                            minimum=0.0, maximum=2.0, value=0.0, step=0.1, label="Temperature", interactive=False
                        )
                        with gr.Row():
                            llm_base_url = gr.Textbox(
                                label="Base URL", value="", interactive=False, info="LLM機能が無効化されています"
                            )
                            llm_api_key = gr.Textbox(
                                label="API Key",
                                type="password",
                                value="",
                                interactive=False,
                                info="LLM機能が無効化されています",
                            )
                        dev_mode = gr.Checkbox(
                            label="Dev Mode", value=False, interactive=False, info="LLM機能が無効化されています"
                        )
                else:
                    # LLM有効時の通常UI
                    with gr.Group():
                        llm_provider = gr.Dropdown(
                            choices=[provider for provider, model in utils.model_names.items()],
                            label="LLM Provider",
                            value=config["llm_provider"],
                            info="Select your preferred language model provider",
                        )
                        llm_model_name = gr.Dropdown(
                            label="Model Name",
                            choices=utils.model_names["openai"],
                            value=config["llm_model_name"],
                            interactive=True,
                            info="Select a model from the dropdown or type a custom model name",
                        )
                        llm_num_ctx = gr.Slider(
                            minimum=2**8,
                            maximum=2**16,
                            value=config["llm_num_ctx"],
                            step=1,
                            label="Max Context Length",
                            info="Controls max context length model needs to handle (less = faster)",
                            visible=config["llm_provider"] == "ollama",
                        )
                        llm_temperature = gr.Slider(
                            minimum=0.0,
                            maximum=2.0,
                            value=config["llm_temperature"],
                            step=0.1,
                            label="Temperature",
                            info="Controls randomness in model outputs",
                        )
                        with gr.Row():
                            llm_base_url = gr.Textbox(
                                label="Base URL", value=config["llm_base_url"], info="API endpoint URL (if required)"
                            )
                            llm_api_key = gr.Textbox(
                                label="API Key",
                                type="password",
                                value=config["llm_api_key"],
                                info="Your API key (leave blank to use .env)",
                            )

                        llm_provider.change(
                            fn=lambda provider: gr.update(visible=provider == "ollama"),
                            inputs=llm_provider,
                            outputs=llm_num_ctx,
                        )

                        with gr.Row():
                            dev_mode = gr.Checkbox(
                                label="Dev Mode", value=config["dev_mode"], info="Use LM Studio compatible endpoints"
                            )

            with gr.TabItem("🤖 Run Agent", id=4):
                # LLM機能の状態に応じてタブの内容を変更
                if not ENABLE_LLM or not LLM_MODULES_AVAILABLE:
                    with gr.Group():
                        gr.Markdown("### ℹ️ ブラウザ自動化モード")
                        gr.Markdown(
                            """
                        **現在のモード**: LLM機能無効
                        **利用可能な機能**:
                        - ブラウザ自動化とスクリプト実行
                        - Playwright Codegen
                        - JSON形式のアクション実行
                        - 基本的なブラウザ操作

                        **制限事項**: 自然言語による指示は利用できません
                        """
                        )

                # Add command helper integration
                with gr.Accordion("📋 Available Commands", open=False):
                    # Create DataFrame with empty initial data to avoid schema issues
                    commands_table = gr.DataFrame(
                        headers=["Command", "Description", "Usage"],
                        label="Available Commands",
                        interactive=False,
                        value=[],  # Start with empty data
                    )

                    def load_commands_table():
                        """Load commands into the table"""
                        try:
                            helper = CommandHelper()
                            return helper.get_commands_for_display()
                        except Exception as e:
                            print(f"Error loading commands: {e}")
                            return [["Error", "Could not load commands", str(e)]]

                    refresh_commands = gr.Button("🔄 Refresh Commands")
                    refresh_commands.click(fn=load_commands_table, outputs=commands_table)

                    # Load commands on page load using the refresh button functionality - temporarily disabled
                    # demo.load(fn=load_commands_table, outputs=commands_table)

                    # Initialize recordings list on app start - add this after Recordings tab is defined
                    def initialize_recordings_on_load():
                        try:
                            recordings_path = config.get("save_recording_path", default_recording_path)
                            # Use appropriate update function based on flag
                            if FeatureFlags.is_enabled("artifacts.recursive_recordings_enabled"):
                                return update_recordings_list_with_service(recordings_path)
                            else:
                                return update_recordings_list_legacy(recordings_path)
                        except Exception:
                            return gr.update(choices=[], value=None), None, "Ready to load recordings"

                    # Load recordings when refresh button is clicked (defined later in Recordings tab)

                # Update task input with placeholder for command usage
                task = gr.Textbox(
                    label="Task Description",
                    lines=4,
                    placeholder="Enter your task or use @command format (e.g., @search query=python)",
                    value=config["task"],
                    info="Describe the task or use a command (@name or /name)",
                )

                # Add command table click-to-insert functionality
                def insert_command(evt: gr.SelectData):
                    """コマンドテンプレートをタスク入力に挿入"""
                    helper = CommandHelper()
                    commands = helper.get_all_commands()

                    # 表示用コマンドリストを取得
                    display_commands = helper.get_commands_for_display()

                    if evt.index[0] < len(display_commands):
                        # 選択されたコマンド名を取得
                        selected_command_name = display_commands[evt.index[0]][0]

                        # 完全なコマンド情報を取得
                        command = next((cmd for cmd in commands if cmd["name"] == selected_command_name), None)

                        if command:
                            # コマンドテンプレートを生成
                            command_text = f"@{command['name']}"

                            # 必須パラメータがあれば追加
                            if command.get("params"):
                                required_params = [p for p in command["params"] if p.get("required", False)]
                                if required_params:
                                    param_str = " ".join([f"{p['name']}=" for p in required_params])
                                    command_text += f" {param_str}"

                            return command_text

                    return ""  # 何も選択されなかった場合

                commands_table.select(fn=insert_command, outputs=task)

                # Load commands into the table initially - defer loading to avoid schema issues
                # commands_table.value = load_commands_table()  # Commented out to avoid Gradio schema error

                add_infos = gr.Textbox(
                    label="Additional Information", lines=3, placeholder="Add any helpful context or instructions..."
                )
                with gr.Row():
                    run_button = gr.Button("▶️ Run Agent", variant="primary", scale=2)
                    stop_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                with gr.Row():
                    browser_view = gr.HTML(
                        value="<h1 style='width:80vw; height:50vh'>Waiting for browser session...</h1>",
                        label="Live Browser View",
                    )

            # New tab for editing llms.txt directly
            with gr.TabItem("📄 LLMS Config", id=5):
                # View section for llms.txt
                with gr.Accordion("📄 View LLMS Config", open=False):
                    llms_code = gr.Code(
                        label="LLMS Config View",
                        language="markdown",
                        value=load_llms_file(),
                        interactive=False,
                        lines=20,
                    )
                    refresh_view_btn = gr.Button("🔄 Refresh View", variant="secondary")
                    refresh_view_btn.click(fn=load_llms_file, inputs=None, outputs=llms_code)
                # Edit section for llms.txt
                with gr.Accordion("✏️ Edit LLMS Config", open=True):
                    llms_text = gr.Textbox(
                        label="LLMS Config (llms.txt)", value=load_llms_file(), lines=20, interactive=True
                    )
                    with gr.Row():
                        save_btn = gr.Button("💾 Save llms.txt", variant="primary")
                        reload_btn = gr.Button("🔄 Reload llms.txt")
                    status_llms = gr.Markdown()
                    save_btn.click(fn=save_llms_file, inputs=llms_text, outputs=status_llms)
                    reload_btn.click(fn=load_llms_file, inputs=None, outputs=llms_text)

            with gr.TabItem("🌐 llms.txt Import", id=13):
                gr.Markdown(
                    """
                ### Remote llms.txt Auto-Import

                自動的にリモートのllms.txtファイルから2bykiltブラウザ自動化コマンドを検出・取得し、
                ローカルのllms.txtへ統合します。セキュリティ検証と競合解決機能を搭載しています。

                **使い方:**
                1. URLを入力 (llms.txt URLまたはベースURL)
                2. 🔍 Discoverボタンでアクション検出
                3. セキュリティ検証結果を確認
                4. マージプレビューで追加内容を確認
                5. ✅ Importボタンで取り込み
                """
                )

                # Step 1: Discovery
                with gr.Accordion("Step 1: 🔍 Discovery", open=True):
                    with gr.Row():
                        url_input = gr.Textbox(
                            label="llms.txt URL または Base URL",
                            placeholder="https://example.com or https://example.com/llms.txt",
                            scale=4,
                        )
                        https_only_checkbox = gr.Checkbox(
                            label="HTTPS Only", value=True, info="HTTPS接続のみ許可", scale=1
                        )

                    discover_btn = gr.Button("🔍 Discover Actions", variant="primary")
                    discovery_status = gr.Markdown()

                    with gr.Accordion("Discovered Actions (JSON)", open=False):
                        discovered_actions_json = gr.Code(
                            label="Discovered Actions", language="json", lines=10, interactive=False
                        )

                # Step 2: Security Validation (auto-displayed after discovery)
                with gr.Accordion("Step 2: 🔒 Security Validation", open=False) as security_accordion:
                    security_status = gr.Markdown()

                # Step 3: Preview Merge
                with gr.Accordion("Step 3: 👁️ Preview Merge", open=False) as preview_accordion:
                    strategy_selector = gr.Radio(
                        choices=["skip", "overwrite", "rename"],
                        label="Conflict Resolution Strategy",
                        value="skip",
                        info="skip: 既存を維持 | overwrite: 新規で上書き | rename: 新規に連番追加",
                    )
                    preview_btn = gr.Button("👁️ Preview Merge")
                    preview_output = gr.Markdown()

                # Step 4: Confirm Import
                with gr.Accordion("Step 4: ✅ Import", open=False) as import_accordion:
                    gr.Markdown(
                        """
                    **注意:**
                    - インポート前に自動でバックアップが作成されます
                    - バックアップは `llms.txt.backup.YYYYMMDD_HHMMSS` 形式で保存されます
                    """
                    )
                    import_btn = gr.Button("✅ Import Actions", variant="primary")
                    import_result = gr.Markdown()

                # Hidden state to pass discovered actions between steps
                discovered_actions_state = gr.State("")

                # Event handlers
                discover_btn.click(
                    fn=discover_and_preview_llmstxt,
                    inputs=[url_input, https_only_checkbox],
                    outputs=[discovered_actions_json, discovery_status, discovered_actions_state],
                )

                preview_btn.click(
                    fn=preview_merge_llmstxt,
                    inputs=[discovered_actions_state, strategy_selector],
                    outputs=preview_output,
                )

                import_btn.click(
                    fn=import_llmstxt_actions,
                    inputs=[discovered_actions_state, strategy_selector],
                    outputs=import_result,
                )

            with gr.TabItem("🌐 Browser Settings", id=3):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### ブラウザー設定")

                        browser_type = gr.Dropdown(
                            choices=["chrome", "edge"],
                            label="使用するブラウザ",
                            value=browser_config.config.get("current_browser", "chrome"),
                            info="Chrome または Edge を選択してください",
                        )

                        use_own_browser = gr.Checkbox(label="既存のブラウザを使用", value=False)
                        headless = gr.Checkbox(label="ヘッドレスモード", value=False)
                        keep_browser_open = gr.Checkbox(label="ブラウザを開いたままにする", value=False)
                        disable_security = gr.Checkbox(
                            label="セキュリティを無効化",
                            value=browser_config.get_browser_settings()["disable_security"],
                            info="ブラウザのセキュリティ機能を無効化します",
                        )

                        # Directly render components instead of using .update()
                        with gr.Row():
                            window_w = gr.Number(
                                value=config.get("window_width", 1920), label="ブラウザウィンドウ幅", precision=0
                            )
                            window_h = gr.Number(
                                value=config.get("window_height", 1080), label="ブラウザウィンドウ高さ", precision=0
                            )

                        enable_recording = gr.Checkbox(
                            label="録画を有効にする", value=config.get("enable_recording", True)
                        )
                        maintain_browser_session = gr.Checkbox(
                            label="ブラウザセッションを維持", value=config.get("maintain_browser_session", False)
                        )
                        tab_selection_strategy = gr.Radio(
                            ["new_tab", "reuse_tab"],
                            label="タブ選択戦略",
                            value=config.get("tab_selection_strategy", "new_tab"),
                        )
                        save_recording_path = gr.Textbox(
                            label="録画保存パス", value=config.get("save_recording_path", default_recording_path)
                        )
                        save_trace_path = gr.Textbox(
                            label="トレース保存パス", value=config.get("save_trace_path", default_trace_path)
                        )
                        save_agent_history_path = gr.Textbox(
                            label="エージェント履歴パス",
                            value=config.get("save_agent_history_path", default_history_path),
                        )

                        browser_path_info = gr.Markdown(
                            value=f"**現在のブラウザパス**: {browser_config.get_browser_settings()['path']}",
                            visible=True,
                        )
                        user_data_info = gr.Markdown(
                            value=f"**ユーザーデータパス**: {browser_config.get_browser_settings()['user_data']}",
                            visible=True,
                        )

                        update_browser_btn = gr.Button("ブラウザ設定を更新", variant="primary")
                        browser_update_result = gr.Markdown("")

                        # Env file path input (replacing File component to fix schema error)
                        env_file_path = gr.Textbox(label="Env File Path", placeholder="Enter path to .env file")
                        load_env_btn = gr.Button("🔄 Load Env Settings", variant="secondary")

                        # Hook to reload browser path/user data from .env
                        def load_env_from_path(file_path):
                            """Load environment settings from file path"""
                            if not file_path:
                                return "No path provided", "No path provided", "Error: Please provide a file path"
                            try:
                                # Mock loading - replace with actual implementation
                                return (
                                    f"Loaded from: {file_path}",
                                    f"User data from: {file_path}",
                                    "Settings loaded successfully",
                                )
                            except Exception as e:
                                return "Error loading", "Error loading", f"Error: {str(e)}"

                        load_env_btn.click(
                            fn=load_env_from_path,
                            inputs=[env_file_path],
                            outputs=[browser_path_info, user_data_info, browser_update_result],
                        )

                        def update_browser_settings(browser_selection, disable_security_flag):
                            """Update browser settings and return results."""
                            try:
                                logger.debug(f"🔍 update_browser_settings 呼び出し:")
                                logger.debug(f"  - browser_selection: {browser_selection}")
                                logger.debug(f"  - disable_security_flag: {disable_security_flag}")
                                logger.debug(f"  - 変更前のbrowser_config.config: {browser_config.config}")

                                browser_config.set_current_browser(browser_selection)

                                logger.debug(f"  - 変更後のbrowser_config.config: {browser_config.config}")

                                settings = browser_config.get_browser_settings()
                                settings["disable_security"] = disable_security_flag

                                browser_path = f"**現在のブラウザパス**: {settings['path']}"
                                user_data = f"**ユーザーデータパス**: {settings['user_data']}"

                                logger.info(f"✅ ブラウザ設定を {browser_selection.upper()} に更新しました")
                                logger.debug(f"🔍 更新された設定: {settings}")

                                return (
                                    browser_path,
                                    user_data,
                                    f"✅ ブラウザ設定を {browser_selection.upper()} に更新しました",
                                )
                            except Exception as e:
                                logger.error(f"❌ update_browser_settings エラー: {e}")
                                import traceback

                                logger.debug(f"🔍 スタックトレース: {traceback.format_exc()}")
                                return (
                                    browser_path_info.value,
                                    user_data_info.value,
                                    f"❌ エラーが発生しました: {str(e)}",
                                )

                        browser_type.change(
                            fn=update_browser_settings,
                            inputs=[browser_type, disable_security],
                            outputs=[browser_path_info, user_data_info, browser_update_result],
                        )

                        update_browser_btn.click(
                            fn=update_browser_settings,
                            inputs=[browser_type, disable_security],
                            outputs=[browser_path_info, user_data_info, browser_update_result],
                        )

            with gr.TabItem("🎭 Playwright Codegen", id=9):
                with gr.Group():
                    gr.Markdown("### 🎮 ブラウザ操作スクリプト自動生成")
                    gr.Markdown(
                        """
URLを入力してPlaywright codegenを起動し、ブラウザ操作を記録。生成されたスクリプトはアクションファイルとして保存できます。

**ブラウザ選択について:**
- **Chrome**: システムにインストールされたGoogle Chromeを使用（プロファイル付き、API警告なし）
- **Edge**: システムにインストールされたMicrosoft Edgeを使用（プロファイル付き）
- ブラウザが見つからない場合: Playwright内蔵Chromium（プロファイルなし、Google API警告表示）
                    """
                    )

                    with gr.Row():
                        url_input = gr.Textbox(
                            label="ウェブサイトURL",
                            placeholder="記録するURLを入力（例: https://example.com）",
                            info="Playwrightが記録を開始するURL",
                        )
                        browser_type_codegen = gr.Radio(
                            label="ブラウザタイプ",
                            choices=["Chrome", "Edge"],
                            value="Chrome",
                            info="記録に使用するブラウザを選択",
                        )
                    run_codegen_button = gr.Button("▶️ Playwright Codegenを実行", variant="primary")

                    codegen_status = gr.Markdown("")

                    # View generated script
                    with gr.Accordion("📄 View Generated Script", open=True):
                        generated_script_view = gr.Code(
                            label="Generated Script",
                            language="python",
                            value="# ここに生成されたスクリプトが表示されます",
                            interactive=False,
                            lines=15,
                        )
                        copy_script_button = gr.Button("📋 Copy to Clipboard")

                    # Edit generated script
                    with gr.Accordion("✏️ Edit Generated Script", open=False):
                        generated_script_edit = gr.Textbox(
                            label="Edit Generated Script", value="", lines=15, interactive=True
                        )
                        with gr.Row():
                            reload_edit_btn = gr.Button("🔄 Load into Editor", variant="secondary")
                        # load view code into editor
                        reload_edit_btn.click(
                            fn=lambda code: code, inputs=generated_script_view, outputs=generated_script_edit
                        )
                    # Save action file using edited script
                    with gr.Accordion("アクションとして保存", open=True):
                        with gr.Row():
                            action_file_name = gr.Textbox(
                                label="ファイル名", placeholder="ファイル名を入力（.pyは不要）"
                            )
                            action_command_name = gr.Textbox(
                                label="コマンド名", placeholder="コマンド名（空白でファイル名使用）"
                            )
                        save_action_button = gr.Button("💾 Save as Action", variant="primary")
                        save_status = gr.Markdown("")
                        save_action_button.click(
                            fn=save_as_action_file,
                            inputs=[generated_script_edit, action_file_name, action_command_name],
                            outputs=[save_status],
                        )

                    with gr.Accordion("アクションとして保存", open=True):
                        with gr.Row():
                            action_file_name = gr.Textbox(
                                label="ファイル名",
                                placeholder="ファイル名を入力（.pyは不要）",
                                info="保存するアクションファイル名（actionsフォルダに保存されます）",
                            )
                            action_command_name = gr.Textbox(
                                label="コマンド名",
                                placeholder="llms.txtに登録するコマンド名（空白の場合はファイル名を使用）",
                                info="llms.txtに登録するコマンド名（空白の場合はファイル名を使用）",
                            )

                        save_action_button = gr.Button("💾 アクションファイルとして保存", variant="primary")
                        save_status = gr.Markdown("")

                    # Playwright codegen操作のハンドラ関数
                    def handle_run_codegen(url, browser_choice):
                        if not url or url.strip() == "":
                            return "⚠️ 有効なURLを入力してください", "# URLを入力してスクリプトを生成してください"

                        # ブラウザタイプの判定
                        browser_type = browser_choice.lower()

                        # ユーザーデータディレクトリの存在確認
                        if browser_type == "edge":
                            from src.utils.playwright_codegen import detect_browser_paths

                            browser_paths = detect_browser_paths()
                            user_data_dir = browser_paths.get("edge_user_data", "")
                            if not user_data_dir or not os.path.exists(user_data_dir):
                                return (
                                    "⚠️ Edgeのユーザーデータディレクトリが見つかりません。自動検出を試みます...",
                                    "# ブラウザ設定確認中...",
                                )

                        # Playwright codegen実行
                        from src.utils.playwright_codegen import run_playwright_codegen

                        success, result = run_playwright_codegen(url, browser_type)
                        if success:
                            return f"✅ {browser_choice}を使用してスクリプトが正常に生成されました", result
                        else:
                            return f"❌ エラー: {result}", "# スクリプト生成中にエラーが発生しました"

                    # UI要素と関数の連携を更新
                    run_codegen_button.click(
                        fn=handle_run_codegen,
                        inputs=[url_input, browser_type_codegen],
                        outputs=[codegen_status, generated_script_view],
                    )

                    save_action_button.click(
                        fn=save_as_action_file,
                        inputs=[generated_script_edit, action_file_name, action_command_name],
                        outputs=[save_status],
                    )

                    # クリップボード機能のためのJavaScript
                    copy_script_button.click(
                        fn=None,
                        js="""
                    () => {
                        const codeBlock = document.querySelector('.gradio-container [data-testid="code"] pre code');
                        if (codeBlock) {
                            const text = codeBlock.textContent;
                            navigator.clipboard.writeText(text);
                            const button = document.querySelector('button:contains("クリップボードにコピー")');
                            const originalText = button.textContent;
                            button.textContent = "✓ コピーしました！";
                            setTimeout(() => { button.textContent = originalText; }, 2000);
                        }
                        return null;
                    }
                    """,
                    )

            with gr.TabItem("🔎 データ抽出", id="data_extract"):  # Data Extraction tab with restored UI
                gr.Markdown("### 🔍 ページからデータを抽出")
                with gr.Row():
                    with gr.Column(scale=1):
                        extraction_url = gr.Textbox(label="抽出先URL", placeholder="https://example.com", lines=1)
                        with gr.Accordion("抽出セレクター設定", open=True):
                            selector_type = gr.Radio(["シンプル", "詳細"], value="シンプル", label="セレクタータイプ")
                            simple_selectors = gr.Textbox(
                                label="セレクター (カンマで区切る)", placeholder="h1, .main-content, #title", lines=2
                            )
                            advanced_selectors = gr.Code(
                                label="セレクター (JSON形式)",
                                language="json",
                                value="""{
  "タイトル": {"selector": "h1", "type": "text"},
  "本文": {"selector": ".content", "type": "html"},
  "画像URL": {"selector": "img.main", "type": "attribute", "attribute": "src"}
}""",
                            )
                        extract_button = gr.Button("データを抽出", variant="primary")
                        save_path = gr.Textbox(
                            label="保存先ファイルパス (空白で自動生成)", placeholder="/path/to/output.json", lines=1
                        )
                        save_format = gr.Dropdown(choices=["json", "csv"], value="json", label="保存形式")
                        save_button = gr.Button("データを保存", variant="secondary")
                    with gr.Column(scale=2):
                        extraction_result = gr.Code(label="抽出結果", language="json", interactive=False)
                        extraction_status = gr.Markdown(label="ステータス")
                # Toggle between simple and advanced selectors
                selector_type.change(
                    fn=lambda t: (gr.update(visible=(t == "シンプル")), gr.update(visible=(t == "詳細"))),
                    inputs=selector_type,
                    outputs=[simple_selectors, advanced_selectors],
                )

                # Extraction logic
                async def run_extraction(
                    url, selector_type, simple_s, advanced_s, use_own, headless, maintain_sess, tab_strategy
                ):
                    if not url:
                        return "{}", "URLを入力してください"
                    try:
                        import json
                        from src.modules.execution_debug_engine import ExecutionDebugEngine

                        engine = ExecutionDebugEngine()
                        selectors = simple_s.split(",") if selector_type == "シンプル" else advanced_s
                        result = await engine.execute_extract_content(
                            {"url": url, "selectors": selectors},
                            use_own_browser=use_own,
                            headless=headless,
                            maintain_browser_session=maintain_sess,
                            tab_selection_strategy=tab_strategy,
                        )
                        if result.get("error"):
                            return json.dumps({"error": result["error"]}, indent=2, ensure_ascii=False), f"❌ エラー: {result['error']}"
                        return json.dumps(result, indent=2, ensure_ascii=False), "✅ 抽出完了"
                    except Exception as e:
                        import json
                        return json.dumps({"error": str(e)}, indent=2, ensure_ascii=False), f"❌ 抽出中に例外: {e}"

                async def save_extracted_data(data_json, path, fmt):
                    if not data_json or data_json == "{}":
                        return "❌ 保存するデータがありません"
                    try:
                        import json
                        from src.modules.execution_debug_engine import ExecutionDebugEngine

                        engine = ExecutionDebugEngine()
                        # JSON文字列を辞書に戻す
                        data = json.loads(data_json)
                        engine.last_extracted_content = data
                        save_result = await engine.save_extracted_content(file_path=path or None, format_type=fmt)
                        return "✅ 保存完了" if save_result.get("success") else f"❌ {save_result.get('message')}"
                    except Exception as e:
                        return f"❌ 保存中に例外: {e}"

                extract_button.click(
                    fn=run_extraction,
                    inputs=[
                        extraction_url,
                        selector_type,
                        simple_selectors,
                        advanced_selectors,
                        use_own_browser,
                        headless,
                        maintain_browser_session,
                        tab_selection_strategy,
                    ],
                    outputs=[extraction_result, extraction_status],
                )
                save_button.click(
                    fn=save_extracted_data,
                    inputs=[extraction_result, save_path, save_format],
                    outputs=[extraction_status],
                )

            with gr.TabItem("📁 Configuration", id=10):
                with gr.Group():
                    # Feature Flagの状態に応じてplaceholderを動的に設定
                    allow_pickle = FeatureFlags.get("security.allow_pickle_config", expected_type=bool, default=False)
                    if allow_pickle:
                        config_placeholder = "Enter path to .pkl or .json config file"
                    else:
                        config_placeholder = "Enter path to .json config file"

                    config_file_path = gr.Textbox(label="Config File Path", placeholder=config_placeholder)
                    git_token = gr.Textbox(
                        label="Git Token (for non-git users)",
                        type="password",
                        info="Personal token for downloading scripts without Git",
                    )
                    load_config_button = gr.Button("Load Existing Config From File", variant="primary")
                    save_config_button = gr.Button("Save Current Config", variant="primary")
                    config_status = gr.Textbox(label="Status", lines=2, interactive=False)

                    load_config_button.click(
                        fn=update_ui_from_config,
                        inputs=[config_file_path],
                        outputs=[
                            agent_type,
                            max_steps,
                            max_actions_per_step,
                            use_vision,
                            tool_calling_method,
                            llm_provider,
                            llm_model_name,
                            llm_num_ctx,
                            llm_temperature,
                            llm_base_url,
                            llm_api_key,
                            use_own_browser,
                            keep_browser_open,
                            headless,
                            disable_security,
                            enable_recording,
                            window_w,
                            window_h,
                            save_recording_path,
                            save_trace_path,
                            save_agent_history_path,
                            task,
                            config_status,
                        ],
                    )
                    save_config_button.click(
                        fn=save_current_config,
                        inputs=[
                            agent_type,
                            max_steps,
                            max_actions_per_step,
                            use_vision,
                            tool_calling_method,
                            llm_provider,
                            llm_model_name,
                            llm_num_ctx,
                            llm_temperature,
                            llm_base_url,
                            llm_api_key,
                            use_own_browser,
                            keep_browser_open,
                            headless,
                            disable_security,
                            enable_recording,
                            window_w,
                            window_h,
                            save_recording_path,
                            save_trace_path,
                            save_agent_history_path,
                            task,
                        ],
                        outputs=[config_status],
                    )

            # New: Interactive Option Availability checks tab
            with gr.TabItem("✅ Option Availability", id=11):
                gr.Markdown("## 🔍 Option Availability - Functional Verification")
                gr.Markdown(
                    """
Execute comprehensive verification tests for all supported action types. This runs actual functional tests to ensure:

- **Script Actions**: Command execution capability
- **Action Runner Templates**: Template processing and execution
- **Browser Control**: Browser initialization, profile loading, and automation
- **Git Script**: Repository operations and script execution

Tests include browser initialization, profile validation, and recording path verification.
"""
                )

                with gr.Row():
                    selected_browser_for_check = gr.Dropdown(
                        choices=["chrome", "edge"],
                        value=browser_config.config.get("current_browser", "chrome"),
                        label="チェック用ブラウザ種別",
                    )
                    recording_path_for_check = gr.Textbox(
                        label="録画保存パス (空なら自動)",
                        value=config.get("save_recording_path", default_recording_path),
                    )

                checks_table = gr.DataFrame(
                    headers=["Action Type", "Browser Init", "Profile", "Recording"],
                    value=[
                        ["script", "—", "—", "—"],
                        ["action_runner_template", "—", "—", "—"],
                        ["browser-control", "—", "—", "—"],
                        ["git-script", "—", "—", "—"],
                    ],
                    interactive=False,
                    label="Verification Test Results",
                )
                availability_status = gr.Markdown()

                def _bool_mark(ok: bool) -> str:
                    return "✅" if ok else "—"

                def run_option_checks(selected_browser_type: str, rec_path: str):
                    """Execute comprehensive option availability verification tests."""
                    import asyncio
                    import tempfile
                    import shutil
                    from pathlib import Path

                    async def execute_test():
                        results = {}

                        # Initialize test environment
                        try:
                            from src.modules.yaml_parser import InstructionLoader
                            from src.browser.browser_config import BrowserConfig
                            from src.browser.browser_manager import prepare_recording_path
                            from src.agent.agent_manager import evaluate_prompt_unified, run_script

                            # Load actions
                            loader = InstructionLoader(local_path=os.path.join(os.path.dirname(__file__), "llms.txt"))
                            res = loader.load_instructions()

                            if not res.success:
                                return {
                                    "script": {
                                        "chrome": "❌",
                                        "profile": "❌",
                                        "recording": "❌",
                                        "error": "Failed to load actions",
                                    },
                                    "browser-control": {
                                        "chrome": "❌",
                                        "profile": "❌",
                                        "recording": "❌",
                                        "error": "Failed to load actions",
                                    },
                                    "git-script": {
                                        "chrome": "❌",
                                        "profile": "❌",
                                        "recording": "❌",
                                        "error": "Failed to load actions",
                                    },
                                }

                            actions_by_type = {}
                            for action in res.instructions:
                                t = action.get("type")
                                if t not in actions_by_type:
                                    actions_by_type[t] = []
                                actions_by_type[t].append(action)

                            # Test each action type with actual command execution
                            prompts = {
                                "script": "@script-nogtips query=Script",
                                "browser-control": "@search-nogtips query=Browser-Control",
                                "git-script": "@site-defined-script query=git",
                            }

                            for action_type in ["script", "browser-control", "git-script"]:
                                results[action_type] = {"chrome": "—", "profile": "—", "recording": "—", "error": None}

                                # Prepare recording path
                                try:
                                    resolved_recording_path = prepare_recording_path(
                                        True, rec_path if rec_path and rec_path.strip() else None
                                    )
                                    if resolved_recording_path and os.path.exists(resolved_recording_path):
                                        results[action_type]["recording"] = "✅"
                                    else:
                                        results[action_type]["recording"] = "❌"
                                except Exception as e:
                                    results[action_type]["recording"] = "❌"
                                    results[action_type]["error"] = f"Recording path error: {str(e)}"

                                # Execute actual command using the same prompts as manual testing
                                prompt = prompts[action_type]
                                try:
                                    script_info = evaluate_prompt_unified(prompt)
                                    if script_info:
                                        result, script_path = await run_script(
                                            script_info["action_def"],
                                            script_info["params"],
                                            headless=False,  # Changed from True to match manual testing behavior
                                            save_recording_path=resolved_recording_path,
                                        )

                                        # Check execution success
                                        if "successfully" in result.lower() or "completed" in result.lower():
                                            results[action_type]["chrome"] = "✅"
                                            results[action_type]["profile"] = "🫥"  # Anonymous browser profile state
                                            results[action_type][
                                                "recording"
                                            ] = "✅"  # Assume recording saved if path prepared
                                        else:
                                            results[action_type]["chrome"] = "❌"
                                            results[action_type]["profile"] = "🫥"  # Anonymous browser profile state
                                            results[action_type]["recording"] = "❌"
                                            results[action_type]["error"] = result
                                    else:
                                        results[action_type]["chrome"] = "❌"
                                        results[action_type]["profile"] = "🫥"  # Anonymous browser profile state
                                        results[action_type]["recording"] = "❌"
                                        results[action_type]["error"] = "No script info found for prompt: " + prompt

                                except Exception as e:
                                    results[action_type]["chrome"] = "❌"
                                    results[action_type]["profile"] = "❌"
                                    results[action_type]["recording"] = "❌"
                                    results[action_type]["error"] = f"Execution error: {str(e)}"

                        except Exception as e:
                            # Global error
                            for action_type in ["script", "browser-control", "git-script"]:
                                results[action_type] = {
                                    "chrome": "❌",
                                    "profile": "❌",
                                    "recording": "❌",
                                    "error": f"Global error: {str(e)}",
                                }

                        return results

                    # Run async test execution
                    try:
                        test_results = asyncio.run(execute_test())
                    except Exception as e:
                        # Fallback for sync context
                        test_results = {
                            "script": {
                                "chrome": "❌",
                                "profile": "❌",
                                "recording": "❌",
                                "error": f"Async error: {str(e)}",
                            },
                            "browser-control": {
                                "chrome": "❌",
                                "profile": "❌",
                                "recording": "❌",
                                "error": f"Async error: {str(e)}",
                            },
                            "git-script": {
                                "chrome": "❌",
                                "profile": "❌",
                                "recording": "❌",
                                "error": f"Async error: {str(e)}",
                            },
                        }

                    # Format results for DataFrame
                    rows = []
                    status_messages = []

                    for action_type in ["script", "browser-control", "git-script"]:
                        result = test_results.get(
                            action_type, {"chrome": "❌", "profile": "❌", "recording": "❌", "error": "Unknown error"}
                        )
                        rows.append(
                            [
                                action_type,
                                result.get("chrome", "❌"),
                                result.get("profile", "❌"),
                                result.get("recording", "❌"),
                            ]
                        )

                        error = result.get("error")
                        if error:
                            status_messages.append(f"{action_type}: {error}")

                    status_text = "Test execution completed."
                    if status_messages:
                        status_text += "\n\nErrors:\n" + "\n".join(f"• {msg}" for msg in status_messages)
                    else:
                        status_text += "\n\nAll tests passed successfully! ✅"

                    # Add notification about anonymous browser profile state
                    status_text += "\n\n🫥 **Browser Profile Status**: All tests run in anonymous browser profile mode. User profile data is not utilized in verification tests."

                    return rows, status_text

                run_checks_btn = gr.Button("� Run Verification Tests", variant="primary")
                run_checks_btn.click(
                    fn=run_option_checks,
                    inputs=[selected_browser_for_check, recording_path_for_check],
                    outputs=[checks_table, availability_status],
                )

                gr.Markdown("### 追加: 安全なブラウザ起動プローブ（任意）")
                gr.Markdown("実際に起動を試す場合のみ使用します。失敗しても自動でフォールバックはしません。")
                with gr.Row():
                    probe_use_own = gr.Checkbox(label="既存のブラウザを使用", value=False)
                    probe_headless = gr.Checkbox(label="ヘッドレス", value=True)
                    probe_button = gr.Button("🚀 起動を試す (browser-control)")
                probe_result = gr.Textbox(label="起動結果", interactive=False)

                async def probe_initialize(use_own: bool, headless_flag: bool, browser_type_choice: str):
                    try:
                        res = await initialize_browser(
                            use_own_browser=use_own,
                            headless=headless_flag,
                            browser_type=browser_type_choice,
                            auto_fallback=False,
                        )
                        if isinstance(res, dict) and res.get("status") == "success":
                            return f"SUCCESS: {browser_type_choice} started"
                        return f"ERROR: {res}"
                    except Exception as e:
                        return f"EXCEPTION: {str(e)}"

                probe_button.click(
                    fn=probe_initialize,
                    inputs=[probe_use_own, probe_headless, selected_browser_for_check],
                    outputs=[probe_result],
                )

            # Issue #272: Feature Flag Admin UI
            with gr.TabItem("🎛️ Feature Flags", id="feature_flags_admin"):
                _ = create_feature_flag_admin_panel()  # Panel is integrated via Gradio context

            # Issue #277: Artifacts UI
            with gr.TabItem("📦 Artifacts", id="artifacts_admin"):
                _ = create_artifacts_panel()  # Panel is integrated via Gradio context

            with gr.TabItem("📊 Results", id=7):
                with gr.Group():
                    recording_display = gr.Textbox(label="Latest Recording Path", interactive=False)
                    gr.Markdown("### Results")
                    with gr.Row():
                        with gr.Column():
                            final_result_output = gr.Textbox(label="Final Result", lines=3, show_label=True)
                        with gr.Column():
                            errors_output = gr.Textbox(label="Errors", lines=3, show_label=True)
                    with gr.Row():
                        with gr.Column():
                            model_actions_output = gr.Textbox(label="Model Actions", lines=3, show_label=True)
                        with gr.Column():
                            model_thoughts_output = gr.Textbox(label="Model Thoughts", lines=3, show_label=True)
                    trace_file_path = gr.Textbox(
                        label="Trace File Path", placeholder="Path where trace file will be saved"
                    )
                    agent_history_path = gr.Textbox(
                        label="Agent History Path", placeholder="Path where agent history will be saved"
                    )

                    # Connect buttons to functions
                    stop_button.click(fn=stop_agent, inputs=[], outputs=[errors_output, stop_button, run_button])
                    run_button.click(
                        fn=run_with_stream,
                        inputs=[
                            agent_type,
                            llm_provider,
                            llm_model_name,
                            llm_num_ctx,
                            llm_temperature,
                            llm_base_url,
                            llm_api_key,
                            use_own_browser,
                            keep_browser_open,
                            headless,
                            disable_security,
                            window_w,
                            window_h,
                            save_recording_path,
                            save_agent_history_path,
                            save_trace_path,
                            enable_recording,
                            task,
                            add_infos,
                            max_steps,
                            use_vision,
                            max_actions_per_step,
                            tool_calling_method,
                            dev_mode,
                            maintain_browser_session,
                            tab_selection_strategy,
                            browser_type,  # Add browser_type parameter
                        ],
                        outputs=[
                            browser_view,
                            final_result_output,
                            errors_output,
                            model_actions_output,
                            model_thoughts_output,
                            recording_display,
                            trace_file_path,
                            agent_history_path,
                            stop_button,
                            run_button,
                        ],
                    )

            with gr.TabItem("🎥 Recordings", id=8):
                gr.Markdown("### 🎥 Browser Recording Playback")
                gr.Markdown("Select and play browser automation recordings")

                # Service-layer integrated recording functions (Issue #304/#305)
                # Constants for byte conversion
                BYTES_TO_MB = 1024 * 1024

                def update_recordings_list_with_service(recordings_path, limit=50, offset=0):
                    """Service-layer integrated update function with pagination support."""
                    try:
                        # Use service layer to fetch recordings
                        root_path = Path(recordings_path) if recordings_path else None
                        params = ListParams(root=root_path, limit=limit, offset=offset)
                        page = list_recordings_service(params)

                        if not page.items:
                            return (
                                gr.update(choices=[], value=None),
                                None,
                                f"No recordings found (limit={limit}, offset={offset})",
                            )

                        # Create display names with timestamps and run_id
                        display_choices = []
                        for item in page.items:
                            filename = os.path.basename(item.path)
                            try:
                                timestamp = datetime.fromtimestamp(item.modified_at).strftime("%Y-%m-%d %H:%M:%S")
                            except (ValueError, OSError, TypeError):
                                timestamp = "[invalid timestamp]"
                            run_id_label = f"[{item.run_id}]" if item.run_id else "[unknown]"
                            size_mb = item.size_bytes / BYTES_TO_MB
                            display_name = f"{run_id_label} {filename} ({timestamp}, {size_mb:.1f}MB)"
                            display_choices.append((display_name, item.path))

                        latest_recording = page.items[0].path if page.items else None
                        status_msg = (
                            f"Found {len(page.items)} recording(s) (showing {offset+1}-{offset+len(page.items)})"
                        )
                        if page.has_next:
                            status_msg += " • More available"

                        return gr.update(choices=display_choices, value=latest_recording), latest_recording, status_msg
                    except FileNotFoundError:
                        error_msg = "Recording directory not found. Please check the path configuration."
                        return gr.update(choices=[], value=None), None, error_msg
                    except Exception:
                        error_msg = "Error loading recordings. Please check logs for details."
                        return gr.update(choices=[], value=None), None, error_msg

                def update_recordings_list_legacy(recordings_path):
                    """Legacy flat directory listing (used when recursive flag is disabled)."""
                    try:
                        if not recordings_path:
                            recordings_path = str(create_or_get_recording_dir())

                        if not os.path.exists(recordings_path):
                            return gr.update(choices=[], value=None), None, f"Directory not found: {recordings_path}"

                        recordings = []
                        for ext in ["mp4", "MP4", "webm", "WEBM", "ogg", "OGG"]:
                            recordings.extend(Path(recordings_path).glob(f"*.{ext}"))

                        if not recordings:
                            return gr.update(choices=[], value=None), None, "No recordings found"

                        # Sort by modification time (newest first)
                        recordings.sort(key=os.path.getmtime, reverse=True)

                        # Create choices list
                        display_choices = []
                        for rec in recordings:
                            filename = rec.name
                            mtime = os.path.getmtime(rec)
                            timestamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                            display_name = f"{filename} ({timestamp})"
                            display_choices.append((display_name, str(rec)))

                        latest_recording = str(recordings[0]) if recordings else None
                        status_msg = f"Found {len(recordings)} recording(s) (flat mode)"

                        return gr.update(choices=display_choices, value=latest_recording), latest_recording, status_msg
                    except Exception as e:
                        error_msg = f"Error loading recordings: {str(e)}"
                        return gr.update(choices=[], value=None), None, error_msg

                def on_recording_select_html(selected_path):
                    """HTML-based recording display for LLM-disabled mode"""
                    if selected_path and os.path.exists(selected_path):
                        filename = os.path.basename(selected_path)
                        file_size = os.path.getsize(selected_path) / 1024 / 1024
                        html_content = f"""
                        <div style="text-align: center; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                            <h3>📹 Selected Recording: {filename}</h3>
                            <p><strong>File Path:</strong> {selected_path}</p>
                            <p><strong>File Size:</strong> {file_size:.2f} MB</p>
                            <p><em>To view the recording, please download the file and open it in your media player.</em></p>
                            <div style="margin-top: 15px;">
                                <button onclick="navigator.clipboard.writeText('{selected_path}')"
                                        style="padding: 10px 20px; margin: 5px; font-size: 14px; background: #007bff; color: white; border: none; border-radius: 5px; cursor: pointer;">
                                    📋 Copy Path
                                </button>
                                <p style="margin-top: 10px; font-size: 12px; color: #666;">
                                    💡 Tip: Copy the path and open it in Windows Explorer or your preferred media player
                                </p>
                            </div>
                        </div>
                        """
                        return html_content
                    return "<p>No recording selected</p>"

                def on_recording_select_video(selected_recording):
                    """Video-based recording display for LLM-enabled mode"""
                    if selected_recording and os.path.exists(selected_recording):
                        return selected_recording
                    return None

                # Check if recursive recordings feature is enabled
                recursive_enabled = FeatureFlags.is_enabled("artifacts.recursive_recordings_enabled")

                # Choose appropriate update function based on flag
                if recursive_enabled:
                    update_func = update_recordings_list_with_service
                else:
                    update_func = update_recordings_list_legacy

                # Conditional UI based on LLM availability
                if ENABLE_LLM and LLM_MODULES_AVAILABLE:
                    # LLM有効時: 元の動画再生可能なUI
                    with gr.Row():
                        with gr.Column(scale=3):
                            recordings_dropdown = gr.Dropdown(
                                label="Select Recording",
                                choices=[],
                                interactive=True,
                                info="Choose a recording to play",
                            )
                            refresh_button = gr.Button("🔄 Refresh Recordings", variant="secondary")
                            status_display = gr.Textbox(label="Status", interactive=False, lines=1)

                        with gr.Column(scale=1):
                            gr.Markdown("**Controls:**")
                            gr.Markdown("- Select recording from dropdown")
                            gr.Markdown("- Use video controls to play/pause")
                            gr.Markdown("- Right-click for more options")
                            if recursive_enabled:
                                gr.Markdown("🔄 **Recursive scan enabled**")

                    # Video Player for LLM-enabled mode
                    try:
                        video_player = gr.Video(label="Recording Player", height=500, show_label=True)

                        # Event handlers for LLM-enabled mode
                        recordings_dropdown.change(
                            fn=on_recording_select_video, inputs=[recordings_dropdown], outputs=[video_player]
                        )

                        refresh_button.click(
                            fn=update_func,
                            inputs=[save_recording_path],
                            outputs=[recordings_dropdown, video_player, status_display],
                        )

                        gr.Markdown("🎬 **LLM Mode**: Full video playback enabled")

                    except Exception as e:
                        # Fallback to HTML mode if Video component fails
                        gr.Markdown("⚠️ **Video component unavailable, using fallback mode**")
                        video_display = gr.HTML(value="<p>Select a recording to view</p>")

                        recordings_dropdown.change(
                            fn=on_recording_select_html, inputs=[recordings_dropdown], outputs=[video_display]
                        )

                        refresh_button.click(
                            fn=update_func,
                            inputs=[save_recording_path],
                            outputs=[recordings_dropdown, video_display, status_display],
                        )

                else:
                    # LLM無効時: 動画プレイヤ非表示、HTML表示のみ
                    recordings_dropdown = gr.Dropdown(label="Select Recording", choices=[], interactive=True)

                    refresh_button = gr.Button("🔄 Refresh Recordings")
                    status_display = gr.Textbox(
                        label="Status", value="Click refresh to load recordings", interactive=False
                    )

                    # HTML-based display (no video player when LLM is disabled)
                    video_display = gr.HTML(value="<p>Select a recording to view</p>")

                    # Event handlers for LLM-disabled mode
                    refresh_button.click(
                        fn=update_func,
                        inputs=[save_recording_path],
                        outputs=[recordings_dropdown, video_display, status_display],
                    )
                    recordings_dropdown.change(
                        fn=on_recording_select_html, inputs=[recordings_dropdown], outputs=[video_display]
                    )

                    mode_label = "Recursive" if recursive_enabled else "Flat"
                    gr.Markdown(
                        f"📁 **Minimal Mode** ({mode_label} scan): Recording file management (LLM disabled, video player hidden)"
                    )

            with gr.TabItem("🧐 Deep Research", id=6):
                research_task_input = gr.Textbox(
                    label="Research Task",
                    lines=5,
                    value="Compose a report on the use of Reinforcement Learning for training Large Language Models, encompassing its origins, current advancements, and future prospects, substantiated with examples of relevant models and techniques. The report should reflect original insights and analysis, moving beyond mere summarization of existing literature.",
                )
                with gr.Row():
                    max_search_iteration_input = gr.Number(label="Max Search Iteration", value=3, precision=0)
                    max_query_per_iter_input = gr.Number(label="Max Query per Iteration", value=1, precision=0)
                with gr.Row():
                    research_button = gr.Button("▶️ Run Deep Research", variant="primary", scale=2)
                    stop_research_button = gr.Button("⏹️ Stop", variant="stop", scale=1)
                markdown_output_display = gr.Markdown(label="Research Report")
                markdown_download_path = gr.Textbox(
                    label="Research Report Download Path", placeholder="Path where report will be saved"
                )

            with gr.TabItem("📊 Batch Processing", id=12):
                gr.Markdown("### 📊 CSV Batch Processing")
                gr.Markdown(
                    """
                Upload a CSV file to start batch processing. Drag and drop the file or click to browse.

                **Features:**
                - Drag & Drop CSV file upload
                - Automatic batch job creation
                - Real-time progress monitoring
                - Job status tracking
                """
                )

                with gr.Row():
                    csv_file_input = gr.File(
                        label="CSV File", file_types=[".csv"], file_count="single", elem_id="csv-upload"
                    )

                # Template selection + preview controls
                # Populate template choices from CommandHelper at startup
                try:
                    helper = CommandHelper()
                    _cmds = helper.get_all_commands()
                    _template_choices = [c.get("name") for c in _cmds if isinstance(c, dict) and c.get("name")]
                except Exception:
                    _template_choices = []

                with gr.Row():
                    template_job_dropdown = gr.Dropdown(
                        choices=_template_choices,
                        label="Template Job",
                        value=(_template_choices[0] if _template_choices else None),
                        info="Select the job template that will be applied to all CSV rows",
                    )
                    # Feature flag controlled: show CSV preview UI only when enabled
                    # For development/testing: enable CSV preview by default
                    csv_preview_enabled = FeatureFlags.get("feature.csv_preview", expected_type=bool, default=True)
                    preview_rows = gr.Slider(
                        minimum=1,
                        maximum=50,
                        value=10,
                        label="Preview rows",
                        info="How many top rows to show in the preview",
                        visible=csv_preview_enabled,
                    )
                    preview_button = gr.Button("🔎 Preview CSV", variant="secondary", visible=csv_preview_enabled)

                # Allow user to override detected unique/id column
                unique_col_dropdown = gr.Dropdown(
                    choices=[],
                    label="Unique ID Column (override)",
                    value=None,
                    info="Override the detected unique-id column (optional)",
                    visible=csv_preview_enabled,
                )

                preview_table = gr.DataFrame(
                    label="CSV Preview", value=[], interactive=False, visible=csv_preview_enabled
                )
                preview_status = gr.Markdown("", visible=csv_preview_enabled)
                confirm_preview = gr.Button(
                    "✅ Confirm Preview & Enable Start", variant="primary", visible=csv_preview_enabled
                )
                preview_confirmed = gr.State(False)

                with gr.Row():
                    start_batch_button = gr.Button("🚀 Start Batch Processing", variant="primary", scale=2)
                    stop_batch_button = gr.Button("⏹️ Stop Batch", variant="stop", scale=1)

                batch_status_output = gr.Textbox(label="Batch Status", lines=5, interactive=False)
                batch_progress_output = gr.Textbox(label="Progress", lines=3, interactive=False)
                # Optional feedback element for JS (errors / warnings)
                csv_feedback = gr.Markdown("", elem_id="csv-upload-feedback")

                # Batch processing functions
                current_batch_ref = {"batch_id": None}  # closure-based mutable reference

                async def start_batch_processing(csv_file, template_job, preview_ok):
                    """Start batch processing from uploaded CSV file and stream incremental progress lines.

                    This function creates the batch, yields an initial status, then runs
                    `engine.execute_batch_jobs` in the background while streaming progress
                    updates (appended lines) to the UI via an asyncio.Queue. When the
                    execution completes it yields the final manifest summary.
                    """
                    if csv_file is None:
                        yield "❌ No CSV file selected", "", ""
                        return

                    # Require preview confirmation before starting the batch
                    # Enforce preview confirmation only when the feature flag is enabled
                    try:
                        if FeatureFlags.get("feature.csv_preview", expected_type=bool, default=False):
                            if not preview_ok:
                                yield "❌ Please preview the CSV and confirm before starting the batch (use the Preview and Confirm buttons).", "", ""
                                return
                    except Exception:
                        # If feature flag retrieval fails, fall back to legacy behavior (do not block)
                        pass

                    try:
                        from src.batch.engine import BatchEngine
                        from src.runtime.run_context import RunContext

                        # Save uploaded file temporarily
                        import tempfile
                        import shutil
                        import os
                        import logging
                        import io
                        from pathlib import Path
                        import asyncio

                        def normalize_csv_input(csv_input):
                            """Normalize CSV input to bytes for file writing."""
                            if hasattr(csv_input, "read"):
                                # File-like object
                                return csv_input.read()
                            elif isinstance(csv_input, str):
                                # Path string
                                with open(csv_input, "rb") as f:
                                    return f.read()
                            elif hasattr(csv_input, "value"):
                                # NamedString (Gradio file upload)
                                return csv_input.value.encode("utf-8")
                            else:
                                raise ValueError(f"Unsupported CSV input type: {type(csv_input)}")

                        temp_csv_path = None
                        try:
                            with tempfile.NamedTemporaryFile(mode="wb", suffix=".csv", delete=False) as temp_file:
                                csv_bytes = normalize_csv_input(csv_file)
                                temp_file.write(csv_bytes)
                                temp_csv_path = temp_file.name

                            # Create run context and engine
                            run_context = RunContext.get()
                            engine = BatchEngine(run_context)

                            # Create batch jobs
                            manifest = engine.create_batch_jobs(temp_csv_path)
                            current_batch_ref["batch_id"] = manifest.batch_id

                            # Yield initial status
                            status_msg = f"""✅ Batch created successfully!

Batch ID: {manifest.batch_id}
Run ID: {manifest.run_id}
Total Jobs: {manifest.total_jobs}
CSV Path: {manifest.csv_path}
Jobs Directory: {run_context.artifact_dir('jobs')}
Manifest: {run_context.artifact_dir('batch')}/batch_manifest.json
"""
                            initial_progress = f"Jobs: 0/{manifest.total_jobs} completed"
                            yield status_msg, initial_progress, manifest.batch_id

                            # Prepare queue to stream progress lines and background task
                            queue: "asyncio.Queue[str]" = asyncio.Queue()
                            progress_lines = []  # appended lines

                            loop = asyncio.get_running_loop()

                            def progress_callback(completed_jobs, total_jobs):
                                """Called by BatchEngine after each job completion.

                                We push the progress line into an asyncio.Queue using
                                call_soon_threadsafe to be safe from other threads.
                                """
                                line = f"Jobs: {completed_jobs}/{total_jobs} completed"
                                try:
                                    loop.call_soon_threadsafe(queue.put_nowait, line)
                                except Exception as _:
                                    logging.getLogger(__name__).debug("Failed to enqueue progress line")

                            # Launch execution in background so we can stream progress
                            exec_task = asyncio.create_task(
                                engine.execute_batch_jobs(manifest.batch_id, progress_callback=progress_callback)
                            )

                            # Stream progress lines as they arrive
                            try:
                                while True:
                                    # Drain available items promptly, but also exit when task done
                                    try:
                                        line = await asyncio.wait_for(queue.get(), timeout=0.5)
                                    except asyncio.TimeoutError:
                                        # If execution finished and queue is empty, break
                                        if exec_task.done() and queue.empty():
                                            break
                                        continue

                                    progress_lines.append(line)
                                    # Append all lines joined by newline so UI shows history
                                    progress_text = "\n".join(progress_lines)
                                    # Provide short status message while running
                                    running_status = f"⏳ Processing batch {manifest.batch_id}..."
                                    yield running_status, progress_text, manifest.batch_id

                                # Wait for execution to finish (propagate errors)
                                exec_result = await exec_task

                            except Exception as e:
                                # If exec_task raised, propagate an error to UI
                                logging.getLogger(__name__).exception("Batch execution error")
                                error_msg = f"❌ Batch execution error: {e}"
                                yield error_msg, "", manifest.batch_id
                                return

                            # Reload manifest to get final status
                            updated_manifest = engine._load_manifest_by_batch_id(manifest.batch_id)
                            if updated_manifest:
                                manifest = updated_manifest

                            # Ensure final progress line present
                            final_line = f"Jobs: {manifest.completed_jobs}/{manifest.total_jobs} completed"
                            if not progress_lines or progress_lines[-1] != final_line:
                                progress_lines.append(final_line)

                            final_progress_text = "\n".join(progress_lines)

                            final_status = f"""✅ Batch execution completed!

Batch ID: {manifest.batch_id}
Run ID: {manifest.run_id}
Total Jobs: {manifest.total_jobs}
Completed: {manifest.completed_jobs}
Failed: {manifest.failed_jobs}
CSV Path: {manifest.csv_path}
Jobs Directory: {run_context.artifact_dir('jobs')}
Manifest: {run_context.artifact_dir('batch')}/batch_manifest.json
"""
                            yield final_status, final_progress_text, manifest.batch_id

                        finally:
                            if temp_csv_path and os.path.exists(temp_csv_path):
                                try:
                                    os.remove(temp_csv_path)
                                except Exception as cleanup_exc:  # noqa: BLE001
                                    logging.getLogger(__name__).warning(
                                        f"Failed to clean up temp file {temp_csv_path}: {cleanup_exc}"
                                    )

                    except Exception as e:
                        import traceback

                        error_msg = f"❌ Error starting batch: {str(e)}\n{traceback.format_exc()}"
                        yield error_msg, "", ""

                def stop_batch_processing():
                    """Stop current batch processing."""
                    try:
                        from src.batch.engine import BatchEngine
                        from src.runtime.run_context import RunContext
                        import logging

                        run_context = RunContext.get()
                        engine = BatchEngine(run_context)
                        batch_id = current_batch_ref.get("batch_id")
                        if not batch_id:
                            return "ℹ️ No active batch to stop", "", ""
                        result = engine.stop_batch(batch_id)
                        status = (
                            f"🛑 Batch stopped. Batch ID: {batch_id}\n"
                            f"Stopped Jobs: {result['stopped_jobs']} / {result['total_jobs']}"
                        )
                        return status, "", batch_id

                    except Exception as e:
                        return f"❌ Error stopping batch: {str(e)}", "", current_batch_ref.get("batch_id") or ""

                # Wire start button: if feature flag disabled, pass False for preview_confirmed
                if FeatureFlags.get("feature.csv_preview", expected_type=bool, default=True):
                    start_batch_button.click(
                        fn=start_batch_processing,
                        inputs=[csv_file_input, template_job_dropdown, preview_confirmed],
                        outputs=[
                            batch_status_output,
                            batch_progress_output,
                            gr.State(),
                        ],  # third value: batch_id (ephemeral)
                    )
                else:
                    # Legacy: no preview gating
                    def _false_state():
                        return False

                    start_batch_button.click(
                        fn=start_batch_processing,
                        inputs=[csv_file_input, template_job_dropdown, gr.State(False)],
                        outputs=[batch_status_output, batch_progress_output, gr.State()],
                    )

                stop_batch_button.click(
                    fn=stop_batch_processing,
                    inputs=[],
                    outputs=[batch_status_output, batch_progress_output, gr.State()],
                )

                # CSV preview handler
                # Use centralized CSV parsing utility for robust encoding handling
                from src.batch.csv_utils import parse_csv_preview

                def _read_uploaded_bytes(csv_file) -> bytes | None:
                    # Normalize various Gradio upload types to raw bytes
                    try:
                        if csv_file is None:
                            return None
                        if hasattr(csv_file, "read"):
                            try:
                                return csv_file.read()
                            except Exception:
                                # Some Gradio versions give a tempfile-like object with .name
                                try:
                                    with open(csv_file.name, "rb") as f:
                                        return f.read()
                                except Exception:
                                    return None
                        if isinstance(csv_file, str) and os.path.exists(csv_file):
                            with open(csv_file, "rb") as f:
                                return f.read()
                        if hasattr(csv_file, "value"):
                            return csv_file.value.encode("utf-8")
                    except Exception:
                        return None
                    return None

                def _detect_unique_candidate(headers, rows):
                    """Heuristic: find a header whose values are unique among the sampled rows and looks like an id."""
                    if not headers or not rows:
                        return None
                    # Candidate names commonly used for unique ids
                    common_candidates = [
                        "id",
                        "ID",
                        "Id",
                        "email",
                        "email_address",
                        "emailAddress",
                        "uuid",
                        "user_id",
                        "username",
                        "user",
                    ]
                    # Prefer common names that exist
                    for cand in common_candidates:
                        if cand in headers:
                            return cand

                    # Otherwise, check which column has unique values across the sample
                    for h in headers:
                        vals = [r.get(h) for r in rows if r.get(h) not in (None, "")]
                        if not vals:
                            continue
                        if len(set(vals)) == len(vals):
                            return h
                    return None

                from src.batch.preview import build_preview_from_bytes

                def preview_csv_fn(csv_file, n_rows, template_job_name, unique_override=None):
                    """Wrapper that adapts build_preview_from_bytes to Gradio update tuples."""
                    file_bytes = _read_uploaded_bytes(csv_file)
                    if file_bytes is None:
                        return (
                            gr.update(value=[], headers=[]),
                            "❌ No CSV file selected or failed to read",
                            gr.update(choices=[], value=None),
                        )

                    try:
                        display_rows, display_headers, status_msg, header_choices, selected_value = (
                            build_preview_from_bytes(file_bytes, n_rows, template_job_name, unique_override)
                        )
                    except Exception as e:
                        return (
                            gr.update(value=[], headers=[]),
                            f"❌ Failed to parse CSV: {e}",
                            gr.update(choices=[], value=None),
                        )

                    return (
                        gr.update(value=display_rows, headers=display_headers),
                        status_msg,
                        gr.update(choices=header_choices, value=selected_value),
                    )

                # Only wire preview handler when feature enabled
                if FeatureFlags.get("feature.csv_preview", expected_type=bool, default=True):
                    # Central wrapper that also resets preview confirmation when inputs change
                    def _preview_and_reset(csv_file, n_rows, template_job_name, unique_override):
                        # Reset confirmation when the CSV or template or preview size changes
                        try:
                            rows, status, dropdown_upd = preview_csv_fn(
                                csv_file, n_rows, template_job_name, unique_override
                            )
                            return rows, status, dropdown_upd, False
                        except Exception as e:  # noqa: BLE001
                            return [], f"❌ Preview error: {e}", gr.update(choices=[], value=None), False

                    # Manual preview button
                    preview_button.click(
                        fn=preview_csv_fn,
                        inputs=[csv_file_input, preview_rows, template_job_dropdown, unique_col_dropdown],
                        outputs=[preview_table, preview_status, unique_col_dropdown],
                    )

                    # Auto-preview: when file, template, preview-size, or override changes, run preview and reset confirmation
                    csv_file_input.change(
                        fn=_preview_and_reset,
                        inputs=[csv_file_input, preview_rows, template_job_dropdown, unique_col_dropdown],
                        outputs=[preview_table, preview_status, unique_col_dropdown, preview_confirmed],
                    )
                    template_job_dropdown.change(
                        fn=_preview_and_reset,
                        inputs=[csv_file_input, preview_rows, template_job_dropdown, unique_col_dropdown],
                        outputs=[preview_table, preview_status, unique_col_dropdown, preview_confirmed],
                    )
                    preview_rows.change(
                        fn=_preview_and_reset,
                        inputs=[csv_file_input, preview_rows, template_job_dropdown, unique_col_dropdown],
                        outputs=[preview_table, preview_status, unique_col_dropdown, preview_confirmed],
                    )
                    unique_col_dropdown.change(
                        fn=_preview_and_reset,
                        inputs=[csv_file_input, preview_rows, template_job_dropdown, unique_col_dropdown],
                        outputs=[preview_table, preview_status, unique_col_dropdown, preview_confirmed],
                    )

                # Only wire confirm action when feature enabled
                if FeatureFlags.get("feature.csv_preview", expected_type=bool, default=False):

                    def confirm_preview_fn(_):
                        return True, "✅ Preview confirmed. You may now start the batch."

                    confirm_preview.click(
                        fn=confirm_preview_fn, inputs=[preview_table], outputs=[preview_confirmed, preview_status]
                    )

        llm_provider.change(
            lambda provider, api_key, base_url: update_model_dropdown(provider, api_key, base_url),
            inputs=[llm_provider, llm_api_key, llm_base_url],
            outputs=llm_model_name,
        )
        enable_recording.change(
            lambda enabled: gr.update(interactive=enabled), inputs=enable_recording, outputs=save_recording_path
        )
        use_own_browser.change(fn=close_global_browser)
        keep_browser_open.change(fn=close_global_browser)

        # JavaScriptファイル読み込み部分を強化
        try:
            # コマンドデータ取得を強化
            helper = CommandHelper()
            commands_json = helper.get_all_commands()

            # デバッグ出力を追加
            print(f"コマンドデータ取得: {len(commands_json)}件")
            for cmd in commands_json[:3]:  # 最初の3つだけ表示
                print(f"  - {cmd.get('name', 'No name')}: {cmd.get('description', 'No description')}")

            # JSONシリアライズを例外処理でラップ
            try:
                commands_json_str = json.dumps(commands_json)
                print(f"JSONシリアライズ成功: {len(commands_json_str)}バイト")
            except Exception as json_err:
                print(f"JSONシリアライズエラー: {json_err}")
                commands_json_str = "[]"  # 空の配列をフォールバックとして使用

            # HTMLとJavaScriptを結合
            combined_html = f"""
            <script>
            // コマンドデータをグローバル変数として設定
            console.log("コマンドデータを埋め込みます");
            window.embeddedCommands = {commands_json_str};
            console.log("埋め込みコマンド数:", window.embeddedCommands ? window.embeddedCommands.length : 0);

            // コマンドサジェスト機能クラス
            class CommandSuggest {{
                constructor() {{
                    this.commands = window.embeddedCommands || [];
                    this.initialized = false;
                    this.suggestionsContainer = null;
                    this.activeTextarea = null;
                    console.log("CommandSuggest初期化:", this.commands.length + "個のコマンド");
                    this.initialize();
                }}

                initialize() {{
                    // テキストエリアを検索
                    setTimeout(() => this.findTextArea(), 1000);
                }}

                findTextArea() {{
                    const textareas = document.querySelectorAll('textarea[placeholder*="task" i], textarea[placeholder*="description" i]');
                    if (textareas.length > 0) {{
                        this.activeTextarea = textareas[0];
                        console.log("テキストエリアを検出:", this.activeTextarea);
                        this.setupListeners();
                        this.createSuggestionsContainer();
                        this.initialized = true;
                    }} else {{
                        console.log("テキストエリアが見つかりません。再試行します...");
                        setTimeout(() => this.findTextArea(), 1000);
                    }}
                }}

                setupListeners() {{
                    // テキストエリアにイベントリスナーを設定
                    this.activeTextarea.addEventListener('input', (e) => this.handleInput(e));
                    this.activeTextarea.addEventListener('keydown', (e) => this.handleKeydown(e));
                }}

                createSuggestionsContainer() {{
                    // コマンド候補表示用のコンテナを作成
                    this.suggestionsContainer = document.createElement('div');
                    this.suggestionsContainer.className = 'command-suggestions';
                    this.suggestionsContainer.style.position = 'absolute';
                    this.suggestionsContainer.style.zIndex = '9999';
                    this.suggestionsContainer.style.backgroundColor = 'white';
                    this.suggestionsContainer.style.border = '1px solid #ddd';
                    this.suggestionsContainer.style.borderRadius = '4px';
                    this.suggestionsContainer.style.boxShadow = '0 2px 8px rgba(0,0,0,0.15)';
                    this.suggestionsContainer.style.maxHeight = '200px';
                    this.suggestionsContainer.style.overflow = 'auto';
                    this.suggestionsContainer.style.width = 'auto';
                    this.suggestionsContainer.style.minWidth = '300px';
                    this.suggestionsContainer.style.display = 'none';
                    document.body.appendChild(this.suggestionsContainer);
                }}

                handleInput(e) {{
                    const text = e.target.value;
                    const cursorPos = e.target.selectionStart;

                    // @または/の入力を検出
                    const lastAtPos = text.lastIndexOf('@', cursorPos - 1);
                    const lastSlashPos = text.lastIndexOf('/', cursorPos - 1);

                    const triggerPos = Math.max(lastAtPos, lastSlashPos);

                    if (triggerPos !== -1 && triggerPos < cursorPos) {{
                        const commandPart = text.substring(triggerPos + 1, cursorPos);

                        // スペースがなければコマンド入力中と判断
                        if (!commandPart.includes(' ') && !commandPart.includes('\\n')) {{
                            this.showSuggestions(commandPart, triggerPos);
                            return;
                        }}
                    }}

                    // サジェストを非表示
                    if (this.suggestionsContainer) {{
                        this.suggestionsContainer.style.display = 'none';
                    }}
                }}

                showSuggestions(inputText, triggerPos) {{
                    // コマンド候補をフィルタリング
                    const filtered = this.commands.filter(cmd =>
                        cmd.name.toLowerCase().startsWith(inputText.toLowerCase())
                    );

                    // 結果がなければ非表示
                    if (filtered.length === 0) {{
                        this.suggestionsContainer.style.display = 'none';
                        return;
                    }}

                    // 位置調整
                    const rect = this.activeTextarea.getBoundingClientRect();
                    this.suggestionsContainer.style.top = `${{rect.bottom + window.scrollY}}px`;
                    this.suggestionsContainer.style.left = `${{rect.left + window.scrollX}}px`;

                    // サジェスト項目の生成
                    this.suggestionsContainer.innerHTML = '';
                    filtered.forEach(cmd => {{
                        const item = document.createElement('div');
                        item.className = 'suggestion-item';
                        item.dataset.command = cmd.name;
                        item.style.padding = '8px 12px';
                        item.style.cursor = 'pointer';

                        const nameSpan = document.createElement('span');
                        nameSpan.textContent = cmd.name;
                        nameSpan.style.fontWeight = 'bold';
                        item.appendChild(nameSpan);

                        if (cmd.description) {{
                            const descSpan = document.createElement('span');
                            descSpan.style.color = '#666';
                            descSpan.style.marginLeft = '10px';
                            descSpan.textContent = cmd.description;
                        }}

                        // クリックイベント
                        item.addEventListener('click', () => {{
                            this.insertCommand(cmd, triggerPos);
                        }});

                        this.suggestionsContainer.appendChild(item);
                    }});

                    // 表示
                    this.suggestionsContainer.style.display = 'block';
                }}

                handleKeydown(e) {{
                    // キーボード操作の処理
                    if (this.suggestionsContainer && this.suggestionsContainer.style.display === 'block') {{
                        const items = this.suggestionsContainer.querySelectorAll('.suggestion-item');
                        let activeItem = this.suggestionsContainer.querySelector('.suggestion-item.active');

                        switch(e.key) {{
                            case 'Enter':
                                if (activeItem) {{
                                    e.preventDefault();
                                    const cmdName = activeItem.dataset.command;
                                    const cmd = this.commands.find(c => c.name === cmdName);
                                    if (cmd) {{
                                        this.insertCommand(cmd, parseInt(this.activeTextarea.dataset.triggerPos));
                                    }}
                                }}
                                break;
                            case 'Escape':
                                this.suggestionsContainer.style.display = 'none';
                                break;
                        }}
                    }}
                }}

                insertCommand(cmd, triggerPos) {{
                    // コマンドを挿入
                    const textarea = this.activeTextarea;
                    const text = textarea.value;

                    let newText = text.substring(0, triggerPos + 1) + cmd.name;

                    // 必須パラメータがあれば追加
                    if (cmd.params && cmd.params.length > 0) {{
                        const requiredParams = cmd.params.filter(p => p.required);
                        if (requiredParams.length > 0) {{
                            newText += ' ' + requiredParams.map(p => `${{p.name}}=`).join(' ');
                        }}
                    }}

                    // カーソル以降のテキスト
                    newText += text.substring(textarea.selectionStart);

                    textarea.value = newText;
                    textarea.focus();

                    // サジェスト非表示
                    this.suggestionsContainer.style.display = 'none';
                }}

                showDebugInfo() {{
                    console.log("=== コマンドサジェスト状態 ===");
                    console.log("初期化完了:", this.initialized);
                    console.log("コマンド数:", this.commands.length);
                    if (this.commands.length > 0) {{
                        console.log("コマンド例:", this.commands[0]);
                    }}
                    console.log("テキストエリア:", this.activeTextarea ? "検出済み" : "未検出");
                    console.log("サジェストコンテナ:", this.suggestionsContainer ? "作成済み" : "未作成");
                    console.log("========================");
                }}
            }}

            // ページ読み込み完了時に初期化
            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    console.log("CommandSuggest初期化を開始");
                    window.CommandSuggest = new CommandSuggest();
                    window.commandSuggestLoaded = true;
                }}, 1000);
            }});

            // CSV Upload Drag & Drop functionality
            class CSVUploadHandler {{
                constructor() {{
                    this.dropZone = null;
                    this.fileInput = null;
                    this.initialize();
                }}

                initialize() {{
                    // Wait for DOM to be ready
                    if (document.readyState === 'loading') {{
                        document.addEventListener('DOMContentLoaded', () => this.setup());
                    }} else {{
                        this.setup();
                    }}
                }}

                setup() {{
                    // Find the CSV upload element
                    this.dropZone = document.getElementById('csv-upload');
                    if (!this.dropZone) {{
                        console.log('CSV upload element not found, retrying...');
                        setTimeout(() => this.setup(), 1000);
                        return;
                    }}

                    // Find the actual file input within the drop zone
                    this.fileInput = this.dropZone.querySelector('input[type="file"]');
                    if (!this.fileInput) {{
                        console.log('File input not found within CSV upload element');
                        return;
                    }}

                    this.setupDragAndDrop();
                    console.log('CSV Upload Handler initialized');
                }}

                setupDragAndDrop() {{
                    // Prevent default drag behaviors
                    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {{
                        this.dropZone.addEventListener(eventName, this.preventDefaults, false);
                        document.body.addEventListener(eventName, this.preventDefaults, false);
                    }});

                    // Highlight drop zone when item is dragged over it
                    ['dragenter', 'dragover'].forEach(eventName => {{
                        this.dropZone.addEventListener(eventName, this.highlight, false);
                    }});

                    ['dragleave', 'drop'].forEach(eventName => {{
                        this.dropZone.addEventListener(eventName, this.unhighlight, false);
                    }});

                    // Handle dropped files
                    this.dropZone.addEventListener('drop', this.handleDrop.bind(this), false);
                }}

                preventDefaults(e) {{
                    e.preventDefault();
                    e.stopPropagation();
                }}

                highlight(e) {{
                    const dropZone = e.target.closest('#csv-upload');
                    if (dropZone) {{
                        dropZone.style.borderColor = '#007bff';
                        dropZone.style.backgroundColor = '#f8f9ff';
                    }}
                }}

                unhighlight(e) {{
                    const dropZone = e.target.closest('#csv-upload');
                    if (dropZone) {{
                        dropZone.style.borderColor = '#ddd';
                        dropZone.style.backgroundColor = '';
                    }}
                }}

                handleDrop(e) {{
                    const dt = e.dataTransfer;
                    const files = dt.files;

                    this.handleFiles(files);
                }}

                handleFiles(files) {{
                    const feedbackEl = document.getElementById('csv-upload-feedback');
                    const emitFeedback = (msg, level='info') => {{
                        if (feedbackEl) {{
                            feedbackEl.textContent = msg;
                            feedbackEl.dataset.level = level;
                        }}
                        console[level === 'error' ? 'error' : 'log'](msg);
                        const evt = new CustomEvent('csv-upload-feedback', {{ detail: {{ message: msg, level }} }});
                        window.dispatchEvent(evt);
                    }};

                    // Filter for CSV files only
                    const csvFiles = Array.from(files).filter(file => {{
                        return file.type === 'text/csv' ||
                               file.type === 'application/vnd.ms-excel' ||
                               file.name.toLowerCase().endsWith('.csv');
                    }});

                    if (csvFiles.length === 0) {{
                        emitFeedback('Please drop a CSV file (.csv)', 'error');
                        return;
                    }}

                    if (csvFiles.length > 1) {{
                        emitFeedback('Please drop only one CSV file at a time', 'error');
                        return;
                    }}

                    const file = csvFiles[0];

                    // Determine max size from data attribute if present (fallback 500MB)
                    if (!this.dropZone.dataset.maxSize) {{
                        this.dropZone.dataset.maxSize = String(500 * 1024 * 1024);
                    }}
                    const maxSize = parseInt(this.dropZone.dataset.maxSize, 10);
                    if (file.size > maxSize) {{
                        const maxMB = (maxSize / (1024 * 1024)).toFixed(0);
                        emitFeedback('File size too large. Maximum size is ' + maxMB + 'MB.', 'error');
                        return;
                    }}

                    // Create a DataTransfer object to set the file
                    const dt = new DataTransfer();
                    dt.items.add(file);
                    this.fileInput.files = dt.files;

                    // Trigger change event to notify Gradio
                    const event = new Event('change', {{ bubbles: true }});
                    this.fileInput.dispatchEvent(event);

                    emitFeedback('CSV file selected: ' + file.name, 'info');
                }}
            }}

            // Initialize CSV upload handler when page loads
            window.addEventListener('load', function() {{
                setTimeout(function() {{
                    window.csvUploadHandler = new CSVUploadHandler();
                }}, 1000);
            }});
            """

            # 結合したHTMLを埋め込み
            gr.HTML(combined_html)

        except Exception as e:
            import traceback

            print(f"JavaScriptファイル読み込みエラー: {e}")
            print(traceback.format_exc())
            gr.HTML(
                f"""
            <div style="color: red; padding: 10px; border: 1px solid red; margin: 10px 0;">
                <h3>JavaScript読み込みエラー</h3>
                <p>{str(e)}</p>
                <pre>{traceback.format_exc()}</pre>
            </div>
            """
            )

        # Add log display tab
        create_log_tab()

    return demo


# Import main function from CLI module
from src.cli.main import main

if __name__ == "__main__":
    main()
