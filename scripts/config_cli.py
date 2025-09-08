#!/usr/bin/env python3
"""
Configuration management CLI for 2bykilt

This script provides command-line tools for:
- Loading and validating configurations
- Comparing configurations between environments
- Generating effective configuration artifacts
- Environment management operations
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config.multi_env_loader import ConfigLoader, ConfigValidationError


def load_command(args):
    """Load and display configuration for an environment"""
    try:
        loader = ConfigLoader(args.config_dir)
        config = loader.load_config(args.environment)
        
        if args.output:
            # Save to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            print(f"Configuration saved to: {output_path}")
        else:
            # Print to stdout
            print(json.dumps(config, indent=2, ensure_ascii=False))
        
        return 0
        
    except ConfigValidationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def validate_command(args):
    """Validate configuration for an environment"""
    try:
        loader = ConfigLoader(args.config_dir)
        config = loader.load_config(args.environment)
        
        print(f"✅ Configuration for '{args.environment}' is valid")
        print(f"Config version: {config.get('config_version', 'unknown')}")
        print(f"Environment: {config.get('_metadata', {}).get('environment', 'unknown')}")
        
        return 0
        
    except ConfigValidationError as e:
        print(f"❌ Configuration validation failed: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        return 1


def compare_command(args):
    """Compare configurations between two environments"""
    try:
        loader = ConfigLoader(args.config_dir)
        comparison = loader.compare_configs(args.env1, args.env2)
        
        if args.output:
            # Save to file
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(comparison, f, indent=2, ensure_ascii=False)
            
            print(f"Comparison saved to: {output_path}")
        else:
            # Print formatted comparison
            print(f"Comparing {args.env1} vs {args.env2}")
            print("=" * 50)
            
            summary = comparison['comparison_summary']
            if summary['configs_identical']:
                print("✅ Configurations are identical")
            else:
                print(f"❌ Found {summary['total_differences']} differences:")
                print()
                
                for diff in comparison['differences']:
                    print(f"Path: {diff['path']}")
                    print(f"Type: {diff['type']}")
                    print(f"  {args.env1}: {diff['value_env1']}")
                    print(f"  {args.env2}: {diff['value_env2']}")
                    print()
        
        return 0
        
    except ConfigValidationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def effective_command(args):
    """Generate effective configuration artifact"""
    try:
        loader = ConfigLoader(args.config_dir)
        config = loader.load_config(args.environment)
        
        # Save effective configuration
        output_path = args.output or f"effective_config_{args.environment}.json"
        saved_path = loader.save_effective_config(config, output_path)
        
        print(f"✅ Effective configuration saved to: {saved_path}")
        print(f"Environment: {args.environment}")
        print(f"Generated at: {config.get('_metadata', {}).get('loaded_at', 'unknown')}")
        
        return 0
        
    except ConfigValidationError as e:
        print(f"Configuration error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        return 1


def list_command(args):
    """List available configuration environments"""
    try:
        config_dir = Path(args.config_dir)
        
        if not config_dir.exists():
            print(f"Configuration directory not found: {config_dir}", file=sys.stderr)
            return 1
        
        print("Available configuration environments:")
        print("=" * 40)
        
        # Find all .yml files except base.yml and schema files
        env_files = []
        for yml_file in config_dir.glob("*.yml"):
            if yml_file.name != "base.yml":
                env_name = yml_file.stem
                env_files.append(env_name)
        
        if not env_files:
            print("No environment configurations found")
            return 1
        
        for env in sorted(env_files):
            print(f"  - {env}")
        
        # Also show current environment
        current_env = ConfigLoader()._get_current_environment()
        print(f"\nCurrent environment (BYKILT_ENV): {current_env}")
        
        return 0
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Configuration management CLI for 2bykilt",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s load development                    # Load development config
  %(prog)s validate staging                   # Validate staging config  
  %(prog)s compare development production     # Compare dev vs prod
  %(prog)s effective production -o prod.json  # Generate effective config
  %(prog)s list                               # List available environments
        """
    )
    
    parser.add_argument(
        '--config-dir', '-c',
        default='config',
        help='Configuration directory path (default: config)'
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Load command
    load_parser = subparsers.add_parser('load', help='Load configuration for an environment')
    load_parser.add_argument('environment', help='Environment name (development/staging/production)')
    load_parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    load_parser.set_defaults(func=load_command)
    
    # Validate command
    validate_parser = subparsers.add_parser('validate', help='Validate configuration')
    validate_parser.add_argument('environment', help='Environment name to validate')
    validate_parser.set_defaults(func=validate_command)
    
    # Compare command
    compare_parser = subparsers.add_parser('compare', help='Compare configurations')
    compare_parser.add_argument('env1', help='First environment name')
    compare_parser.add_argument('env2', help='Second environment name')
    compare_parser.add_argument('--output', '-o', help='Output file path (default: stdout)')
    compare_parser.set_defaults(func=compare_command)
    
    # Effective command
    effective_parser = subparsers.add_parser('effective', help='Generate effective configuration')
    effective_parser.add_argument('environment', help='Environment name')
    effective_parser.add_argument('--output', '-o', help='Output file path')
    effective_parser.set_defaults(func=effective_command)
    
    # List command
    list_parser = subparsers.add_parser('list', help='List available environments')
    list_parser.set_defaults(func=list_command)
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    return args.func(args)


# Add helper method to ConfigLoader for current environment
def _get_current_environment(self):
    """Get current environment name"""
    env = os.getenv('BYKILT_ENV', 'dev')
    if env == 'dev':
        return 'development'
    elif env == 'staging':
        return 'staging'
    elif env == 'prod':
        return 'production'
    else:
        return env

# Monkey patch the method
import os
ConfigLoader._get_current_environment = _get_current_environment


if __name__ == '__main__':
    sys.exit(main())