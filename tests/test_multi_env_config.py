#!/usr/bin/env python3
"""
Tests for multi-environment configuration loader

Test cases for the ConfigLoader class and CLI tools.
"""

import unittest
import tempfile
import os
import json
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.multi_env_loader import ConfigLoader, ConfigValidationError


class TestConfigLoader(unittest.TestCase):
    """Test cases for ConfigLoader class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(parents=True)
        
        # Create test configuration files
        self._create_test_configs()
        
        self.loader = ConfigLoader(self.config_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_configs(self):
        """Create test configuration files"""
        # Base config
        base_config = {
            'config_version': '1.0.0',
            'agent': {
                'type': 'custom',
                'max_steps': 100
            },
            'llm': {
                'provider': 'openai',
                'temperature': 1.0
            },
            'browser': {
                'headless': False
            },
            'storage': {
                'save_recording_path': './tmp/record_videos'
            }
        }
        
        # Development config
        dev_config = {
            'llm': {
                'temperature': 1.2
            },
            'browser': {
                'headless': False
            },
            'development': {
                'dev_mode': True
            }
        }
        
        # Production config
        prod_config = {
            'llm': {
                'temperature': 0.8
            },
            'browser': {
                'headless': True
            },
            'development': {
                'dev_mode': False
            }
        }
        
        # Write files
        import yaml
        
        with open(self.config_dir / 'base.yml', 'w') as f:
            yaml.safe_dump(base_config, f)
        
        with open(self.config_dir / 'development.yml', 'w') as f:
            yaml.safe_dump(dev_config, f)
        
        with open(self.config_dir / 'production.yml', 'w') as f:
            yaml.safe_dump(prod_config, f)
    
    def test_load_development_config(self):
        """Test loading development configuration"""
        config = self.loader.load_config('development')
        
        self.assertEqual(config['config_version'], '1.0.0')
        self.assertEqual(config['agent']['type'], 'custom')
        self.assertEqual(config['agent']['max_steps'], 100)
        self.assertEqual(config['llm']['provider'], 'openai')
        self.assertEqual(config['llm']['temperature'], 1.2)  # Overridden
        self.assertEqual(config['browser']['headless'], False)
        self.assertEqual(config['development']['dev_mode'], True)
        
        # Check metadata
        self.assertIn('_metadata', config)
        self.assertEqual(config['_metadata']['environment'], 'development')
    
    def test_load_production_config(self):
        """Test loading production configuration"""
        config = self.loader.load_config('production')
        
        self.assertEqual(config['llm']['temperature'], 0.8)  # Overridden
        self.assertEqual(config['browser']['headless'], True)  # Overridden
        self.assertEqual(config['development']['dev_mode'], False)
    
    def test_load_with_env_variable(self):
        """Test loading config with BYKILT_ENV environment variable"""
        # Set environment variable
        os.environ['BYKILT_ENV'] = 'prod'
        
        try:
            config = self.loader.load_config()
            self.assertEqual(config['_metadata']['environment'], 'production')
        finally:
            # Clean up
            if 'BYKILT_ENV' in os.environ:
                del os.environ['BYKILT_ENV']
    
    def test_load_default_environment(self):
        """Test loading default environment when no env specified"""
        config = self.loader.load_config()
        self.assertEqual(config['_metadata']['environment'], 'development')
    
    def test_missing_base_config(self):
        """Test error when base config is missing"""
        # Remove base config
        (self.config_dir / 'base.yml').unlink()
        
        with self.assertRaises(ConfigValidationError):
            self.loader.load_config('development')
    
    def test_missing_environment_config(self):
        """Test loading with missing environment config (should use base only)"""
        config = self.loader.load_config('nonexistent')
        
        # Should still load base config
        self.assertEqual(config['config_version'], '1.0.0')
        self.assertEqual(config['llm']['temperature'], 1.0)  # Base value
    
    def test_compare_configs(self):
        """Test configuration comparison"""
        comparison = self.loader.compare_configs('development', 'production')
        
        self.assertEqual(comparison['environment_1'], 'development')
        self.assertEqual(comparison['environment_2'], 'production')
        self.assertGreater(len(comparison['differences']), 0)
        self.assertFalse(comparison['comparison_summary']['configs_identical'])
        
        # Check specific differences
        diffs = comparison['differences']
        temp_diff = next((d for d in diffs if d['path'] == 'llm.temperature'), None)
        self.assertIsNotNone(temp_diff)
        self.assertEqual(temp_diff['value_env1'], 1.2)
        self.assertEqual(temp_diff['value_env2'], 0.8)
    
    def test_save_effective_config(self):
        """Test saving effective configuration"""
        config = self.loader.load_config('development')
        
        output_path = Path(self.temp_dir) / 'effective.json'
        saved_path = self.loader.save_effective_config(config, str(output_path))
        
        self.assertEqual(saved_path, str(output_path))
        self.assertTrue(output_path.exists())
        
        # Verify saved content
        with open(output_path, 'r') as f:
            saved_config = json.load(f)
        
        self.assertEqual(saved_config['config_version'], '1.0.0')
        self.assertEqual(saved_config['llm']['temperature'], 1.2)
    
    def test_environment_variable_override(self):
        """Test environment variable overrides"""
        # Set up environment variable
        os.environ['BYKILT_LLM_TEMPERATURE'] = '2.0'
        
        try:
            # Create schema file for overrides
            schema_dir = self.config_dir / 'schema'
            schema_dir.mkdir(exist_ok=True)
            
            schema = {
                'properties': {
                    'llm': {
                        'type': 'object',
                        'properties': {
                            'temperature': {
                                'type': 'float',
                                'environment_override': 'BYKILT_LLM_TEMPERATURE'
                            }
                        }
                    }
                }
            }
            
            import yaml
            with open(schema_dir / 'v1.0.yml', 'w') as f:
                yaml.safe_dump(schema, f)
            
            config = self.loader.load_config('development')
            self.assertEqual(config['llm']['temperature'], 2.0)
            
        finally:
            # Clean up
            if 'BYKILT_LLM_TEMPERATURE' in os.environ:
                del os.environ['BYKILT_LLM_TEMPERATURE']


class TestConfigCLI(unittest.TestCase):
    """Test cases for configuration CLI"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / "config"
        self.config_dir.mkdir(parents=True)
        
        # Create minimal test configs
        self._create_test_configs()
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def _create_test_configs(self):
        """Create minimal test configuration files"""
        import yaml
        
        base_config = {
            'config_version': '1.0.0',
            'agent': {'type': 'custom'},
            'llm': {'provider': 'openai'},
            'browser': {'headless': False},
            'storage': {'save_recording_path': './tmp'}
        }
        
        dev_config = {
            'development': {'dev_mode': True}
        }
        
        with open(self.config_dir / 'base.yml', 'w') as f:
            yaml.safe_dump(base_config, f)
        
        with open(self.config_dir / 'development.yml', 'w') as f:
            yaml.safe_dump(dev_config, f)
    
    def test_cli_validate_command(self):
        """Test CLI validation command"""
        import subprocess
        
        cmd = [
            sys.executable, 
            'scripts/config_cli.py',
            '--config-dir', str(self.config_dir),
            'validate', 
            'development'
        ]
        
        # Change to project root for CLI execution
        project_root = Path(__file__).parent.parent
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        self.assertIn('Configuration for \'development\' is valid', result.stdout)
    
    def test_cli_load_command(self):
        """Test CLI load command"""
        import subprocess
        
        cmd = [
            sys.executable,
            'scripts/config_cli.py', 
            '--config-dir', str(self.config_dir),
            'load',
            'development'
        ]
        
        project_root = Path(__file__).parent.parent
        result = subprocess.run(cmd, cwd=project_root, capture_output=True, text=True)
        
        self.assertEqual(result.returncode, 0)
        
        # Parse JSON output
        config = json.loads(result.stdout)
        self.assertEqual(config['config_version'], '1.0.0')
        self.assertEqual(config['development']['dev_mode'], True)


if __name__ == '__main__':
    # Run tests
    unittest.main()