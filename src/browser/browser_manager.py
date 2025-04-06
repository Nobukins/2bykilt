import os
import logging
from typing import Dict, Optional, Any

from src.utils.globals_manager import get_globals
from src.browser.browser_config import BrowserConfig

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
    """Generate browser configuration based on parameters"""
    extra_chromium_args = [f"--window-size={window_w},{window_h}"]
    
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
            
        if browser_path == "":
            browser_path = None
            
        if browser_user_data:
            extra_chromium_args += [f"--user-data-dir={browser_user_data}"]
    
    return {
        "browser_path": browser_path,  # Changed from chrome_path
        "extra_chromium_args": extra_chromium_args
    }

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
    """Prepare recording path based on settings"""
    if not enable_recording:
        return None
        
    if save_recording_path:
        os.makedirs(save_recording_path, exist_ok=True)
        return save_recording_path
        
    return None
