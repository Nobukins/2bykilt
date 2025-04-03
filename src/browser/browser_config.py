import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BrowserConfig:
    """Manage browser configurations for Chrome and Edge."""
    
    def __init__(self):
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load browser configurations from environment variables."""
        return {
            "chrome": {
                "path": os.environ.get("CHROME_PATH", ""),
                "user_data": os.environ.get("CHROME_USER_DATA", ""),
                "debugging_port": int(os.environ.get("CHROME_DEBUGGING_PORT", "9222")),
            },
            "edge": {
                "path": os.environ.get("EDGE_PATH", ""),
                "user_data": os.environ.get("EDGE_USER_DATA", ""),
                "debugging_port": int(os.environ.get("EDGE_DEBUGGING_PORT", "9223")),
            },
            "current_browser": "chrome"  # Default browser
        }
    
    def get_browser_settings(self, browser_type: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve settings for the specified browser type."""
        browser_type = browser_type or self.config.get("current_browser", "chrome")
        if browser_type not in ["chrome", "edge"]:
            logger.warning(f"Unknown browser type: {browser_type}. Defaulting to Chrome.")
            browser_type = "chrome"
        return {**self.config[browser_type], "browser_type": browser_type}
    
    def set_current_browser(self, browser_type: str) -> None:
        """Set the current browser type."""
        if browser_type in ["chrome", "edge"]:
            self.config["current_browser"] = browser_type
            logger.info(f"Current browser set to {browser_type}.")
        else:
            logger.error(f"Invalid browser type: {browser_type}")
