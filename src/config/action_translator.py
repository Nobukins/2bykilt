import json
from pathlib import Path
import os

class ActionTranslator:
    """Converts llms.txt actions into JSON command format."""
    
    def __init__(self, temp_dir="./tmp/json_commands"):
        """Initialize the translator with a temporary directory."""
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def translate_to_json(self, action_name, params, actions_config, maintain_session=False, tab_selection_strategy="new_tab"):
        """
        Translate an action into a JSON command file.
        
        Args:
            action_name: Name of the action to execute.
            params: Dictionary of parameters for the action.
            actions_config: List or dictionary of actions loaded from llms.txt.
            maintain_session: Whether to maintain browser session between commands.
            tab_selection_strategy: Strategy for tab selection ("new_tab", "active_tab", "last_tab").
        
        Returns:
            str: Path to the generated JSON file.
        """
        # Handle both dict and list formats for actions_config
        if isinstance(actions_config, dict) and 'actions' in actions_config:
            action_list = actions_config.get('actions', [])
        else:
            # actions_config is already a list
            action_list = actions_config
        
        # Find the action definition
        action_def = next((action for action in action_list if action.get('name') == action_name), None)
        if not action_def:
            raise ValueError(f"Action '{action_name}' is not defined in the provided actions configuration.")
        
        # Create JSON command structure
        json_commands = {
            "commands": [],
            "maintain_session": maintain_session,
            "tab_selection_strategy": tab_selection_strategy,  # Include tab selection strategy
            "keep_tab_open": action_def.get("keep_tab_open", False),
            "slowmo": action_def.get("slowmo", 1000)
        }
        
        if action_def.get('type') in ['browser-control', 'unlock-future']:
            for step in action_def.get('flow', []):
                command = {"action": step['action']}
                
                if step['action'] == 'command':
                    # Make URL parameter optional
                    if 'url' in step:
                        command['args'] = [step['url']]
                    else:
                        # If no URL provided, use the current page
                        command['args'] = ["current"]
                    
                    # Add optional parameters
                    if 'wait_for' in step:
                        command['wait_for'] = step['wait_for']
                    if 'wait_until' in step:
                        command['wait_until'] = step['wait_until']
                
                elif step['action'] in ['click', 'fill_form']:
                    # 正しいフォーマットに変換
                    command['args'] = []
                    if 'selector' in step:
                        command['args'].append(step['selector'])
                    if step['action'] == 'fill_form' and 'value' in step:
                        value = step['value']
                        for param_name, param_value in params.items():
                            value = value.replace(f"${{params.{param_name}}}", param_value)
                        command['args'].append(value)
                
                elif step['action'] == 'keyboard_press':
                    # キーボード操作のパラメータを修正
                    key = step.get('key', 'Enter')  # デフォルト値を設定
                    command['args'] = [key]  # 配列として設定
                
                json_commands["commands"].append(command)
        
        # Save to a temporary JSON file
        file_path = Path(self.temp_dir) / f"{action_name}_{hash(str(params))}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_commands, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
