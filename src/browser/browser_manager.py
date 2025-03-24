import os
import logging
from typing import Dict, Optional, Any

from src.utils.globals_manager import get_globals

# Configure logging
logger = logging.getLogger(__name__)

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

async def initialize_browser(use_own_browser, window_w, window_h):
    """Centralized browser initialization logic."""
    chrome_path = None
    extra_chromium_args = []

    if use_own_browser:
        chrome_path = os.getenv("CHROME_PATH", None)
        if chrome_path == "":
            chrome_path = None
        chrome_user_data = os.getenv("CHROME_USER_DATA", None)
        if chrome_user_data:
            extra_chromium_args += [f"--user-data-dir={chrome_user_data}"]

    browser = await p.chromium.launch(
        headless=False,
        executable_path=chrome_path,
        args=extra_chromium_args + [f"--window-size={window_w},{window_h}"]
    )
    return browser

def get_browser_configs(
    use_own_browser: bool, 
    window_w: int, 
    window_h: int
) -> Dict[str, Any]:
    """Generate browser configuration based on parameters"""
    extra_chromium_args = [f"--window-size={window_w},{window_h}"]
    
    chrome_path = None
    if use_own_browser:
        chrome_path = os.getenv("CHROME_PATH", "")
        if chrome_path == "":
            chrome_path = None
            
        chrome_user_data = os.getenv("CHROME_USER_DATA", None)
        if chrome_user_data:
            extra_chromium_args += [f"--user-data-dir={chrome_user_data}"]
    
    return {
        "chrome_path": chrome_path,
        "extra_chromium_args": extra_chromium_args
    }

def prepare_recording_path(enable_recording: bool, save_recording_path: Optional[str]) -> Optional[str]:
    """Prepare recording path based on settings"""
    if not enable_recording:
        return None
        
    if save_recording_path:
        os.makedirs(save_recording_path, exist_ok=True)
        return save_recording_path
        
    return None
