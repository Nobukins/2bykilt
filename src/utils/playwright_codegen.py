import os
import subprocess
import tempfile
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

def run_playwright_codegen(url):
    """
    Run playwright codegen for the given URL and capture the generated script.
    """
    try:
        fd, temp_path = tempfile.mkstemp(suffix='.py')
        os.close(fd)
        
        cmd = f"playwright codegen {url} --target python -o {temp_path}"
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        stdout, stderr = process.communicate(timeout=300)
        
        if process.returncode == 0 and os.path.exists(temp_path):
            with open(temp_path, 'r') as f:
                script_content = f.read()
            script_content = convert_to_action_format(script_content)
            os.unlink(temp_path)
            return True, script_content
        else:
            error_msg = stderr.decode('utf-8') if stderr else "Unknown error"
            return False, f"Error running playwright codegen: {error_msg}"
    except subprocess.TimeoutExpired:
        process.kill()
        return False, "Playwright codegen timed out after 5 minutes"
    except Exception as e:
        logger.error(f"Failed to run playwright codegen: {str(e)}")
        return False, f"Failed to run playwright codegen: {str(e)}"

def convert_to_action_format(script_content):
    """
    Convert the playwright codegen output to action_runner_template format.
    """
    lines = script_content.splitlines()
    action_lines = []
    for line in lines:
        if line.startswith('from playwright') or line.startswith('import ') or line.startswith('#') or not line.strip():
            continue
        if 'playwright.sync_api' in line or '.launch(' in line or '.new_context(' in line or '.new_page(' in line or '.close(' in line:
            continue
        if '.goto(' in line or '.click(' in line or '.fill(' in line or '.check(' in line or '.press(' in line or '.wait_for' in line:
            if not line.strip().startswith('await '):
                line = re.sub(r'(\s*)(page\.\w+\()', r'\1await \2', line)
            action_lines.append(line)
    
    template = """async def run_actions(page, query=None):
    \"\"\"Auto-generated from playwright codegen\"\"\"
    """
    for line in action_lines:
        template += f"    {line}\n"
    template += "    await page.wait_for_timeout(3000)\n"
    return template

def save_as_action_file(script_content, file_name, action_name=None):
    """
    Save the script content as a new action file and update llms.txt.
    
    Args:
        script_content (str): Script content to save
        file_name (str): File name (without extension)
        action_name (str, optional): Custom name for the action. Defaults to file_name.
        
    Returns:
        tuple: (success, message)
    """
    try:
        # Ensure file_name has .py extension
        if not file_name.endswith('.py'):
            file_name += '.py'
            
        # Default action_name to file_name without extension if not provided
        if action_name is None or action_name.strip() == '':
            action_name = os.path.splitext(file_name)[0]
            
        # Get the actions directory path
        root_dir = Path(__file__).parent.parent.parent
        actions_dir = root_dir / 'tmp/myscript/actions'
        
        # Create actions directory if it doesn't exist
        if not actions_dir.exists():
            actions_dir.mkdir(parents=True)
            
        # Full path to save the action file
        file_path = actions_dir / file_name
        
        # Save the script content to the file
        with open(file_path, 'w') as f:
            f.write(script_content)
            
        # Update llms.txt
        llms_path = root_dir / 'llms.txt'
        new_entry = f"""
  - name: {action_name}
    type: action_runner_template
    action_script: actions/{file_name}
    params:
      - name: query
        required: true
        type: string
        description: "検索クエリ"
    command: python ./tmp/myscript/action_runner.py --action ${{action_script}} --query "${{params.query}}" --slowmo 1500 --countdown 3
"""
        if llms_path.exists():
            # Read existing content
            with open(llms_path, 'r') as f:
                content = f.read()
                
            # Check if entry already exists
            if f"name: {action_name}" in content:
                return True, f"Action file saved but entry already exists in llms.txt"
                
            # Append new entry to llms.txt
            with open(llms_path, 'a') as f:
                f.write(new_entry)
        else:
            # Create llms.txt if it doesn't exist
            with open(llms_path, 'w') as f:
                f.write(f"actions:{new_entry}")
                
        return True, f"Successfully saved action file and added to llms.txt: {action_name}"
    except Exception as e:
        logger.error(f"Failed to save action file: {str(e)}")
        return False, f"Failed to save action file: {str(e)}"
