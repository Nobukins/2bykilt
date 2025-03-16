from src.modules.yaml_parser import BrowserAutomationConfig, InstructionLoader, InstructionResult
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class BrowserAutomationManager:
    """Manages browser automation actions loaded from various sources"""
    
    def __init__(self, local_path: str = "llms.txt", website_url: Optional[str] = None):
        self.local_path = local_path
        self.website_url = website_url
        self.actions = {}
        self.instruction_source = None
    
    def initialize(self):
        """
        Initialize the manager by loading actions from available sources.
        Returns True if actions were loaded successfully, False if falling back to LLM.
        """
        loader = InstructionLoader(self.local_path, self.website_url)
        result = loader.load_instructions()
        
        if result.success:
            self.instruction_source = result.source
            for action in result.instructions:
                self.register_action(action)
            logger.info(f"Successfully loaded {len(result.instructions)} actions from {result.source}")
            return True
        else:
            logger.warning(f"No actions loaded: {result.error}")
            return False
    
    def register_action(self, action_config: Dict[str, Any]) -> None:
        """Register a browser automation action"""
        name = action_config.get('name')
        if not name:
            logger.error("Cannot register action without a name")
            return
            
        if name in self.actions:
            logger.warning(f"Overwriting existing action '{name}'")
            
        self.actions[name] = action_config
        logger.info(f"Registered action: {name}")
    
    def execute_action(self, name: str, **params) -> bool:
        """Execute a registered browser automation action with parameters"""
        if name not in self.actions:
            logger.error(f"Unknown action: {name}")
            return False
            
        action = self.actions[name]
        
        # Validate required parameters
        if 'params' in action:
            missing_params = []
            if isinstance(action['params'], list):
                for param in action['params']:
                    if isinstance(param, dict) and param.get('required', False):
                        param_name = param.get('name')
                        if param_name not in params:
                            missing_params.append(param_name)
            
            if missing_params:
                logger.error(f"Missing required parameters for action '{name}': {', '.join(missing_params)}")
                return False
        
        try:
            # Execute based on action type
            if action.get('type') == 'browser-control':
                return self._execute_browser_control(action, **params)
            elif 'script' in action:
                return self._execute_script(action, **params)
            else:
                logger.error(f"Unknown action type for '{name}'")
                return False
        except Exception as e:
            logger.error(f"Error executing action '{name}': {e}")
            return False
    
    def _execute_browser_control(self, action: Dict[str, Any], **params) -> bool:
        """Execute browser control automation flow"""
        logger.info(f"Executing browser control action: {action['name']}")
        
        # Here would be the actual browser automation implementation
        flow = action.get('flow', [])
        slowmo = action.get('slowmo', 0)
        
        for step in flow:
            step_type = step.get('action')
            logger.info(f"Executing step: {step_type}")
            
            # Process templated values in step parameters
            for key, value in step.items():
                if isinstance(value, str) and '{' in value:
                    for param_name, param_value in params.items():
                        placeholder = f"{{{param_name}}}"
                        if placeholder in value:
                            step[key] = value.replace(placeholder, str(param_value))
            
            # Implement browser automation steps here
            # This would connect to your actual browser automation system
        
        return True
    
    def _execute_script(self, action: Dict[str, Any], **params) -> bool:
        """Execute a script-based automation"""
        script = action.get('script')
        command = action.get('command')
        
        logger.info(f"Executing script action: {action['name']} using {script}")
        
        # Implement script execution here
        # This would run the specified script with parameters
        
        return True

# Main application function that integrates the above classes
def setup_browser_automation(website_url: Optional[str] = None) -> BrowserAutomationManager:
    """
    Set up browser automation following priority order:
    1. Local file
    2. Website
    3. LLM fallback
    """
    manager = BrowserAutomationManager(
        local_path="llms.txt",
        website_url=website_url
    )
    
    success = manager.initialize()
    if success:
        logger.info("Browser automation initialized from file source")
        return manager
    
    # If we get here, both local and website sources failed
    logger.info("Falling back to LLM for browser automation")
    # Call your existing LLM implementation here
    # llm_manager = initialize_llm_automation()
    # return llm_manager
    
    # For now, return the manager even with no actions
    return manager