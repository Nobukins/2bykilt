"""
Configuration adapter for backward compatibility

This module provides adapters between the new multi-environment configuration
system and the existing pickle-based configuration system.
"""

import os
from typing import Dict, Any
from pathlib import Path

from .multi_env_loader import ConfigLoader, ConfigValidationError

# Import unified recording directory resolver
try:
    from ..utils.recording_dir_resolver import create_or_get_recording_dir
except ImportError:
    # Fallback if resolver is not available
    def create_or_get_recording_dir():
        return Path("./tmp/record_videos").resolve()


class ConfigAdapter:
    """Adapter to bridge new and legacy configuration systems"""
    
    def __init__(self):
        self.config_loader = ConfigLoader()
        
    def get_effective_config(self, environment: str = None) -> Dict[str, Any]:
        """
        Get effective configuration, merging multi-env config with legacy settings
        
        Args:
            environment: Environment name (dev/staging/prod)
            
        Returns:
            Configuration dictionary compatible with existing code
        """
        try:
            # Load multi-environment configuration
            config = self.config_loader.load_config(environment)
            
            # Convert to legacy format for backward compatibility
            legacy_config = self._convert_to_legacy_format(config)
            
            return legacy_config
            
        except ConfigValidationError:
            # Fall back to default configuration if multi-env config fails
            from ..utils.default_config_settings import default_config
            return default_config()
    
    def _convert_to_legacy_format(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert new configuration format to legacy format
        
        Args:
            config: New format configuration
            
        Returns:
            Legacy format configuration
        """
        # Extract nested values for flat legacy structure
        agent = config.get('agent', {})
        llm = config.get('llm', {})
        browser = config.get('browser', {})
        storage = config.get('storage', {})
        development = config.get('development', {})
        task = config.get('task', {})
        
        # Map to legacy keys
        legacy_config = {
            # Agent settings
            "agent_type": agent.get('type', 'custom'),
            "max_steps": agent.get('max_steps', 100),
            "max_actions_per_step": agent.get('max_actions_per_step', 10),
            "use_vision": agent.get('use_vision', True),
            "tool_calling_method": agent.get('tool_calling_method', 'auto'),
            
            # LLM settings
            "llm_provider": llm.get('provider', 'openai'),
            "llm_model_name": llm.get('model_name', 'gpt-4o'),
            "llm_num_ctx": llm.get('num_ctx', 32000),
            "llm_temperature": llm.get('temperature', 1.0),
            "llm_base_url": llm.get('base_url', ''),
            "llm_api_key": llm.get('api_key', ''),
            
            # Browser settings
            "use_own_browser": browser.get('use_own_browser', False),
            "keep_browser_open": browser.get('keep_browser_open', False),
            "headless": browser.get('headless', False),
            "disable_security": browser.get('disable_security', True),
            "enable_recording": browser.get('enable_recording', True),
            "window_w": browser.get('window_width', 1280),
            "window_h": browser.get('window_height', 1100),
            
            # Storage paths
            "save_recording_path": storage.get('save_recording_path', str(create_or_get_recording_dir())),
            "save_trace_path": storage.get('save_trace_path', './tmp/traces'),
            "save_agent_history_path": storage.get('save_agent_history_path', './tmp/agent_history'),
            
            # Task and development
            "task": task.get('default', ''),
            "dev_mode": development.get('dev_mode', False),
        }
        
        return legacy_config
    
    def save_effective_config_artifact(self, environment: str = None, output_path: str = None):
        """
        Save effective configuration as JSON artifact
        
        Args:
            environment: Environment name
            output_path: Output file path
            
        Returns:
            Path to saved file
        """
        config = self.config_loader.load_config(environment)
        
        if not output_path:
            env_name = config.get('_metadata', {}).get('environment', 'unknown')
            output_path = f"effective_config_{env_name}.json"
        
        return self.config_loader.save_effective_config(config, output_path)


# Global instance for easy access
config_adapter = ConfigAdapter()


def get_config_for_environment(environment: str = None) -> Dict[str, Any]:
    """
    Get configuration for specified environment in legacy format
    
    Args:
        environment: Environment name (dev/staging/prod)
        
    Returns:
        Configuration dictionary compatible with existing code
    """
    return config_adapter.get_effective_config(environment)


def get_current_environment() -> str:
    """Get current environment from BYKILT_ENV or default"""
    env = os.getenv('BYKILT_ENV', 'dev')
    if env == 'dev':
        return 'development'
    elif env == 'staging':
        return 'staging' 
    elif env == 'prod':
        return 'production'
    else:
        return env


def is_multi_env_config_available() -> bool:
    """Check if multi-environment configuration is available"""
    config_dir = Path('config')
    return (config_dir.exists() and 
            (config_dir / 'base.yml').exists())


def create_default_config_files():
    """Create default configuration files if they don't exist"""
    config_dir = Path('config')
    
    if not config_dir.exists():
        # This should be handled by the installer/setup script
        # For now, we'll just indicate that setup is needed
        print("Multi-environment configuration not set up.")
        print("Run: python scripts/setup_config.py")
        return False
    
    return True