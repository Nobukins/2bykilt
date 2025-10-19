"""
Main entry point module for 2Bykilt application.
Handles CLI argument parsing and UI/API initialization.
"""

import argparse
import os
import sys
import traceback

from src.utils.default_config_settings import default_config
from src.ui.helpers import (
    discover_and_preview_llmstxt,
    preview_merge_llmstxt,
    import_llmstxt_actions,
)
from src.api.app import create_fastapi_app, run_app
from src.utils.path_helpers import get_assets_dir
from src.version.cli import create_version_parser, version_command


def _handle_llms_cli(args) -> None:
    """Handle llms.txt import CLI commands."""
    if args.preview_llms:
        print(f"🔍 Previewing llms.txt import from: {args.preview_llms}")
        print(f"   Strategy: {args.strategy}")
        print(f"   HTTPS Only: {args.https_only}")
        print()
        
        _, status, actions_json = discover_and_preview_llmstxt(args.preview_llms, args.https_only)
        print(status)
        
        if actions_json:
            print("\n" + "="*60)
            print("Merge Preview:")
            print("="*60)
            preview_result = preview_merge_llmstxt(actions_json, args.strategy)
            print(preview_result)
        
        sys.exit(0)
    
    if args.import_llms:
        print(f"📥 Importing llms.txt from: {args.import_llms}")
        print(f"   Strategy: {args.strategy}")
        print(f"   HTTPS Only: {args.https_only}")
        print()
        
        _, status, actions_json = discover_and_preview_llmstxt(args.import_llms, args.https_only)
        print(status)
        
        if not actions_json:
            print("❌ Discovery failed or no actions found. Import aborted.")
            sys.exit(1)
        
        if "Security validation failed" in status:
            print("❌ Security validation failed. Import aborted.")
            sys.exit(1)
        
        print("\n" + "="*60)
        print("Merge Preview:")
        print("="*60)
        preview_result = preview_merge_llmstxt(actions_json, args.strategy)
        print(preview_result)
        
        print("\n" + "="*60)
        print("Confirming Import...")
        print("="*60)
        import_result = import_llmstxt_actions(actions_json, args.strategy)
        print(import_result)
        
        if "✅ Import completed!" in import_result:
            sys.exit(0)
        else:
            sys.exit(1)


def _ensure_asset_directories() -> None:
    """Create placeholder asset directories required by the UI."""
    assets_dir = get_assets_dir()
    css_dir = assets_dir / "css"
    js_dir = assets_dir / "js"
    fonts_dir = assets_dir / "fonts"

    for directory in (css_dir, js_dir, fonts_dir):
        directory.mkdir(parents=True, exist_ok=True)

    for family in ["ui-sans-serif", "system-ui"]:
        family_dir = fonts_dir / family
        family_dir.mkdir(parents=True, exist_ok=True)

        for weight in ["Regular", "Bold"]:
            font_path = family_dir / f"{family}-{weight}.woff2"
            font_path.touch(exist_ok=True)


