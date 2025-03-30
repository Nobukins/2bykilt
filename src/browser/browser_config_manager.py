import os
from typing import Dict, Any, Optional

class BrowserConfigManager:
    """ブラウザ設定の統合管理クラス"""
    
    def __init__(self, gui_config: Optional[Dict[str, Any]] = None):
        """
        ブラウザ設定マネージャを初期化
        
        Args:
            gui_config: GUIから渡される設定辞書（オプション）
        """
        self.gui_config = gui_config or {}
        self.env_config = self._load_env_config()
        self.effective_config = self._merge_configs()
        
    def _load_env_config(self) -> Dict[str, Any]:
        """環境変数から設定を読み込む"""
        return {
            "chrome_path": os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
            "chrome_user_data": os.getenv("CHROME_USER_DATA", ""),
            "chrome_debugging_port": int(os.getenv("CHROME_DEBUGGING_PORT", "9222")),
            "chrome_debugging_host": os.getenv("CHROME_DEBUGGING_HOST", "localhost"),
            "chrome_persistent_session": os.getenv("CHROME_PERSISTENT_SESSION", "false").lower() == "true"
        }
    
    def _merge_configs(self) -> Dict[str, Any]:
        """GUIとENV設定を優先順位に基づいてマージ"""
        config = self.env_config.copy()
        
        # GUIの設定がある場合は環境変数より優先
        if self.gui_config:
            config.update(self.gui_config)
        
        return config
    
    def get_browser_config(self) -> Dict[str, Any]:
        """現在有効な設定を取得"""
        return self.effective_config
    
    def get_cdp_endpoint(self) -> str:
        """CDPエンドポイントURLを取得"""
        host = self.effective_config["chrome_debugging_host"]
        port = self.effective_config["chrome_debugging_port"]
        return f"http://{host}:{port}"
