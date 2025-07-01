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
        """Load browser configurations from environment variables with auto-detection."""
        import platform
        
        def auto_detect_browser_path(browser_type: str) -> str:
            """Auto-detect browser path based on platform and browser type."""
            system = platform.system()
            
            if browser_type == "chrome":
                if system == "Windows":
                    possible_paths = [
                        os.path.expandvars(r"%PROGRAMFILES%\Google\Chrome\Application\chrome.exe"),
                        os.path.expandvars(r"%PROGRAMFILES(X86)%\Google\Chrome\Application\chrome.exe"),
                        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
                    ]
                elif system == "Darwin":  # macOS
                    possible_paths = [
                        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
                    ]
                else:  # Linux
                    possible_paths = [
                        "/usr/bin/google-chrome",
                        "/usr/bin/google-chrome-stable",
                        "/usr/bin/chromium-browser",
                        "/usr/bin/chromium",
                        "/snap/bin/chromium"
                    ]
            elif browser_type == "edge":
                if system == "Windows":
                    possible_paths = [
                        os.path.expandvars(r"%PROGRAMFILES(X86)%\Microsoft\Edge\Application\msedge.exe"),
                        os.path.expandvars(r"%PROGRAMFILES%\Microsoft\Edge\Application\msedge.exe"),
                    ]
                elif system == "Darwin":  # macOS
                    possible_paths = [
                        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
                    ]
                else:  # Linux
                    possible_paths = [
                        "/usr/bin/microsoft-edge",
                        "/usr/bin/microsoft-edge-stable",
                        "/opt/microsoft/msedge/msedge"
                    ]
            else:
                return ""
            
            for path in possible_paths:
                if os.path.exists(path):
                    logger.debug(f"🔍 {browser_type} パスを自動検出: {path}")
                    return path
            
            logger.warning(f"⚠️ {browser_type} の実行ファイルが見つかりません")
            return ""

        def auto_detect_user_data_path(browser_type: str) -> str:
            """Auto-detect browser user data path based on platform and browser type."""
            system = platform.system()
            
            if browser_type == "chrome":
                if system == "Windows":
                    return os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\User Data")
                elif system == "Darwin":  # macOS
                    return os.path.expanduser("~/Library/Application Support/Google/Chrome")
                else:  # Linux
                    return os.path.expanduser("~/.config/google-chrome")
            elif browser_type == "edge":
                if system == "Windows":
                    return os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data")
                elif system == "Darwin":  # macOS
                    return os.path.expanduser("~/Library/Application Support/Microsoft Edge")
                else:  # Linux
                    return os.path.expanduser("~/.config/microsoft-edge")
            
            return ""

        # 環境変数から取得、なければ自動検出
        chrome_path = os.environ.get("CHROME_PATH") or auto_detect_browser_path("chrome")
        edge_path = os.environ.get("EDGE_PATH") or auto_detect_browser_path("edge")
        chrome_user_data = os.environ.get("CHROME_USER_DATA") or auto_detect_user_data_path("chrome")
        edge_user_data = os.environ.get("EDGE_USER_DATA") or auto_detect_user_data_path("edge")

        return {
            "chrome": {
                "path": chrome_path,
                "user_data": chrome_user_data,
                "debugging_port": int(os.environ.get("CHROME_DEBUGGING_PORT", "9222")),
                "disable_security": os.environ.get("CHROME_DISABLE_SECURITY", "false").lower() == "true",
            },
            "edge": {
                "path": edge_path,
                "user_data": edge_user_data,
                "debugging_port": int(os.environ.get("EDGE_DEBUGGING_PORT", "9223")),
                "disable_security": os.environ.get("EDGE_DISABLE_SECURITY", "false").lower() == "true",
            },
            "current_browser": os.environ.get("DEFAULT_BROWSER", "chrome").lower()
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
        original_browser_type = browser_type
        browser_type = browser_type or self.config.get("current_browser", "chrome")
        
        logger.debug(f"🔍 get_browser_settings 呼び出し:")
        logger.debug(f"  - 要求されたbrowser_type: {original_browser_type}")
        logger.debug(f"  - 使用するbrowser_type: {browser_type}")
        logger.debug(f"  - current_browser設定: {self.config.get('current_browser', 'chrome')}")
        
        if browser_type not in ["chrome", "edge"]:
            logger.warning(f"Unknown browser type: {browser_type}. Defaulting to Chrome.")
            browser_type = "chrome"
            
        settings = {**self.config[browser_type], "browser_type": browser_type}
        logger.debug(f"🔍 返却する設定: {settings}")
        return settings
    
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
        logger.debug(f"🔍 set_current_browser 呼び出し - browser_type: {browser_type}")
        logger.debug(f"🔍 現在の設定: {self.config}")
        
        if browser_type in ["chrome", "edge"]:
            previous_browser = self.config.get("current_browser", "chrome")
            logger.debug(f"🔍 変更前のブラウザ: {previous_browser}")
            
            if previous_browser != browser_type:
                self.config["current_browser"] = browser_type
                logger.info(f"🔄 ブラウザ変更: {previous_browser} -> {browser_type}")
                logger.debug(f"🔍 変更後の設定: {self.config}")
                self.log_current_browser_settings()
            else:
                logger.info(f"ℹ️ ブラウザは既に {browser_type} に設定済み")
        else:
            logger.error(f"❌ 無効なブラウザタイプ: {browser_type}")
            logger.debug(f"🔍 有効なブラウザタイプ: ['chrome', 'edge']")

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
    
    def get_current_browser(self) -> str:
        """現在設定されているブラウザタイプを取得"""
        return self.config.get("current_browser", "chrome")
    
    def get_current_browser_path(self) -> str:
        """現在設定されているブラウザの実行ファイルパスを取得"""
        current_browser = self.get_current_browser()
        settings = self.get_browser_settings(current_browser)
        return settings.get("path", "")
    
    def is_browser_available(self, browser_type: str) -> bool:
        """指定されたブラウザが利用可能かチェック"""
        if browser_type not in ["chrome", "edge"]:
            return False
        
        settings = self.get_browser_settings(browser_type)
        browser_path = settings.get("path", "")
        
        return bool(browser_path and os.path.exists(browser_path))
    
    def get_available_browsers(self) -> list:
        """利用可能なブラウザのリストを取得"""
        available = []
        for browser_type in ["chrome", "edge"]:
            if self.is_browser_available(browser_type):
                available.append(browser_type)
        return available
    
    def validate_current_browser(self) -> bool:
        """現在設定されているブラウザが利用可能かチェックし、利用不可能な場合は自動フォールバック"""
        current_browser = self.get_current_browser()
        
        if self.is_browser_available(current_browser):
            logger.info(f"✅ 現在のブラウザ {current_browser} は利用可能です")
            return True
        
        logger.warning(f"⚠️ 現在のブラウザ {current_browser} が利用できません。フォールバックを開始...")
        
        # 利用可能なブラウザを探してフォールバック
        available_browsers = self.get_available_browsers()
        if available_browsers:
            fallback_browser = available_browsers[0]
            logger.info(f"🔄 {fallback_browser} にフォールバック")
            self.set_current_browser(fallback_browser)
            return True
        
        logger.error("❌ 利用可能なブラウザが見つかりません")
        return False

# グローバルシングルトンインスタンス
browser_config = BrowserConfig()
