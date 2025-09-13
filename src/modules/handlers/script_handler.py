"""
Script Handler - Handles script type actions
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def handle_script(action: Dict[str, Any], params: Dict[str, Any], use_own_browser: bool = False, headless: bool = False) -> str:
    """
    Handle script type actions.

    Args:
        action: Action definition from llms.txt
        params: Parameters for the action
        use_own_browser: Whether to use existing browser session
        headless: Whether to run in headless mode

    Returns:
        str: Result message
    """
    try:
        logger.info(f"Handling script action: {action.get('name', 'unknown')}")

        # Import the script executor
        from src.script.script_manager import execute_script

        # Prepare execution parameters
        execution_params = {
            'headless': headless,
            'browser_type': params.get('browser_type'),
            'save_recording_path': params.get('save_recording_path'),
            **params  # Include all other parameters
        }

        # Execute the script action
        result_msg, _ = await execute_script(
            script_info=action,
            **execution_params
        )

        logger.info(f"Script action result: {result_msg}")
        return result_msg

    except Exception as e:
        error_msg = f"❌ Error in script handler: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return error_msg