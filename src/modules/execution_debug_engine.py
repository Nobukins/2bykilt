import asyncio
import json
import os
import traceback
from datetime import datetime
from src.browser.browser_debug_manager import BrowserDebugManager
from src.modules.yaml_parser import load_yaml_from_file, InstructionLoader
from src.utils.app_logger import logger

class ExecutionDebugEngine:
    """デバッグツール用のブラウザコマンド実行エンジン"""
    
    def __init__(self):
        """実行エンジンの初期化"""
        self.browser_manager = BrowserDebugManager()
    
    async def execute_commands(self, commands, use_own_browser=False, headless=False, tab_selection="active_tab", action_type=None, keep_tab_open=None):
        """
        Execute a list of commands in the browser.
        
        Args:
            commands: List of commands to execute.
            use_own_browser: Whether to use the user's own browser.
            headless: Whether to run in headless mode.
            tab_selection: Strategy for selecting a tab ("new_tab", "active_tab", "last_tab").
            action_type: Type of action (e.g., "unlock-future").
            keep_tab_open: Whether to keep the tab open after execution.
        """
        logger.info("コマンドを実行しています:")
        for i, cmd in enumerate(commands, 1):
            logger.info(f" {i}. {cmd['action']}: {cmd.get('args', [])}")

        # Default to true for unlock-future type, otherwise default to false
        if keep_tab_open is None:
            keep_tab_open = True if action_type == "unlock-future" else False
        
        logger.debug(f"Action Type: {action_type}, Keep Tab Open: {keep_tab_open}")
        
        try:
            logger.info("ブラウザを初期化しています...")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)

            # Handle browser initialization failure
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return

            # Get or create tab using the specified strategy
            context, page, is_new = await self.browser_manager.get_or_create_tab(tab_selection)

            if is_new:
                logger.info("新しいタブを作成しました")
            else:
                logger.info("現在表示中のタブを操作します")

            # Highlight the tab being automated
            await self.browser_manager.highlight_automated_tab(page)

            # Execute commands
            for cmd in commands:
                action = cmd["action"]
                args = cmd.get("args", [])
                logger.info(f"実行中: {action} {args}")

                if action == "command" and args and args[0].startswith("http"):
                    await page.goto(args[0], wait_until="domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                    logger.info(f"ナビゲートしました: {args[0]}")
                elif action == "wait_for_navigation":
                    await page.wait_for_load_state("networkidle")
                    logger.info("ナビゲーションが完了しました。")
                elif action == "fill_form" and len(args) >= 2:
                    selector, value = args[0], args[1]
                    await page.fill(selector, value)
                    logger.info(f"フォーム '{selector}' に '{value}' を入力しました")
                elif action == "click" and args:
                    selector = args[0]
                    await page.click(selector)
                    logger.info(f"要素 '{selector}' をクリックしました")
                elif action == "keyboard_press" and args:
                    key = args[0]
                    await page.keyboard.press(key)
                    logger.info(f"キー '{key}' を押しました")
                elif action == "extract_content":
                    selectors = args if args else ["h1", "h2", "h3", "p"]
                    content = {}
                    for selector in selectors:
                        elements = await page.query_selector_all(selector)
                        texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                        content[selector] = texts
                    logger.info("抽出されたコンテンツ:")
                    logger.info(json.dumps(content, indent=2, ensure_ascii=False))

                logger.info("コマンドを実行しました。次のコマンドは3秒後...")
                await asyncio.sleep(3)

            # Handle tab closure based on keep_tab_open setting
            logger.info("Execution complete.")
            if not keep_tab_open:
                logger.info("Tab will close in 5 seconds...")
                logger.info("(Press Ctrl+C to close earlier)")
                await asyncio.sleep(5)
                await page.close()
                logger.info("タブを閉じました")
            else:
                logger.info("タブを開いたままにします（keep_tab_open: true）")

        except Exception as e:
            logger.error(f"コマンド実行中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    async def execute_google_search(self, query, use_own_browser=False, headless=False):
        """Googleで検索を実行"""
        try:
            logger.info(f"Googleで検索しています: {query}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return
            browser = browser_data.get("browser")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.google.com", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.fill("input[name='q']", query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            logger.info(f"検索結果を表示しました: {query}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            logger.error(f"Google検索中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def execute_beatport_search(self, query, use_own_browser=False, headless=False):
        """Beatportで検索を実行"""
        try:
            logger.info(f"Beatportで検索しています: {query}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return
            browser = browser_data.get("browser")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto("https://www.beatport.com", wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            await page.fill("input[name='q']", query)
            await page.keyboard.press("Enter")
            await page.wait_for_load_state("networkidle")
            logger.info(f"検索結果を表示しました: {query}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            logger.error(f"Beatport検索中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def execute_goto_url(self, url, use_own_browser=False, headless=False):
        """指定したURLに移動"""
        try:
            logger.info(f"URLに移動しています: {url}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return
            browser = browser_data.get("browser")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            logger.info(f"URLに移動しました: {url}")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            logger.error(f"URL移動中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def execute_form_input(self, params, use_own_browser=False, headless=False):
        """フォーム入力を実行"""
        try:
            logger.info(f"フォーム入力を実行しています: {params}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)

            # Guard against initialization failures returning an error dict or None
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return

            browser = browser_data.get("browser")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(params["url"], wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            for selector, value in params["inputs"].items():
                await page.fill(selector, value)
                logger.info(f"フォーム '{selector}' に '{value}' を入力しました")
            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            logger.error(f"フォーム入力中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def execute_extract_content(self, params, use_own_browser=False, headless=False, 
                                       save_to_file=False, file_path=None, format_type='json',
                                       maintain_browser_session=False, tab_selection_strategy="new_tab"):
        """コンテンツ抽出を実行"""
        try:
            logger.info(f"コンテンツ抽出を実行しています: {params}")
            
            # Browser Settingsと一貫したブラウザ初期化方法を使用
            browser_data = await self.browser_manager.initialize_custom_browser(
                use_own_browser=use_own_browser, 
                headless=headless,
                tab_selection_strategy=tab_selection_strategy
            )

            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return {"error": error_msg}

            browser = browser_data.get("browser")
            if not browser:
                logger.error("ブラウザインスタンスが初期化されていません")
                return {"error": "ブラウザインスタンスが初期化されていません"}
                
            # タブ選択戦略に基づいてタブを取得
            context, page, is_new = await self.browser_manager.get_or_create_tab(tab_selection_strategy)
            if is_new:
                logger.info("新しいタブを作成しました")
            else:
                logger.info("既存のタブを再利用します")
            
            # URLに移動
            logger.info(f"URLに移動します: {params['url']}")
            await page.goto(params["url"], wait_until="domcontentloaded")
            try:
                # ネットワークアイドル待ち（タイムアウト設定）
                await page.wait_for_load_state("networkidle", timeout=10000)
            except Exception as e:
                logger.warning(f"ネットワークアイドル状態に達しませんでしたが、続行します: {e}")
            
            # 結果を格納する辞書
            content = {}
            extracted_data = {}
            
            # セレクター情報に基づいてデータを抽出
            if isinstance(params["selectors"], list):
                for selector in params["selectors"]:
                    elements = await page.query_selector_all(selector)
                    texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                    content[selector] = texts
                    
            elif isinstance(params["selectors"], dict):
                for key, selector_info in params["selectors"].items():
                    selector = selector_info if isinstance(selector_info, str) else selector_info.get("selector")
                    extraction_type = "text" if isinstance(selector_info, str) else selector_info.get("type", "text")
                    attribute = None if isinstance(selector_info, str) else selector_info.get("attribute")
                    
                    try:
                        locator = page.locator(selector)
                        count = await locator.count()
                        
                        if count > 0:
                            if extraction_type == "text":
                                content[key] = await locator.text_content() if count == 1 else [await locator.nth(i).text_content() for i in range(count)]
                            elif extraction_type == "inner_text":
                                content[key] = await locator.inner_text() if count == 1 else [await locator.nth(i).inner_text() for i in range(count)]
                            elif extraction_type == "html":
                                content[key] = await locator.inner_html() if count == 1 else [await locator.nth(i).inner_html() for i in range(count)]
                            elif extraction_type == "attribute" and attribute:
                                content[key] = await locator.get_attribute(attribute) if count == 1 else [await locator.nth(i).get_attribute(attribute) for i in range(count)]
                            elif extraction_type == "count":
                                content[key] = count
                    except Exception as e:
                        logger.error(f"セレクター '{selector}' の抽出中にエラーが発生: {e}")
                        content[key] = f"エラー: {str(e)}"
            else:
                selector = params["selectors"]
                elements = await page.query_selector_all(selector)
                texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                content[selector] = texts

            # メタデータを追加
            extracted_data = {
                "content": content,
                "metadata": {
                    "url": params["url"],
                    "timestamp": datetime.now().isoformat(),
                    "selectors": params["selectors"]
                }
            }

            # 将来の参照用にデータを保存
            self.last_extracted_content = extracted_data
            
            # データを保存（リクエストされた場合）
            if save_to_file:
                save_result = await self.save_extracted_content(file_path, format_type)
                extracted_data["saved"] = save_result
            
            logger.info("抽出されたコンテンツ:")
            logger.info(json.dumps(content, indent=2, ensure_ascii=False))
            
            # 維持フラグがなければタブを閉じる
            if not maintain_browser_session:
                await page.close()
                if not browser_data.get("is_cdp", False) and "playwright" in browser_data:
                    await browser_data["playwright"].stop()
                
            return extracted_data
            
        except Exception as e:
            logger.error(f"コンテンツ抽出中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return {"error": str(e), "traceback": traceback.format_exc()}

    async def save_extracted_content(self, file_path=None, format_type='json'):
        """最後に抽出したコンテンツをファイルに保存する"""
        if not hasattr(self, 'last_extracted_content') or not self.last_extracted_content:
            logger.error("保存するコンテンツがありません。先に extract_content を実行してください。")
            return {"success": False, "message": "保存するコンテンツがありません"}
        
        try:
            save_path = file_path or self._generate_default_save_path(format_type)
            self._save_extracted_data_to_file(self.last_extracted_content, save_path, format_type)
            logger.info(f"データを保存しました: {save_path}")
            return {"success": True, "message": f"データを保存しました: {save_path}", "file_path": save_path}
        except Exception as e:
            logger.error(f"データ保存中にエラーが発生しました: {e}")
            logger.error(traceback.format_exc())
            return {"success": False, "message": f"エラー: {str(e)}"}

    def _generate_default_save_path(self, format_type):
        """デフォルトの保存パスを生成"""
        data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
        os.makedirs(data_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return os.path.join(data_dir, f"extracted_content_{timestamp}.{format_type}")

    def _save_extracted_data_to_file(self, data, file_path, format_type):
        """データを指定された形式でファイルに保存"""
        if file_path.endswith('.json') or format_type == 'json':
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif file_path.endswith('.csv') or format_type == 'csv':
            import csv
            content = data.get("content", {})
            flattened_data = {}
            for key, value in content.items():
                if isinstance(value, list):
                    for i, item in enumerate(value):
                        flattened_data[f"{key}_{i+1}"] = str(item)
                else:
                    flattened_data[key] = str(value)
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(flattened_data.keys())
                writer.writerow(flattened_data.values())

    async def execute_complex_sequence(self, params, use_own_browser=False, headless=False):
        """複雑なシーケンスを実行"""
        try:
            logger.info(f"複雑なシーケンスを実行しています: {params}")
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return
            browser = browser_data.get("browser")
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            page = await context.new_page()
            await page.goto(params["url"], wait_until="domcontentloaded")
            await page.wait_for_load_state("networkidle")
            for step in params["steps"]:
                action = step["action"]
                args = step.get("args", [])
                logger.info(f"実行中: {action} {args}")

                if action == "command" and args and args[0].startswith("http"):
                    await page.goto(args[0], wait_until="domcontentloaded")
                    await page.wait_for_load_state("networkidle")
                    logger.info(f"ナビゲートしました: {args[0]}")
                elif action == "wait_for_navigation":
                    await page.wait_for_load_state("networkidle")
                    logger.info("ナビゲーションが完了しました。")
                elif action == "fill_form" and len(args) >= 2:
                    selector, value = args[0], args[1]
                    await page.fill(selector, value)
                    logger.info(f"フォーム '{selector}' に '{value}' を入力しました")
                elif action == "click" and args:
                    selector = args[0]
                    await page.click(selector)
                    logger.info(f"要素 '{selector}' をクリックしました")
                elif action == "keyboard_press" and args:
                    key = args[0]
                    await page.keyboard.press(key)
                    logger.info(f"キー '{key}' を押しました")
                elif action == "extract_content":
                    selectors = args if args else ["h1", "h2", "h3", "p"]
                    content = {}
                    for selector in selectors:
                        elements = await page.query_selector_all(selector)
                        texts = [await element.text_content() for element in elements if (await element.text_content()).strip()]
                        content[selector] = texts
                    logger.info("抽出されたコンテンツ:")
                    logger.info(json.dumps(content, indent=2, ensure_ascii=False))

                logger.info("コマンドを実行しました。次のコマンドは3秒後...")
                await asyncio.sleep(3)

            await page.close()
            if not browser_data.get("is_cdp", False):
                await browser_data["playwright"].stop()
        except Exception as e:
            logger.error(f"複雑なシーケンス実行中にエラーが発生しました: {e}")
            import traceback
            logger.error(traceback.format_exc())

    async def execute_json_commands(self, commands_data, use_own_browser=False, headless=False, action_name=None, params=None, tab_selection=None):
        """Execute JSON or YAML commands for browser automation."""
        try:
            logger.debug(f"commands_data type: {type(commands_data)}")
            logger.debug(f"commands_data value: {commands_data}")
            
            logger.debug(f"initial keep_tab_open state: {commands_data.get('keep_tab_open', 'Not Set')}")
            
            action_type = None
            keep_tab_open = None
            
            if isinstance(commands_data, str) and (commands_data.endswith('.txt') or commands_data.endswith('.yml') or commands_data.endswith('.yaml')):
                try:
                    logger.info(f"Loading commands from file: {commands_data}")
                    
                    if commands_data.endswith('llms.txt'):
                        logger.debug(f"Processing llms.txt file: {commands_data}")
                        loader = InstructionLoader(local_path=commands_data)
                        result = loader.load_instructions()
                        
                        logger.debug(f"InstructionLoader result: {result}")
                        logger.debug(f"Number of instructions loaded: {len(result.instructions) if hasattr(result, 'instructions') else 'None'}")
                        
                        if not result.success:
                            logger.error(f"Failed to load instructions: {result.error}")
                            return
                            
                        logger.debug(f"Searching for action name: {action_name}")
                        action = next((instr for instr in result.instructions 
                                       if isinstance(instr, dict) and 'name' in instr and instr['name'] == action_name), None)
                        
                        logger.debug(f"Action found: {action is not None}")
                        if action:
                            action_type = action.get('type')
                            keep_tab_open = action.get('keep_tab_open', False)
                            
                            flow = action.get('flow', [])
                            commands_data = {
                                'commands': flow,
                                'action_type': action_type,
                                'keep_tab_open': keep_tab_open,
                                'slowmo': action.get('slowmo', 1000)
                            }
                            logger.debug(f"Extracted keep_tab_open from action: {keep_tab_open}")

                    else:
                        commands_data = load_yaml_from_file(commands_data)
                    
                except Exception as e:
                    logger.error(f"Error processing file {commands_data}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return
            
            if isinstance(commands_data, dict) and 'keep_tab_open' in commands_data:
                logger.debug(f"keep_tab_open from commands_data: {commands_data['keep_tab_open']}")
            
            action_type = action_type or commands_data.get("action_type", "unlock-future")
            commands = commands_data.get("commands", [])
            slowmo = commands_data.get("slowmo", 1000)
            
            if keep_tab_open is None:
                keep_tab_open = commands_data.get("keep_tab_open", True)
                logger.debug(f"default keep_tab_open value: {keep_tab_open}")
                if keep_tab_open is None:
                    keep_tab_open = True 
                    logger.debug(f"1.Setting keep_tab_open to True")
                    if action_type == "unlock-future" and keep_tab_open:
                        keep_tab_open = True
                        logger.debug(f"Setting keep_tab_open to True for unlock-future")
                    else:
                        keep_tab_open = True
                        logger.debug(f"2.Setting keep_tab_open to True")
                    
            logger.debug(f"Final decision - Action Type: {action_type}, Keep Tab Open: {keep_tab_open}")
            logger.debug(f"'keep_tab_open' in commands_data: {'keep_tab_open' in commands_data}")
            if 'keep_tab_open' in commands_data:
                logger.debug(f"commands_data['keep_tab_open'] = {commands_data['keep_tab_open']}")
            
            if not commands:
                logger.error("No commands found in the provided data")
                return
                
            logger.info(f"Executing {len(commands)} commands of type: {action_type}")
            
            browser_data = await self.browser_manager.initialize_custom_browser(use_own_browser, headless)

            # Guard against initialization failures returning an error dict or None
            if not browser_data or (isinstance(browser_data, dict) and browser_data.get("status") == "error"):
                error_msg = browser_data.get("message", "不明なエラーでブラウザを初期化できませんでした") if isinstance(browser_data, dict) else "ブラウザデータが返されませんでした"
                logger.error(f"ブラウザ初期化エラー: {error_msg}")
                return

            browser = browser_data.get("browser")
            
            tab_strategy = tab_selection or commands_data.get('tab_selection_strategy', 'new_tab')
            logger.debug(f"Initial tab selection strategy: {tab_strategy}, from arg: {tab_selection}")
            
            context, page, is_new = await self.browser_manager.get_or_create_tab(tab_strategy)
            logger.info(f"{'新しい' if is_new else '既存の'}タブを使用します (タブ選択戦略: {tab_strategy})")
            
            await self.browser_manager.highlight_automated_tab(page)
            
            try:
                for i, cmd in enumerate(commands, 1):
                    action = cmd.get("action", "")
                    
                    logger.info(f"Command {i}/{len(commands)}: {action}")
                    logger.info(f"Details: {json.dumps(cmd, indent=2, ensure_ascii=False)}")
                    
                    if action == "command":
                        url = cmd.get("url") or (cmd.get("args", [""])[0] if "args" in cmd and cmd["args"] else "")
                        if not url:
                            logger.warning("Missing URL in command action, skipping...")
                            continue
                        
                        await page.goto(url)
                        logger.info(f"Navigated to: {url}")
                        
                        if 'wait_for' in cmd:
                            await page.wait_for_selector(cmd['wait_for'])
                            logger.info(f"Waited for selector: {cmd['wait_for']}")
                    
                    elif action == "click":
                        selector = cmd.get("selector") or (cmd.get("args", [""])[0] if "args" in cmd and cmd["args"] else "")
                        if not selector:
                            logger.warning("Missing selector for click action, skipping...")
                            continue
                            
                        wait_for_navigation = cmd.get("wait_for_navigation", False)
                        
                        await page.click(selector)
                        logger.info(f"Clicked: {selector}")
                        
                        if wait_for_navigation:
                            await page.wait_for_load_state("networkidle")
                            logger.info("Waited for navigation to complete")
                    
                    elif action == "fill_form":
                        selector = cmd.get("selector") or (cmd.get("args", [""])[0] if "args" in cmd and len(cmd.get("args", [])) > 0 else "")
                        value = cmd.get("value") or (cmd.get("args", ["", ""])[1] if "args" in cmd and len(cmd.get("args", [])) > 1 else None)
                        
                        if not selector or value is None:
                            logger.warning("Missing selector or value for fill_form action, skipping...")
                            continue
                        
                        await page.fill(selector, value)
                        logger.info(f"Filled {selector} with: {value}")
                    
                    elif action == "keyboard_press":
                        key = cmd.get("key") or cmd.get("selector") or (cmd.get("args", [""])[0] if "args" in cmd and cmd["args"] else "")
                        
                        if not key:
                            logger.warning("Missing key for keyboard_press action, skipping...")
                            continue
                        
                        await page.keyboard.press(key)
                        logger.info(f"Pressed key: {key}")
                    
                    elif action == "wait":
                        timeout = cmd.get("timeout", 3000)
                        logger.info(f"Waiting for {timeout}ms...")
                        await asyncio.sleep(timeout / 1000)
                    
                    else:
                        logger.warning(f"Unknown action type: {action}, skipping...")
                    
                    await asyncio.sleep(slowmo / 1000)
                
                logger.debug(f"Final keep_tab_open value: {keep_tab_open}")
                
                logger.info("Execution complete.")
                if not keep_tab_open:
                    logger.info("Tab will close in 5 seconds...")
                    logger.info("(Press Ctrl+C to close earlier)")
                    await asyncio.sleep(5)
                else:
                    logger.info("Tab will remain open as requested.")
                
            except Exception as e:
                logger.error(f"Error during command execution: {e}")
                import traceback
                logger.error(traceback.format_exc())
                
            finally:
                if not keep_tab_open:
                    await page.close()
                    logger.info("タブを閉じました")
                else:
                    logger.info("タブを開いたままにしました（keep_tab_open: true）")
        
        except Exception as e:
            logger.error(f"Error in execute_json_commands: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
        logger.info("変換されたコマンド一覧:")
        for i, cmd in enumerate(commands):
            logger.info(f"  コマンド {i+1}:")
            logger.info(f"  - アクション: {cmd.get('action', '不明')}")
            logger.info(f"  - 引数: {cmd.get('args', [])}")
            logger.info(f"  - セレクタ: {cmd.get('selector', '未設定')}")
            logger.info(f"  - その他パラメータ: {[k for k in cmd.keys() if k not in ['action', 'args', 'selector']]}")
