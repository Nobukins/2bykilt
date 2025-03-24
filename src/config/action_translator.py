import json
from pathlib import Path
import os

class ActionTranslator:
    """Converts llms.txt actions into JSON command format."""
    
    def __init__(self, temp_dir="./tmp/json_commands"):
        """Initialize the translator with a temporary directory."""
        self.temp_dir = temp_dir
        os.makedirs(self.temp_dir, exist_ok=True)
    
    def translate_to_json(self, action_name, params, actions_config):
        """
        Translate an action into a JSON command file.
        
        Args:
            action_name: Name of the action to execute.
            params: Dictionary of parameters for the action.
            actions_config: List of actions loaded from llms.txt.
        
        Returns:
            str: Path to the generated JSON file.
        """
        # Find the action definition
        action_def = next((action for action in actions_config if action.get('name') == action_name), None)
        if not action_def:
            raise ValueError(f"Action '{action_name}' is not defined in llms.txt.")
        
        # Create JSON command structure
        json_commands = {"commands": []}
        
        if action_def.get('type') in ['browser-control', 'unlock-future']:
            for step in action_def.get('flow', []):
                command = {"action": step['action']}
                
                if step['action'] == 'command':
                    # Ensure 'url' parameter exists
                    if 'url' not in step:
                        raise ValueError(f"Missing 'url' parameter in command action: {step}")
                    
                    # Add 'url' to args
                    command['args'] = [step['url']]
                    
                    # Add optional parameters
                    if 'wait_for' in step:
                        command['wait_for'] = step['wait_for']
                    if 'wait_until' in step:
                        command['wait_until'] = step['wait_until']
                
                elif step['action'] in ['click', 'fill_form']:
                    command['selector'] = step['selector']
                    if step['action'] == 'fill_form':
                        value = step['value']
                        for param_name, param_value in params.items():
                            value = value.replace(f"${{params.{param_name}}}", param_value)
                        command['value'] = value
                
                elif step['action'] == 'keyboard_press':
                    command['key'] = step.get('selector', 'Enter')
                
                json_commands["commands"].append(command)
        
        # Save to a temporary JSON file
        file_path = Path(self.temp_dir) / f"{action_name}_{hash(str(params))}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(json_commands, f, ensure_ascii=False, indent=2)
        
        return str(file_path)
