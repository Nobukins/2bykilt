"""
Browser Control Execution Module

This module handles the generation and execution of browser control scripts using Playwright.
Extracted from script_manager.py as part of Issue #329 refactoring (Phase 2).
"""

import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Tuple, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.utils.app_logger import logger


def generate_browser_script(script_info: Dict[str, Any], params: Dict[str, str], headless: bool = False) -> str:
    """
    Generate a pytest script from a browser control flow using Jinja2 template
    
    Args:
        script_info: Dictionary containing the script information
        params: Dictionary of parameters to use in the script
        headless: Boolean indicating if browser should run in headless mode (default: False)
        
    Returns:
        str: The generated script content
    """
    flow = script_info.get('flow', [])
    
    # Process flow to replace parameter placeholders
    processed_flow = []
    for step in flow:
        processed_step = {}
        for key, value in step.items():
            if isinstance(value, str):
                # Replace ${params.param_name} placeholders with actual values
                import re
                param_pattern = r'\$\{params\.([^}]+)\}'
                def replace_param(match):
                    param_name = match.group(1)
                    if param_name in params:
                        return params[param_name]
                    else:
                        # Keep placeholder if parameter not found
                        return match.group(0)
                processed_value = re.sub(param_pattern, replace_param, value)
                processed_step[key] = processed_value
            else:
                processed_step[key] = value
        processed_flow.append(processed_step)
    
    # Prepare template variables
    template_vars = {
        'output_file_param': repr(params.get("output_file")),
        'output_mode_param': repr(params.get("output_mode")),
        'flow': str(processed_flow)
    }
    
    # Load template and render
    # Template directory is at project root level (not src/templates)
    project_root = Path(__file__).parent.parent.parent
    template_dir = project_root / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    template = env.get_template('browser_control_template.py.jinja2')
    script_content = template.render(**template_vars)
    
    return script_content


