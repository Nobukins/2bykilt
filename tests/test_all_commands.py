#!/usr/bin/env python3
"""
All command types testing script for debugging UI execution issues
"""
import asyncio
import pytest
import logging
import os
import sys
import threading
from pathlib import Path
from _pytest.outcomes import OutcomeException

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import modules
from src.script.script_manager import run_script
from src.modules.direct_browser_control import execute_direct_browser_control

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def _run_async(coro_fn):
    result = {}

    def worker():
        try:
            result["value"] = asyncio.run(coro_fn())
        except (Exception, OutcomeException) as exc:
            result["error"] = exc

    thread = threading.Thread(target=worker, name="test-all-commands-runner", daemon=True)
    thread.start()
    thread.join()

    if "error" in result:
        raise result["error"]

    return result.get("value")


async def _run_action_runner_template():
    """Test action_runner_template type"""
    logger.info("\n=== Testing action_runner_template ===")
    
    script_info = {
        'name': 'action-runner-nogtips',
        'type': 'action_runner_template',
        'action_script': 'nogtips_search',
        'description': '保存済みのブラウザ操作魔法を唱える',
        'params': [
            {
                'name': 'query',
                'required': False,
                'type': 'string',
                'description': '検索クエリ',
                'default': 'LLMs.txt'
            }
        ],
        'command': 'python ./myscript/unified_action_launcher.py --action ${action_script} --query ${params.query|LLMs.txt} --slowmo 2500 --countdown 3'
    }
    
    params = {'query': 'テストクエリ'}
    
    try:
        result, _ = await run_script(script_info, params, headless=False)
        logger.info(f"✅ action_runner_template result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ action_runner_template failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


@pytest.mark.local_only
def test_action_runner_template():
    assert _run_async(_run_action_runner_template)


async def _run_browser_control():
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


@pytest.mark.local_only
@pytest.mark.playwright_required
def test_browser_control():
    assert _run_async(_run_browser_control)


async def _run_git_script():
    """Test git-script type"""
    logger.info("\n=== Testing git-script ===")
    
    script_info = {
        'name': 'site-defined-script',
        'type': 'git-script',
        'git': 'https://github.com/Nobukins/sample-tests.git',
        'script_path': 'search_script.py',
        'version': 'main',
        'description': 'git管理でのブラウザ操作のコマンド管理',
        'params': [
            {
                'name': 'query',
                'required': True,
                'type': 'string',
                'description': 'Search query to execute'
            }
        ],
        'command': 'python -m pytest ${script_path} --query ${params.query}',
        'timeout': 120,
        'slowmo': 1000
    }
    
    params = {'query': 'gitテスト'}
    
    try:
        result, _ = await run_script(script_info, params, headless=False)
        logger.info(f"✅ git-script result: {result}")
        return True
    except Exception as e:
        logger.error(f"❌ git-script failed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


@pytest.mark.local_only
def test_git_script():
    assert _run_async(_run_git_script)


def main():
    """Run all tests"""
    logger.info("Starting comprehensive test of all command types...")
    
    # Test each command type
    results = {}
    
    results['action_runner_template'] = _run_async(_run_action_runner_template)
    results['browser_control'] = _run_async(_run_browser_control)
    results['git_script'] = _run_async(_run_git_script)
    
    # Summary
    logger.info("\n=== TEST SUMMARY ===")
    for cmd_type, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"{cmd_type}: {status}")
    
    total_passed = sum(results.values())
    logger.info(f"\nPassed: {total_passed}/3 tests")
    
    if total_passed == 3:
        logger.info("🎉 All tests passed!")
    else:
        logger.warning("⚠️ Some tests failed. Check logs for details.")

if __name__ == "__main__":
    main()
