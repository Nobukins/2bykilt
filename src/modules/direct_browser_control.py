import asyncio
import logging
from typing import Dict, Any, List
import json
from src.browser.browser_debug_manager import BrowserDebugManager
from src.utils.debug_utils import DebugUtils

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
        elif action_type == "screenshot":
            cmd["action"] = "screenshot"
            cmd["args"] = [processed_step.get("path", "screenshot.png")]
        else:
            logger.warning(f"Unsupported action type: {action_type}")
            continue
        commands.append(cmd)
    return commands

async def execute_direct_browser_control(action: Dict[str, Any], **params) -> bool:
    """Execute browser control directly using modular components"""
    logger.info(f"Executing direct browser control for action: {action['name']}")
    try:
        flow = action.get('flow', [])
        use_own_browser = params.get('use_own_browser', False)
        headless = params.get('headless', False)
        
        # Convert flow to command format
        commands = await convert_flow_to_commands(flow, params)
        logger.info(f"Converted flow to {len(commands)} commands: {json.dumps(commands)}")
        
        # Use BrowserDebugManager and DebugUtils directly
        browser_manager = BrowserDebugManager()
        debug_utils = DebugUtils()
        debug_utils.browser_manager = browser_manager
        
        # Execute commands
        await execute_commands(commands, browser_manager, use_own_browser, headless)
        
        logger.info(f"Successfully executed direct browser control for action: {action['name']}")
        return True
    except Exception as e:
        logger.error(f"Error executing direct browser control: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

async def execute_commands(commands, browser_manager, use_own_browser=False, headless=False):
    """Execute a list of commands in the browser using BrowserDebugManager"""
    logger.info("\nExecuting commands:")
    for i, cmd in enumerate(commands, 1):
        logger.info(f" {i}. {cmd['action']}: {cmd.get('args', [])}")

    try:
        browser_data = await browser_manager.initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            logger.info("Using existing Chrome window to create a new tab")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # Create a new tab in the context
        page = await context.new_page()
        
        # Add element indexing for debugging
        debug_utils = DebugUtils()
        await debug_utils.setup_element_indexer(page)

        for cmd in commands:
            action = cmd["action"]
            args = cmd.get("args", [])
            logger.info(f"Executing: {action} {args}")

            if action == "go_to_url" and args:
                await page.goto(args[0], wait_until="domcontentloaded")
                try:
                    # Use a shorter timeout for networkidle to prevent long hangs
                    await page.wait_for_load_state("networkidle", timeout=10000)
                except Exception as e:
                    logger.warning(f"Network didn't reach idle state, but page is usable: {e}")
                    # Continue execution even if networkidle isn't reached
                logger.info(f"Navigated to: {args[0]}")
            elif action == "wait_for_navigation":
                await page.wait_for_load_state("networkidle")
                logger.info("Navigation completed")
            elif action == "input_text" and len(args) >= 2:
                selector, value = args[0], args[1]
                await page.fill(selector, value)
                logger.info(f"Filled form field '{selector}' with '{value}'")
            elif action == "click_element" and args:
                selector = args[0]
                await page.click(selector)
                logger.info(f"Clicked element '{selector}'")
            elif action == "keyboard_press" and args:
                key = args[0]
                await page.keyboard.press(key)
                logger.info(f"Pressed key '{key}'")
            elif action == "extract_content":
                selectors = args if args else ["h1", "h2", "h3", "p"]
                content = {}
                for selector in selectors:
                    elements = await page.query_selector_all(selector)
                    texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                    content[selector] = texts
                logger.info("\nExtracted content:")
                logger.info(json.dumps(content, indent=2))

            # Small delay between commands for stability
            await asyncio.sleep(1)

        # Close only the tab, keeping the browser open
        await page.close()
        
        # Only stop playwright if this was not a CDP connection
        if not browser_data.get("is_cdp", False):
            await browser_data["playwright"].stop()

    except Exception as e:
        logger.error(f"\nError executing commands: {e}")
        import traceback
        logger.error(traceback.format_exc())