async def execute_browser_control(
    script_info: Dict[str, Any],
    params: Dict[str, str],
    headless: bool = False,
    save_recording_path: Optional[str] = None,
    browser_type: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """
    Execute a browser control script
    
    Args:
        script_info: Dictionary containing the script information
        params: Dictionary of parameters for the script
        headless: Boolean indicating if browser should run in headless mode
        save_recording_path: Path to save browser recordings
        browser_type: Browser type to use (chrome/edge), overrides config if provided
        
    Returns:
        tuple: (execution message, script path)
    """
    # Ensure scripts directory exists in myscript (not artifacts)
    script_dir = 'myscript'
    os.makedirs(script_dir, exist_ok=True)

    # Log the parameters being used
    logger.info(f"Generating browser control script with params: {params}")
    logger.info(f"🔍 Headless mode setting: {headless}")

    # Generate and save the script with headless parameter
    script_content = generate_browser_script(script_info, params, headless)
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

    logger.info(f"Generated browser control script at: {script_path}")
    
    # Build pytest command with appropriate parameters
    # Use pytest to ensure fixtures work properly for recording
    import sys as _sys
    # Use relative path since we're running pytest from within the script_dir
    relative_script_path = os.path.basename(script_path)
    # Use pytest to run the test function with fixtures
    command = [_sys.executable, "-m", "pytest", relative_script_path + "::test_browser_control", "-v", "--tb=short"]
    
    logger.info(f"🔧 Final command: {' '.join(command)}")
    
    # Add slowmo parameter if specified
    slowmo = script_info.get('slowmo')
    if slowmo is not None:
        try:
            slowmo_ms = int(slowmo)
            command.extend(['--slowmo', str(slowmo_ms)])
            logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
        except ValueError:
            logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")
    
    # Set up environment variables including browser configuration
    env = os.environ.copy()
    
    # Set headless mode environment variable for script fixtures
    env['BYKILT_HEADLESS'] = 'true' if headless else 'false'
    logger.info(f"🔍 Setting BYKILT_HEADLESS environment variable to: {env['BYKILT_HEADLESS']}")
    
    # Get browser configuration from BrowserConfig
    try:
        from src.browser.browser_config import browser_config
        
        # Check for browser type override from environment (browser-control)
        override_browser = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE')
        if browser_type:
            current_browser = browser_type
            env['BYKILT_OVERRIDE_BROWSER_TYPE'] = browser_type
            logger.info(f"🎯 Using browser type from parameter: {browser_type}")
        elif override_browser:
            current_browser = override_browser
            logger.info(f"🎯 Using override browser type: {override_browser}")
        else:
            current_browser = browser_config.get_current_browser()
            logger.info(f"🔍 Using current browser from config: {current_browser}")
        
        browser_settings = browser_config.get_browser_settings(current_browser)
        
        # Set browser-specific environment variables for Playwright
        env['BYKILT_BROWSER_TYPE'] = current_browser
        logger.info(f"🎯 Browser type set to: {current_browser}")
        
        # Set browser executable path if available for Chrome/Edge
        browser_path = browser_settings.get("path")
        if current_browser == "chrome" and browser_path and os.path.exists(browser_path):
            env['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = browser_path
            logger.info(f"🎯 Chrome executable path set to: {browser_path}")
            command.extend(['--browser-type', 'chrome'])
            logger.info(f"🔍 Using Chrome browser at {browser_path}")
        elif current_browser == "edge" and browser_path and os.path.exists(browser_path):
            env['PLAYWRIGHT_EDGE_EXECUTABLE_PATH'] = browser_path
            logger.info(f"🎯 Edge executable path set to: {browser_path}")
            command.extend(['--browser-type', 'msedge'])
            logger.info(f"🔍 Using Edge browser at {browser_path}")
        elif current_browser in ["chrome", "edge", "chromium"]:
            if current_browser == "chrome":
                command.extend(['--browser-type', 'chrome'])
            elif current_browser == "edge":
                command.extend(['--browser-type', 'msedge'])
            else:
                command.extend(['--browser-type', 'chromium'])
            logger.info(f"🔍 Using default {current_browser} browser")
        elif current_browser in ["firefox", "webkit"]:
            command.extend(['--browser-type', current_browser])
            logger.info(f"🔍 Using {current_browser} browser")
            
    except Exception as e:
        logger.warning(f"⚠️ Could not load browser configuration: {e}")
        logger.info("Using default Playwright browser settings")
        # フォールバック: 環境変数から直接設定
        if browser_type:
            env['BYKILT_BROWSER_TYPE'] = browser_type
            command.extend(['--browser-type', 'chromium'])
            logger.info(f"🔍 Using chromium browser type for better compatibility")
    
    # Add recording configuration if enabled
    if save_recording_path:
        # Use unified recording directory resolver
        from src.utils.recording_dir_resolver import create_or_get_recording_dir
        unified_recording_path = str(create_or_get_recording_dir(save_recording_path))
        env['RECORDING_PATH'] = unified_recording_path
        logger.info(f"Recording enabled, saving to: {unified_recording_path}")
    
    # Headless mode is configured via env/fixtures in generated script; avoid pytest CLI flags
    if headless:
        logger.info("🔍 Headless mode requested (handled via script fixtures)")
    
    # Execute the pytest command
    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env=env,
        cwd=script_dir
    )
    
    stdout, stderr = await process.communicate()
    
    # Process output
    output_lines = []
    if stdout:
        for line in stdout.decode('utf-8').splitlines():
            if line.strip():
                logger.info(f"PYTEST: {line.strip()}")
                output_lines.append(line.strip())
    
    if stderr:
        for line in stderr.decode('utf-8').splitlines():
            if line.strip():
                logger.error(f"PYTEST ERROR: {line.strip()}")
    
    # Check return code and return results
    if process.returncode != 0:
        error_msg = f"Browser control script execution failed with exit code {process.returncode}"
        logger.error(error_msg)
        return error_msg, script_path
    else:
        success_msg = "Script executed successfully"
        logger.info(success_msg)
        
        # Move generated files from myscript to artifacts directory
        try:
            from src.script.artifact_management import move_script_files_to_artifacts
            await move_script_files_to_artifacts(script_info, script_path, 'browser-control')
            logger.info("✅ Browser control files archived to artifacts directory")
        except Exception as e:
            logger.warning(f"⚠️ Failed to move browser control files to artifacts: {e}")
        
        return success_msg, script_path
