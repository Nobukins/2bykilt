import os
import yaml
import logging
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger(__name__)

class CommandDispatcher:
    """
    Command Dispatcher - Parses prompts and delegates execution to appropriate handlers.
    """
    
    def __init__(self):
        self.handlers = {}
        self.actions_cache = {}
        self.processed_commands = set()  # Track processed commands to prevent recursion
        self.register_default_handlers()
        
    def register_handler(self, action_type: str, handler: Callable):
        """Register a handler for a specific action type."""
        self.handlers[action_type] = handler
        
    def register_default_handlers(self):
        """Register default handlers."""
        try:
            from src.modules.handlers.script_handler import handle_script  # type: ignore
            from src.modules.handlers.browser_control_handler import handle_browser_control  # type: ignore
            from src.modules.handlers.git_script_handler import handle_git_script  # type: ignore

            self.register_handler('script', handle_script)
            self.register_handler('browser-control', handle_browser_control)
            self.register_handler('git-script', handle_git_script)
            return
        except Exception:
            # Fallback: lightweight internal handlers to keep tests CI-safe without optional modules
            import asyncio
            from src.script import script_manager as sm

            async def _handle_script(action, params, use_own_browser, headless):
                # Delegate to execute_script wrapper; ignore recording_path in tests
                msg, _ = await sm.execute_script(
                    script_info=action,
                    params=params,
                    headless=headless,
                    save_recording_path=None,
                    browser_type=params.get('browser') or None,
                )
                return msg

            async def _handle_browser_control(action, params, use_own_browser, headless):
                msg, _ = await sm.execute_script(
                    script_info=action,
                    params=params,
                    headless=headless,
                    save_recording_path=None,
                    browser_type=params.get('browser') or None,
                )
                return msg

            async def _handle_git_script(action, params, use_own_browser, headless):
                # Prefer the NEW METHOD executor when available
                browser_type = params.get('browser') or os.getenv('BYKILT_BROWSER_TYPE') or None
                return await sm.execute_git_script_new_method(
                    action, params, headless, None, browser_type
                )

            self.register_handler('script', _handle_script)
            self.register_handler('browser-control', _handle_browser_control)
            self.register_handler('git-script', _handle_git_script)
        
    def get_actions_from_file(self, file_path: str = 'llms.txt') -> List[Dict[str, Any]]:
        """Load actions from llms.txt."""
        if file_path in self.actions_cache:
            return self.actions_cache[file_path]
            
        if not os.path.exists(file_path):
            logger.error(f"Action definition file not found: {file_path}")
            return []
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                data = yaml.safe_load(content)
                actions = data.get('actions', [])
                self.actions_cache[file_path] = actions
                return actions
        except Exception as e:
            logger.error(f"Error loading action definition file: {e}")
            return []
            
    def parse_command(self, prompt: str) -> Dict[str, Any]:
        """Parse the prompt into command and parameters."""
        parts = prompt.split()
        command = parts[0] if parts else ""
        
        params = {}
        for part in parts[1:]:
            if "=" in part:
                key, value = part.split("=", 1)
                params[key] = value
                
        return {"command": command, "params": params}
        
    def find_matching_action(self, command: str) -> Optional[Dict[str, Any]]:
        """Find an action definition matching the command."""
        actions = self.get_actions_from_file()
        for action in actions:
            if action.get('name') == command:
                return action
        return None
        
    async def dispatch(self, prompt: str, use_own_browser: bool = False, headless: bool = False) -> Dict[str, Any]:
        """Dispatch the prompt to the appropriate handler."""
        # Check for circular references
        command_key = f"{prompt}_{use_own_browser}_{headless}"
        if command_key in self.processed_commands:
            logger.warning(f"Circular reference detected: {prompt}")
            return {
                "success": False,
                "action_type": "error",
                "error": "Circular reference detected",
                "result": "Command recursion detected"
            }
        
        # Mark the command as processed
        self.processed_commands.add(command_key)
        
        try:
            # Parse the command and parameters
            parsed = self.parse_command(prompt)
            command = parsed["command"]
            params = parsed["params"]
            
            logger.info(f"Dispatching command: {command}, params: {params}")
            
            # Find matching action
            action = self.find_matching_action(command)
            
            if not action:
                # If no matching action, delegate to LLM
                logger.info(f"No matching action found. Delegating to LLM: {prompt}")
                self.processed_commands.remove(command_key)  # Remove from processed set
                return {
                    "success": True,
                    "action_type": "llm",
                    "prompt": prompt,
                    "result": "Delegated to LLM"
                }
                
            # Get action type
            action_type = action.get('type', 'unknown')
            
            # Execute using the registered handler
            if action_type in self.handlers:
                handler = self.handlers[action_type]
                result = await handler(action, params, use_own_browser, headless)
                self.processed_commands.remove(command_key)  # Remove from processed set
                return {
                    "success": True,
                    "action_type": action_type,
                    "result": result
                }
            else:
                # Unknown action type, delegate to LLM
                logger.info(f"Unknown action type. Delegating to LLM: {action_type}")
                self.processed_commands.remove(command_key)  # Remove from processed set
                return {
                    "success": True,
                    "action_type": "llm",
                    "prompt": prompt,
                    "result": "Delegated to LLM"
                }
        except Exception as e:
            # Remove from processed set on error
            self.processed_commands.remove(command_key)
            logger.error(f"Error processing command: {e}")
            return {
                "success": False,
                "action_type": "error",
                "error": str(e),
                "result": "Error processing command"
            }
