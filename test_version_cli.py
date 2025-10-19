#!/usr/bin/env python3
"""
Quick test script to verify version CLI integration works.
This bypasses the heavy bykilt.py imports.
"""
import sys
import argparse
from unittest.mock import MagicMock

# Mock heavy dependencies before importing
sys.modules['gradio'] = MagicMock()
sys.modules['nest_asyncio'] = MagicMock()

# Now import the actual CLI  
from src.version.cli import create_version_parser, version_command

def test_version_command():
    """Test that version command integration works"""
    
    # Create main parser
    parser = argparse.ArgumentParser(description="Test 2Bykilt CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Add version subparser (this is what src/cli/main.py does)
    create_version_parser(subparsers)
    
    # Test version show
    print("Testing: version show")
    args = parser.parse_args(['version', 'show'])
    assert args.command == 'version'
    assert args.version_subcommand == 'show'
    result = version_command(args)
    assert result == 0
    print("✅ version show works\n")
    
    # Test version set
    print("Testing: version set 1.0.0")
    args = parser.parse_args(['version', 'set', '1.0.0'])
    assert args.command == 'version'
    assert args.version_subcommand == 'set'
    result = version_command(args)
    assert result == 0
    print("✅ version set works\n")
    
    # Test version bump
    print("Testing: version bump --type minor")
    args = parser.parse_args(['version', 'bump', '--type', 'minor'])
    assert args.command == 'version'
    assert args.version_subcommand == 'bump'
    result = version_command(args)
    assert result == 0
    print("✅ version bump works\n")
    
    print("="*60)
    print("✅ ALL VERSION COMMAND TESTS PASSED")
    print("="*60)

if __name__ == '__main__':
    test_version_command()