def main():
    """Main entry point for both CLI and UI."""
    # Initialize metrics system
    try:
        from src.metrics import initialize_metrics
        initialize_metrics()
        print("📊 Metrics system initialized successfully")
    except Exception as e:
        print(f"⚠️  Failed to initialize metrics system: {e}")
        traceback.print_exc()

    # Initialize timeout manager for job/run timeout and cancellation support
    try:
        from src.utils.timeout_manager import get_timeout_manager, TimeoutConfig
        from src.utils.timeout_manager import reset_timeout_manager
        
        # Reset any existing manager to ensure clean state
        reset_timeout_manager()
        
        # Create timeout config with reasonable defaults for job execution
        timeout_config = TimeoutConfig(
            job_timeout=int(os.getenv('JOB_TIMEOUT', '3600')),  # 1 hour default
            operation_timeout=int(os.getenv('OPERATION_TIMEOUT', '300')),  # 5 minutes default
            step_timeout=int(os.getenv('STEP_TIMEOUT', '60')),  # 1 minute default
            network_timeout=int(os.getenv('NETWORK_TIMEOUT', '30')),  # 30 seconds default
            enable_cancellation=True,
            graceful_shutdown_timeout=int(os.getenv('GRACEFUL_SHUTDOWN_TIMEOUT', '10'))
        )
        
        # Initialize global timeout manager
        get_timeout_manager(timeout_config)
        print("⏱️  Timeout manager initialized successfully")
        print(f"   Job timeout: {timeout_config.job_timeout}s")
        print(f"   Operation timeout: {timeout_config.operation_timeout}s")
        print(f"   Cancellation enabled: {timeout_config.enable_cancellation}")
        
    except Exception as e:
        print(f"⚠️  Failed to initialize timeout manager: {e}")
        traceback.print_exc()

    # Import theme_map here to avoid circular imports
    from bykilt import theme_map, create_ui
    
    # For UI or default case, proceed with Gradio
    parser = argparse.ArgumentParser(description="Gradio UI for 2Bykilt Agent")
    
    # Create subparsers for version command (Issue #342)
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    create_version_parser(subparsers)
    
    # Global arguments (UI + version)
    parser.add_argument(
        "--ui",
        action="store_true",
        help="Launch the Gradio UI (default mode). Provided for CLI compatibility.",
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["ui"],
        help="Legacy alias for `--ui`. Optional; defaults to UI mode when omitted.",
    )
    parser.add_argument("--ip", type=str, default="127.0.0.1", help="IP address to bind to")
    parser.add_argument("--port", type=int, default=7788, help="Port to listen on")
    parser.add_argument("--theme", type=str, default="Ocean", choices=theme_map.keys(), help="Theme to use for the UI")
    parser.add_argument("--dark-mode", action="store_true", help="Enable dark mode")
    
    # llms.txt import CLI arguments (Issue #320 Phase 3)
    parser.add_argument(
        "--import-llms",
        metavar="URL",
        help="Import actions from remote llms.txt URL into local llms.txt. Performs discovery, security validation, and merge."
    )
    parser.add_argument(
        "--preview-llms",
        metavar="URL",
        help="Preview what would be imported from remote llms.txt URL without modifying files."
    )
    parser.add_argument(
        "--strategy",
        choices=["skip", "overwrite", "rename"],
        default="skip",
        help="Conflict resolution strategy for llms.txt import. skip: keep existing (default) | overwrite: replace with new | rename: add with number suffix"
    )
    parser.add_argument(
        "--https-only",
        action="store_true",
        help="Only allow HTTPS URLs for llms.txt import (default: True)"
    )
    parser.add_argument(
        "--no-https-only",
        dest="https_only",
        action="store_false",
        default=True,
        help="Allow HTTP URLs for llms.txt import (not recommended)"
    )
    
    args = parser.parse_args()
    
    # Handle version command (Issue #342)
    if args.command == "version":
        return version_command(args)
    
    # Handle llms.txt import CLI commands before launching UI
    _handle_llms_cli(args)


    # Normalize legacy UI flags/commands so downstream code has a single source of truth
    if getattr(args, "mode", None) == "ui":
        # Mirror the boolean flag for easier detection and future branching if needed
        setattr(args, "ui", True)

    ui_requested = getattr(args, "ui", False)
    if ui_requested:
        print("🖥️  UI mode requested via CLI flags")

    print(f"🔍 DEBUG: Selected theme: {args.theme}")
    print(f"🔍 DEBUG: Dark mode enabled: {args.dark_mode}")

    config_dict = default_config()
    demo = create_ui(config_dict, theme_name=args.theme)

    _ensure_asset_directories()

    # GradioとFastAPIを統合 - モジュール化版
    app = create_fastapi_app(demo, args)
    run_app(app, args)
