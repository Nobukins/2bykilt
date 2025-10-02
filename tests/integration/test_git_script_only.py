#!/usr/bin/env python3

import os
import sys
import asyncio
import logging
import pytest

pytestmark = pytest.mark.integration

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.script.script_manager import run_script

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_git_script():
    """Test git-script execution"""
    logger.info("\n=== Testing git-script ===")
    
    # Test data using the approved sample repository
    git_script_info = {
        "type": "git-script",
        "name": "search-script-test",
        "git": "https://github.com/Nobukins/sample-tests",
        "script_path": "search_script.py",
        "version": "main",
        "command": "python -m pytest ${script_path} --query='${params.query}' --slowmo=1000"
    }
    
    params = {
        "query": "edge"
    }
    
    try:
        result, script_path = await run_script(
            git_script_info,
            params=params,
            headless=False,
            browser_type="edge"  # Test with Edge to verify V8 OOM mitigation
        )
        logger.info(f"✅ git-script result: {result}")
        logger.info(f"Script path: {script_path}")
        return True
    except Exception as e:
        logger.error(f"❌ git-script failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    asyncio.run(test_git_script())
