"""Helper functions for UI components.

This module contains utility functions used by the Gradio UI.
"""
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import yaml

from src.utils.path_helpers import get_llms_txt_path

logger = logging.getLogger(__name__)


def load_actions_config(config_path: Optional[Path] = None) -> Dict[str, Any]:
    """Load actions configuration from llms.txt file.
    
    Args:
        config_path: Optional custom path to llms.txt file
        
    Returns:
        Dictionary containing parsed YAML configuration, or empty dict on error
    """
    target_path = Path(config_path or get_llms_txt_path())
    try:
        if not target_path.exists():
            logger.warning("Actions config file not found at %s", target_path)
            return {}

        with target_path.open('r', encoding='utf-8') as file:
            content = file.read()

        try:
            actions_config = yaml.safe_load(content) or {}
        except yaml.YAMLError as exc:
            logger.error("YAML parsing error: %s", exc)
            return {}

        if isinstance(actions_config, dict) and 'actions' in actions_config:
            return actions_config

        logger.warning("Invalid actions config structure in %s", target_path)
        return {}
    except (OSError, IOError) as error:
        logger.error("Failed to load actions config from %s: %s", target_path, error)
        return {}
    except Exception as error:  # pragma: no cover - unexpected errors
        logger.exception("Unexpected error loading actions config: %s", error)
        return {}


def load_llms_file(path: Optional[Path] = None) -> str:
    """Load llms.txt file content for UI editing.
    
    Args:
        path: Optional custom path to llms.txt file
        
    Returns:
        File content as string, or empty string if file not found
    """
    target_path = Path(path or get_llms_txt_path())
    try:
        return target_path.read_text(encoding='utf-8')
    except FileNotFoundError:
        logger.info("llms.txt file not found at %s, returning empty string", target_path)
        return ''
    except (OSError, IOError) as error:
        logger.error("Failed to read llms.txt from %s: %s", target_path, error)
        return ''


def save_llms_file(content: str, path: Optional[Path] = None) -> str:
    """Save content to llms.txt file.
    
    Args:
        content: YAML content to write to file
        path: Optional custom path to llms.txt file
        
    Returns:
        Success message string
        
    Raises:
        IOError: If file write fails
    """
    target_path = Path(path or get_llms_txt_path())
    try:
        target_path.write_text(content, encoding='utf-8')
        logger.info("Successfully saved llms.txt to %s", target_path)
        return "✅ llms.txtを保存しました"
    except (OSError, IOError) as error:
        logger.error("Failed to save llms.txt to %s: %s", target_path, error)
        raise IOError(f"Failed to save llms.txt: {error}") from error


def discover_and_preview_llmstxt(url: str, https_only: bool = True) -> Tuple[str, str, str]:
    """Discover and preview llms.txt from remote URL.
    
    Returns:
        tuple: (preview_json, status_message, discovered_actions_json)
    """
    try:
        from src.modules.llmstxt_discovery import discover_and_parse
        from src.security.llmstxt_validator import validate_remote_llmstxt
        
        # Auto-discover and parse
        result = discover_and_parse(url, https_only=https_only)
        
        if not result['success']:
            return (
                "",
                f"❌ Discovery failed: {result.get('error', 'Unknown error')}",
                ""
            )
        
        # Extract discovered actions
        all_actions = []
        browser_control = result.get('browser_control', [])
        git_scripts = result.get('git_scripts', [])
        
        all_actions.extend(browser_control)
        all_actions.extend(git_scripts)
        
        if not all_actions:
            return (
                "",
                "ℹ️ No 2bykilt actions found in the discovered llms.txt",
                ""
            )
        
        # Security validation
        yaml_content = result.get('raw_content', '')
        validation_result = validate_remote_llmstxt(
            url, all_actions, yaml_content, https_only=https_only
        )
        
        if not validation_result.valid:
            errors = "\n".join(validation_result.errors)
            return (
                json.dumps(all_actions, indent=2, ensure_ascii=False),
                f"⚠️ Security validation failed:\n{errors}",
                json.dumps(all_actions, indent=2, ensure_ascii=False)
            )
        
        # Success - prepare preview
        preview_text = "✅ Discovery successful!\n\n"
        preview_text += f"Source URL: {url}\n"
        preview_text += f"Actions found: {len(all_actions)}\n"
        preview_text += f"  - Browser control: {len(browser_control)}\n"
        preview_text += f"  - Git scripts: {len(git_scripts)}\n\n"

        if validation_result.warnings:
            preview_text += "⚠️ Warnings:\n"
            for warning in validation_result.warnings:
                preview_text += f"  - {warning}\n"
            preview_text += "\n"

        preview_text += "Actions to be imported:\n"
        for action in all_actions:
            action_name = action.get('name', '<unnamed>')
            action_type = action.get('type', '<unknown>')
            preview_text += f"  - {action_name} ({action_type})\n"

        return (
            json.dumps(all_actions, indent=2, ensure_ascii=False),
            preview_text,
            json.dumps(all_actions, indent=2, ensure_ascii=False)
        )
        
    except Exception as e:
        return (
            "",
            f"❌ Error during discovery: {str(e)}",
            ""
        )


def import_llmstxt_actions(actions_json: str, strategy: str = "skip", llms_txt_path: Optional[Path] = None) -> str:
    """Import discovered actions into local llms.txt."""
    try:
        from src.modules.llmstxt_merger import LlmsTxtMerger

        actions = json.loads(actions_json)
        if not actions:
            return "❌ No actions to import"

        target_path = Path(llms_txt_path or get_llms_txt_path())
        merger = LlmsTxtMerger(str(target_path), strategy=strategy)
        result = merger.merge_actions(actions, create_backup=True)

        if not result.success:
            return f"❌ Import failed: {result.error_message}"

        summary = result.summary()
        return f"✅ Import completed!\n\n{summary}"
    except Exception as error:  # pragma: no cover - surfaced via UI
        return f"❌ Error during import: {error}"


def preview_merge_llmstxt(actions_json: str, strategy: str = "skip", llms_txt_path: Optional[Path] = None) -> str:
    """Preview what would happen during merge without modifying files."""
    try:
        from src.modules.llmstxt_merger import LlmsTxtMerger

        actions = json.loads(actions_json)
        if not actions:
            return "ℹ️ No actions to preview"

        target_path = Path(llms_txt_path or get_llms_txt_path())
        merger = LlmsTxtMerger(str(target_path), strategy=strategy)
        preview = merger.preview_merge(actions)

        summary = preview.summary()
        if preview.has_conflicts:
            conflict_details = "\n\nConflict Details:\n"
            for conflict in preview.conflicts:
                conflict_details += (
                    f"  - {conflict['name']}: {conflict['existing_type']} → "
                    f"{conflict['new_type']} ({conflict['resolution']})\n"
                )
            summary += conflict_details

        return summary
    except Exception as error:  # pragma: no cover - surfaced via UI
        return f"❌ Error during preview: {error}"


def load_env_browser_settings_file(env_file) -> Tuple[str, str, str]:
    """Load browser settings from environment file."""
    from dotenv import load_dotenv
    
    if not env_file:
        return ("", "", "❌ No env file selected")
    # Load environment vars from file path
    load_dotenv(env_file.name, override=True)
    path = os.getenv('CHROME_PATH', '')
    user_data = os.getenv('CHROME_USER_DATA', '')
    return (
        f"**現在のブラウザパス**: {path}",
        f"**ユーザーデータパス**: {user_data}",
        "✅ Env settings loaded"
    )
