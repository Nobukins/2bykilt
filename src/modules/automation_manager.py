from src.modules.yaml_parser import BrowserAutomationConfig, InstructionLoader, InstructionResult
from typing import Dict, Any, List, Optional
import logging
from src.modules.git_helper import clone_or_pull_repository, checkout_version
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

class BrowserAutomationManager:
    """Manages browser automation actions loaded from various sources"""
    
    def __init__(self, local_path: str = "llms.txt", website_url: Optional[str] = None):
        self.local_path = local_path
        self.website_url = website_url
        self.actions = {}
        self.instruction_source = None
        self.git_repos_dir = Path("./tmp/git_scripts").absolute()
        self.git_repos_dir.mkdir(parents=True, exist_ok=True)
    
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
            action_type = action.get('type')
            if action_type == 'browser-control':
                return self._execute_browser_control(action, **params)
            elif action_type == 'git-script':
                return self._execute_git_script(action, **params)
            elif action_type in ['script', 'unlock-future', 'action_runner_template']:
                return self._execute_script(action, **params)
            else:
                logger.error(f"Unknown action type for '{name}': {action_type}")
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
    
    def _execute_git_script(self, action: Dict[str, Any], **params) -> bool:
        """Execute git-script type actions by integrating with script_manager"""
        logger.info(f"git_script: start - Executing git-script action: {action['name']}")
        
        try:
            # Import script_manager run_script function  
            from src.script.script_manager import run_script
            import asyncio
            
            # Extract git script information
            script_info = {
                'type': 'git-script',
                'git': action.get('git'),
                'script_path': action.get('script_path'),
                'version': action.get('version', 'main'),
                'command': action.get('command'),
                'timeout': action.get('timeout', 120),
                'slowmo': action.get('slowmo')
            }
            
            # Validate required fields
            if not script_info['git'] or not script_info['script_path']:
                logger.error("git-script action requires 'git' and 'script_path' fields")
                return False
            
            if not script_info['command']:
                logger.error("git-script action requires 'command' field")
                return False
            
            logger.info(f"git_script: cloning repository {script_info['git']}")
            logger.info(f"git_script: executing script {script_info['script_path']}")
            
            # Run the git script using script_manager
            try:
                result, script_path = asyncio.run(run_script(script_info, params, headless=True))
                
                if "successfully" in result.lower():
                    logger.info(f"git_script: completed successfully - {result}")
                    return True
                else:
                    logger.error(f"git_script: failed - {result}")
                    return False
                    
            except Exception as e:
                logger.error(f"git_script: error during execution - {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"git_script: failed to execute git-script action: {str(e)}")
            return False
    
        """Gitリポジトリからスクリプトを準備"""
        if "git" not in action:
            return False, None
            
        repo_url = action["git"]
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        target_dir = self.git_repos_dir / repo_name
        
        # Clone or update repository
        success = clone_or_pull_repository(repo_url, target_dir)
        if not success:
            return False, None
        
        # Checkout specific version if specified
        version = action.get("version", None)
        if version and not checkout_version(target_dir, version):
            return False, None
        
        # Get script path
        script_path = target_dir / action.get("script_path", "")
        return True, str(script_path)
    
    def _execute_script(self, action: Dict[str, Any], **params) -> bool:
        """Execute script actions (non-git script types)"""
        from src.script.script_manager import run_script
        import asyncio
        
        action_type = action.get('type')
        logger.info(f"Executing {action_type} action: {action['name']}")
        
        try:
            # Run the script using script_manager
            result, script_path = asyncio.run(run_script(action, params, headless=True))
            
            if "successfully" in result.lower():
                logger.info(f"Script execution completed successfully - {result}")
                return True
            else:
                logger.error(f"Script execution failed - {result}")
                return False
                
        except Exception as e:
            logger.error(f"Error executing {action_type} action: {str(e)}")
            return False
    
    def _fallback_to_llm(self, action_name, **params):
        """LLMを使用したフォールバック処理"""
        logger.info(f"アクション実行をLLMにフォールバック: {action_name}")
        # Implement the LLM fallback logic here
        # This would connect to the existing LLM processing pipeline
        return False

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