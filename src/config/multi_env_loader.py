"""
Multi-environment configuration loader for 2bykilt

This module provides hierarchical configuration loading with support for:
- Base + environment-specific configuration merging
- Environment variable overrides
- Configuration validation
- Effective configuration generation
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from copy import deepcopy


class ConfigValidationError(Exception):
    """Raised when configuration validation fails"""
    pass


class ConfigLoader:
    """Multi-environment configuration loader"""
    
    def __init__(self, config_dir: Union[str, Path] = "config"):
        """
        Initialize the configuration loader
        
        Args:
            config_dir: Path to configuration directory
        """
        self.config_dir = Path(config_dir)
        self._schema_cache = {}
        
    def load_config(self, environment: Optional[str] = None) -> Dict[str, Any]:
        """
        Load configuration for specified environment
        
        Args:
            environment: Environment name (dev/staging/prod). 
                        If None, uses BYKILT_ENV or defaults to 'development'
        
        Returns:
            Merged configuration dictionary
        """
        if not environment:
            # Map 'dev' to 'development' for compatibility
            env = os.getenv('BYKILT_ENV', 'dev')
            if env == 'dev':
                environment = 'development'
            elif env == 'staging':
                environment = 'staging' 
            elif env == 'prod':
                environment = 'production'
            else:
                environment = env
        
        # 1. Load base configuration
        base_config = self._load_yaml_file('base.yml')
        if not base_config:
            raise ConfigValidationError("Base configuration file not found or empty")
        
        # 2. Load environment-specific configuration
        env_config = self._load_yaml_file(f'{environment}.yml')
        
        # 3. Merge configurations (deep merge)
        config = self._merge_configs(base_config, env_config)
        
        # 4. Apply environment variable overrides
        config = self._apply_env_overrides(config)
        
        # 5. Validate configuration
        self._validate_config(config)
        
        # 6. Add metadata
        config['_metadata'] = {
            'environment': environment,
            'loaded_at': self._get_iso_timestamp(),
            'config_dir': str(self.config_dir),
            'base_file': 'base.yml',
            'env_file': f'{environment}.yml'
        }
        
        return config
    
    def save_effective_config(self, config: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Save effective configuration as JSON artifact
        
        Args:
            config: Configuration dictionary to save
            output_path: Optional output path. If None, saves to ./effective_config.json
        
        Returns:
            Path to saved file
        """
        if not output_path:
            output_path = "effective_config.json"
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        return str(output_path)
    
    def compare_configs(self, env1: str, env2: str) -> Dict[str, Any]:
        """
        Compare configurations between two environments
        
        Args:
            env1: First environment name
            env2: Second environment name
            
        Returns:
            Dictionary containing comparison results
        """
        config1 = self.load_config(env1)
        config2 = self.load_config(env2)
        
        # Remove metadata for comparison
        config1_clean = {k: v for k, v in config1.items() if k != '_metadata'}
        config2_clean = {k: v for k, v in config2.items() if k != '_metadata'}
        
        differences = self._find_differences(config1_clean, config2_clean, '')
        
        return {
            'environment_1': env1,
            'environment_2': env2,
            'differences': differences,
            'comparison_summary': {
                'total_differences': len(differences),
                'configs_identical': len(differences) == 0
            }
        }
    
    def _load_yaml_file(self, filename: str) -> Dict[str, Any]:
        """Load YAML configuration file"""
        file_path = self.config_dir / filename
        if not file_path.exists():
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            raise ConfigValidationError(f"Failed to parse YAML file {filename}: {e}")
        except Exception as e:
            raise ConfigValidationError(f"Failed to read file {filename}: {e}")
    
    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Merge configurations with deep merge support"""
        if not override:
            return deepcopy(base)
        
        result = deepcopy(base)
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = deepcopy(value)
        
        return result
    
    def _apply_env_overrides(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides based on schema"""
        try:
            schema = self._load_schema(config.get('config_version', '1.0.0'))
        except Exception:
            # If schema loading fails, continue without env overrides
            return config
        
        result = deepcopy(config)
        self._apply_overrides_recursive(result, schema.get('properties', {}))
        return result
    
    def _apply_overrides_recursive(self, config: Dict[str, Any], schema: Dict[str, Any]):
        """Recursively apply environment variable overrides"""
        for key, value in config.items():
            if key in schema:
                schema_section = schema[key]
                
                if isinstance(value, dict) and schema_section.get('type') == 'object':
                    # Recurse into nested objects
                    self._apply_overrides_recursive(value, schema_section.get('properties', {}))
                else:
                    # Check for environment override
                    env_var = schema_section.get('environment_override')
                    if env_var and env_var in os.environ:
                        config[key] = self._convert_env_value(
                            os.environ[env_var], 
                            schema_section.get('type', 'string')
                        )
    
    def _convert_env_value(self, value: str, value_type: str) -> Any:
        """Convert environment variable string to appropriate type"""
        if value_type == 'boolean':
            return value.lower() in ('true', '1', 'yes', 'on')
        elif value_type == 'integer':
            try:
                return int(value)
            except ValueError:
                return 0
        elif value_type == 'float':
            try:
                return float(value)
            except ValueError:
                return 0.0
        else:
            return value
    
    def _load_schema(self, version: str) -> Dict[str, Any]:
        """Load configuration schema for validation"""
        if version in self._schema_cache:
            return self._schema_cache[version]
        
        # Map version to filename
        version_file = f"v{version.replace('.', '.')}.yml"
        schema_path = self.config_dir / "schema" / version_file
        
        if not schema_path.exists():
            # Try without patch version
            major_minor = '.'.join(version.split('.')[:2])
            version_file = f"v{major_minor}.yml"
            schema_path = self.config_dir / "schema" / version_file
        
        if not schema_path.exists():
            raise ConfigValidationError(f"Schema file not found for version {version}")
        
        schema = self._load_yaml_file(f"schema/{version_file}")
        self._schema_cache[version] = schema
        return schema
    
    def _validate_config(self, config: Dict[str, Any]):
        """Basic configuration validation"""
        required_sections = ['agent', 'llm', 'browser', 'storage']
        for section in required_sections:
            if section not in config:
                raise ConfigValidationError(f"Required configuration section '{section}' missing")
    
    def _find_differences(self, dict1: Dict[str, Any], dict2: Dict[str, Any], path: str) -> list:
        """Find differences between two configuration dictionaries"""
        differences = []
        
        # Check all keys in dict1
        for key in dict1:
            current_path = f"{path}.{key}" if path else key
            
            if key not in dict2:
                differences.append({
                    'path': current_path,
                    'type': 'missing_in_env2',
                    'value_env1': dict1[key],
                    'value_env2': None
                })
            elif isinstance(dict1[key], dict) and isinstance(dict2[key], dict):
                # Recursively compare nested dictionaries
                differences.extend(self._find_differences(dict1[key], dict2[key], current_path))
            elif dict1[key] != dict2[key]:
                differences.append({
                    'path': current_path,
                    'type': 'value_different',
                    'value_env1': dict1[key],
                    'value_env2': dict2[key]
                })
        
        # Check for keys that exist only in dict2
        for key in dict2:
            if key not in dict1:
                current_path = f"{path}.{key}" if path else key
                differences.append({
                    'path': current_path,
                    'type': 'missing_in_env1',
                    'value_env1': None,
                    'value_env2': dict2[key]
                })
        
        return differences
    
    def _get_iso_timestamp(self) -> str:
        """Get current ISO timestamp"""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'


# Convenience functions for backward compatibility
def load_config(environment: Optional[str] = None) -> Dict[str, Any]:
    """Load configuration using default config directory"""
    loader = ConfigLoader()
    return loader.load_config(environment)


def save_effective_config(config: Dict[str, Any], output_path: Optional[str] = None) -> str:
    """Save effective configuration as JSON"""
    loader = ConfigLoader()
    return loader.save_effective_config(config, output_path)