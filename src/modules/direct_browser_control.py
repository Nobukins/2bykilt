import asyncio
import logging
from typing import Dict, Any, List
import json
import os
import tempfile
from src.utils.debug_utils import DebugUtils
from src.utils.git_script_automator import GitScriptAutomator
from src.utils.profile_manager import ProfileManager
from src.utils.browser_launcher import BrowserLauncher
from src.utils.timeout_manager import get_timeout_manager, TimeoutScope, TimeoutError, CancellationError, TimeoutManager

logger = logging.getLogger(__name__)

async def convert_flow_to_commands(flow: List[Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert YAML flow actions to commands format for direct execution"""
    commands = []
    for step in flow:
        action_type = step.get('action')
        processed_step = {}
        for key, value in step.items():
            if isinstance(value, str) and '{' in value:
                for param_name, param_value in params.items():
                    placeholder = f"${{params.{param_name}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(param_value))
            processed_step[key] = value

        cmd = {"action": None, "args": []}
        if action_type == "command" and "url" in processed_step:
            cmd["action"] = "go_to_url"
            cmd["args"] = [processed_step["url"]]
        elif action_type == "click":
            cmd["action"] = "click_element"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "fill_form":
            cmd["action"] = "input_text"
            cmd["args"] = [processed_step["selector"], processed_step["value"]]
        elif action_type == "keyboard_press":
            cmd["action"] = "keyboard_press"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "wait_for_navigation":
            cmd["action"] = "wait_for_navigation"
            cmd["args"] = []
        elif action_type == "wait_for":
            cmd["action"] = "wait_for_element"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "extract_text":
            cmd["action"] = "extract_content"
            cmd["args"] = [processed_step.get("selector", None)]
        elif action_type == "extract_content":
            cmd["action"] = "extract_content"
            cmd["args"] = []
        elif action_type == "screenshot":
            cmd["action"] = "screenshot"
            cmd["args"] = [processed_step.get("path", "screenshot.png")]
        else:
            logger.warning(f"Unsupported action type: {action_type}")
            continue
        commands.append(cmd)
    return commands

async def _execute_browser_operation_impl(action: Dict[str, Any], params: Dict[str, Any], timeout_manager: TimeoutManager) -> bool:
    """Execute the browser operation implementation"""
    flow = action.get('flow', [])
    slowmo = action.get('slowmo', 1000)

    # Get browser type from config if not provided
    browser_type = params.get('browser_type')
    if not browser_type:
        from src.browser.browser_config import BrowserConfig
        browser_config = BrowserConfig()
        browser_type = browser_config.get_current_browser()
        logger.info(f"🔍 Using browser type from config: {browser_type}")

    # Convert flow to command format
    commands = await convert_flow_to_commands(flow, params)
    logger.info(f"Converted flow to {len(commands)} commands: {json.dumps(commands)}")

    # Use new method: GitScriptAutomator with NEW_METHOD
    automator = GitScriptAutomator(browser_type)

    # Create a temporary workspace directory for the automator
    with tempfile.TemporaryDirectory() as temp_workspace:
        # Execute the commands using the browser context
        logger.info(f"🔍 Executing browser-control with NEW_METHOD, browser_type={browser_type}")

        # Initialize recording if enabled
        recording_context = None
        if params.get('save_recording_path') or params.get('enable_recording', True):
            from src.utils.recording_factory import RecordingFactory
            run_context = {
                'run_id': action.get('name', 'browser_control'),
                'run_type': 'browser-control',
                'save_recording_path': params.get('save_recording_path'),
                'enable_recording': params.get('enable_recording', True)
            }
            recording_context = RecordingFactory.init_recorder(run_context)

        # Use recording context if available
        if recording_context:
            async with recording_context:
                async with automator.browser_context(temp_workspace, headless=False, record_video_dir=str(recording_context.recording_path)) as context:
                    return await _execute_with_context(context, commands, timeout_manager, slowmo, action)
        else:
            async with automator.browser_context(temp_workspace, headless=False) as context:
                return await _execute_with_context(context, commands, timeout_manager, slowmo, action)

async def _execute_with_context(context, commands: List[Dict[str, Any]], timeout_manager: TimeoutManager, slowmo: int, action: Dict[str, Any]) -> bool:
    """
    Execute a sequence of browser commands within the provided browser context.

    Args:
        context: The browser context in which to execute the commands.
        commands (List[Dict[str, Any]]): A list of command dictionaries to execute.
        timeout_manager (TimeoutManager): The timeout manager to enforce timeouts and handle cancellations.
        slowmo (int): Delay in milliseconds between commands for debugging or throttling.
        action (Dict[str, Any]): The action dictionary containing metadata about the operation.

    Returns:
        bool: True if all commands were executed successfully, False otherwise.
    """
    page = await context.new_page()

    try:
        # Execute each command with timeout protection
        for cmd in commands:
            # Check for cancellation between commands
            if timeout_manager.is_cancelled():
                logger.warning(f"Browser control cancelled during command execution")
                return False

            cmd_action = cmd["action"]
            args = cmd.get("args", [])
            logger.info(f"Executing: {cmd_action} {args}")

            try:
                # Use network timeout for page operations
                if cmd_action == "go_to_url" and args:
                    await timeout_manager.apply_timeout_to_coro(
                        page.goto(args[0], wait_until="domcontentloaded"),
                        TimeoutScope.NETWORK
                    )
                    logger.info(f"Navigated to: {args[0]}")
                elif cmd_action == "wait_for_navigation":
                    try:
                        await timeout_manager.apply_timeout_to_coro(
                            page.wait_for_load_state("networkidle", timeout=15000),
                            TimeoutScope.NETWORK
                        )
                        logger.info("Navigation completed")
                    except Exception as e:
                        logger.warning(f"Navigation wait timed out, continuing: {e}")
                elif cmd_action == "input_text" and len(args) >= 2:
                    selector, value = args[0], args[1]
                    await timeout_manager.apply_timeout_to_coro(
                        page.wait_for_selector(selector, timeout=10000),
                        TimeoutScope.NETWORK
                    )
                    await timeout_manager.apply_timeout_to_coro(
                        page.fill(selector, value),
                        TimeoutScope.OPERATION
                    )
                    logger.info(f"Filled form field '{selector}' with '{value}'")
                elif cmd_action == "click_element" and args:
                    selector = args[0]
                    await timeout_manager.apply_timeout_to_coro(
                        page.wait_for_selector(selector, timeout=10000),
                        TimeoutScope.NETWORK
                    )
                    await timeout_manager.apply_timeout_to_coro(
                        page.click(selector),
                        TimeoutScope.OPERATION
                    )
                    logger.info(f"Clicked element '{selector}'")
                elif cmd_action == "keyboard_press" and args:
                    key = args[0]
                    await timeout_manager.apply_timeout_to_coro(
                        page.keyboard.press(key),
                        TimeoutScope.OPERATION
                    )
                    logger.info(f"Pressed key '{key}'")
                elif cmd_action == "extract_content":
                    selectors = args if args else ["h1", "h2", "h3", "p"]
                    content = {}
                    for selector in selectors:
                        try:
                            elements = await timeout_manager.apply_timeout_to_coro(
                                page.query_selector_all(selector),
                                TimeoutScope.NETWORK
                            )
                            texts = []
                            for element in elements:
                                text = await timeout_manager.apply_timeout_to_coro(
                                    element.text_content(),
                                    TimeoutScope.OPERATION
                                )
                                if text and text.strip():
                                    texts.append(text.strip())
                            content[selector] = texts
                        except Exception as e:
                            logger.warning(f"Failed to extract content for selector '{selector}': {e}")
                            content[selector] = []
                    logger.info("Extracted content:")
                    logger.info(json.dumps(content, indent=2, ensure_ascii=False))

                # Add slowmo delay with cancellation check
                if timeout_manager.is_cancelled():
                    logger.warning("Operation cancelled during slowmo delay")
                    return False
                await asyncio.sleep(slowmo / 1000.0)

            except TimeoutError as e:
                logger.error(f"Browser operation timed out: {cmd_action}")
                return False
            except CancellationError:
                logger.warning(f"Browser operation cancelled: {cmd_action}")
                return False

        # Close the page
        try:
            await page.close()
        except Exception as close_exc:
            logger.error(f"Error closing page after successful execution: {close_exc}")

        logger.info(f"Successfully executed direct browser control for action: {action['name']}")
        return True

    except Exception as e:
        logger.error(f"Error in browser context execution: {e}")
        try:
            await page.close()
        except Exception as close_exc:
            logger.error(f"Error closing page after exception: {close_exc}")
        raise

async def execute_direct_browser_control(action: Dict[str, Any], **params) -> bool:
    """Execute direct browser control with recording support"""
    logger.info(f"🔍 Executing direct browser control for action: {action['name']}")

    # Extract recording parameters from action or params
    recording_params = {
        'save_recording_path': action.get('save_recording_path') or params.get('save_recording_path'),
        'enable_recording': action.get('enable_recording', params.get('enable_recording', True)),
        'run_id': action.get('name', 'browser_control'),
        'run_type': 'browser-control'
    }

    # Merge recording params into the main params dict
    params.update(recording_params)

    # Create timeout manager
    timeout_manager = get_timeout_manager()

    try:
        # Execute the browser operation
        result = await _execute_browser_operation_impl(action, params, timeout_manager)

        if result:
            logger.info(f"✅ Successfully executed direct browser control for action: {action['name']}")
        else:
            logger.warning(f"⚠️ Browser control execution failed for action: {action['name']}")

        return result

    except Exception as e:
        logger.error(f"❌ Error executing direct browser control: {e}")
        raise
