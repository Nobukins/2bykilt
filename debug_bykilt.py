import asyncio
import json
import os
import sys
import re
from pathlib import Path
import argparse
from dotenv import load_dotenv
import subprocess  # Ensure subprocess is imported
from src.utils.app_logger import logger

# Load environment variables with error handling
try:
    load_dotenv()
    logger.info("✅ Environment variables loaded successfully")
except Exception as e:
    logger.warning(f"⚠️ Warning: Error loading .env file: {e}")

# 省略可能な依存関係のチェック
HAVE_PSUTIL = False
try:
    import psutil
    HAVE_PSUTIL = True
except ImportError:
    pass

# グローバル変数でブラウザインスタンスを追跡
chrome_process = None
global_browser = None
global_playwright = None

async def initialize_custom_browser(use_own_browser=False, headless=False):
    """Initialize a browser instance with optional custom profile or connect via CDP."""
    global chrome_process, global_browser, global_playwright
    
    # すでにブラウザインスタンスが存在する場合はそれを返す
    if global_browser is not None:
        logger.info("✅ 既存のブラウザインスタンスを再利用します")
        return {"browser": global_browser, "playwright": global_playwright, "is_cdp": True}
    
    from playwright.async_api import async_playwright
    import subprocess
    
    playwright = await async_playwright().start()
    global_playwright = playwright
    
    chrome_debugging_port = os.getenv("CHROME_DEBUGGING_PORT", "9222")
    chrome_path = os.getenv("CHROME_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    
    # ユーザーデータディレクトリの確認
    chrome_user_data = os.getenv("CHROME_USER_DATA")
    if not chrome_user_data or chrome_user_data.strip() == "":
        chrome_user_data = os.path.expanduser("~/Library/Application Support/Google/Chrome")
        logger.warning(f"⚠️ CHROME_USER_DATA が設定されていないため、デフォルト値を使用します: {chrome_user_data}")
    
    if use_own_browser:
        # Chromeが実行中かチェック
        chrome_running = False
        if HAVE_PSUTIL:
            chrome_running = any("Google Chrome" in p.name() for p in psutil.process_iter(['name']))
        
        if chrome_running:
            logger.warning("⚠️ Chromeが既に実行中です。デバッグポートを有効にして接続を試みます...")
            # 既存のChromeを一度閉じずに、タイムアウトを設定してCDPに接続を試みる
            try:
                browser = await playwright.chromium.connect_over_cdp(
                    endpoint_url=f'http://localhost:{chrome_debugging_port}',
                    timeout=3000  # 3秒のタイムアウト
                )
                logger.info(f"✅ 既存のChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
                global_browser = browser
                
                # Return the default context if available
                default_context = browser.contexts[0] if browser.contexts else None
                return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True}
            except Exception:
                # 失敗したら既存のChromeをデバッグモードで再起動するか確認
                logger.warning("\n⚠️ 既存のChromeに接続できませんでした。")
                logger.warning("既存のChromeを閉じてデバッグモードで再起動しますか？")
                logger.warning("⚠️ これにより、現在開いているすべてのChromeタブが閉じられます。")
                result = input("続行しますか？ (y/n): ").lower().startswith('y')
                
                if result:
                    # ユーザーが確認したので、Chromeを終了して再起動
                    logger.info("既存のChromeインスタンスを終了しています...")
                    if sys.platform == 'darwin':  # macOS
                        subprocess.run(['killall', 'Google Chrome'], stderr=subprocess.DEVNULL)
                    elif sys.platform == 'win32':  # Windows
                        subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], stderr=subprocess.DEVNULL)
                    else:  # Linux and others
                        subprocess.run(['killall', 'chrome'], stderr=subprocess.DEVNULL)
                    
                    logger.info("Chromeが完全に終了するのを待っています...")
                    await asyncio.sleep(2)
                else:
                    logger.info("新しいChromeウィンドウの開始を試みます...")
        
        # 新しいChromeインスタンスを起動（既存が閉じられたか、ユーザーが拒否した場合）
        cmd_args = [
            chrome_path,
            f"--remote-debugging-port={chrome_debugging_port}",
            "--no-first-run",
            "--no-default-browser-check"
        ]
        
        # ユーザーデータディレクトリの追加
        if chrome_user_data and chrome_user_data.strip():
            cmd_args.append(f"--user-data-dir={chrome_user_data}")
            logger.info(f"📁 ユーザーデータディレクトリを使用: {chrome_user_data}")
        
        logger.info(f"Chromeを起動しています: {' '.join(cmd_args)}")
        chrome_process = subprocess.Popen(cmd_args)
        logger.info(f"🔄 デバッグモードでChromeを起動しました (ポート {chrome_debugging_port})")
        await asyncio.sleep(3)  # Chromeが起動する時間を確保

        # 接続を再試行
        try:
            browser = await playwright.chromium.connect_over_cdp(
                endpoint_url=f'http://localhost:{chrome_debugging_port}'
            )
            logger.info(f"✅ 起動したChromeインスタンスに接続しました (ポート {chrome_debugging_port})")
            global_browser = browser
            
            # Return the default context if available
            default_context = browser.contexts[0] if browser.contexts else None
            return {"browser": browser, "context": default_context, "playwright": playwright, "is_cdp": True}
        except Exception as e:
            logger.warning(f"⚠️ 起動したChromeへの接続に失敗しました: {e}")
            logger.warning("新しいブラウザインスタンスの起動にフォールバックします...")
    
    # フォールバック: 通常のPlaywright管理ブラウザを使用
    browser = await playwright.chromium.launch(headless=headless)
    context = await browser.new_context()
    return {"browser": browser, "context": context, "playwright": playwright, "is_cdp": False}

