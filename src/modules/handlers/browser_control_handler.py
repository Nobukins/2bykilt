"""
Browser Control Handler - Handles browser-control type actions
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def handle_browser_control(action: Dict[str, Any], params: Dict[str, Any], use_own_browser: bool = False, headless: bool = False) -> str:
    """
    Handle browser-control type actions.

    Args:
        action: Action definition from llms.txt
        params: Parameters for the action
        use_own_browser: Whether to use existing browser session
        headless: Whether to run in headless mode

    Returns:
        str: Result message
    """
    try:
        logger.info(f"Handling browser-control action: {action.get('name', 'unknown')}")

        # Import the direct browser control executor
        from src.modules.direct_browser_control import execute_direct_browser_control

        # Prepare execution parameters
        execution_params = {
            'use_own_browser': use_own_browser,
            'headless': headless,
            'browser_type': params.get('browser_type'),
            **params  # Include all other parameters
        }

        # Add recording parameters from action if present
        if 'save_recording_path' in action:
            execution_params['save_recording_path'] = action['save_recording_path']
        if 'enable_recording' in action:
            execution_params['enable_recording'] = action['enable_recording']

        # Execute the browser control action
        success = await execute_direct_browser_control(action, **execution_params)

        if success:
            result_msg = f"✅ Browser control action '{action.get('name', 'unknown')}' executed successfully"
            logger.info(result_msg)
            return result_msg
        else:
            result_msg = f"❌ Browser control action '{action.get('name', 'unknown')}' failed"
            logger.error(result_msg)
            return result_msg

    except Exception as e:
        error_msg = f"❌ Error in browser control handler: {str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(traceback.format_exc())
        return error_msg