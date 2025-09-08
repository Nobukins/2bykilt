#!/usr/bin/env python3
"""
Browser control only testing script
"""
import asyncio
import logging
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.modules.direct_browser_control import execute_direct_browser_control

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_browser_control():
    """Test browser-control type"""
    logger.info("\n=== Testing browser-control ===")
    
    action = {
        'name': 'phrase-search',
        'type': 'browser-control',
        'params': [
            {
                'name': 'query',
                'required': True,
                'type': 'string',
                'description': 'Search query to execute'
            }
        ],
        'slowmo': 1000,
        'description': 'browser-controlを利用したplaywrightベーススクリプト実行　その１',
        'flow': [
            {
                'action': 'command',
                'url': 'https://www.google.com',
                'wait_for': '#APjFqb'
            },
            {
                'action': 'click',
                'selector': '#APjFqb',
                'wait_for_navigation': True
            },
            {
                'action': 'fill_form',
                'selector': '#APjFqb',
                'value': '${params.query}'
            },
            {
                'action': 'keyboard_press',
                'selector': 'Enter'
            }
        ]
    }
    
    params = {'query': 'テスト'}
    
    try:
        result = await execute_direct_browser_control(action, **params)
        logger.info(f"✅ browser-control result: {result}")
        return result
    except Exception as e:
        logger.error(f"❌ browser-control failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    asyncio.run(test_browser_control())
