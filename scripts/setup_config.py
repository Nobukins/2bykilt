#!/usr/bin/env python3
"""
Setup script for multi-environment configuration

This script sets up the multi-environment configuration system for 2bykilt.
"""

import os
import sys
from pathlib import Path

def setup_config_directory():
    """Set up the configuration directory structure"""
    print("Setting up multi-environment configuration...")
    
    # Check if we're in the correct directory
    if not Path('bykilt.py').exists():
        print("Error: Please run this script from the 2bykilt project root directory")
        return False
    
    # Check if config directory already exists
    config_dir = Path('config')
    if config_dir.exists() and (config_dir / 'base.yml').exists():
        print("✅ Multi-environment configuration is already set up")
        return True
    
    print("❌ Configuration files not found")
    print("Please ensure the following files exist:")
    print("  - config/base.yml")
    print("  - config/development.yml") 
    print("  - config/staging.yml")
    print("  - config/production.yml")
    print("  - config/schema/v1.0.yml")
    
    return False

def test_configuration():
    """Test the configuration system"""
    print("\nTesting configuration system...")
    
    try:
        # Add project root to path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        
        from src.config.multi_env_loader import ConfigLoader
        
        loader = ConfigLoader()
        
        # Test each environment
        environments = ['development', 'staging', 'production']
        
        for env in environments:
            try:
                config = loader.load_config(env)
                print(f"✅ {env}: Configuration loaded successfully")
            except Exception as e:
                print(f"❌ {env}: Configuration failed - {e}")
                return False
        
        # Test CLI
        print("\nTesting CLI tools...")
        
        import subprocess
        result = subprocess.run([
            sys.executable, 'scripts/config_cli.py', 'list'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ CLI tools working")
        else:
            print(f"❌ CLI tools failed: {result.stderr}")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    except Exception as e:
        print(f"❌ Configuration test failed: {e}")
        return False

def show_usage_examples():
    """Show usage examples"""
    print("\n" + "="*60)
    print("Multi-Environment Configuration Setup Complete!")
    print("="*60)
    
    print("\n📋 Usage Examples:")
    print("\n1. Environment switching:")
    print("   export BYKILT_ENV=dev      # Use development config")
    print("   export BYKILT_ENV=staging  # Use staging config")
    print("   export BYKILT_ENV=prod     # Use production config")
    
    print("\n2. CLI tools:")
    print("   python scripts/config_cli.py list")
    print("   python scripts/config_cli.py validate development")
    print("   python scripts/config_cli.py compare development production")
    print("   python scripts/config_cli.py effective production -o prod_config.json")
    
    print("\n3. Environment variable overrides:")
    print("   export BYKILT_LLM_TEMPERATURE=1.5")
    print("   export BYKILT_HEADLESS=true")
    print("   export BYKILT_DEV_MODE=false")
    
    print("\n📂 Configuration Files:")
    print("   config/base.yml         - Base configuration")
    print("   config/development.yml  - Development overrides")
    print("   config/staging.yml      - Staging overrides")
    print("   config/production.yml   - Production overrides")
    print("   config/schema/v1.0.yml  - Configuration schema")
    
    print("\n🔧 Integration:")
    print("   The existing default_config() function now automatically")
    print("   uses multi-environment configuration when available.")
    
    print("\n✨ Features:")
    print("   • Hierarchical configuration merging")
    print("   • Environment variable overrides")
    print("   • Configuration validation")
    print("   • Diff comparison between environments")
    print("   • Effective configuration artifacts")
    print("   • Backward compatibility with existing code")

def main():
    """Main setup function"""
    print("2bykilt Multi-Environment Configuration Setup")
    print("=" * 50)
    
    # Setup configuration
    if not setup_config_directory():
        sys.exit(1)
    
    # Test configuration
    if not test_configuration():
        print("\n❌ Configuration testing failed")
        sys.exit(1)
    
    # Show usage examples
    show_usage_examples()
    
    print(f"\n🎉 Setup complete! Current environment: {os.getenv('BYKILT_ENV', 'dev')}")

if __name__ == '__main__':
    main()