async def cleanup_resources():
    """リソースをクリーンアップする"""
    global global_browser, global_playwright
    
    if global_browser:
        logger.info("🧹 ブラウザインスタンスをクリーンアップしています...")
        try:
            # 明示的に接続を閉じないでリソースのみ解放
            # await global_browser.close()
            # これによりChromeウィンドウは開いたままになる
            await global_playwright.stop()
        except Exception as e:
            logger.error(f"クリーンアップ中にエラーが発生しました: {e}")
        
        global_browser = None
        global_playwright = None

async def test_llm_response(json_file_path, use_own_browser=False, headless=False):
    """LLMレスポンスのJSONファイルを読み込んでPlaywrightで直接処理する"""
    logger.info(f"Settings: Use Own Browser={use_own_browser}, Headless={headless}")
    
    try:
        # JSONファイルを読み込み
        with open(json_file_path, 'r') as f:
            content = f.read()
            # JSONをパース
            try:
                response_data = json.loads(content)
                logger.info("パースされたJSON:")
                logger.info(json.dumps(response_data, indent=2))
            except json.JSONDecodeError as e:
                # JSON形式でない場合、JSONブロックを探す
                json_blocks = re.findall(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
                if not json_blocks:
                    logger.error(f"JSONのパースに失敗し、JSONブロックも見つかりませんでした: {e}")
                    return
                # 最初のJSONブロックを処理
                try:
                    response_data = json.loads(json_blocks[0].strip())
                    logger.info("JSONブロックからパースされたデータ:")
                    logger.info(json.dumps(response_data, indent=2))
                except json.JSONDecodeError as e2:
                    logger.error(f"JSONブロックのパースにも失敗しました: {e2}")
                    logger.error(f"問題のあるJSON文字列: {json_blocks[0][:100]}...")
                    return
        
        # スクリプト名とパラメータを取得
        if "script_name" in response_data:
            script_name = response_data["script_name"]
            params = response_data.get("params", {})
            logger.info(f"\n実行するスクリプト: {script_name}")
            logger.info(f"パラメータ: {params}")
            
            # Playwrightを使用して処理
            if script_name == "search-beatport" and "query" in params:
                await execute_beatport_search(params["query"], use_own_browser, headless)
            elif script_name == "search-google" and "query" in params:
                await execute_google_search(params["query"], use_own_browser, headless)
            elif script_name == "go_to_url":
                url = params.get("url", "")
                if url:
                    await execute_goto_url(url, use_own_browser, headless)
                else:
                    logger.error("URLが指定されていません")
            elif script_name == "form_input":
                await execute_form_input(params, use_own_browser, headless)
            elif script_name == "extract_content":
                await execute_extract_content(params, use_own_browser, headless)
            elif script_name == "complex_sequence":
                await execute_complex_sequence(params, use_own_browser, headless)
            else:
                logger.error(f"未対応のスクリプト名: {script_name}")
        # コマンドが含まれている場合
        elif "commands" in response_data:
            await execute_commands(response_data["commands"], use_own_browser, headless)
        
        else:
            logger.error("\n認識可能なフォーマットではありません。")
            logger.error("JSONには 'script_name' または 'commands' が必要です。")
    except Exception as e:
        logger.error(f"エラーが発生しました: {e}")

async def execute_commands(commands, use_own_browser=False, headless=False):
    """Execute a list of commands in the browser."""
    logger.info("\nコマンドを実行しています:")
    for i, cmd in enumerate(commands, 1):
        logger.info(f" {i}. {cmd['action']}: {cmd.get('args', [])}")

    try:
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Use the default context for CDP browsers to ensure new tabs appear in the existing window
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # Create a new tab in the context
        page = await context.new_page()
        await setup_element_indexer(page)

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
                logger.info("\n抽出されたコンテンツ:")
                logger.info(json.dumps(content, indent=2, ensure_ascii=False))

            logger.info("\nコマンドを実行しました。次のコマンドは3秒後...")
            await asyncio.sleep(3)

        # タブを閉じるが、ブラウザは開いたままにする
        await page.close()
        
        # Only stop playwright if this was not a CDP connection
        if not browser_data.get("is_cdp", False):
            await browser_data["playwright"].stop()

    except Exception as e:
        logger.error(f"\nコマンド実行中にエラーが発生しました: {e}")

async def execute_google_search(query, use_own_browser=False, headless=False):
    """Googleで検索を実行"""
    try:
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # Create a new tab in the context
        page = await context.new_page()

        await page.goto("https://www.google.com/")
        search_input = await page.query_selector("input[name='q']")
        if search_input:
            await search_input.fill(query)
            await search_input.press("Enter")
            logger.info(f"検索クエリ「{query}」を入力しEnterを押しました")
        await page.wait_for_load_state("networkidle")
        logger.info("検索結果ページが読み込まれました")

        # Close the tab but keep the browser open
        await page.close()
        
        # Only stop playwright if not using CDP
        if not browser_data.get("is_cdp", False):
            await browser_data["playwright"].stop()

    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def execute_beatport_search(query, use_own_browser=False, headless=False):
    """Beatportで検索を実行"""
    try:
        logger.info(f"\nBeatportで「{query}」を検索します...")
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser_data["browser"].contexts[0] if browser_data["browser"].contexts else await browser_data["browser"].new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data["context"]
        
        page = await context.new_page()
        
        # Beatportに移動
        await page.goto("https://www.beatport.com/")
        
        # Cookieの承認をクリック
        try:
            await page.get_by_role("button", name="I Accept").click()
            logger.info("Cookieの承認ボタンをクリックしました")
        except Exception as e:
            logger.error(f"Cookieの承認ボタンの検索中にエラー: {e}")
        
        # 検索アイコンをクリック（サイトのレイアウトによる）
        try:
            # 検索ボタンを探す（サイトの構造に依存）
            search_button = page.get_by_test_id("header-search-input")
            await search_button.click()
            logger.info("検索ボタンをクリックしました")
        except Exception as e:
            logger.error(f"検索ボタンの検索中にエラー: {e}")
            logger.info("検索フィールドを直接探します...")
        
        # 検索入力フィールドを探して入力
        try:
            search_input = page.get_by_test_id("header-search-input")
            await search_input.fill(query)
            await search_input.press("Enter")
            logger.info(f"検索クエリ「{query}」を入力しEnterを押しました")
        except Exception as e:
            logger.error(f"検索フィールドの操作中にエラー: {e}")
        
        # 検索結果が表示されるのを待つ
        await page.wait_for_load_state("networkidle")
        logger.info("検索結果ページが読み込まれました")
        
        # ユーザーに検査する時間を与える
        logger.info("\n実行完了。ブラウザは30秒後に閉じられます...")
        logger.info("(Ctrl+Cで早く終了できます)")
        await asyncio.sleep(30)
        await context.close()
        if browser_data["browser"]:
            await browser_data["browser"].close()
        await browser_data["playwright"].stop()
    
    except ImportError:
        logger.error("\nPlaywrightがインストールされていません。")
        logger.error("以下のコマンドでインストールできます:")
        logger.error("pip install playwright")
        logger.error("playwright install")
    
    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def execute_goto_url(url, use_own_browser=False, headless=False):
    """指定したURLに移動"""
    try:
        logger.info(f"\n{url} に移動します...")
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser_data["browser"].contexts[0] if browser_data["browser"].contexts else await browser_data["browser"].new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data["context"]
        
        page = await context.new_page()
        
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        logger.info(f"ページに移動しました: {url}")
        
        # ユーザーに検査する時間を与える
        logger.info("\n実行完了。ブラウザは30秒後に閉じられます...")
        logger.info("(Ctrl+Cで早く終了できます)")
        await asyncio.sleep(30)
        await context.close()
        if browser_data["browser"]:
            await browser_data["browser"].close()
        await browser_data["playwright"].stop()
    
    except ImportError:
        logger.error("\nPlaywrightがインストールされていません。")
        logger.error("以下のコマンドでインストールできます:")
        logger.error("pip install playwright")
        logger.error("playwright install")
    
    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def execute_form_input(params, use_own_browser=False, headless=False):
    """フォーム入力を実行"""
    try:
        url = params.get("url")
        inputs = params.get("inputs", [])
        submit_selector = params.get("submit_selector")
        logger.info(f"\n{url} のフォームに入力します...")
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # 新しいタブを開く
        page = await context.new_page()
        
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        logger.info(f"ページに移動しました: {url}")
        
        # 各フィールドに入力
        for input_data in inputs:
            selector = input_data.get("selector")
            value = input_data.get("value")
            if selector and value:  # Fix: removed Japanese と
                await page.fill(selector, value)
                logger.info(f"フィールド '{selector}' に '{value}' を入力しました")
        
        # 送信ボタンをクリック
        if submit_selector:
            await page.click(submit_selector)
            logger.info(f"送信ボタン '{submit_selector}' をクリックしました")
            await page.wait_for_load_state("networkidle")
        
        # ユーザーに検査する時間を与える
        logger.info("\n実行完了。30秒後にタブを閉じます...")
        logger.info("(Ctrl+Cで早く終了できます)")
        await asyncio.sleep(30)
        
        # タブのみを閉じる
        await page.close()
    
    except ImportError:
        logger.error("\nPlaywrightがインストールされていません。")
        logger.error("以下のコマンドでインストールできます:")
        logger.error("pip install playwright")
        logger.error("playwright install")
    
    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def execute_extract_content(params, use_own_browser=False, headless=False):
    """コンテンツ抽出を実行"""
    try:
        url = params.get("url")
        selectors = params.get("selectors", ["h1", "h2", "h3", "p"])
        logger.info(f"\n{url} からコンテンツを抽出します...")
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser_data["browser"].contexts[0] if browser_data["browser"].contexts else await browser_data["browser"].new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data["context"]
        
        page = await context.new_page()
        
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        logger.info(f"ページに移動しました: {url}")
        
        # コンテンツを抽出
        content = {}
        for selector in selectors:
            elements = await page.query_selector_all(selector)
            texts = []
            for element in elements:
                text = await element.text_content()
                if text.strip():
                    texts.append(text.strip())
            content[selector] = texts
        
        logger.info("\n抽出されたコンテンツ:")
        logger.info(json.dumps(content, indent=2, ensure_ascii=False))
        
        # ユーザーに検査する時間を与える
        logger.info("\n実行完了。ブラウザは30秒後に閉じられます...")
        logger.info("(Ctrl+Cで早く終了できます)")
        await asyncio.sleep(30)
        await context.close()
        if browser_data["browser"]:
            await browser_data["browser"].close()
        await browser_data["playwright"].stop()
    
    except ImportError:
        logger.error("\nPlaywrightがインストールされていません。")
        logger.error("以下のコマンドでインストールできます:")
        logger.error("pip install playwright")
        logger.error("playwright install")
    
    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def execute_complex_sequence(params, use_own_browser=False, headless=False):
    """複雑なシーケンスを実行"""
    try:
        url = params.get("url")
        search_term = params.get("search_term")
        click_result_index = params.get("click_result_index", 0)
        logger.info(f"\n複雑なシーケンスを実行します... URL: {url}, 検索語: {search_term}")
        browser_data = await initialize_custom_browser(use_own_browser, headless)
        browser = browser_data["browser"]
        
        # Use the default context for CDP browsers
        if browser_data.get("is_cdp", False):
            context = browser.contexts[0] if browser.contexts else await browser.new_context()
            logger.info("✅ 既存のChromeウィンドウに新しいタブを作成します")
        else:
            context = browser_data.get("context") or await browser.new_context()
        
        # 新しいタブを開く
        page = await context.new_page()
        
        # URLに移動
        await page.goto(url)
        await page.wait_for_load_state("networkidle")
        logger.info(f"ページに移動しました: {url}")
        
        # 検索フォームに入力
        await page.fill('input[name="q"]', search_term)
        logger.info(f"検索語 '{search_term}' を入力しました")
        
        # Enterキーを押して検索
        await page.keyboard.press("Enter")
        await page.wait_for_load_state("networkidle")
        logger.info("検索を実行しました")
        
        # 検索結果をクリック
        result_links = await page.query_selector_all('#search a')
        if result_links and len(result_links) > click_result_index:  # Fix: removed Japanese と
            await result_links[click_result_index].click()
            await page.wait_for_load_state("networkidle")
            logger.info(f"検索結果 {click_result_index + 1} 番目をクリックしました")
            
            # コンテンツを抽出
            content = {}
            for selector in ["h1", "p"]:
                elements = await page.query_selector_all(selector)
                texts = []
                for element in elements:
                    text = await element.text_content()
                    if text.strip():
                        texts.append(text.strip())
                content[selector] = texts
            
            logger.info("\n抽出されたコンテンツ:")
            logger.info(json.dumps(content, indent=2, ensure_ascii=False))
        else:
            logger.error(f"クリックする検索結果が見つかりませんでした")
        
        # ユーザーに検査する時間を与える
        logger.info("\n実行完了。30秒後にタブを閉じます...")
        logger.info("(Ctrl+Cで早く終了できます)")
        await asyncio.sleep(30)
        
        # タブのみを閉じる
        await page.close()
    
    except ImportError:
        logger.error("\nPlaywrightがインストールされていません。")
        logger.error("以下のコマンドでインストールできます:")
        logger.error("pip install playwright")
        logger.error("playwright install")
    
    except Exception as e:
        logger.error(f"\n実行エラー: {e}")

async def setup_element_indexer(page):
    """Setup element indexer with proper async handling."""
    await page.evaluate("""() => {
        // Clear existing indices
        document.querySelectorAll('.element-index-overlay').forEach(el => el.remove());
        
        // Get all visible elements
        const elements = Array.from(document.querySelectorAll('*'));
        const visibleElements = elements.filter(el => {
            const style = window.getComputedStyle(el);
            const rect = el.getBoundingClientRect();
            return style.display !== 'none' && 
                    style.visibility !== 'hidden' && 
                    rect.width > 0 && rect.height > 0;
        });
        
        // Add indices to elements
        visibleElements.forEach((el, i) => {
            // Determine if element is interactive
            const isInteractive = ['A', 'BUTTON', 'INPUT', 'SELECT', 'TEXTAREA'].includes(el.tagName) || 
                                el.getAttribute('role') === 'button' || 
                                parseInt(el.getAttribute('tabindex') || '-1') >= 0;
            
            // Create index prefix based on interactivity
            const prefix = isInteractive ? `${i}[:]` : `_[:]`;
            
            // Create overlay element with index
            const overlay = document.createElement('div');
            overlay.className = 'element-index-overlay';
            overlay.textContent = prefix + el.tagName.toLowerCase();
            overlay.style.cssText = `
                position: absolute;
                background-color: ${isInteractive ? 'rgba(0, 255, 0, 0.7)' : 'rgba(255, 0, 0, 0.7)'};
                color: white;
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 12px;
                z-index: 10000;
                pointer-events: none;
            `;
            
            // Position the overlay
            const rect = el.getBoundingClientRect();
            overlay.style.top = `${window.scrollY + rect.top}px`;
            overlay.style.left = `${window.scrollX + rect.left}px`;
            
            // Add to document
            document.body.appendChild(overlay);
            
            // Store element data with selector for interaction
            if (!window.__elementIndices) window.__elementIndices = [];
            window.__elementIndices[i] = {
                index: i,
                isInteractive: isInteractive,
                tagName: el.tagName.toLowerCase(),
                element: el
            };
        });
        
        return window.__elementIndices ? window.__elementIndices.length : 0;
    }""")

def show_help():
    logger.info("LLMレスポンスデバッガ")
    logger.info("使用法: python debug_bykilt.py <llm_response_file>")
    logger.info("\nオプション:")
    logger.info("  --list        利用可能なサンプルを一覧表示")
    logger.info("  --use-own-browser Use your own browser profile")
    logger.info("  --headless        Run browser in headless mode")
    logger.info("\n例:")
    logger.info("  python debug_bykilt.py external/samples/navigate_url.json")

def list_samples():
    samples_dir = Path("external/samples")
    if samples_dir.exists():
        for sample_file in samples_dir.glob("*.json"):
            with open(sample_file, "r") as f:
                try:
                    data = json.load(f)
                    script_name = data.get("script_name", "unknown")
                    params = data.get("params", {})
                    logger.info(f"- {sample_file.name} ({script_name}): {params}")
                except json.JSONDecodeError:
                    logger.error(f"- {sample_file.name} (解析エラー)")
    else:
        logger.error(f"サンプルディレクトリが見つかりません: {samples_dir}")
        logger.info("ディレクトリを作成するには:")
        logger.info(f"  mkdir -p {samples_dir}")

if __name__ == "__main__":
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
    
    if args.list:
        list_samples()
        sys.exit(0)
    
    if not args.file:
        parser.print_help()
        sys.exit(1)
    
    try:
        json_file_path = args.file
        asyncio.run(test_llm_response(json_file_path, args.use_own_browser, args.headless))
    except KeyboardInterrupt:
        logger.error("\n🛑 実行が中断されました。リソースをクリーンアップしています...")
    finally:
        # プログラム終了時にリソースをクリーンアップ
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(cleanup_resources())
            loop.close()
            logger.info("✅ リソースのクリーンアップが完了しました")
        except Exception as e:
            logger.error(f"⚠️ クリーンアップ中にエラーが発生しました: {e}")