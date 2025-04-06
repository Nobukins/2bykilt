import json
import re
import asyncio
from pathlib import Path
from src.browser.browser_debug_manager import BrowserDebugManager
from src.utils.app_logger import logger
from src.modules.execution_debug_engine import ExecutionDebugEngine

class DebugUtils:
    """デバッグツールのユーティリティ機能を提供するクラス"""
    
    def __init__(self, browser_manager=None):
        """ユーティリティの初期化"""
        # Allow passing an external browser manager
        self.browser_manager = browser_manager or BrowserDebugManager()
        # 循環参照を避けるため、ExecutionDebugEngineは必要な時に作成
    
    async def test_llm_response(self, json_file_path, use_own_browser=False, headless=False, session_id=None, tab_selection_strategy=None, keep_browser_open=False):
        """
        JSON形式のLLMレスポンスをテストします。
        
        Args:
            json_file_path: JSONファイルのパス
            use_own_browser: 独自のブラウザを使用するかどうか
            headless: ヘッドレスモードで実行するか
            session_id: セッションID（オプション）
            tab_selection_strategy: タブ選択戦略 ("new_tab", "active_tab", "last_tab")。None の場合はコマンドの設定を使用
            keep_browser_open: ブラウザを開いたままにするか
        """
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                commands_data = json.loads(content)
            
            logger.debug(f"JSON File Path: {json_file_path}")
            logger.debug(f"use_own_browser = {use_own_browser}")
            logger.debug(f"headless = {headless}")
            logger.debug(f"session_id = {session_id}")
            logger.debug(f"initial tab_selection_strategy param = {tab_selection_strategy}")
            
            cmd_tab_strategy = commands_data.get('tab_selection_strategy')
            if cmd_tab_strategy:
                logger.debug(f"Found strategy in commands: {cmd_tab_strategy}")
                if tab_selection_strategy is None:
                    tab_selection_strategy = cmd_tab_strategy
                    logger.debug(f"Using command-specified strategy: {tab_selection_strategy}")
            
            if tab_selection_strategy is None:
                tab_selection_strategy = "new_tab"
                logger.debug(f"Using default strategy: {tab_selection_strategy}")
            
            logger.debug(f"final tab_selection_strategy = {tab_selection_strategy}")
            logger.debug(f"keep_browser_open = {keep_browser_open}")
            
            # Fix: Create ExecutionDebugEngine without the browser_manager parameter
            execution_engine = ExecutionDebugEngine()
            
            if session_id:
                logger.info(f"Using saved session ID: {session_id}")
            
            await execution_engine.execute_json_commands(
                commands_data, 
                use_own_browser=use_own_browser, 
                headless=headless,
                tab_selection=tab_selection_strategy
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error in test_llm_response: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
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
        logger.info("✅ ページ内の要素にインデックスを付けました。")

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
        logger.info(help_text)
        return help_text

    def list_samples(self):
        """サンプルJSONファイルの一覧を表示"""
        from pathlib import Path
        import json

        sample_dir = Path(__file__).parent.parent.parent / "samples" / "debug"
        if not sample_dir.exists():
            logger.error(f"❌ サンプルディレクトリが見つかりません: {sample_dir}")
            return []

        sample_files = list(sample_dir.glob("*.json"))
        if not sample_files:
            logger.error("❌ サンプルJSONファイルが見つかりません。")
            return []

        logger.info(f"📋 利用可能なサンプルJSONファイル ({len(sample_files)}個):")
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
                logger.info(f"\n{i+1}. {title}")
                logger.info(f"   📄 ファイル: {file_path.name}")
                logger.info(f"   📝 説明: {description}")
                logger.info(f"   🔢 コマンド数: {commands_count}")
            except Exception as e:
                logger.error(f"⚠️ {file_path.name} の読み込みに失敗: {e}")
        return samples_info

    def debug_command_structure(self, commands_data):
        """Debug helper to inspect command structure"""
        logger.debug("\n🔍 DEBUG COMMAND STRUCTURE:")
        logger.debug(f"Type: {type(commands_data)}")
        logger.debug(f"Contents: {json.dumps(commands_data, indent=2, ensure_ascii=False)}")
        
        if isinstance(commands_data, dict):
            action_type = commands_data.get("action_type", "unknown")
            commands = commands_data.get("commands", [])
            logger.debug(f"Action Type: {action_type}")
            logger.debug(f"Commands Count: {len(commands)}")
            
            if commands:
                logger.debug("\nFirst Command Structure:")
                logger.debug(json.dumps(commands[0], indent=2, ensure_ascii=False))
        
        return commands_data
