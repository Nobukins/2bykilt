import os
import tempfile
import subprocess
import shutil
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from src.utils.app_logger import logger

async def clone_git_repo(git_url: str, version: str = 'main', target_dir: Optional[str] = None) -> str:
    """Clone a git repository and checkout specified version/branch"""
    if target_dir is None:
        target_dir = tempfile.mkdtemp()
    
    try:
        # If the directory already exists, handle it appropriately
        if os.path.exists(target_dir):
            if os.path.exists(os.path.join(target_dir, '.git')):
                # It's a git repo, try to pull the latest changes
                logger.info(f"Repository already exists at {target_dir}, pulling latest changes")
                subprocess.run(['git', 'fetch', '--all'], cwd=target_dir, check=True)
                subprocess.run(['git', 'reset', '--hard', 'origin/main'], cwd=target_dir, check=True)
            else:
                # Directory exists but is not a git repo, remove it and clone
                logger.info(f"Directory exists but is not a git repo, removing: {target_dir}")
                shutil.rmtree(target_dir)
                os.makedirs(target_dir, exist_ok=True)
                logger.info(f"Cloning repository from {git_url} to {target_dir}")
                subprocess.run(['git', 'clone', git_url, target_dir], check=True)
        else:
            # Directory doesn't exist, create it and clone
            os.makedirs(os.path.dirname(target_dir), exist_ok=True)
            logger.info(f"Cloning repository from {git_url} to {target_dir}")
            subprocess.run(['git', 'clone', git_url, target_dir], check=True)
        
        # Checkout specific version/branch if provided
        if version:
            logger.info(f"Checking out version/branch: {version}")
            subprocess.run(['git', 'checkout', version], cwd=target_dir, check=True)
        
        return target_dir
    except subprocess.SubprocessError as e:
        logger.error(f"Git operation failed: {str(e)}")
        if os.path.exists(target_dir):
            shutil.rmtree(target_dir)
        raise RuntimeError(f"Failed to clone repository: {str(e)}")

def generate_browser_script(script_info: Dict[str, Any], params: Dict[str, str]) -> str:
    """
    Generate a pytest script from a browser control flow
    
    Args:
        script_info: Dictionary containing the script information
        params: Dictionary of parameters to use in the script
        
    Returns:
        str: The generated script content
    """
    flow = script_info.get('flow', [])
    script_content = '''
import pytest
from playwright.sync_api import expect, Page
import json
import os

@pytest.fixture(scope="module")
def browser_context_args(browser_context_args):
    context_args = {
        **browser_context_args,
        "viewport": {"width": 1280, "height": 720}
    }
    
    # Handle recording from environment variable
    recording_path = os.environ.get('RECORDING_PATH')
    if recording_path:
        context_args["record_video_dir"] = recording_path
        
    return context_args

@pytest.mark.browser_control
def test_browser_control(page: Page):
    try:
'''
    
    for step in flow:
        action = step.get('action')
        
        # Process dynamic values in parameters using the format ${params.key}
        for key, value in step.items():
            if isinstance(value, str) and '${params.' in value:
                for param_name, param_value in params.items():
                    placeholder = f"${{params.{param_name}}}"
                    if placeholder in value:
                        step[key] = value.replace(placeholder, str(param_value))
        
        # Handle URL navigation (command with URL or navigate)
        if action == 'command' and 'url' in step:
            url = step['url']
            
            if 'wait_until' in step:
                script_content += f'        page.goto("{url}", wait_until="{step["wait_until"]}", timeout=30000)\n'
            else:
                script_content += f'        page.goto("{url}")\n'
        elif action == 'navigate':
            url = step['url']
            
            if 'wait_until' in step:
                script_content += f'        page.goto("{url}", wait_until="{step["wait_until"]}", timeout=30000)\n'
            else:
                script_content += f'        page.goto("{url}")\n'
            
            if 'wait_for' in step:
                script_content += f'        expect(page.locator("{step["wait_for"]}")).to_be_visible(timeout=10000)\n'
                script_content += f'        page.goto("{url}")\n'
            
            if 'wait_for' in step:
                script_content += f'        expect(page.locator("{step["wait_for"]}")).to_be_visible(timeout=10000)\n'
        
        # Handle form filling
        elif action in ['fill', 'fill_form']:
            selector = step['selector']
            value = step['value']
            script_content += f'''        locator = page.locator("{selector}")
        expect(locator).to_be_visible(timeout=10000)
        locator.fill("{value}")\n'''
        
        # Handle element clicking
        elif action == 'click':
            selector = step['selector']
            script_content += f'''        locator = page.locator("{selector}")
        expect(locator).to_be_visible(timeout=10000)
        locator.click()\n'''
            
            if step.get('wait_for_navigation', False):
                script_content += '        page.wait_for_load_state("networkidle")\n'
        
        # Handle keyboard key press
        elif action == 'keyboard_press':
            key = step.get('selector', '') or step.get('key', 'Enter')
            script_content += f'        page.keyboard.press("{key}")\n'
            
        # Handle waiting for navigation (page load)
        elif action == 'wait_for_navigation':
            script_content += '        page.wait_for_load_state("networkidle")\n'
        
        # Handle waiting for a selector to appear
        elif action == 'wait_for_selector':
            selector = step['selector']
            timeout = step.get('timeout', 10000)
            script_content += f'        expect(page.locator("{selector}")).to_be_visible(timeout={timeout})\n'
            
        # Handle content extraction
        elif action == 'extract_content':
            selectors = step.get('selectors', ["h1", "h2", "h3", "p"])
            script_content += '''        content = {}
'''
            for selector in selectors:
                script_content += f'''        elements = page.query_selector_all("{selector}")
        texts = []
        for element in elements:
            text = element.text_content()
            if text.strip():
                texts.append(text.strip())
        content["{selector}"] = texts
'''
            script_content += '''        print("Extracted content:", json.dumps(content, indent=2))
'''
    
    script_content += '''    except Exception as e:
        page.screenshot(path="error.png")
        raise e
'''
    return script_content

