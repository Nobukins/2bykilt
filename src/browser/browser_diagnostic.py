import os
import json
import psutil
import socket
import subprocess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class BrowserDiagnostic:
    """ブラウザ関連の診断情報を収集・保存するためのユーティリティ"""
    
    @staticmethod
    def capture_browser_state(diagnostic_type="browser_state"):
        """現在のブラウザ設定状態をキャプチャしてファイルに保存"""
        from src.browser.browser_config import BrowserConfig
        
        # 診断情報を収集
        browser_config = BrowserConfig()
        current_browser = browser_config.config.get("current_browser", "未設定")
        
        # ポート診断情報を追加
        port_diagnostics = BrowserDiagnostic.check_port_availability()
        
        # プロセス診断情報を追加
        process_diagnostics = BrowserDiagnostic.check_browser_processes()
        
        # 現在のブラウザ設定
        browser_settings = browser_config.get_browser_settings()
        
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "diagnostic_type": diagnostic_type,
            "browser_config": {
                "current_browser": current_browser,
                "settings": browser_settings,
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
            "port_diagnostics": port_diagnostics,
            "process_diagnostics": process_diagnostics
        }
        
        # 診断情報を保存
        os.makedirs("logs/browser_diagnostics", exist_ok=True)
        filename = f"logs/browser_diagnostics/browser_state_{diagnostic_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(diagnostics, f, indent=2)
        
        logger.info(f"ブラウザ状態診断情報を保存しました: {filename}")
        return filename
        
    @staticmethod
    def check_port_availability():
        """ブラウザデバッグポートの可用性チェック"""
        chrome_port = int(os.getenv("CHROME_DEBUGGING_PORT", "9222"))
        edge_port = int(os.getenv("EDGE_DEBUGGING_PORT", "9223"))
        
        result = {}
        
        # Chrome ポートチェック
        chrome_available, chrome_error = BrowserDiagnostic._check_port(chrome_port)
        result["chrome_port"] = {
            "port": chrome_port,
            "available": chrome_available,
            "error": chrome_error,
            "http_response": BrowserDiagnostic._check_debug_endpoint(chrome_port)
        }
        
        # Edge ポートチェック
        edge_available, edge_error = BrowserDiagnostic._check_port(edge_port)
        result["edge_port"] = {
            "port": edge_port,
            "available": edge_available,
            "error": edge_error,
            "http_response": BrowserDiagnostic._check_debug_endpoint(edge_port)
        }
        
        return result
    
    @staticmethod
    def _check_port(port):
        """指定されたポートが空いているかチェック"""
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("localhost", port))
            return True, None  # ポートは利用可能
        except socket.error as e:
            return False, str(e)  # ポートは使用中
        finally:
            s.close()
    
    @staticmethod
    def _check_debug_endpoint(port):
        """デバッグエンドポイントの応答をチェック"""
        try:
            import requests
            response = requests.get(f"http://localhost:{port}/json/version", timeout=2)
            return {
                "status_code": response.status_code,
                "content": response.json() if response.status_code == 200 else None
            }
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def check_browser_processes():
        """実行中のブラウザプロセスを検出"""
        result = {
            "chrome": [],
            "edge": []
        }
        
        # プロセスをスキャン
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                # Chrome プロセスの検出
                if "chrome" in proc.info['name'].lower():
                    result["chrome"].append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": proc.info['cmdline']
                    })
                
                # Edge プロセスの検出
                if "edge" in proc.info['name'].lower():
                    result["edge"].append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "cmdline": proc.info['cmdline']
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        return result
    
    @staticmethod
    def diagnose_connection_error(browser_type, port, error_message):
        """ブラウザ接続エラーを診断"""
        diagnostic_file = BrowserDiagnostic.capture_browser_state(f"error_during_init")
        logger.error(f"詳細な診断情報: {diagnostic_file}")
        
        # 接続エラーの場合、自動的にブラウザを再起動するヘルパー
        if "ECONNREFUSED" in error_message:
            logger.warning(f"接続エラーを検出: {browser_type} ブラウザへの接続が拒否されました")
            logger.info(f"自動再起動を試みます...")
            
            # 起動コマンドの例（実際の実装はシステムに応じて調整）
            if browser_type == "edge":
                path = os.getenv("EDGE_PATH", "")
                if path:
                    cmd = f"{path} --remote-debugging-port={port}"
                    logger.info(f"再起動コマンド: {cmd}")
                    # 自動再起動は実際の実装で判断
                    # subprocess.Popen(cmd.split())
            
        return diagnostic_file

    @staticmethod
    def diagnose_browser_startup_issues(browser_type, port, error_message, attempt_repair=False):
        """ブラウザ起動の問題を診断して対処策を提案"""
        # 診断情報の収集
        diagnostic_file = BrowserDiagnostic.capture_browser_state(f"startup_issue_{browser_type}")
        logger.error(f"ブラウザ起動診断情報: {diagnostic_file}")
        
        # 接続エラーの分析
        if "ECONNREFUSED" in error_message:
            logger.error(f"🔥 接続エラー分析: {browser_type} ブラウザは起動していないか、指定されたポート {port} でリッスンしていません")
            
            # 実行中のブラウザプロセスを確認
            processes = BrowserDiagnostic.check_browser_processes()
            browser_processes = processes.get(browser_type.lower(), [])
            
            if browser_processes:
                logger.info(f"🔍 {len(browser_processes)} 個の {browser_type} プロセスが見つかりました")
                for proc in browser_processes:
                    logger.info(f"  - PID: {proc['pid']}, コマンドライン: {' '.join(proc['cmdline'] or [])}")
                    
                # リモートデバッグフラグを持つプロセスを検索
                debug_procs = [p for p in browser_processes if any('--remote-debugging-port' in cmd for cmd in (p['cmdline'] or []))]
                if debug_procs:
                    logger.info(f"✅ リモートデバッグが有効な {browser_type} プロセスが見つかりました")
                    for proc in debug_procs:
                        debug_args = [arg for arg in (proc['cmdline'] or []) if '--remote-debugging-port' in arg]
                        logger.info(f"  - PID: {proc['pid']}, デバッグフラグ: {debug_args}")
                else:
                    logger.error(f"❌ リモートデバッグが有効な {browser_type} プロセスが見つかりません")
                    
                    # 自動修復を試みる
                    if attempt_repair:
                        logger.info(f"🛠️ {browser_type} を自動的に起動します...")
                        BrowserDiagnostic.start_browser_with_debug(browser_type, port)
            else:
                logger.error(f"❌ 実行中の {browser_type} プロセスが見つかりません")
                
                # 自動修復を試みる
                if attempt_repair:
                    logger.info(f"🛠️ {browser_type} を自動的に起動します...")
                    BrowserDiagnostic.start_browser_with_debug(browser_type, port)
        
        return diagnostic_file

    @staticmethod
    def start_browser_with_debug(browser_type, port):
        """指定されたブラウザをデバッグモードで起動する"""
        import subprocess
        
        browser_config = BrowserConfig()
        current_settings = browser_config.get_browser_settings()
        
        if browser_type.lower() == "edge":
            browser_path = current_settings.get("path", os.getenv("EDGE_PATH", ""))
            user_data_dir = current_settings.get("user_data", os.getenv("EDGE_USER_DATA", ""))
        else:  # デフォルトはchrome
            browser_path = current_settings.get("path", os.getenv("CHROME_PATH", ""))
            user_data_dir = current_settings.get("user_data", os.getenv("CHROME_USER_DATA", ""))
        
        if not browser_path:
            logger.error(f"❌ {browser_type} の実行パスが設定されていません")
            return False
        
        cmd = [browser_path, f"--remote-debugging-port={port}"]
        if user_data_dir:
            cmd.append(f"--user-data-dir={user_data_dir}")
        
        logger.info(f"🚀 {browser_type} 起動コマンド: {' '.join(cmd)}")
        
        try:
            subprocess.Popen(cmd)
            logger.info(f"✅ {browser_type} の起動を開始しました。接続を待機しています...")
            
            # 接続成功するまで待機
            import time
            for _ in range(10):  # 最大10秒待機
                time.sleep(1)
                try:
                    import requests
                    response = requests.get(f"http://localhost:{port}/json/version", timeout=1)
                    if response.status_code == 200:
                        logger.info(f"✅ {browser_type} に正常に接続しました")
                        return True
                except:
                    pass
            
            logger.warning(f"⚠️ {browser_type} の起動は開始しましたが、接続できません")
            return False
        except Exception as e:
            logger.error(f"❌ {browser_type} の起動に失敗しました: {e}")
            return False

    @staticmethod
    def diagnose_playwright_initialization(browser_type, error_message):
        """Playwright初期化問題の診断"""
        logger.error(f"Playwright初期化エラー: {error_message}")
        
        # Playwrightのバージョン確認
        try:
            import playwright
            logger.info(f"Playwrightバージョン: {playwright.__version__}")
        except Exception as e:
            logger.error(f"Playwrightバージョン取得エラー: {e}")
        
        # 依存関係の確認
        try:
            import sys
            logger.info(f"Python バージョン: {sys.version}")
            import platform
            logger.info(f"プラットフォーム: {platform.platform()}")
        except Exception as e:
            logger.error(f"システム情報取得エラー: {e}")
        
        # 診断情報のキャプチャと返却
        return BrowserDiagnostic.capture_browser_state(f"playwright_init_error_{browser_type}")
