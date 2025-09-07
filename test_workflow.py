#!/usr/bin/env python3
"""
Test GitScriptAutomator workflow
"""
import asyncio
import tempfile
import os
import sys
sys.path.insert(0, '/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt')

from src.utils.git_script_automator import GitScriptAutomator

async def test_workflow():
    # Create test workspace
    workspace = tempfile.mkdtemp()
    script_path = '/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt/test_script.py'
    
    print(f"Test workspace: {workspace}")
    print(f"Script path: {script_path}")
    
    # Create automator
    automator = GitScriptAutomator('edge')
    
    try:
        result = await automator.execute_git_script_workflow(
            workspace_dir=workspace,
            script_path=script_path,
            command='python ${script_path} --query=${params.query}',
            params={'query': 'test_value'}
        )
        print('SUCCESS - Result:', result)
    except Exception as e:
        print('ERROR:', str(e))
        import traceback
        traceback.print_exc()
    finally:
        # Cleanup
        automator.cleanup_selenium_profile()
        import shutil
        shutil.rmtree(workspace, ignore_errors=True)

if __name__ == "__main__":
    asyncio.run(test_workflow())
