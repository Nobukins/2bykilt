#!/usr/bin/env python3
"""
Migration script to convert existing .pkl config files to JSON format.

Usage:
    python scripts/migrate_pkl_to_json.py [--input-dir INPUT_DIR] [--output-dir OUTPUT_DIR]

This script scans for .pkl files in the input directory (default: ./tmp/webui_settings),
loads them safely (only if ALLOW_PICKLE_CONFIG=true), validates the config,
and saves them as config.json in the output directory.

Security Note: This script only processes .pkl files if the environment variable
ALLOW_PICKLE_CONFIG is set to 'true'. This is to prevent accidental execution
of untrusted pickle data.
"""

import os
import sys
import argparse
import glob
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from utils.default_config_settings import load_config_from_file, save_config_to_json, CONFIG_SCHEMA

# Import Feature Flags for security control
try:
    from src.config.feature_flags import FeatureFlags
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False

def migrate_pkl_to_json(input_dir="./tmp/webui_settings", output_dir="./tmp/webui_settings"):
    """Migrate .pkl files to JSON format."""
    # Use Feature Flag for security control (fallback to env var if flags unavailable)
    if FEATURE_FLAGS_AVAILABLE:
        allow_pickle = FeatureFlags.is_enabled("security.allow_pickle_config")
    else:
        allow_pickle = os.getenv('ALLOW_PICKLE_CONFIG', 'false').lower() == 'true'
    
    if not allow_pickle:
        print("Error: ALLOW_PICKLE_CONFIG must be set to 'true' to process .pkl files.")
        print("This is a security measure to prevent deserialization of untrusted data.")
        return False

    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    pkl_files = list(input_path.glob("*.pkl"))
    if not pkl_files:
        print(f"No .pkl files found in {input_dir}")
        return True

    success_count = 0
    error_count = 0

    for pkl_file in pkl_files:
        print(f"Processing {pkl_file}...")
        try:
            config = load_config_from_file(str(pkl_file))
            if isinstance(config, dict):
                result = save_config_to_json(config, str(output_path))
                if result.startswith("Configuration saved"):
                    print(f"  ✓ Migrated to {result}")
                    success_count += 1
                else:
                    print(f"  ✗ Failed to save: {result}")
                    error_count += 1
            else:
                print(f"  ✗ Failed to load: {config}")
                error_count += 1
        except Exception as e:
            print(f"  ✗ Error processing {pkl_file}: {e}")
            error_count += 1

    print(f"\nMigration complete: {success_count} successful, {error_count} errors")
    return error_count == 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate .pkl config files to JSON")
    parser.add_argument("--input-dir", default="./tmp/webui_settings", help="Directory containing .pkl files")
    parser.add_argument("--output-dir", default="./tmp/webui_settings", help="Directory to save JSON files")
    args = parser.parse_args()

    success = migrate_pkl_to_json(args.input_dir, args.output_dir)
    sys.exit(0 if success else 1)