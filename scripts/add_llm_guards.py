#!/usr/bin/env python3
"""
Script to add LLM import guards to agent modules.
Part of Issue #43 implementation.
"""
import sys
from pathlib import Path

# Guard template
GUARD_TEMPLATE = '''"""
{module_description}

This module provides LLM agent functionality and requires:
- ENABLE_LLM=true environment variable or feature flag
- Full requirements.txt installation (not requirements-minimal.txt)

When ENABLE_LLM=false, this module cannot be imported and will raise ImportError.
This ensures complete isolation of LLM dependencies for AI governance compliance.
"""

# Import guard: Block import when LLM functionality is disabled
try:
    from src.config.feature_flags import is_llm_enabled
    _ENABLE_LLM = is_llm_enabled()
except Exception:
    import os
    _ENABLE_LLM = os.getenv("ENABLE_LLM", "false").lower() == "true"

if not _ENABLE_LLM:
    raise ImportError(
        "LLM agent functionality is disabled (ENABLE_LLM=false). "
        "This module requires full requirements.txt installation and ENABLE_LLM=true. "
        "To use agent features: "
        "1. Install full requirements: pip install -r requirements.txt "
        "2. Enable LLM: export ENABLE_LLM=true or set in .env file"
    )

'''

def add_guard_to_file(filepath: Path, module_description: str):
    """Add import guard to a Python file."""
    try:
        content = filepath.read_text(encoding='utf-8')
        
        # Check if guard already exists
        if '_ENABLE_LLM' in content or 'Import guard:' in content:
            print(f"⏭️  Skip: {filepath.name} (guard already exists)")
            return False
        
        # Find first import or class/function definition
        lines = content.split('\n')
        insert_position = 0
        
        # Skip shebang and existing docstring
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            if stripped.startswith('import ') or stripped.startswith('from '):
                insert_position = i
                break
            if stripped.startswith('class ') or stripped.startswith('def '):
                insert_position = i
                break
        
        # Insert guard
        guard = GUARD_TEMPLATE.format(module_description=module_description)
        new_content = '\n'.join(lines[:insert_position]) + '\n' + guard + '\n'.join(lines[insert_position:])
        
        filepath.write_text(new_content, encoding='utf-8')
        print(f"✅ Added guard: {filepath.name}")
        return True
        
    except Exception as e:
        print(f"❌ Error processing {filepath.name}: {e}")
        return False

def main():
    """Main entry point."""
    project_root = Path(__file__).parent.parent
    
    # Define files to process with their descriptions
    files_to_process = [
        (project_root / "src/agent/custom_agent.py", "Custom browser automation agent implementation"),
        (project_root / "src/agent/custom_message_manager.py", "Agent message management and history tracking"),
        (project_root / "src/agent/custom_prompts.py", "System prompts and agent instructions"),
        (project_root / "src/agent/custom_views.py", "Agent view models and data structures"),
        (project_root / "src/agent/agent_manager.py", "Agent lifecycle and execution management"),
        (project_root / "src/agent/simplified_prompts.py", "Simplified prompt templates"),
        (project_root / "src/llm/docker_sandbox.py", "LLM execution sandbox with Docker isolation"),
        (project_root / "src/controller/custom_controller.py", "Custom browser controller for agent actions"),
        (project_root / "src/browser/custom_browser.py", "Custom browser implementation with LLM integration"),
        (project_root / "src/browser/custom_context.py", "Custom browser context management"),
    ]
    
    processed = 0
    skipped = 0
    errors = 0
    
    print("🔧 Adding LLM import guards to modules...")
    print()
    
    for filepath, description in files_to_process:
        if not filepath.exists():
            print(f"⚠️  Warning: {filepath.name} not found")
            errors += 1
            continue
        
        result = add_guard_to_file(filepath, description)
        if result:
            processed += 1
        else:
            if '_ENABLE_LLM' in filepath.read_text():
                skipped += 1
            else:
                errors += 1
    
    print()
    print(f"📊 Summary:")
    print(f"  ✅ Processed: {processed}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"  ❌ Errors: {errors}")
    
    return 0 if errors == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