# Helper function to capture and log subprocess output
async def log_subprocess_output(process):
    """Capture and log subprocess output in real-time"""
    while True:
        line = await process.stdout.readline()
        if not line:
            break
        line_str = line.decode('utf-8').strip()
        if line_str:
            logger.info(f"SUBPROCESS: {line_str}")

async def process_execution(command_parts, env=None, cwd=None):
    """
    Execute a subprocess command asynchronously with real-time output capture.
    
    Args:
        command_parts (list): Command to execute as a list of string parts
        env (dict, optional): Environment variables for the subprocess
        cwd (str, optional): Working directory for the subprocess
        
    Returns:
        tuple: (process, output_lines) - The subprocess object and captured output lines
    """
    if env is None:
        env = os.environ.copy()
    
    logger.info(f"Executing command: {' '.join(command_parts)}")
    
    process = await asyncio.create_subprocess_exec(
        *command_parts,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=cwd
    )
    
    output_lines = []

    async def read_stream(stream, is_error=False):
        while True:
            line = await stream.readline()
            if not line:
                break
            line_str = line.decode('utf-8').rstrip()
            if line_str:
                if is_error:
                    logger.error(f"SUBPROCESS ERROR: {line_str}")
                else:
                    logger.info(f"SUBPROCESS: {line_str}")
                    output_lines.append(line_str)

    stdout_task = asyncio.create_task(read_stream(process.stdout))
    stderr_task = asyncio.create_task(read_stream(process.stderr, is_error=True))
    await asyncio.gather(stdout_task, stderr_task)
    
    return process, output_lines

