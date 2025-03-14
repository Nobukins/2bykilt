#!/usr/bin/env python
# filepath: /Users/nobuaki/Documents/Github/2bykilt/debug_bykilt.py

import asyncio
import json
import os
import sys
import re
from pathlib import Path

async def test_llm_response(json_file_path):
    """
    LLMレスポンスのJSONファイルを読み込んでPlaywrightで直接処理する
    """
    print(f"JSONファイル {json_file_path} を処理中...")
    
    try:
        # JSONファイルを読み込み
        with open(json_file_path, 'r') as f:
            content = f.read()
        
        # JSONをパース
        try:
            response_data = json.loads(content)
            print("パースされたJSON:")
            print(json.dumps(response_data, indent=2))
        except json.JSONDecodeError as e:
            # JSON形式でない場合、JSONブロックを探す
            json_blocks = re.findall(r'```(?:json)?\s*(.*?)```', content, re.DOTALL)
            if not json_blocks:
                print(f"JSONのパースに失敗し、JSONブロックも見つかりませんでした: {e}")
                returnj
            
            # 最初のJSONブロックを処理
            try:
                response_data = json.loads(json_blocks[0].strip())
                print("JSONブロックからパースされたデータ:")
                print(json.dumps(response_data, indent=2))
            except json.JSONDecodeError as e2:
                print(f"JSONブロックのパースにも失敗しました: {e2}")
                print(f"問題のあるJSON文字列: {json_blocks[0][:100]}...")
                return
        
        # スクリプト名とパラメータを取得
        if "script_name" in response_data:
            script_name = response_data["script_name"]
            params = response_data.get("params", {})
            
            print(f"\n実行するスクリプト: {script_name}")
            print(f"パラメータ: {params}")
            
            # Playwrightを使用して処理
            if script_name == "search-beatport" and "query" in params:
                await execute_beatport_search(params["query"])
            elif script_name == "go_to_url":
                url = params.get("url", "")
                if url:
                    await execute_goto_url(url)
                elif "commands" in response_data:
                    await execute_commands(response_data["commands"])
                else:
                    print("URLが指定されていません")
            else:
                print(f"未対応のスクリプト名: {script_name}")
                if "commands" in response_data:
                    await execute_commands(response_data["commands"])
        
        # コマンドが含まれている場合
        elif "commands" in response_data:
            await execute_commands(response_data["commands"])
        
        else:
            print("\n認識可能なフォーマットではありません。")
            print("JSONには 'script_name' または 'commands' が必要です。")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")

async def execute_commands(commands):
    """コマンドリストを実行"""
    print("\n実行するコマンド:")
    for i, cmd in enumerate(commands, 1):
        print(f" {i}. {cmd['action']}: {cmd.get('args', [])}")
    
    try:
        from playwright.async_api import async_playwright
        
        print("\nPlaywrightを使用してコマンドを実行中...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            for cmd in commands:
                action = cmd["action"]
                args = cmd.get("args", [])
                
                print(f"実行: {action} {args}")
                
                if action == "command" and args and args[0].startswith("http"):
                    # URLに移動
                    await page.goto(args[0])
                    print(f"ページに移動しました: {args[0]}")
                
                elif action == "wait_for_navigation":
                    # ナビゲーションの完了を待つ
                    try:
                        await page.wait_for_load_state("networkidle")
                        print("ページの読み込みが完了しました")
                    except Exception as e:
                        print(f"ナビゲーション待機中にエラーが発生しました: {e}")
            
            # ユーザーに検査する時間を与える
            print("\n実行完了。ブラウザは30秒後に閉じられます...")
            print("(Ctrl+Cで早く終了できます)")
            await asyncio.sleep(30)
    
    except ImportError:
        print("\nPlaywrightがインストールされていません。")
        print("以下のコマンドでインストールできます:")
        print("pip install playwright")
        print("playwright install")
    except Exception as e:
        print(f"\nコマンド実行エラー: {e}")

async def execute_beatport_search(query):
    """Beatportで検索を実行"""
    try:
        from playwright.async_api import async_playwright
        
        print(f"\nBeatportで「{query}」を検索します...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            # Beatportに移動
            await page.goto("https://www.beatport.com/")
            await page.wait_for_load_state("networkidle")
            
            # 検索アイコンをクリック（サイトのレイアウトによる）
            try:
                # 検索ボタンを探す（サイトの構造に依存）
                search_button = page.locator('button[data-testid="search-button"], .header-v2__search-button')
                await search_button.click()
                print("検索ボタンをクリックしました")
            except Exception as e:
                print(f"検索ボタンの検索中にエラー: {e}")
                print("検索フィールドを直接探します...")
            
            # 検索入力フィールドを探して入力
            try:
                search_input = page.locator('input[type="search"], input[placeholder*="Search"], .header-v2__search-input')
                await search_input.fill(query)
                await search_input.press("Enter")
                print(f"検索クエリ「{query}」を入力しEnterを押しました")
            except Exception as e:
                print(f"検索フィールドの操作中にエラー: {e}")
            
            # 検索結果が表示されるのを待つ
            await page.wait_for_load_state("networkidle")
            print("検索結果ページが読み込まれました")
            
            # ユーザーに検査する時間を与える
            print("\n実行完了。ブラウザは30秒後に閉じられます...")
            print("(Ctrl+Cで早く終了できます)")
            await asyncio.sleep(30)
    
    except ImportError:
        print("\nPlaywrightがインストールされていません。")
        print("以下のコマンドでインストールできます:")
        print("pip install playwright")
        print("playwright install")
    except Exception as e:
        print(f"\n実行エラー: {e}")

async def execute_goto_url(url):
    """指定したURLに移動"""
    try:
        from playwright.async_api import async_playwright
        
        print(f"\n{url} に移動します...")
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=False)
            page = await browser.new_page()
            
            await page.goto(url)
            await page.wait_for_load_state("networkidle")
            print(f"ページに移動しました: {url}")
            
            # ユーザーに検査する時間を与える
            print("\n実行完了。ブラウザは30秒後に閉じられます...")
            print("(Ctrl+Cで早く終了できます)")
            await asyncio.sleep(30)
    
    except ImportError:
        print("\nPlaywrightがインストールされていません。")
        print("以下のコマンドでインストールできます:")
        print("pip install playwright")
        print("playwright install")
    except Exception as e:
        print(f"\n実行エラー: {e}")

def show_help():
    print("LLMレスポンスデバッガ")
    print("使用法: python debug_bykilt.py <llm_response_file>")
    print("\nオプション:")
    print("  --help, -h    このヘルプメッセージを表示")
    print("\n例:")
    print("  python debug_bykilt.py external/sample_llm_response.json")

if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h"]:
        show_help()
        sys.exit(0 if sys.argv[1] in ["--help", "-h"] else 1)
    
    json_file_path = sys.argv[1]
    asyncio.run(test_llm_response(json_file_path))