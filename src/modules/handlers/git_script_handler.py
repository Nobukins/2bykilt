"""
Git Script Handler - Handles git-script type actions
"""

import logging
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)

async def handle_git_script(action: Dict[str, Any], params: Dict[str, Any], use_own_browser: bool = False, headless: bool = False) -> str:
    """
    Handle git-script type actions.

    Args:
        action: Action definition from llms.txt
        params: Parameters for the action
        use_own_browser: Whether to use existing browser session
        headless: Whether to run in headless mode

    Returns:
        str: Result message
    """
    try:
        logger.info(f"Handling git-script action: {action.get('name', 'unknown')}")

        # Import the git script executor
        from src.script.script_manager import execute_git_script_new_method

        # Prepare execution parameters
        browser_type = params.get('browser_type') or os.getenv('BYKILT_BROWSER_TYPE')
        execution_params = {
            'headless': headless,
            'save_recording_path': params.get('save_recording_path') or action.get('save_recording_path'),
            'browser_type': browser_type,
            **params  # Include all other parameters
        }

        # Execute the git script action
        result = await execute_git_script_new_method(
            action=action,
            **execution_params
        )

        logger.info(f"Git script action result: {result}")
        return result

    except Exception as e:
        error_msg = f"❌ Error in git script handler: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return error_msg