import asyncio
import json
import os
from src.browser.browser_debug_manager import BrowserDebugManager
from src.modules.yaml_parser import load_yaml_from_file, InstructionLoader

class ExecutionDebugEngine:
    """デバッグツール用のブラウザコマンド実行エンジン"""
    
    def __init__(self):
        """実行エンジンの初期化"""
        self.browser_manager = BrowserDebugManager()
    
    async def execute_commands(self, commands, use_own_browser=False, headless=False, tab_selection="active"):
        """
        Execute a list of commands in the browser.
        
        Args:
            commands: List of commands to execute.
            use_own_browser: Whether to use the user's own browser.
            headless: Whether to run in headless mode.
            tab_selection: Strategy for selecting a tab ("new", "active", "last").
        """
        print("\nコマンドを実行しています:")
        for i, cmd in enumerate(commands, 1):
            print(f" {i}. {cmd['action']}: {cmd.get('args', [])}")

        try:
            print("ブラウザを初期化しています...")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)

            # Get or create tab using the specified strategy
            context, page, is_new = await self.browser_manager.get_or_create_tab(tab_selection)

            if is_new:
                print("✅ 新しいタブを作成しました")
            else:
                print("✅ 現在表示中のタブを操作します")

            # Highlight the tab being automated
            await self.browser_manager.highlight_automated_tab(page)

            # Execute commands
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

            # Close the tab if it was newly created
            if is_new:
                await page.close()
                print("✅ 新しいタブを閉じました")

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

    async def execute_json_commands(self, commands_data, use_own_browser=False, headless=False, action_name=None, params=None):
        """Execute JSON or YAML commands for browser automation."""
        try:
            # Debug input data type and value
            print(f"🔍 DEBUG [execute_json_commands]: commands_data の型: {type(commands_data)}")
            print(f"🔍 DEBUG [execute_json_commands]: commands_data の値: {commands_data}")
            
            # Handle file path input
            if isinstance(commands_data, str) and (commands_data.endswith('.txt') or commands_data.endswith('.yml') or commands_data.endswith('.yaml')):
                try:
                    print(f"📄 Loading commands from file: {commands_data}")
                    
                    # Use InstructionLoader for llms.txt
                    if commands_data.endswith('llms.txt'):
                        print(f"🔍 DEBUG: llms.txtファイルを処理します: {commands_data}")
                        loader = InstructionLoader(local_path=commands_data)
                        result = loader.load_instructions()
                        
                        # Debug InstructionLoader result
                        print(f"🔍 DEBUG: InstructionLoader 結果: {result}")
                        print(f"🔍 DEBUG: 読み込まれた指示の数: {len(result.instructions) if hasattr(result, 'instructions') else 'なし'}")
                        
                        if not result.success:
                            print(f"❌ 指示の読み込みに失敗しました: {result.error}")
                            return
                            
                        # Find the action by name if provided
                        print(f"🔍 検索するアクション名: {action_name}")
                        action = next((instr for instr in result.instructions 
                                       if isinstance(instr, dict) and 'name' in instr and instr['name'] == action_name), None)
                        
                        # Debug action detection
                        print(f"🔍 DEBUG: 指定されたactionが見つかりました: {action is not None}")
                        if action:
                            print(f"🔍 DEBUG: Action名: {action.get('name', '無名')}")
                            print(f"🔍 DEBUG: フローステップ数: {len(action.get('flow', []))}")
                            print(f"🔍 DEBUG: Action詳細: {json.dumps(action, ensure_ascii=False)}")
                        
                        if not action:
                            print("❌ 指定されたactionがllms.txtに見つかりませんでした")
                            return
                            
                        print(f"✅ 使用するaction: {action.get('name', '無名')}")
                        
                        # Convert action flow to commands format
                        commands = []
                        for i, step in enumerate(action.get('flow', [])):
                            # Debug current step
                            print(f"🔍 DEBUG: ステップ {i+1} を処理中: {step}")
                            
                            cmd = {"action": step.get('action', '')}
                            
                            # Handle different action types
                            if 'url' in step:
                                cmd['args'] = [step['url']]
                                print(f"🔍 DEBUG: URLを追加: {step['url']}")
                            elif 'selector' in step:
                                cmd['selector'] = step['selector']
                                print(f"🔍 DEBUG: セレクタを追加: {step['selector']}")
                            
                            # Handle additional parameters
                            for key, value in step.items():
                                if key not in ['action', 'url', 'args']:
                                    # Perform parameter substitution
                                    if isinstance(value, str) and '${params.' in value:
                                        param_name = value.split('${params.')[1].split('}')[0]
                                        if param_name in params:
                                            value = value.replace(f"${{params.{param_name}}}", params[param_name])
                                            print(f"🔍 DEBUG: パラメータ置換: {key}の値を{value}に変更")
                                    cmd[key] = value
                                    print(f"🔍 DEBUG: パラメータを追加 {key}: {value}")
                                        
                            commands.append(cmd)
                            print(f"🔍 DEBUG: コマンドを追加: {cmd}")
                        
                        # Create the commands structure
                        commands_data = {
                            "action_type": action.get('type', 'browser-control'),
                            "commands": commands,
                            "slowmo": action.get('slowmo', 1000)
                        }
                        
                        # Debug final commands_data structure
                        print(f"🔍 DEBUG: 最終的なcommands_data構造:")
                        print(f"🔍 DEBUG: - action_type: {commands_data['action_type']}")
                        print(f"🔍 DEBUG: - コマンド数: {len(commands_data['commands'])}")
                        print(f"🔍 DEBUG: - slowmo: {commands_data['slowmo']}")
                        print(f"🔍 DEBUG: - 全コマンド: {json.dumps(commands_data['commands'], ensure_ascii=False)}")
                        
                        if hasattr(result, 'instructions'):
                            print("🔎 読み込まれた指示の詳細:")
                            for i, instr in enumerate(result.instructions):
                                print(f"  指示 {i+1}:")
                                print(f"  - タイプ: {type(instr)}")
                                if isinstance(instr, dict):
                                    print(f"  - キー: {list(instr.keys())}")
                                    if 'name' in instr:
                                        print(f"  - 名前: {instr['name']}")
                                    if 'flow' in instr:
                                        print(f"  - フローステップ数: {len(instr['flow'])}")
                    
                    # For other YAML files, use direct loading
                    else:
                        yaml_data = load_yaml_from_file(commands_data)
                        if not yaml_data:
                            print(f"❌ Failed to load or parse YAML from {commands_data}")
                            return
                        commands_data = yaml_data
                    
                except Exception as e:
                    print(f"❌ Error processing file {commands_data}: {e}")
                    import traceback
                    print(traceback.format_exc())
                    return
            
            # Extract command information
            action_type = commands_data.get("action_type", "browser-control")
            commands = commands_data.get("commands", [])
            slowmo = commands_data.get("slowmo", 1000)
            
            # Validate commands structure
            if not commands:
                print("❌ No commands found in the provided data")
                return
                
            print(f"⚙️ Executing {len(commands)} commands of type: {action_type}")
            
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
                # Execute each command
                for i, cmd in enumerate(commands, 1):
                    action = cmd.get("action", "")
                    
                    # Log the command being executed
                    print(f"Command {i}/{len(commands)}: {action}")
                    print(f"Details: {json.dumps(cmd, ensure_ascii=False)}")
                    
                    if action == "command":
                        # Handle URL from args or direct url field
                        url = cmd.get("url") or (cmd.get("args", [""])[0] if "args" in cmd else "")
                        if not url:
                            print("⚠️ Missing URL in command action, skipping...")
                            continue
                        
                        await page.goto(url)
                        print(f"✅ Navigated to: {url}")
                        
                        # Wait for a specific selector if specified
                        if 'wait_for' in cmd:
                            await page.wait_for_selector(cmd['wait_for'])
                            print(f"✅ Waited for selector: {cmd['wait_for']}")
                    
                    elif action == "click":
                        selector = cmd.get("selector")
                        if not selector:
                            print("⚠️ Missing selector for click action, skipping...")
                            continue
                            
                        wait_for_navigation = cmd.get("wait_for_navigation", False)
                        
                        await page.click(selector)
                        print(f"✅ Clicked: {selector}")
                        
                        if wait_for_navigation:
                            await page.wait_for_load_state("networkidle")
                            print("✅ Waited for navigation to complete")
                    
                    elif action == "fill_form":
                        selector = cmd.get("selector")
                        value = cmd.get("value")
                        
                        if not selector or value is None:
                            print("⚠️ Missing selector or value for fill_form action, skipping...")
                            continue
                        
                        # コマンド生成部分で、valueがある場合に追加
                        if 'value' in cmd and isinstance(cmd['value'], str) and '${params.' in cmd['value']:
                            print(f"🔎 パラメータ置換前の値: {cmd['value']}")
                            # パラメータ置換処理を実装
                            param_name = cmd['value'].split('${params.')[1].split('}')[0]
                            if param_name in params:
                                cmd['value'] = cmd['value'].replace(f"${{params.{param_name}}}", params[param_name])
                                print(f"🔎 パラメータ置換後の値: {cmd['value']}")
                        
                        await page.fill(selector, value)
                        print(f"✅ Filled {selector} with: {value}")
                    
                    elif action == "keyboard_press":
                        # Get key from selector or key property
                        key = cmd.get("key") or cmd.get("selector")
                        
                        if not key:
                            print("⚠️ Missing key for keyboard_press action, skipping...")
                            continue
                        
                        await page.keyboard.press(key)
                        print(f"✅ Pressed key: {key}")
                    
                    elif action == "wait":
                        timeout = cmd.get("timeout", 3000)
                        print(f"⏱️ Waiting for {timeout}ms...")
                        await asyncio.sleep(timeout / 1000)
                    
                    else:
                        print(f"⚠️ Unknown action type: {action}, skipping...")
                    
                    # Apply slowmo delay between actions
                    await asyncio.sleep(slowmo / 1000)
                
                # Allow time to view the result
                print("\n✅ Execution complete. Tab will close in 30 seconds...")
                print("(Press Ctrl+C to close earlier)")
                await asyncio.sleep(30)
                
            except Exception as e:
                print(f"❌ Error during command execution: {e}")
                import traceback
                print(traceback.format_exc())
                
            finally:
                # Keep tab open as requested
                print("タブ開けっぱなし")
        
        except Exception as e:
            print(f"❌ Error in execute_json_commands: {e}")
            import traceback
            print(traceback.format_exc())
        
        # コマンド変換後に追加
        print("🔎 変換されたコマンド一覧:")
        for i, cmd in enumerate(commands):
            print(f"  コマンド {i+1}:")
            print(f"  - アクション: {cmd.get('action', '不明')}")
            print(f"  - 引数: {cmd.get('args', [])}")
            print(f"  - セレクタ: {cmd.get('selector', '未設定')}")
            print(f"  - その他パラメータ: {[k for k in cmd.keys() if k not in ['action', 'args', 'selector']]}")
