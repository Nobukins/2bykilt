import os
import logging
import platform
import sys
from typing import Dict, Optional, Any
from pathlib import Path

from src.utils.globals_manager import get_globals
from src.core.artifact_manager import ArtifactManager
from src.utils.recording_dir_resolver import create_or_get_recording_dir
from src.browser.browser_config import BrowserConfig
from src.browser.browser_debug_manager import BrowserDebugManager

# 録画パスユーティリティのインポート（フォールバック付き）
try:
    from src.utils.recording_path_utils import get_recording_path
except ImportError:
    # フォールバック: 基本的な録画パス設定
    from src.utils.recording_path_utils import get_recording_path

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
    browser_type: str = None  # Allow None to use current browser from config
) -> Dict[str, Any]:
    """Generate browser configuration based on parameters with improved browser selection."""
    
    # ブラウザタイプの決定（UIで選択されたブラウザを優先）
    if browser_type is None:
        browser_type = browser_config.get_current_browser()
        logger.info(f"🔍 UIで選択されたブラウザタイプを使用: {browser_type}")
    
    # ブラウザが利用可能かチェック
    if not browser_config.is_browser_available(browser_type):
        logger.warning(f"⚠️ 指定されたブラウザ {browser_type} が利用できません")
        available_browsers = browser_config.get_available_browsers()
        if available_browsers:
            browser_type = available_browsers[0]
            logger.info(f"🔄 利用可能なブラウザ {browser_type} にフォールバック")
        else:
            logger.warning("⚠️ 利用可能なブラウザが見つかりません。デフォルトを使用")
            browser_type = "chrome"
    
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
        # BrowserConfigから設定を取得
        settings = browser_config.get_browser_settings(browser_type)
        browser_path = settings.get("path", "")
        browser_user_data = settings.get("user_data", None)
        
        logger.info(f"Using {browser_type} browser: {browser_path}")
        
        # Windows環境でのデフォルトブラウザパス検出（フォールバック）
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
        "browser_path": browser_path,
        "browser_type": browser_type,  # Add browser_type to return
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
    logger.debug(f"🔍 browser_manager.initialize_browser 呼び出し - use_own_browser: {use_own_browser}, headless: {headless}, browser_type: {browser_type}, auto_fallback: {auto_fallback}")
    
    browser_debug_manager = BrowserDebugManager()
    
    # 使用するブラウザタイプを決定（優先順位: 引数 > config設定 > デフォルト）
    if browser_type is None:
        browser_type = browser_config.config.get("current_browser", "chrome")
    else:
        # 引数で指定された場合は、configも更新
        logger.debug(f"🔍 引数でブラウザタイプが指定されました: {browser_type}")
        browser_config.set_current_browser(browser_type)
    
    logger.info(f"🔄 ブラウザ初期化開始: {browser_type.upper()}")
    logger.debug(f"🔍 決定されたブラウザタイプ: {browser_type}")
    logger.debug(f"🔍 browser_config.config: {browser_config.config}")
    
    try:
        # 指定されたブラウザタイプで初期化
        logger.debug(f"🔍 browser_debug_manager.initialize_custom_browser を呼び出し中...")
        result = await browser_debug_manager.initialize_custom_browser(
            use_own_browser=use_own_browser, 
            headless=headless,
            tab_selection_strategy="new_tab"
        )
        
        if result.get("status") == "success":
            logger.info(f"✅ {browser_type.upper()} の初期化に成功しました")
            logger.debug(f"🔍 成功したブラウザタイプ: {browser_type}")
            return result
        
        logger.error(f"❌ {browser_type.upper()} の初期化に失敗しました: {result.get('message', 'Unknown error')}")
        logger.debug(f"🔍 失敗の詳細 - browser_type: {browser_type}, auto_fallback: {auto_fallback}")
        
        # 自動フォールバックが有効なら代替ブラウザを試す
        if auto_fallback:
            fallback_type = "chrome" if browser_type == "edge" else "edge"
            logger.warning(f"⚠️ フォールバック実行: {browser_type} -> {fallback_type}")
            logger.debug(f"🔍 フォールバック条件分岐:")
            logger.debug(f"  - 元のブラウザタイプ: {browser_type}")
            logger.debug(f"  - フォールバック先: {fallback_type}")
            logger.debug(f"  - auto_fallback: {auto_fallback}")
            
            from src.browser.browser_diagnostic import BrowserDiagnostic
            BrowserDiagnostic.diagnose_browser_startup_issues(
                browser_type, 
                browser_config.get_browser_settings().get("debugging_port"),
                result.get("message", ""),
                attempt_repair=False  # 診断のみ
            )
            
            # 元のブラウザ設定を保存
            original_browser = browser_config.config.get("current_browser")
            
            # 代替ブラウザでの初期化を試みる（再帰呼び出し、無限ループ防止のためauto_fallback=False）
            logger.debug(f"🔍 フォールバック実行中: {fallback_type} で再試行...")
            fallback_result = await initialize_browser(
                use_own_browser=use_own_browser,
                headless=headless,
                browser_type=fallback_type,
                auto_fallback=False
            )
            
            # フォールバック結果にオリジナルの選択を記録
            if isinstance(fallback_result, dict):
                fallback_result["original_browser_choice"] = original_browser
                fallback_result["fallback_used"] = True
                fallback_result["fallback_from"] = browser_type
                fallback_result["fallback_to"] = fallback_type
                logger.warning(f"⚠️ フォールバック完了: {browser_type} -> {fallback_type} (元の選択: {original_browser})")
            
            return fallback_result
        else:
            logger.debug(f"🔍 auto_fallback=False のため、フォールバックをスキップ")
    except Exception as e:
        logger.error(f"❌ ブラウザ初期化中の予期せぬエラー: {e}")
        logger.debug(f"🔍 例外の詳細:")
        logger.debug(f"  - browser_type: {browser_type}")
        logger.debug(f"  - auto_fallback: {auto_fallback}")
        logger.debug(f"  - 例外タイプ: {type(e).__name__}")
        import traceback
        logger.debug(f"  - スタックトレース: {traceback.format_exc()}")
        
        if auto_fallback:
            fallback_type = "chrome" if browser_type == "edge" else "edge"
            logger.warning(f"⚠️ 例外によるフォールバック実行: {browser_type} -> {fallback_type}")
            logger.debug(f"🔍 例外フォールバック条件分岐:")
            logger.debug(f"  - 元のブラウザタイプ: {browser_type}")
            logger.debug(f"  - フォールバック先: {fallback_type}")
            logger.debug(f"  - auto_fallback: {auto_fallback}")
            
            return await initialize_browser(
                use_own_browser=use_own_browser,
                headless=headless,
                browser_type=fallback_type,
                auto_fallback=False
            )
        else:
            logger.debug(f"🔍 auto_fallback=False のため、例外フォールバックをスキップ")
    
    # すべて失敗した場合
    return {"status": "error", "message": f"すべてのブラウザ初期化試行が失敗しました"}

def prepare_recording_path(enable_recording: bool, save_recording_path: Optional[str]) -> Optional[str]:
    """Prepare recording path (Wave A3 #28 integration).

    Uses ArtifactManager.resolve_recording_dir for unified path strategy when
    feature flag artifacts.unified_recording_path is enabled. Falls back to
    legacy behavior for backward compatibility.
    """
    if not enable_recording:
        return None
    try:
        # Centralized resolver (Issue #28 refactor): explicit UI value passed as save_recording_path
        path = create_or_get_recording_dir(save_recording_path if save_recording_path else None)
        logger.info(f"Recording directory prepared: {path}")
        return str(path)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Failed to resolve recording directory: {e}")
        try:
            path = Path(get_recording_path("./tmp/record_videos")).resolve()
            return str(path)
        except Exception:
            import tempfile
            tmp = tempfile.gettempdir()
            logger.warning(f"Using system temporary directory as final fallback: {tmp}")
            return tmp
