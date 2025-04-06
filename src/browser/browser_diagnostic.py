import os
import json
import logging
from datetime import datetime
import platform
import sys
import subprocess

logger = logging.getLogger(__name__)

class BrowserDiagnostic:
    """ブラウザ関連の診断情報を収集・保存するためのユーティリティ"""
    
    @staticmethod
    def capture_browser_state(action_name="general", include_process_info=True):
        """現在のブラウザ設定状態をキャプチャしてファイルに保存"""
        from src.browser.browser_config import BrowserConfig
        
        # 診断情報を収集
        browser_config = BrowserConfig()
        current_browser = browser_config.config.get("current_browser", "未設定")
        
        # 実行中のブラウザプロセスの検出
        running_processes = {}
        if include_process_info and platform.system() in ["Darwin", "Linux"]:
            try:
                chrome_ps = subprocess.run(["pgrep", "-f", "Google Chrome"], capture_output=True, text=True)
                edge_ps = subprocess.run(["pgrep", "-f", "Microsoft Edge"], capture_output=True, text=True)
                
                running_processes = {
                    "chrome_running": len(chrome_ps.stdout.strip()) > 0,
                    "edge_running": len(edge_ps.stdout.strip()) > 0,
                    "chrome_pids": chrome_ps.stdout.strip().split("\n") if chrome_ps.stdout else [],
                    "edge_pids": edge_ps.stdout.strip().split("\n") if edge_ps.stdout else []
                }
            except Exception as e:
                logger.error(f"プロセス情報取得エラー: {e}")
                running_processes = {"error": str(e)}
        
        # 環境変数の取得
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "action": action_name,
            "system_info": {
                "os": platform.system(),
                "platform": platform.platform(),
                "python": sys.version
            },
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
            },
            "running_processes": running_processes
        }
        
        # 診断情報を保存
        os.makedirs("logs/browser_diagnostics", exist_ok=True)
        filename = f"logs/browser_diagnostics/browser_state_{action_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w") as f:
            json.dump(diagnostics, f, indent=2)
        
        logger.info(f"ブラウザ状態診断情報を保存しました: {filename}")
        return {"filename": filename, "diagnostic_data": diagnostics}
