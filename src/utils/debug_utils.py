import json
import re
import asyncio
from pathlib import Path
from src.browser.browser_debug_manager import BrowserDebugManager
# Removed circular import from here

class DebugUtils:
    """デバッグツールのユーティリティ機能を提供するクラス"""
    
    def __init__(self, browser_manager=None):
        """ユーティリティの初期化"""
        # Allow passing an external browser manager
        self.browser_manager = browser_manager or BrowserDebugManager()
        # 循環参照を避けるため、ExecutionDebugEngineは必要な時に作成
    
    async def test_llm_response(self, json_file_path, use_own_browser=False, headless=False):
        """LLMレスポンスのJSONファイルを読み込んでPlaywrightで直接処理する"""
        print(f"Settings: Use Own Browser={use_own_browser}, Headless={headless}")
        
        # Import inside method to avoid circular imports
        from src.modules.execution_debug_engine import ExecutionDebugEngine
        # 循環参照を回避するためにここでエンジンを初期化
        engine = ExecutionDebugEngine()
        # Share the browser manager with the engine
        engine.browser_manager = self.browser_manager
        
        try:
            # JSONファイルを読み込み
            with open(json_file_path, 'r') as f:
                content = f.read()
                response_data = json.loads(content)
            
            # Process based on content structure
            if "commands" in response_data:
                # Direct execution of commands
                action_type = response_data.get("action_type", "browser-control")
                print(f"\nExecuting {action_type} commands...")
                await engine.execute_json_commands(response_data, use_own_browser, headless)
                return f"Successfully executed {action_type} commands"
            
            # Handle other formats (script_name, etc.)
            elif "script_name" in response_data:
                # Handle existing script logic
                if "script_name" in response_data:
                    script_name = response_data["script_name"]
                    params = response_data.get("params", {})
                    print(f"\n実行するスクリプト: {script_name}")
                    print(f"パラメータ: {params}")
                    
                    # Playwrightを使用して処理
                    if script_name == "search-beatport" and "query" in params:
                        await engine.execute_beatport_search(params["query"], use_own_browser, headless)
                    elif script_name == "search-google" and "query" in params:
                        await engine.execute_google_search(params["query"], use_own_browser, headless)
                    elif script_name == "go_to_url":
                        url = params.get("url", "")
                        if url:
                            await engine.execute_goto_url(url, use_own_browser, headless)
                        else:
                            print("URLが指定されていません")
                    elif script_name == "form_input":
                        await engine.execute_form_input(params, use_own_browser, headless)
                    elif script_name == "extract_content":
                        await engine.execute_extract_content(params, use_own_browser, headless)
                    elif script_name == "complex_sequence":
                        await engine.execute_complex_sequence(params, use_own_browser, headless)
                    else:
                        print(f"未対応のスクリプト名: {script_name}")
                # コマンドが含まれている場合
                elif "commands" in response_data:
                    await engine.execute_commands(response_data["commands"], use_own_browser, headless)
                
                else:
                    print("\n認識可能なフォーマットではありません。")
                    print("JSONには 'script_name' または 'commands' が必要です。")
                return f"Successfully executed script: {script_name}"
            
            else:
                print("❌ Unknown JSON format")
                return "Error: Unknown JSON format"
                
        except Exception as e:
            print(f"Error processing JSON: {e}")
            return f"Error: {str(e)}"
    
    async def setup_element_indexer(self, page):
        """ページ内の要素にインデックスを付けて視覚化"""
        # ...existing code...
    
    def show_help(self):
        """ヘルプ情報を表示"""
        # ...existing code...
    
    def list_samples(self):
        """サンプルJSONファイルの一覧を表示"""
        # ...existing code...
