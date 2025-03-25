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
    
    async def test_llm_response(self, json_file_path, use_own_browser=False, headless=False, session_id=None, tab_selection_strategy="new_tab"):
        """
        JSON形式のLLMレスポンスをテストします。
        
        Args:
            json_file_path: JSONファイルのパス
            use_own_browser: 独自のブラウザを使用するかどうか
            headless: ヘッドレスモードで実行するかどうか
            session_id: セッションID（オプション）
            tab_selection_strategy: タブ選択戦略 ("new_tab", "active_tab", "last_tab")
        """
        import json
        from src.modules.execution_debug_engine import ExecutionDebugEngine
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = json.loads(content)
            
            # コマンドの取得
            commands = data.get('commands', [])
            
            if not commands:
                return {"status": "error", "message": "実行するコマンドがありません"}
                
            # # 各コマンドをExecutionDebugEngine用の形式に変換
            # engine_commands = []
            # for cmd in commands:
            #     engine_command = {
            #         "action": cmd.get('type', ''),
            #         "args": []
            #     }
                
            #     # コマンドタイプごとの引数設定
            #     if cmd.get('type') == 'goto':
            #         engine_command["args"] = [cmd.get('url', '')]
            #     elif cmd.get('type') in ['click', 'wait_for_selector']:
            #         engine_command["args"] = [cmd.get('selector', '')]
            #     elif cmd.get('type') == 'fill':
            #         engine_command["args"] = [cmd.get('selector', ''), cmd.get('value', '')]
            #     elif cmd.get('type') == 'wait':
            #         engine_command["args"] = [cmd.get('timeout', 5000)]
            #     elif cmd.get('type') == 'keyboard_press':
            #         engine_command["args"] = [cmd.get('key', '')]
            #     # 必要に応じて他のタイプを追加
                
            #     engine_commands.append(engine_command)
            
            # ExecutionDebugEngineを使用してコマンドを実行
            engine = ExecutionDebugEngine()
            # await engine.execute_commands(engine_commands, use_own_browser, headless, tab_selection_strategy)
            await engine.execute_commands(commands, use_own_browser, headless, tab_selection_strategy)
            return {"status": "success", "message": "コマンドを実行しました"}
                
        except Exception as e:
            print(f"Error processing JSON: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
    
    async def setup_element_indexer(self, page):
        """ページ内の要素にインデックスを付けて視覚化"""
        await page.evaluate("""() => {
            const existingStyles = document.getElementById('element-indexer-styles');
            const existingOverlay = document.getElementById('element-indexer-overlay');
            if (existingStyles) existingStyles.remove();
            if (existingOverlay) existingOverlay.remove();

            const style = document.createElement('style');
            style.id = 'element-indexer-styles';
            style.innerHTML = `
                .element-index {
                    position: absolute;
                    background: rgba(255, 165, 0, 0.8);
                    color: white;
                    border-radius: 50%;
                    width: 22px;
                    height: 22px;
                    text-align: center;
                    line-height: 22px;
                    font-weight: bold;
                    font-size: 12px;
                    z-index: 10000;
                    pointer-events: none;
                }
                .element-highlight {
                    outline: 2px solid orange !important;
                    position: relative;
                }
            `;
            document.head.appendChild(style);

            const interactiveElements = document.querySelectorAll('a, button, input, select, textarea, [role="button"], [onclick]');
            let index = 1;

            interactiveElements.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.top < window.innerHeight && rect.bottom > 0 && rect.left < window.innerWidth && rect.right > 0) {
                    const marker = document.createElement('div');
                    marker.className = 'element-index';
                    marker.textContent = index++;
                    marker.style.top = (rect.top + window.scrollY) + 'px';
                    marker.style.left = (rect.left + window.scrollX) + 'px';
                    document.body.appendChild(marker);
                    el.classList.add('element-highlight');
                }
            });
        }""")
        print("✅ ページ内の要素にインデックスを付けました。")

    def show_help(self):
        """ヘルプ情報を表示"""
        help_text = """
        ╔══════════════════════════════════════════════╗
        ║                デバッグユーティリティヘルプ                ║
        ╚══════════════════════════════════════════════╝

        📋 基本コマンド:
        
          ▶ test_llm_response(json_file_path, ...)
            JSONファイルの指示に従ってブラウザ操作を実行します。
            - json_file_path: JSONファイルのパス
            - use_own_browser: 独自のブラウザを使用 (デフォルト: False)
            - headless: ヘッドレスモードで実行 (デフォルト: False)
            - tab_selection_strategy: "new_tab"/"active_tab"/"last_tab"
        
          ▶ setup_element_indexer(page)
            ページ内の要素に番号を付けて操作しやすくします。
            - page: Playwrightのページオブジェクト
        
          ▶ list_samples()
            利用可能なサンプルJSONファイルを一覧表示します。
        
        📄 JSONファイル形式:
        {
          "commands": [
            {"type": "goto", "url": "https://example.com"},
            {"type": "click", "selector": "#button-id"},
            {"type": "fill", "selector": "input[name=search]", "value": "検索キーワード"}
          ],
          "maintain_session": true  // セッションを維持するかどうか
        }
        """
        print(help_text)
        return help_text

    def list_samples(self):
        """サンプルJSONファイルの一覧を表示"""
        from pathlib import Path
        import json

        sample_dir = Path(__file__).parent.parent.parent / "samples" / "debug"
        if not sample_dir.exists():
            print(f"❌ サンプルディレクトリが見つかりません: {sample_dir}")
            return []

        sample_files = list(sample_dir.glob("*.json"))
        if not sample_files:
            print("❌ サンプルJSONファイルが見つかりません。")
            return []

        print(f"📋 利用可能なサンプルJSONファイル ({len(sample_files)}個):")
        samples_info = []
        for i, file_path in enumerate(sample_files):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                title = data.get('title', '無題')
                description = data.get('description', '説明なし')
                commands_count = len(data.get('commands', []))
                samples_info.append({
                    'path': str(file_path),
                    'title': title,
                    'description': description,
                    'commands_count': commands_count
                })
                print(f"\n{i+1}. {title}")
                print(f"   📄 ファイル: {file_path.name}")
                print(f"   📝 説明: {description}")
                print(f"   🔢 コマンド数: {commands_count}")
            except Exception as e:
                print(f"⚠️ {file_path.name} の読み込みに失敗: {e}")
        return samples_info

    def debug_command_structure(self, commands_data):
        """Debug helper to inspect command structure"""
        print("\n🔍 DEBUG COMMAND STRUCTURE:")
        print(f"Type: {type(commands_data)}")
        print(f"Contents: {json.dumps(commands_data, indent=2, ensure_ascii=False)}")
        
        if isinstance(commands_data, dict):
            action_type = commands_data.get("action_type", "unknown")
            commands = commands_data.get("commands", [])
            print(f"Action Type: {action_type}")
            print(f"Commands Count: {len(commands)}")
            
            if commands:
                print("\nFirst Command Structure:")
                print(json.dumps(commands[0], indent=2, ensure_ascii=False))
        
        return commands_data
