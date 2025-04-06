import os
import json
import platform
import sys
from datetime import datetime
import psutil

from src.utils.logger import Logger

logger = Logger.setup("diagnostics")

class BrowserDiagnostics:
    @staticmethod
    def collect_browser_info():
        """ブラウザ関連の診断情報を収集"""
        from src.browser.browser_config import BrowserConfig
        
        browser_config = BrowserConfig()
        current_browser = browser_config.config.get("current_browser", "chrome")
        
        # 起動中のブラウザプロセスをチェック
        chrome_processes = []
        edge_processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                if 'chrome' in proc.info['name'].lower():
                    chrome_processes.append({
                        'pid': proc.info['pid'],
                        'cmdline': proc.info['cmdline']
                    })
                elif 'edge' in proc.info['name'].lower():
                    edge_processes.append({
                        'pid': proc.info['pid'], 
                        'cmdline': proc.info['cmdline']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # 環境変数の収集
        env_vars = {
            'CHROME_PATH': os.getenv('CHROME_PATH', '未設定'),
            'CHROME_USER_DATA': os.getenv('CHROME_USER_DATA', '未設定'),
            'CHROME_DEBUGGING_PORT': os.getenv('CHROME_DEBUGGING_PORT', '未設定'),
            'EDGE_PATH': os.getenv('EDGE_PATH', '未設定'),
            'EDGE_USER_DATA': os.getenv('EDGE_USER_DATA', '未設定'),
            'EDGE_DEBUGGING_PORT': os.getenv('EDGE_DEBUGGING_PORT', '未設定')
        }
        
        # 情報を収集
        diagnostics = {
            'timestamp': datetime.now().isoformat(),
            'system_info': {
                'os': platform.system(),
                'release': platform.release(),
                'python_version': sys.version
            },
            'browser_config': {
                'current_browser': current_browser,
                'settings': browser_config.config['browsers']
            },
            'running_processes': {
                'chrome': chrome_processes,
                'edge': edge_processes
            },
            'environment_variables': env_vars
        }
        
        # 診断ファイルを保存
        os.makedirs('logs', exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'logs/browser_diagnostics_{timestamp}.json'
        
        with open(filename, 'w') as f:
            json.dump(diagnostics, f, indent=2)
            
        logger.info(f"診断情報を保存しました: {filename}")
        return filename
    
    @staticmethod
    def diagnose_on_error():
        """エラーが発生した時に呼び出す診断関数"""
        try:
            filename = BrowserDiagnostics.collect_browser_info()
            logger.info(f"エラー診断情報を収集しました: {filename}")
            return filename
        except Exception as e:
            logger.error(f"診断情報の収集中にエラーが発生しました: {str(e)}")
            return None
