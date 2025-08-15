# 使用例: 新しく分割されたモジュールを使用する

import asyncio
import argparse
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager
from src.utils.app_logger import logger

async def main():
    parser = argparse.ArgumentParser(description="LLM Response Debugger")
    parser.add_argument("file", nargs="?", help="Path to the LLM response JSON file")
    parser.add_argument("--list", action="store_true", help="List available sample JSON files")
    parser.add_argument("--use-own-browser", action="store_true", help="Use your own browser profile")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    parser.add_argument("--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                        help="Set logging level")
    args = parser.parse_args()
    
    logger.set_level(args.log_level)
    logger.info("Starting LLM Response Debugger")
    
    browser_manager = BrowserDebugManager()
    debug_utils = DebugUtils(browser_manager=browser_manager)
    
    if args.list:
        logger.info("Listing sample JSON files")
        debug_utils.list_samples()
        return
    
    if not args.file:
        logger.info("No file specified, showing help")
        debug_utils.show_help()
        return
    
    try:
        logger.info(f"Testing LLM response from file: {args.file}")
        await debug_utils.test_llm_response(args.file, args.use_own_browser, args.headless)
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    asyncio.run(main())