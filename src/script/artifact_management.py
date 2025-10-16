"""
Artifact management for script execution.

This module provides functions for managing artifacts generated during
script execution, including moving files to artifact directories and
creating execution metadata.
"""

import shutil
import datetime
from pathlib import Path
from typing import Dict, Any
from src.utils.app_logger import logger


async def move_script_files_to_artifacts(script_info: Dict[str, Any], script_path: str, script_type: str) -> None:
    """
    Move generated script files from myscript directory to artifacts directory after successful execution.
    
    Args:
        script_info: Dictionary containing script information
        script_path: Path to the executed script
        script_type: Type of script (browser-control, git-script, etc.)
    """
    try:
        # Only move files for browser-control type to preserve static scripts
        if script_type != 'browser-control':
            logger.info(f"ℹ️ Skipping file movement for {script_type} type (preserving static scripts)")
            return
            
        # Create artifacts/runs directory structure
        artifacts_dir = Path('artifacts')
        runs_dir = artifacts_dir / 'runs'
        runs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate run ID based on script type and timestamp
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        script_name = script_info.get('name', 'unknown').replace(' ', '_').replace('/', '_')
        run_id = f"{script_type}_{script_name}_{timestamp}"
        
        # Create run-specific directory
        run_dir = runs_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"📁 Moving files to artifacts directory: {run_dir}")
        
        # Move files based on script type
        if script_type == 'browser-control':
            # Move browser_control.py and related files from myscript
            myscript_dir = Path('myscript')
            if myscript_dir.exists():
                # Move the generated script
                script_file = myscript_dir / 'browser_control.py'
                if script_file.exists():
                    shutil.copy2(str(script_file), str(run_dir / 'browser_control.py'))
                    logger.info(f"📄 Copied browser_control.py to {run_dir}")
                
                # Move pytest.ini if it exists
                pytest_ini = myscript_dir / 'pytest.ini'
                if pytest_ini.exists():
                    shutil.copy2(str(pytest_ini), str(run_dir / 'pytest.ini'))
                    logger.info(f"📄 Copied pytest.ini to {run_dir}")
                
                # Move any generated __pycache__ files
                pycache_dir = myscript_dir / '__pycache__'
                if pycache_dir.exists():
                    try:
                        shutil.copytree(str(pycache_dir), str(run_dir / '__pycache__'), dirs_exist_ok=True)
                        logger.info(f"📄 Copied __pycache__ to {run_dir}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not copy __pycache__: {e}")
                
                # Move any .pytest_cache files
                pytest_cache_dir = myscript_dir / '.pytest_cache'
                if pytest_cache_dir.exists():
                    try:
                        shutil.copytree(str(pytest_cache_dir), str(run_dir / '.pytest_cache'), dirs_exist_ok=True)
                        logger.info(f"📄 Copied .pytest_cache to {run_dir}")
                    except Exception as e:
                        logger.warning(f"⚠️ Could not copy .pytest_cache: {e}")
        
        # Create a metadata file with execution information
        metadata = {
            'script_type': script_type,
            'script_name': script_info.get('name', 'unknown'),
            'execution_time': timestamp,
            'run_id': run_id,
            'original_path': script_path
        }
        
        metadata_file = run_dir / 'execution_metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        logger.info(f"📋 Created execution metadata: {metadata_file}")
        logger.info(f"✅ Successfully archived {script_type} files to artifacts directory")

    except Exception as e:
        logger.error(f"❌ Failed to archive script files to artifacts: {e}")
        # Don't raise exception to avoid breaking the main execution flow
