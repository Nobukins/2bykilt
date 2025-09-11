from src.modules.yaml_parser import BrowserAutomationConfig, InstructionLoader, InstructionResult
from typing import Dict, Any, List, Optional
import logging
from src.modules.git_helper import clone_or_pull_repository, checkout_version
import os
import subprocess
from pathlib import Path
from src.utils.timeout_manager import get_timeout_manager, TimeoutScope, TimeoutError, CancellationError

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
    
    async def execute_action(self, name: str, **params) -> bool:
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
        
        # Get timeout manager and check for cancellation
        timeout_manager = get_timeout_manager()
        if timeout_manager.is_cancelled():
            logger.warning(f"Action '{name}' cancelled due to global cancellation request")
            return False
        
        try:
            # Execute based on action type with timeout protection
            action_type = action.get('type')
            if action_type == 'browser-control':
                return await self._execute_browser_control(action, **params)
            elif (
                action_type in ('git-script', 'action_runner_template', 'script')
                or 'git' in action
                or 'command' in action
                or 'script' in action
            ):
                return await self._execute_script(action, **params)
            else:
                logger.error(f"Unknown action type for '{name}'")
                return False
        except TimeoutError as e:
            logger.error(f"Action '{name}' timed out: {e}")
            return False
        except CancellationError as e:
            logger.warning(f"Action '{name}' cancelled: {e}")
            return False
        except Exception as e:
            logger.error(f"Error executing action '{name}': {e}")
            return False
    
    async def _execute_browser_control(self, action: Dict[str, Any], **params) -> bool:
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
    
    def _prepare_git_script(self, action):
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
    
    async def _execute_script(self, action: Dict[str, Any], **params) -> bool:
        """スクリプト実行（Gitリポジトリ対応）"""
        timeout_manager = get_timeout_manager()
        
        if "git" in action:
            # Gitリポジトリからスクリプトを取得
            success, script_path = self._prepare_git_script(action)
            if not success:
                logger.warning(f"Gitリポジトリの準備に失敗しました: {action['git']}")
                # フォールバックとしてLLMを使用
                return await self._fallback_to_llm(action["name"], **params)
            
            # コマンド構築とパラメータ置換
            command = action["command"]
            
            # ${script_path}を実際のパスで置換
            command = command.replace("${script_path}", script_path)
            
            # コマンド内のパラメータを置換
            for param_name, param_value in params.items():
                placeholder = f"${{{param_name}}}"
                if placeholder in command:
                    command = command.replace(placeholder, str(param_value))
            
            # 環境変数の設定
            env = os.environ.copy()
            if "slowmo" in action:
                env["SLOWMO"] = str(action["slowmo"])
            
            # Ensure python invocations use current interpreter
            try:
                import sys as _sys
                if command.strip().startswith('python '):
                    command = command.replace('python', _sys.executable, 1)
            except Exception:
                pass
            
            # コマンド実行 with timeout protection
            logger.info(f"コマンド実行: {command}")
            try:
                # Get timeout value from action or use default
                timeout_value = action.get("timeout", 300)
                
                # Execute with timeout manager protection
                result = await timeout_manager.wait_with_timeout(
                    self._run_subprocess(command, env),
                    timeout=timeout_value,
                    operation_name=f"script execution for {action['name']}"
                )
                
                success = result.returncode == 0
                if not success:
                    logger.error(f"コマンド実行が失敗しました: コード {result.returncode}")
                return success
            except TimeoutError:
                logger.error(f"コマンド実行がタイムアウトしました: {action['name']}")
                return False
            except CancellationError:
                logger.warning(f"コマンド実行がキャンセルされました: {action['name']}")
                return False
            except Exception as e:
                logger.error(f"コマンド実行エラー: {str(e)}")
                return False
        
        # ...existing script execution code...
        script = action.get('script')
        command = action.get('command')
        
        logger.info(f"Executing script action: {action['name']} using {script}")
        
        # Implement script execution here
        # This would run the specified script with parameters
        
        return True
    
    async def _fallback_to_llm(self, action_name: str, **params) -> bool:
        """LLMフォールバック処理"""
        logger.warning(f"LLMフォールバックを使用: {action_name}")
        
        # LLMを使用したアクション実行の実装
        # ここではシンプルにログ出力のみ
        logger.info(f"LLMでアクション '{action_name}' を実行します")
        
        # 実際のLLM実装をここに追加
        # 例: llm_response = await call_llm_api(action_name, params)
        
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