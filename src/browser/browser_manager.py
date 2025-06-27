import os
import logging
import platform
import sys
from typing import Dict, Optional, Any
from pathlib import Path

from src.utils.globals_manager import get_globals
from src.browser.browser_config import BrowserConfig
from src.browser.browser_debug_manager import BrowserDebugManager

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
    """Generate browser configuration based on parameters (Windows対応済み)"""
    extra_chromium_args = [f"--window-size={window_w},{window_h}"]
    
    # Windows対応のブラウザ引数追加
    if platform.system() == "Windows":
        extra_chromium_args.extend([
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--no-first-run",
            "--no-default-browser-check"
        ])
    
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
        
        # Windows環境でのデフォルトブラウザパス検出
        if (not browser_path or browser_path == "") and platform.system() == "Windows":
            browser_path = _find_browser_path_windows(browser_type)
            
        if browser_path == "":
            browser_path = None
            
        if browser_user_data:
            # Windows対応のパス処理
            if platform.system() == "Windows":
                browser_user_data = str(Path(browser_user_data).resolve())
            extra_chromium_args += [f"--user-data-dir={browser_user_data}"]
    
    return {
        "browser_path": browser_path,  # Changed from chrome_path
        "extra_chromium_args": extra_chromium_args
    }

def _find_browser_path_windows(browser_type: str = "chrome") -> Optional[str]:
    """Windows環境でブラウザの実行可能ファイルパスを検出"""
    if browser_type == "edge":
        edge_paths = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            os.path.expanduser(r"~\AppData\Local\Microsoft\Edge\Application\msedge.exe")
        ]
        for path in edge_paths:
            if os.path.exists(path):
                logger.info(f"Found Edge at: {path}")
                return path
    else:  # Chrome
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        for path in chrome_paths:
            if os.path.exists(path):
                logger.info(f"Found Chrome at: {path}")
                return path
    
    logger.warning(f"Could not find {browser_type} browser in standard Windows locations")
    return None

async def initialize_browser(use_own_browser=False, headless=False, browser_type=None, auto_fallback=True):
    """ブラウザを初期化し、失敗時には代替ブラウザにフォールバック"""
    browser_debug_manager = BrowserDebugManager()
    
    # 使用するブラウザタイプを決定
    if browser_type is None:
        browser_type = browser_config.config.get("current_browser", "chrome")
    
    logger.info(f"🔄 ブラウザ初期化開始: {browser_type.upper()}")
    
    try:
        # 指定されたブラウザタイプで初期化
        result = await browser_debug_manager.initialize_custom_browser(
            use_own_browser=use_own_browser, 
            headless=headless,
            tab_selection_strategy="new_tab"
        )
        
        if result.get("status") == "success":
            logger.info(f"✅ {browser_type.upper()} の初期化に成功しました")
            return result
        
        logger.error(f"❌ {browser_type.upper()} の初期化に失敗しました: {result.get('message', 'Unknown error')}")
        
        # 自動フォールバックが有効なら代替ブラウザを試す
        if auto_fallback:
            fallback_type = "chrome" if browser_type == "edge" else "edge"
            logger.warning(f"⚠️ {fallback_type.upper()} へのフォールバックを試みます")
            
            from src.browser.browser_diagnostic import BrowserDiagnostic
            BrowserDiagnostic.diagnose_browser_startup_issues(
                browser_type, 
                browser_config.get_browser_settings().get("debugging_port"),
                result.get("message", ""),
                attempt_repair=False  # 診断のみ
            )
            
            # 代替ブラウザでの初期化を試みる（再帰呼び出し、無限ループ防止のためauto_fallback=False）
            return await initialize_browser(
                use_own_browser=use_own_browser,
                headless=headless,
                browser_type=fallback_type,
                auto_fallback=False
            )
    except Exception as e:
        logger.error(f"❌ ブラウザ初期化中の予期せぬエラー: {e}")
        if auto_fallback:
            fallback_type = "chrome" if browser_type == "edge" else "edge"
            logger.warning(f"⚠️ 例外発生のため {fallback_type.upper()} へのフォールバックを試みます")
            return await initialize_browser(
                use_own_browser=use_own_browser,
                headless=headless,
                browser_type=fallback_type,
                auto_fallback=False
            )
    
    # すべて失敗した場合
    return {"status": "error", "message": f"すべてのブラウザ初期化試行が失敗しました"}

def prepare_recording_path(enable_recording: bool, save_recording_path: Optional[str]) -> Optional[str]:
    """Prepare recording path based on settings (Windows対応済み)"""
    if not enable_recording:
        return None
        
    if save_recording_path:
        # Windows対応: pathlibを使用してパス処理を統一
        recording_path = Path(save_recording_path).resolve()
        
        try:
            recording_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Recording directory prepared: {recording_path}")
            return str(recording_path)
        except PermissionError as e:
            logger.error(f"Permission denied creating recording directory: {e}")
            # Windows環境でのフォールバック: temp/recordingsを使用
            if platform.system() == "Windows":
                fallback_path = Path.cwd() / "tmp" / "record_videos"
                fallback_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Using fallback recording directory: {fallback_path}")
                return str(fallback_path)
            return None
        except Exception as e:
            logger.error(f"Failed to create recording directory: {e}")
            return None
        
    return None
