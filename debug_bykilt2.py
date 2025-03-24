# 使用例: 新しく分割されたモジュールを使用する

import asyncio
import argparse
from src.utils.debug_utils import DebugUtils
from src.browser.browser_debug_manager import BrowserDebugManager

async def main():
    parser = argparse.ArgumentParser(description="LLM Response Debugger")
    parser.add_argument("file", nargs="?", help="Path to the LLM response JSON file")
    parser.add_argument("--list", action="store_true", help="List available sample JSON files")
    parser.add_argument("--use-own-browser", action="store_true", help="Use your own browser profile")
    parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    args = parser.parse_args()
    
    # Create browser manager first
    browser_manager = BrowserDebugManager()
    
    # Pass the browser manager to DebugUtils
    debug_utils = DebugUtils()
    debug_utils.browser_manager = browser_manager  # Override the internal browser manager
    
    if args.list:
        debug_utils.list_samples()
        return
    
    if not args.file:
        debug_utils.show_help()
        return
    
    try:
        await debug_utils.test_llm_response(args.file, args.use_own_browser, args.headless)
    except KeyboardInterrupt:
        print("\n🛑 実行が中断されました。リソースをクリーンアップしています...")
    finally:
        await browser_manager.cleanup_resources()
        print("✅ リソースのクリーンアップが完了しました")

if __name__ == "__main__":
    asyncio.run(main())