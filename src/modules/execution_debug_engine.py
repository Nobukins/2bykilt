import asyncio
import json
from src.browser.browser_debug_manager import BrowserDebugManager
# Removed circular import from here

class ExecutionDebugEngine:
    """デバッグツール用のブラウザコマンド実行エンジン"""
    
    def __init__(self):
        """実行エンジンの初期化"""
        self.browser_manager = BrowserDebugManager()
        # Remove dependency on DebugUtils
        self.debug_utils = None
    
    async def execute_commands(self, commands, use_own_browser=False, headless=False):
        """コマンドのリストをブラウザで実行"""
        print("\nコマンドを実行しています:")
        for i, cmd in enumerate(commands, 1):
            print(f" {i}. {cmd['action']}: {cmd.get('args', [])}")

        try:
            print("ブラウザを初期化しています...")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            
            # Use the default context for CDP browsers to ensure new tabs appear in the existing window
            if browser_data.get("is_cdp", False):
                context = browser.contexts[0] if browser.contexts else await browser.new_context()
                print("✅ 既存のChromeウィンドウに新しいタブを作成します")
            else:
                context = browser_data.get("context") or await browser.new_context()
            
            # Create a new tab in the context
            page = await context.new_page()
            # Import locally to avoid circular dependency
            from src.utils.debug_utils import DebugUtils
            debug_utils = DebugUtils()
            # await debug_utils.setup_element_indexer(page)

            for cmd in commands:
                action = cmd["action"]
                args = cmd.get("args", [])
                print(f"実行中: {action} {args}")

                if action == "command" and args and args[0].startswith("http"):
                    await page.goto(args[0], wait_until="domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                    print(f"ナビゲートしました: {args[0]}")
                elif action == "wait_for_navigation":
                    await page.wait_for_load_state("networkidle")
                    print("ナビゲーションが完了しました。")
                elif action == "fill_form" and len(args) >= 2:
                    selector, value = args[0], args[1]
                    await page.fill(selector, value)
                    print(f"フォーム '{selector}' に '{value}' を入力しました")
                elif action == "click" and args:
                    selector = args[0]
                    await page.click(selector)
                    print(f"要素 '{selector}' をクリックしました")
                elif action == "keyboard_press" and args:
                    key = args[0]
                    await page.keyboard.press(key)
                    print(f"キー '{key}' を押しました")
                elif action == "extract_content":
                    selectors = args if args else ["h1", "h2", "h3", "p"]
                    content = {}
                    for selector in selectors:
                        elements = await page.query_selector_all(selector)
                        texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                        content[selector] = texts
                    print("\n抽出されたコンテンツ:")
                    print(json.dumps(content, indent=2, ensure_ascii=False))

                print("\nコマンドを実行しました。次のコマンドは3秒後...")
                await asyncio.sleep(3)

            # タブを閉じるが、ブラウザは開いたままにする
            await page.close()
            
            # Only stop playwright if this was not a CDP connection
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()

        except Exception as e:
            print(f"\nコマンド実行中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())
    
    async def execute_google_search(self, query, use_own_browser=False, headless=False):
        """Googleで検索を実行"""
        try:
            print(f"Googleで検索しています: {query}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.fill("input[name='q']", query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            print(f"検索結果を表示しました: {query}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\nGoogle検索中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_beatport_search(self, query, use_own_browser=False, headless=False):
        """Beatportで検索を実行"""
        try:
            print(f"Beatportで検索しています: {query}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.beatport.com", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.fill("input[name='q']", query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            print(f"検索結果を表示しました: {query}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\nBeatport検索中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_goto_url(self, url, use_own_browser=False, headless=False):
        """指定したURLに移動"""
        try:
            print(f"URLに移動しています: {url}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            print(f"URLに移動しました: {url}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\nURL移動中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_form_input(self, params, use_own_browser=False, headless=False):
        """フォーム入力を実行"""
        try:
            print(f"フォーム入力を実行しています: {params}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(params["url"], wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            for selector, value in params["inputs"].items():
                await page.fill(selector, value)
                print(f"フォーム '{selector}' に '{value}' を入力しました")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\nフォーム入力中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_extract_content(self, params, use_own_browser=False, headless=False):
        """コンテンツ抽出を実行"""
        try:
            print(f"コンテンツ抽出を実行しています: {params}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(params["url"], wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            content = {}
            for selector in params["selectors"]:
                elements = await page.query_selector_all(selector)
                texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                content[selector] = texts
            print("\n抽出されたコンテンツ:")
            print(json.dumps(content, indent=2, ensure_ascii=False))
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\nコンテンツ抽出中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_complex_sequence(self, params, use_own_browser=False, headless=False):
        """複雑なシーケンスを実行"""
        try:
            print(f"複雑なシーケンスを実行しています: {params}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            browser = browser_data["browser"]
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(params["url"], wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            for step in params["steps"]:
                action = step["action"]
                args = step.get("args", [])
                print(f"実行中: {action} {args}")

                if action == "command" and args and args[0].startswith("http"):
                    await page.goto(args[0], wait_until="domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                    print(f"ナビゲートしました: {args[0]}")
                elif action == "wait_for_navigation":
                    await page.wait_for_load_state("networkidle")
                    print("ナビゲーションが完了しました。")
                elif action == "fill_form" and len(args) >= 2:
                    selector, value = args[0], args[1]
                    await page.fill(selector, value)
                    print(f"フォーム '{selector}' に '{value}' を入力しました")
                elif action == "click" and args:
                    selector = args[0]
                    await page.click(selector)
                    print(f"要素 '{selector}' をクリックしました")
                elif action == "keyboard_press" and args:
                    key = args[0]
                    await page.keyboard.press(key)
                    print(f"キー '{key}' を押しました")
                elif action == "extract_content":
                    selectors = args if args else ["h1", "h2", "h3", "p"]
                    content = {}
                    for selector in selectors:
                        elements = await page.query_selector_all(selector)
                        texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                        content[selector] = texts
                    print("\n抽出されたコンテンツ:")
                    print(json.dumps(content, indent=2, ensure_ascii=False))

                print("\nコマンドを実行しました。次のコマンドは3秒後...")
                await asyncio.sleep(3)

            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            print(f"\n複雑なシーケンス実行中にエラーが発生しました: {e}")
            import traceback
            print(traceback.format_exc())

    async def execute_json_commands(self, commands_data, use_own_browser=False, headless=False):
        """Execute JSON commands for browser automation."""
        action_type = commands_data.get("action_type", "browser-control")
        commands = commands_data.get("commands", [])
        slowmo = commands_data.get("slowmo", 1000)
        
        # Initialize browser
        browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Get or create context
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            print("✅ Using existing Chrome window with a new tab")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # Create a new page/tab
        page = await context.new_page()
        
        try:
            # Special handling for unlock-future type if needed
            if action_type == "unlock-future":
                print("🔓 Executing unlock-future action sequence")
            
            # Execute each command
            for cmd in commands:
                action = cmd.get("action")
                
                if action == "command":
                    # Ensure 'args' contains the URL
                    if 'args' not in cmd or not cmd['args']:
                        raise ValueError("Missing URL in command action")
                    
                    # Extract the URL
                    url = cmd['args'][0]
                    await page.goto(url)  # Navigate to the URL
                    print(f"Navigated to: {url}")
                    
                    # Wait for a specific selector if specified
                    if 'wait_for' in cmd:
                        await page.wait_for_selector(cmd['wait_for'])
                        print(f"Waited for selector: {cmd['wait_for']}")
                
                elif action == "click":
                    selector = cmd.get("selector")
                    wait_for_navigation = cmd.get("wait_for_navigation", False)
                    
                    await page.click(selector)
                    print(f"Clicked: {selector}")
                    
                    if wait_for_navigation:
                        await page.wait_for_load_state("networkidle")
                        print("Waited for navigation to complete")
                
                elif action == "fill_form":
                    selector = cmd.get("selector")
                    value = cmd.get("value")
                    
                    await page.fill(selector, value)
                    print(f"Filled {selector} with: {value}")
                
                elif action == "keyboard_press":
                    key = cmd.get("selector")  # In your YAML, you use selector for the key
                    
                    await page.keyboard.press(key)
                    print(f"Pressed key: {key}")
                
                # Add more action types as needed
                
                # Apply slowmo delay between actions
                await asyncio.sleep(slowmo / 1000)
            
            # Allow time to view the result
            print("\nExecution complete. Tab will close in 30 seconds...")
            print("(Press Ctrl+C to close earlier)")
            await asyncio.sleep(30)
            
        finally:
            # Close only the tab, not the browser
            await page.close()
            print("Tab closed, browser remains open")
