import logging
from typing import List, Dict, Any, Optional
from src.config.llms_parser import load_actions_config  # Reuse llms_parser

logger = logging.getLogger(__name__)

class CommandHelper:
    """Helper class to manage commands for the UI"""
    
    def __init__(self):
        """Initialize the command helper"""
        self.commands = self._extract_commands_from_config()
    
    def _extract_commands_from_config(self) -> List[Dict[str, Any]]:
        """Extract commands from llms.txt using llms_parser"""
        try:
            from src.config.llms_parser import load_actions_config
            actions_config = load_actions_config()
            commands = []
            
            if isinstance(actions_config, dict) and 'actions' in actions_config:
                for action in actions_config['actions']:
                    if isinstance(action, dict) and 'name' in action:
                        # 基本情報だけを抽出
                        cmd = {
                            'name': action['name'],
                            'description': action.get('description', ''),
                            'params': []
                        }
                        
                        # パラメータがあれば追加
                        if 'params' in action and isinstance(action['params'], list):
                            cmd['params'] = [
                                {
                                    'name': p['name'],
                                    'required': p.get('required', False),
                                    'description': p.get('description', '')
                                }
                                for p in action['params'] 
                                if isinstance(p, dict) and 'name' in p
                            ]
                        
                        commands.append(cmd)
            
            # コマンドが見つからなかった場合はデフォルトセットを提供
            if not commands:
                logger.warning("llms.txtからコマンドが取得できませんでした。デフォルトコマンドを使用します。")
                commands = [
                    {
                        "name": "search",
                        "description": "Web検索を実行します",
                        "params": [{"name": "query", "required": True, "description": "検索クエリ"}]
                    },
                    {
                        "name": "visit",
                        "description": "指定したURLにアクセスします",
                        "params": [{"name": "url", "required": True, "description": "アクセスするURL"}]
                    }
                ]
            
            return commands
        except Exception as e:
            logger.error(f"コマンド抽出エラー: {e}")
            import traceback
            logger.error(traceback.format_exc())
            
            # エラー時もデフォルトコマンドを返す
            return [
                {
                    "name": "search",
                    "description": "Web検索を実行します",
                    "params": [{"name": "query", "required": True, "description": "検索クエリ"}]
                },
                {
                    "name": "visit",
                    "description": "指定したURLにアクセスします",
                    "params": [{"name": "url", "required": True, "description": "アクセスするURL"}]
                }
            ]
    
    def _get_command_format(self, action: Dict[str, Any]) -> str:
        """Generate usage format for a command"""
        cmd_format = action['name']
        
        if 'params' in action and isinstance(action['params'], list):
            required_params = [p for p in action['params'] if p.get('required', False)]
            optional_params = [p for p in action['params'] if not p.get('required', False)]
            
            # Add required parameters
            for param in required_params:
                cmd_format += f" {param['name']}=<value>"
            
            # Add optional parameters
            if optional_params:
                cmd_format += " [Options: "
                cmd_format += ", ".join([f"{p['name']}=<value>" for p in optional_params])
                cmd_format += "]"
        
        return cmd_format
    
    def get_commands_for_display(self) -> List[List[str]]:
        """Return commands formatted for display in a table"""
        result = []
        for cmd in self.commands:
            result.append([
                cmd['name'],
                cmd.get('description', ''),
                cmd.get('format', cmd['name'])
            ])
        return result
    
    def get_command_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Find a command by its name"""
        for cmd in self.commands:
            if cmd['name'] == name:
                return cmd
        return None
    
    def generate_command_template(self, command_name: str) -> str:
        """Generate a template for a command"""
        cmd = self.get_command_by_name(command_name)
        if not cmd:
            return command_name
        
        result = command_name
        params = cmd.get('params', [])
        required_params = [p for p in params if p.get('required', False)]
        
        # Add placeholders for required parameters
        for param in required_params:
            result += f" {param['name']}="
        
        return result
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """コマンド情報をJSON変換可能な形式で取得する"""
        try:
            # コマンドデータの取得
            commands = self._extract_commands_from_config()
            if not commands:
                print("警告: コマンドデータが空です")
                # ダミーデータを返す（テスト用）
                return [
                    {"name": "search", "description": "Webで検索を行います", 
                     "params": [{"name": "query", "required": True, "description": "検索キーワード"}]},
                    {"name": "help", "description": "ヘルプを表示します"}
                ]
            
            # データを整形してreturn
            return commands
        except Exception as e:
            import traceback
            print(f"コマンド取得エラー: {str(e)}")
            print(traceback.format_exc())
            # 例外発生時もダミーデータを返す
            return [{"name": "help", "description": "ヘルプを表示します"}]
