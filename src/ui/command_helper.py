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
        actions_config = load_actions_config()
        commands = []
        
        if isinstance(actions_config, dict) and 'actions' in actions_config:
            for action in actions_config['actions']:
                if 'name' in action:
                    command = {
                        'name': action['name'],
                        'type': action.get('type', ''),
                        'description': action.get('description', ''),
                        'format': self._get_command_format(action),
                        'params': []
                    }
                    
                    # Extract parameter information
                    if 'params' in action and isinstance(action['params'], list):
                        for param in action['params']:
                            if 'name' in param:
                                param_info = {
                                    'name': param['name'],
                                    'required': param.get('required', False),
                                    'description': param.get('description', ''),
                                    'default': param.get('default', '')
                                }
                                command['params'].append(param_info)
                    
                    commands.append(command)
        
        return commands
    
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
        required_params = [p for p in cmd['params'] if p.get('required', False)]
        
        # Add placeholders for required parameters
        for param in required_params:
            result += f" {param['name']}="
        
        return result
    
    def get_all_commands(self) -> List[Dict[str, Any]]:
        """Return all commands in a JSON-serializable format"""
        return self.commands