async def run_script(
    script_info: Dict[str, Any], 
    params: Dict[str, str], 
    headless: bool = False, 
    save_recording_path: Optional[str] = None
) -> Tuple[str, Optional[str]]:
    """
    Run a browser automation script
    
    Args:
        script_info: Dictionary containing the script information
        params: Dictionary of parameters for the script
        headless: Boolean indicating if browser should run in headless mode
        save_recording_path: Path to save browser recordings
        
    Returns:
        tuple: (execution message, script path)
    """
    try:
        if 'type' in script_info:
            script_type = script_info['type']
            
            if script_type == 'browser-control':
                # Ensure directories exist
                script_dir = os.path.join('tmp', 'myscript')
                os.makedirs(script_dir, exist_ok=True)
                
                # Log the parameters being used
                logger.info(f"Generating browser control script with params: {params}")
                
                # Generate and save the script
                script_content = generate_browser_script(script_info, params)
                script_path = os.path.join(script_dir, 'browser_control.py')
                
                # Create pytest.ini if needed
                pytest_ini_path = os.path.join(script_dir, 'pytest.ini')
                if not os.path.exists(pytest_ini_path):
                    with open(pytest_ini_path, 'w', encoding='utf-8') as f:
                        f.write('''[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
addopts = --verbose --capture=no
markers =
    browser_control: mark tests as browser control automation
''')
                
                # Save the generated script
                with open(script_path, 'w', encoding='utf-8') as f:
                    f.write(script_content)
                    
                logger.info(f"Generated browser control script at {script_path}")
            elif script_type == 'git-script':
                # Handle git-script type
                if 'git' not in script_info or 'script_path' not in script_info:
                    logger.error("Git-script type requires 'git' and 'script_path' fields")
                    raise ValueError("Missing required fields for git-script type")
                
                git_url = script_info['git']
                script_path = script_info['script_path']
                version = script_info.get('version', 'main')
                
                # Create directory for git repository
                repo_dir = os.path.join(tempfile.gettempdir(), 'bykilt_gitscripts', Path(git_url).stem)
                os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
                
                # Clone repository
                repo_dir = await clone_git_repo(git_url, version, repo_dir)
                full_script_path = os.path.join(repo_dir, script_path)
                
                if not os.path.exists(full_script_path):
                    raise FileNotFoundError(f"Script not found at path: {full_script_path}")
                
                # Build command
                command_template = script_info.get('command', '')
                if not command_template:
                    logger.error("No command specified for git-script execution")
                    raise ValueError("Command field is required for git-script type")
                
                # Replace script path placeholder
                command_template = command_template.replace('${script_path}', full_script_path)
                
                # Replace parameter placeholders
                for param_name, param_value in params.items():
                    placeholder = f"${{params.{param_name}}}"
                    if placeholder in command_template:
                        # Quote values with spaces or special characters
                        if ' ' in str(param_value) or any(c in str(param_value) for c in '!@#$%^&*()'):
                            param_value = f'"{param_value}"'
                        command_template = command_template.replace(placeholder, str(param_value))
                
                # Parse command into parts for subprocess
                command_parts = command_template.split()
                
                # Add slowmo parameter if specified
                slowmo = script_info.get('slowmo')
                if slowmo is not None:
                    try:
                        slowmo_ms = int(slowmo)
                        if '--slowmo' not in command_template:
                            command_parts.extend(['--slowmo', str(slowmo_ms)])
                        logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
                    except ValueError:
                        logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")
                
                # Add headless mode parameter
                if not headless and '--headed' not in command_template:
                    command_parts.append('--headed')
                
                # Set up environment variables
                env = os.environ.copy()
                if save_recording_path:
                    os.makedirs(save_recording_path, exist_ok=True)
                    env['RECORDING_PATH'] = save_recording_path
                    logger.info(f"Recording enabled, saving to: {save_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env,
                    cwd=os.path.dirname(full_script_path)
                )
                
                # Get any remaining stdout/stderr
                stdout, stderr = await process.communicate()
                
                # Log any remaining output
                if stdout:
                    for line in stdout.decode('utf-8').splitlines():
                        if line.strip() and line.strip() not in output_lines:
                            logger.info(f"SCRIPT: {line.strip()}")
                            output_lines.append(line.strip())
                
                if stderr:
                    for line in stderr.decode('utf-8').splitlines():
                        if line.strip():
                            logger.error(f"SCRIPT ERROR: {line.strip()}")
                
                # Check return code and return results
                if process.returncode != 0:
                    error_msg = f"Script execution failed with exit code {process.returncode}"
                    logger.error(error_msg)
                    return error_msg, None
                else:
                    success_msg = "Script executed successfully"
                    logger.info(success_msg)
                    return success_msg, full_script_path
            elif script_type == 'unlock-future':
                # Handle unlock-future type
                logger.info(f"Executing unlock-future script: {script_info.get('name', 'unknown')}")
                
                # Convert the script to JSON format using ActionTranslator
                from src.config.action_translator import ActionTranslator
                translator = ActionTranslator()
                from src.config.llms_parser import load_actions_config  # Updated import

                # Get the complete actions list
                actions_config = load_actions_config()
                if isinstance(actions_config, dict) and 'actions' in actions_config:
                    action_list = actions_config['actions']
                else:
                    action_list = actions_config  # Fallback if it's already a list

                # Pass the complete list to the translator
                json_path = translator.translate_to_json(
                    script_info.get('name', ''), 
                    params, 
                    action_list,
                    tab_selection_strategy=script_info.get('tab_selection_strategy', 'new_tab')  # Pass tab selection strategy
                )
                
                # Execute the JSON commands using DebugUtils
                from src.utils.debug_utils import DebugUtils
                debug_utils = DebugUtils()
                result = await debug_utils.test_llm_response(json_path, use_own_browser=True, headless=headless)
                
                return f"Unlock-future script executed successfully: {result}", json_path
            elif script_type == 'script':
                # Handle direct script execution type
                logger.info(f"Executing direct script: {script_info.get('name', 'unknown')}")
                
                # Get script path and command
                script_name = script_info.get('script')
                if not script_name:
                    error_msg = "Script type requires 'script' field"
                    logger.error(error_msg)
                    return error_msg, None
                
                # Ensure script directory exists
                script_dir = os.path.join('tmp', 'myscript')
                os.makedirs(script_dir, exist_ok=True)
                
                # Construct script path
                script_path = os.path.join(script_dir, script_name)
                
                # Check if script exists
                if not os.path.exists(script_path):
                    error_msg = f"Script not found: {script_path}"
                    logger.error(error_msg)
                    return error_msg, None
                
                # Get command template
                command_template = script_info.get('command', f'pytest {script_path}')
                command_parts = []
                
                # Parse the command template
                if isinstance(command_template, str):
                    # Replace script path placeholder if present
                    command_template = command_template.replace('${script_path}', script_path)
                    
                    # Replace parameter placeholders (${params.name} format)
                    for param_name, param_value in params.items():
                        placeholder = f"${{params.{param_name}}}"
                        if placeholder in command_template:
                            # Quote values with spaces or special characters
                            if ' ' in str(param_value) or any(c in str(param_value) for c in '!@#$%^&*()'):
                                param_value = f'"{param_value}"'
                            command_template = command_template.replace(placeholder, str(param_value))
                    
                    # Split into parts for subprocess execution
                    command_parts = command_template.split()
                
                # Add slowmo parameter if specified
                slowmo = script_info.get('slowmo')
                if slowmo is not None:
                    try:
                        slowmo_ms = int(slowmo)
                        if '--slowmo' not in command_template:
                            command_parts.extend(['--slowmo', str(slowmo_ms)])
                        logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
                    except ValueError:
                        logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")
                
                # Add headless mode parameter
                if not headless and '--headed' not in command_template:
                    command_parts.append('--headed')
                
                # Add recording configuration if enabled
                env = os.environ.copy()
                if save_recording_path:
                    os.makedirs(save_recording_path, exist_ok=True)
                    env['RECORDING_PATH'] = save_recording_path
                    logger.info(f"Recording enabled, saving to: {save_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env
                )
                
                # Get any remaining stdout/stderr
                stdout, stderr = await process.communicate()
                
                # Log any remaining output
                if stdout:
                    for line in stdout.decode('utf-8').splitlines():
                        if line.strip() and line.strip() not in output_lines:
                            logger.info(f"SCRIPT: {line.strip()}")
                            output_lines.append(line.strip())
                
                if stderr:
                    for line in stderr.decode('utf-8').splitlines():
                        if line.strip():
                            logger.error(f"SCRIPT ERROR: {line.strip()}")
                
                # Check return code and return results
                if process.returncode != 0:
                    error_msg = f"Script execution failed with exit code {process.returncode}"
                    logger.error(error_msg)
                    return error_msg, None
                else:
                    success_msg = "Script executed successfully"
                    logger.info(success_msg)
                    return success_msg, script_path
            elif script_type == 'action_runner_template':
                # Handle action runner template type
                logger.info(f"Executing action runner template: {script_info.get('name', 'unknown')}")
                
                # Get action script name
                action_script = script_info.get('action_script')
                if not action_script:
                    error_msg = "Action runner template requires 'action_script' field"
                    logger.error(error_msg)
                    return error_msg, None
                
                # Get command template
                command_template = script_info.get('command', '')
                if not command_template:
                    error_msg = "Command field is required for action_runner_template type"
                    logger.error(error_msg)
                    return error_msg, None
                
                # Replace action_script placeholder
                command_template = command_template.replace('${action_script}', action_script)
                
                # Replace parameter placeholders (${params.name} format)
                for param_name, param_value in params.items():
                    placeholder = f"${{params.{param_name}}}"
                    if placeholder in command_template:
                        # Quote values with spaces or special characters
                        if ' ' in str(param_value) or any(c in str(param_value) for c in '!@#$%^&*()'):
                            param_value = f'"{param_value}"'
                        command_template = command_template.replace(placeholder, str(param_value))
                
                # Split into parts for subprocess execution
                command_parts = command_template.split()
                
                # Add slowmo parameter if specified and not already in command
                slowmo = script_info.get('slowmo')
                if slowmo is not None and '--slowmo' not in command_template:
                    try:
                        slowmo_ms = int(slowmo)
                        command_parts.extend(['--slowmo', str(slowmo_ms)])
                        logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
                    except ValueError:
                        logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")
                
                # Set up environment variables
                env = os.environ.copy()
                if save_recording_path:
                    os.makedirs(save_recording_path, exist_ok=True)
                    env['RECORDING_PATH'] = save_recording_path
                    logger.info(f"Recording enabled, saving to: {save_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env
                )
                
                # Get any remaining stdout/stderr
                stdout, stderr = await process.communicate()
                
                # Log any remaining output
                if stdout:
                    for line in stdout.decode('utf-8').splitlines():
                        if line.strip() and line.strip() not in output_lines:
                            logger.info(f"SCRIPT: {line.strip()}")
                            output_lines.append(line.strip())
                
                if stderr:
                    for line in stderr.decode('utf-8').splitlines():
                        if line.strip():
                            logger.error(f"SCRIPT ERROR: {line.strip()}")
                
                # Check return code and return results
                if process.returncode != 0:
                    error_msg = f"Action runner execution failed with exit code {process.returncode}"
                    logger.error(error_msg)
                    return error_msg, None
                else:
                    success_msg = "Action runner executed successfully"
                    logger.info(success_msg)
                    return success_msg, None
            else:
                logger.error(f"Unsupported script type: {script_type}")
                raise ValueError(f"Unsupported script type: {script_type}")
        else:
            error_msg = "Invalid script_info: missing 'type' field"
            logger.error(error_msg)
            return error_msg, None

        # Check if script file exists
        if not os.path.exists(script_path):
            error_msg = f"Script not found: {script_path}"
            logger.error(error_msg)
            return error_msg, None
        
        # Build pytest command with appropriate parameters
        command = ['pytest', script_path]
        if not headless:
            command.append('--headed')
        
        # Add all parameters that exist in params dictionary
        for param_name, param_value in params.items():
            command.extend([f'--{param_name}', str(param_value)])
        
        # Add slowmo parameter if specified
        slowmo = script_info.get('slowmo')
        if slowmo is not None:
            try:
                slowmo_ms = int(slowmo)
                command.extend(['--slowmo', str(slowmo_ms)])
                logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
            except ValueError:
                logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")

        # Add recording configuration if enabled - use environment variable instead of command line arg
        env = os.environ.copy()
        if save_recording_path:
            os.makedirs(save_recording_path, exist_ok=True)
            env['RECORDING_PATH'] = save_recording_path
            logger.info(f"Recording enabled, saving to: {save_recording_path}")
        
        # Log command before execution
        logger.info(f"Executing command: {' '.join(command)}")
        
        # Run the command asynchronously with the environment variable
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        # Track the output to return later
        output_lines = []
        
        # Process stdout in real-time
        while True:
            line = await process.stdout.readline()
            if not line:
                break
            line_str = line.decode('utf-8').strip()
            if line_str:
                logger.info(f"SCRIPT: {line_str}")
                output_lines.append(line_str)
        
        # Get any remaining stdout/stderr
        stdout, stderr = await process.communicate()
        
        # Log any remaining output
        if stdout:
            for line in stdout.decode('utf-8').splitlines():
                if line.strip() and line.strip() not in output_lines:
                    logger.info(f"SCRIPT: {line.strip()}")
                    output_lines.append(line.strip())
        
        if stderr:
            for line in stderr.decode('utf-8').splitlines():
                if line.strip():
                    logger.error(f"SCRIPT ERROR: {line.strip()}")
        
        # Check return code and return results
        if process.returncode != 0:
            error_msg = f"Script execution failed with exit code {process.returncode}"
            logger.error(error_msg)
            return error_msg, None
        else:
            success_msg = "Script executed successfully"
            logger.info(success_msg)
            return success_msg, script_path
    
    except Exception as e:
        import traceback
        error_msg = f"Error running script: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, None
