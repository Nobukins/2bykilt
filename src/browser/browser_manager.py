import os
import logging
from typing import Dict, Optional, Any

from src.utils.globals_manager import get_globals
from src.browser.browser_config import BrowserConfig

# Configure logging
logger = logging.getLogger(__name__)

browser_config = BrowserConfig()

async def close_global_browser():
    """Close the global browser and browser context if they exist"""
    globals_dict = get_globals()
    browser_context = globals_dict["browser_context"]
    browser = globals_dict["browser"]
    
    if browser_context:
        await browser_context.close()
        logger.info("Closed browser context")
    
    if browser:
        await browser.close()
        logger.info("Closed browser")

def get_browser_configs(
    use_own_browser: bool, 
    window_w: int, 
    window_h: int,
    browser_type: str = "chrome"  # Add browser_type parameter with default
) -> Dict[str, Any]:
    """Generate browser configuration based on parameters"""
    extra_chromium_args = [f"--window-size={window_w},{window_h}"]
    
    browser_path = None
    browser_user_data = None
    
    if use_own_browser:
        # Use correct environment variables based on browser type
        if browser_type == "edge":
            browser_path = os.getenv("EDGE_PATH", "")
            browser_user_data = os.getenv("EDGE_USER_DATA", None)
            logger.info(f"Using Edge browser: {browser_path}")
        else:  # Default to Chrome
            browser_path = os.getenv("CHROME_PATH", "")
            browser_user_data = os.getenv("CHROME_USER_DATA", None)
            logger.info(f"Using Chrome browser: {browser_path}")
            
        if browser_path == "":
            browser_path = None
            
        if browser_user_data:
            extra_chromium_args += [f"--user-data-dir={browser_user_data}"]
    
    return {
        "browser_path": browser_path,  # Changed from chrome_path
        "extra_chromium_args": extra_chromium_args
    }

async def initialize_browser(use_own_browser, window_w, window_h, browser_type=None):
    """Centralized browser initialization logic with support for Chrome and Edge."""
    browser_configs = get_browser_configs(use_own_browser, window_w, window_h, browser_type)
    browser_path = browser_configs["browser_path"]
    extra_chromium_args = browser_configs["extra_chromium_args"]

    browser = await p.chromium.launch(
        headless=False,
        executable_path=browser_path,
        args=extra_chromium_args
    )
    return browser

def prepare_recording_path(enable_recording: bool, save_recording_path: Optional[str]) -> Optional[str]:
    """Prepare recording path based on settings"""
    if not enable_recording:
        return None
        
    if save_recording_path:
        os.makedirs(save_recording_path, exist_ok=True)
        return save_recording_path
        
    return None
