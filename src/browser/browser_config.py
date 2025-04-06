import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class BrowserConfig:
    """ブラウザ設定を管理するクラス（シングルトン）"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(BrowserConfig, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load browser configurations from environment variables."""
        return {
            "chrome": {
                "path": os.environ.get("CHROME_PATH", ""),
                "user_data": os.environ.get("CHROME_USER_DATA", ""),
                "debugging_port": int(os.environ.get("CHROME_DEBUGGING_PORT", "9222")),
                "disable_security": os.environ.get("CHROME_DISABLE_SECURITY", "false").lower() == "true",
            },
            "edge": {
                "path": os.environ.get("EDGE_PATH", ""),
                "user_data": os.environ.get("EDGE_USER_DATA", ""),
                "debugging_port": int(os.environ.get("EDGE_DEBUGGING_PORT", "9223")),
                "disable_security": os.environ.get("EDGE_DISABLE_SECURITY", "false").lower() == "true",
            },
            "current_browser": "chrome"  # Default browser
        }
    
    def _validate_browser_paths(self, config: Dict[str, Any], browser_name: str) -> None:
        """Validate browser paths and log details."""
        if not config["path"] or not os.path.exists(config["path"]):
            logger.warning(f"{browser_name} executable path not found: {config['path']}")
        
        if config["user_data"]:
            user_data_dir = config["user_data"]
            if os.path.exists(user_data_dir):
                logger.info(f"{browser_name} user data directory found: {user_data_dir}")
                logger.info(f"Using {browser_name} profile path directly: {user_data_dir}")
                if os.path.isdir(user_data_dir):
                    profiles = [d for d in os.listdir(user_data_dir) 
                                if os.path.isdir(os.path.join(user_data_dir, d)) and 
                                (d == "Default" or d.startswith("Profile"))]
                    if profiles:
                        logger.info(f"Available {browser_name} profiles: {', '.join(profiles)}")
            else:
                logger.warning(f"{browser_name} user data directory not found: {user_data_dir}")

    def get_browser_settings(self, browser_type: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve settings for the specified browser type."""
        browser_type = browser_type or self.config.get("current_browser", "chrome")
        if browser_type not in ["chrome", "edge"]:
            logger.warning(f"Unknown browser type: {browser_type}. Defaulting to Chrome.")
            browser_type = "chrome"
        return {**self.config[browser_type], "browser_type": browser_type}
    
    def log_current_browser_settings(self) -> None:
        """Log detailed settings of the currently selected browser."""
        browser_type = self.config.get("current_browser", "chrome")
        settings = self.get_browser_settings(browser_type)
        
        logger.info("=" * 50)
        logger.info(f"CURRENT BROWSER SETTINGS: {browser_type.upper()}")
        logger.info("-" * 50)
        logger.info(f"Executable Path: {settings['path']}")
        logger.info(f"User Data Path: {settings['user_data']}")
        logger.info(f"Debugging Port: {settings['debugging_port']}")
        logger.info(f"Disable Security: {settings['disable_security']}")
        logger.info("=" * 50)

    def set_current_browser(self, browser_type: str) -> None:
        """Set the current browser type and log changes."""
        if browser_type in ["chrome", "edge"]:
            previous_browser = self.config.get("current_browser", "chrome")
            if previous_browser != browser_type:
                self.config["current_browser"] = browser_type
                logger.info(f"Browser changed from {previous_browser} to {browser_type}")
                self.log_current_browser_settings()
            else:
                logger.info(f"Current browser is already set to {browser_type}")
        else:
            logger.error(f"Invalid browser type: {browser_type}")

    def change_browser(self, browser_type):
        """ブラウザタイプを変更して変更が確実に反映されたことを検証"""
        if browser_type in self.config["browsers"]:
            old_browser = self.config["current_browser"]
            self.config["current_browser"] = browser_type
            logger.info(f"Browser changed from {old_browser} to {browser_type}")
            
            # 変更が確実に反映されたことを検証
            actual_browser = self.config.get("current_browser")
            if actual_browser != browser_type:
                logger.error(f"⚠️ ブラウザ設定の反映に失敗！期待: {browser_type}, 実際: {actual_browser}")
                # 強制的に修正
                self.config["current_browser"] = browser_type
                logger.info(f"✅ ブラウザ設定を強制的に修正: {browser_type}")
            
            # 診断情報を記録
            from src.utils.browser_diagnostic import BrowserDiagnostic
            BrowserDiagnostic.capture_browser_state()
            
            self.log_current_browser_settings()
            return True
        else:
            logger.error(f"無効なブラウザタイプ: {browser_type}")
            return False

    def log_all_browser_states(self):
        """ブラウザ設定の全状態を詳細に記録"""
        global_instance = browser_config  # グローバルインスタンス
        new_instance = BrowserConfig()    # 新しいインスタンス
        
        logger.info("======================== ブラウザ設定状態 ========================")
        logger.info(f"グローバル設定: {global_instance.config.get('current_browser', 'undefined')}")
        logger.info(f"新規インスタンス: {new_instance.config.get('current_browser', 'undefined')}")
        logger.info(f"環境変数: CHROME_PATH={os.getenv('CHROME_PATH')}, EDGE_PATH={os.getenv('EDGE_PATH')}")
        logger.info("================================================================")
        
        return {
            "global": global_instance.config.get("current_browser"),
            "new": new_instance.config.get("current_browser"),
            "matching": global_instance.config.get("current_browser") == new_instance.config.get("current_browser")
        }
