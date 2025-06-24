import os
import json
from datetime import datetime
from src.utils.logger import Logger

logger = Logger.setup("browser_diagnostic")

class BrowserDiagnostic:
    """ブラウザ関連の診断情報を収集・保存するためのユーティリティ"""
    
    @staticmethod
    def capture_browser_state():
        """現在のブラウザ設定状態をキャプチャしてファイルに保存"""
        from src.browser.browser_config import BrowserConfig
        
        # 診断情報を収集
        browser_config = BrowserConfig()
        current_browser = browser_config.config.get("current_browser", "未設定")
        
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "browser_config": {
                "current_browser": current_browser,
                "browsers": browser_config.config.get("browsers", {})
            },
            "environment": {
                "CHROME_PATH": os.getenv("CHROME_PATH", "未設定"),
                "CHROME_USER_DATA": os.getenv("CHROME_USER_DATA", "未設定"),
                "CHROME_DEBUGGING_PORT": os.getenv("CHROME_DEBUGGING_PORT", "未設定"),
                "EDGE_PATH": os.getenv("EDGE_PATH", "未設定"),
                "EDGE_USER_DATA": os.getenv("EDGE_USER_DATA", "未設定"),
                "EDGE_DEBUGGING_PORT": os.getenv("EDGE_DEBUGGING_PORT", "未設定")
            }
        }
        
        # 診断情報を保存
        os.makedirs("logs", exist_ok=True)
        filename = f"logs/browser_state_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
        
        logger.info(f"ブラウザ状態診断情報を保存しました: {filename}")
        return filename
