import os
import tempfile
import subprocess
import shutil
import asyncio
import inspect
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List
from src.utils.app_logger import logger
# New 2024+ Browser Automation Integration
from src.utils.git_script_automator import GitScriptAutomator, EdgeAutomator, ChromeAutomator
from typing import Dict as _DictReturn

# Import git operations from new module
from src.script.git_operations import (
    execute_git_script,
    clone_git_repo,
    execute_git_script_new_method,
)

# Initialize directory migration on module import
try:
    from src.runner.migration_tool import migrate_user_scripts
    logger.info("🔄 Checking for user script directory migration...")
    migration_result = migrate_user_scripts()
    if migration_result['success'] and migration_result['migrated_files']:
        logger.info(f"✅ Migration completed: {len(migration_result['migrated_files'])} files migrated")
    elif migration_result['needs_migration']:
        logger.warning("⚠️ Migration needed but failed - check logs for details")
    else:
        logger.info("✅ No migration needed")
except ImportError:
    logger.warning("⚠️ Migration tool not available, skipping directory migration")
except Exception as e:
    logger.error(f"❌ Migration initialization failed: {e}")


def generate_browser_script(script_info: Dict[str, Any], params: Dict[str, str], headless: bool = False) -> str:
    """
    Generate a pytest script from a browser control flow
    
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
    
    flow = processed_flow
    script_content = '''import pytest
from playwright.sync_api import expect, Page, Browser
import json
import os
import sys
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from src.runtime.run_context import RunContext
except Exception:  # pragma: no cover - optional dependency for artifact routing
    RunContext = None  # type: ignore[assignment]

OUTPUT_FILE_PARAM = ''' + repr(params.get("output_file")) + '''
OUTPUT_MODE_PARAM = ''' + repr(params.get("output_mode")) + '''

# NOTE:
# pytest-playwright defines core fixtures like `browser` with session scope. If we
# provide custom overriding fixtures (browser_context_args, browser_type_launch_args)
# with a narrower (module/function) scope, pytest raises ScopeMismatch when the
# session-scoped fixture chain attempts to access them. Therefore these MUST be
# session-scoped. See Issue #220 / PR #235.

def _resolve_output_path():
    candidate = OUTPUT_FILE_PARAM.strip() if isinstance(OUTPUT_FILE_PARAM, str) else ""
    base_dir = None
    if RunContext is not None:
        try:
            base_dir = RunContext.get().artifact_dir("browser_control_get_title", ensure=True)
        except Exception as run_exc:  # noqa: BLE001
            print(f"⚠️ Failed to resolve RunContext artifact directory: {run_exc}")
            base_dir = None
    if base_dir is None:
        base_dir = (PROJECT_ROOT / "artifacts" / "runs" / "browser_control_get_title")
        base_dir.mkdir(parents=True, exist_ok=True)

    if candidate:
        path = Path(candidate)
        if not path.is_absolute():
            path = (base_dir / path).resolve()
        else:
            path = path.resolve()
    else:
        path = (base_dir / "get_title_output.txt").resolve()

    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _determine_output_mode():
    raw = OUTPUT_MODE_PARAM.lower() if isinstance(OUTPUT_MODE_PARAM, str) else str(OUTPUT_MODE_PARAM or "").lower()
    return "w" if raw in {"overwrite", "write", "w"} else "a"


OUTPUT_PATH = _resolve_output_path()
OUTPUT_MODE = _determine_output_mode()


def _append_content_to_file(payload: dict):
    if not OUTPUT_PATH:
        return
    path = Path(OUTPUT_PATH)
    mode = OUTPUT_MODE
    try:
        record = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "content": payload,
        }
        existing_size = path.stat().st_size if path.exists() else 0
        with open(path, mode, encoding="utf-8") as fh:
            if mode == "a" and existing_size > 0:
                fh.write("\\n")
            json.dump(record, fh, ensure_ascii=False, indent=2)
            fh.write("\\n")
        print(f"📝 Saved extracted content to {path} (mode={mode})")
    except Exception as write_exc:  # noqa: BLE001
        print(f"⚠️ Failed to write output file {path}: {write_exc}")


@pytest.fixture(scope="session")
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

@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    """Configure browser launch arguments based on environment variables"""
    launch_args = {**browser_type_launch_args}
    
    # Check browser type from environment (with override support)
    browser_type = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE') or os.environ.get('BYKILT_BROWSER_TYPE', 'chrome')
    print(f"🔍 Browser type: {browser_type}")
    
    # Configure headless mode - explicitly set to False unless BYKILT_HEADLESS=true
    headless_env = os.environ.get('BYKILT_HEADLESS', 'false').lower()
    if headless_env == 'true':
        launch_args["headless"] = True
        print(f"🔍 Headless mode: ENABLED (via environment variable)")
    else:
        launch_args["headless"] = False
        print(f"🔍 Headless mode: DISABLED (UI will be visible)")
    
    # Check for browser executable path from environment
    browser_executable = None
    if browser_type == 'chrome':
        browser_executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
        if browser_executable:
            launch_args["executable_path"] = browser_executable
            launch_args["channel"] = "chrome"
    elif browser_type == 'edge':
        browser_executable = os.environ.get('PLAYWRIGHT_EDGE_EXECUTABLE_PATH')
        if browser_executable:
            launch_args["executable_path"] = browser_executable
        launch_args["channel"] = "msedge"  # Use Microsoft Edge
    
    if browser_executable and os.path.exists(browser_executable):
        print(f"🎯 Using custom browser: {browser_executable}")
    
    print(f"🔍 Browser executable: {browser_executable}")
    
    return launch_args

@pytest.mark.browser_control
def test_browser_control(page: Page):  # noqa: C901
    try:
        # Basic browser control test - verify page is accessible
        assert page is not None
        print("✅ Browser control test passed - page is accessible")
        
        # Test basic page operations
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Process automation flow if defined
        flow = ''' + str(flow) + '''
        if flow:
            print(f"🔄 Processing {len(flow)} automation steps...")
            for step in flow:
                action = step.get('action')
                print(f"🔄 Executing action: {action}")
                
                # Handle URL navigation
                if action in ['navigate', 'command']:
                    url = step['url']
                    print(f"🌐 Navigating to: {url}")
                    if 'wait_until' in step:
                        page.goto(url, wait_until=step["wait_until"], timeout=30000)
                    else:
                        page.goto(url, timeout=30000)
                    
                    # Wait for page to be fully loaded (with fallback for dynamic content)
                    try:
                        page.wait_for_load_state("networkidle", timeout=15000)
                        print(f"✅ Page loaded: {page.url}")
                    except Exception as e:
                        print(f"⚠️ Network idle timeout, continuing with page load: {e}")
                        # Fallback: wait for DOM to be ready
                        page.wait_for_load_state("domcontentloaded", timeout=5000)
                        print(f"✅ Page DOM loaded: {page.url}")
                    
                    if step.get('wait_for'):
                        escaped_selector = step['wait_for'].replace('"', '\\"').replace("'", "\\'")
                        expect(page.locator(escaped_selector)).to_be_visible(timeout=10000)
                
                # Handle waiting for selector
                elif action == 'wait_for_selector':
                    selector = step['selector']
                    escaped_selector = selector.replace('"', '\\"').replace("'", "\\'")
                    timeout = step.get('timeout', 10000)
                    print(f"⏳ Waiting for selector: {selector}")
                    expect(page.locator(escaped_selector)).to_be_visible(timeout=timeout)
                
                # Handle scrolling to bottom
                elif action == 'scroll_to_bottom':
                    print(f"⬇️ Scrolling to bottom of page")
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    print(f"✅ Scrolled to bottom of page")
                
                # Handle element clicking
                elif action == 'click':
                    selector = step['selector']
                    escaped_selector = selector.replace('"', '\\"').replace("'", "\\'")
                    print(f"👆 Clicking selector: {selector}")
                    locator = page.locator(escaped_selector)
                    
                    # Wait for element to be visible with retry logic
                    try:
                        expect(locator).to_be_visible(timeout=5000)
                        locator.click()
                        print(f"✅ Clicked selector: {selector}")
                    except Exception as e:
                        print(f"⚠️ Selector '{selector}' not found or not clickable: {e}")
                        
                        # Try force click if pointer events are intercepted
                        if "intercepts pointer events" in str(e):
                            try:
                                print(f"🔧 Trying force click for selector: {selector}")
                                locator.click(force=True, timeout=5000)
                                print(f"✅ Force clicked selector: {selector}")
                                continue  # Skip alternative selectors if force click succeeds
                            except Exception as force_e:
                                print(f"⚠️ Force click also failed: {force_e}")
                                # Try clicking with JavaScript as last resort
                                try:
                                    print(f"🔧 Trying JavaScript click for selector: {selector}")
                                    page.evaluate(f"document.querySelector('{escaped_selector}').click()")
                                    print(f"✅ JavaScript clicked selector: {selector}")
                                    continue  # Skip alternative selectors if JS click succeeds
                                except Exception as js_e:
                                    print(f"⚠️ JavaScript click also failed: {js_e}")
                                    # Continue to alternative selectors
                        
                        # Try alternative selectors if available
                        alt_selectors = step.get('alt_selectors', [])
                        for alt_selector in alt_selectors:
                            try:
                                alt_escaped = alt_selector.replace('"', '\\"').replace("'", "\\'")
                                alt_locator = page.locator(alt_escaped)
                                expect(alt_locator).to_be_visible(timeout=3000)
                                alt_locator.click()
                                print(f"✅ Clicked alternative selector: {alt_selector}")
                                break
                            except Exception as alt_e:
                                print(f"⚠️ Alternative selector '{alt_selector}' also failed: {alt_e}")
                                continue
                        else:
                            # If no alternative worked, raise the original error
                            raise e
                    
                    if step.get('wait_for_navigation', False):
                        page.wait_for_load_state("networkidle", timeout=30000)
                
                # Handle waiting for navigation
                elif action == 'wait_for_navigation':
                    print("⏳ Waiting for navigation...")
                    page.wait_for_load_state("networkidle")
                
                # Handle form filling
                elif action in ['fill', 'fill_form']:
                    selector = step['selector']
                    value = step['value']
                    escaped_selector = selector.replace('"', '\\"').replace("'", "\\'")
                    escaped_value = value.replace('"', '\\"').replace("'", "\\'")
                    print(f"� Filling form: {selector} = {value}")
                    locator = page.locator(escaped_selector)
                    expect(locator).to_be_visible(timeout=10000)
                    locator.fill(escaped_value)
                
                # Handle keyboard press
                elif action == 'keyboard_press':
                    key = step.get('selector', '') or step.get('key', 'Enter')
                    print(f"⌨️ Pressing key: {key}")
                    page.keyboard.press(key)
                
                # Handle content extraction
                elif action == 'extract_content':
                    selectors = step.get('selectors', ["h1", "h2", "h3", "p"])
                    print(f"📄 Extracting content from selectors: {selectors}")
                    content = {}
                    for selector_config in selectors:
                        if isinstance(selector_config, dict):
                            selector = selector_config.get('selector', '')
                            label = selector_config.get('label') or selector
                            fields = selector_config.get('fields') or ['text']
                            attributes = selector_config.get('attributes') or []
                        else:
                            selector = selector_config
                            label = selector
                            fields = ['text']
                            attributes = []

                        if not selector:
                            print("⚠️ Empty selector encountered in extract_content step, skipping")
                            continue

                        escaped_selector = selector.replace('"', '\\"').replace("'", "\\'")
                        elements = page.query_selector_all(escaped_selector)
                        if not elements:
                            print(f"⚠️ No elements found for selector: {selector}")

                        entry_data = {}
                        normalized_fields = [field.lower() for field in fields]

                        if 'text' in normalized_fields:
                            entry_data['text'] = [
                                (element.text_content() or '').strip()
                                for element in elements
                                if element and (element.text_content() or '').strip()
                            ]

                        if 'html' in normalized_fields:
                            entry_data['html'] = [
                                element.inner_html()
                                for element in elements
                                if element
                            ]

                        if 'value' in normalized_fields:
                            entry_data['value'] = [
                                element.get_attribute('value')
                                for element in elements
                                if element
                            ]

                        attribute_values = {}
                        for attribute_name in attributes:
                            attribute_values[attribute_name] = [
                                element.get_attribute(attribute_name) if element else None
                                for element in elements
                            ]

                        if attribute_values:
                            entry_data['attributes'] = attribute_values

                        if not entry_data:
                            entry_data['text'] = [
                                (element.text_content() or '').strip()
                                for element in elements
                                if element and (element.text_content() or '').strip()
                            ]

                        if len(entry_data) == 1 and 'text' in entry_data:
                            content[label] = entry_data['text']
                        else:
                            content[label] = entry_data

                    print("Extracted content:", json.dumps(content, indent=2))
                    _append_content_to_file(content)
        else:
            print("ℹ️ No automation flow defined, basic test completed")
    except Exception as e:
        try:
            from src.core.screenshot_manager import capture_page_screenshot
            _p,_b = capture_page_screenshot(page, prefix="error")
        except Exception as primary_exc:
            try:
                page.screenshot(path="error.png")  # fallback legacy
            except Exception as legacy_exc:
                print(f"Screenshot capture failed (legacy fallback also failed): {legacy_exc}; primary: {primary_exc}")
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
            
            # Windows対応: エンコーディングの自動検出とフォールバック
            def safe_decode_line(data):
                if not data:
                    return ""
                
                # 複数のエンコーディングを試行
                encodings = ['utf-8', 'cp932', 'shift_jis', 'latin1']
                for encoding in encodings:
                    try:
                        return data.decode(encoding).rstrip()
                    except UnicodeDecodeError:
                        continue
                # すべて失敗した場合はエラーを無視してデコード
                return data.decode('utf-8', errors='replace').rstrip()
            
            line_str = safe_decode_line(line)
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
    save_recording_path: Optional[str] = None,
    browser_type: Optional[str] = None,
    git_script_resolver = None
) -> Tuple[str, Optional[str]]:
    """
    Run a browser automation script
    
    Args:
        script_info: Dictionary containing the script information
        params: Dictionary of parameters for the script
        headless: Boolean indicating if browser should run in headless mode
        save_recording_path: Path to save browser recordings
        browser_type: Browser type to use (chrome/edge), overrides config if provided
        git_script_resolver: Optional injected resolver for testing (defaults to singleton)
        
    Returns:
        tuple: (execution message, script path)
    """
    try:
        # Set browser type in environment if provided
        if browser_type:
            os.environ['BYKILT_OVERRIDE_BROWSER_TYPE'] = browser_type
            logger.info(f"🔍 Override browser type set to: {browser_type}")
        
        if 'type' in script_info:
            script_type = script_info['type']
            
            if script_type == 'browser-control':
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
                        await move_script_files_to_artifacts(script_info, script_path, 'browser-control')
                        logger.info("✅ Browser control files archived to artifacts directory")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to move browser control files to artifacts: {e}")
                    
                    return success_msg, script_path
            elif script_type == 'git-script':
                # Handle git-script type with NEW 2024+ METHOD
                logger.info(f"🔍 Processing git-script: {script_info.get('name', 'unknown')}")
                
                # NEW: Use git_script_resolver to resolve script information
                # Use injected resolver or get singleton instance
                if git_script_resolver is None:
                    from src.script.git_script_resolver import get_git_script_resolver
                    from src.runtime.run_context import RunContext
                    run_context = RunContext.get()
                    resolver = get_git_script_resolver(run_id=run_context.run_id_base)
                else:
                    resolver = git_script_resolver
                
                # If not provided, try to resolve from script name
                if not script_info.get('git') or not script_info.get('script_path'):
                    script_name = script_info.get('name') or script_info.get('script')
                    if script_name:
                        logger.info(f"🔍 Resolving git-script from name: {script_name}")
                        resolved_info = await resolver.resolve_git_script(script_name, params)
                        if resolved_info:
                            script_info.update(resolved_info)
                            logger.info(f"✅ Resolved git-script: {script_info.get('git')} -> {script_info.get('script_path')}")
                        else:
                            logger.error(f"❌ Could not resolve git-script: {script_name}")
                            raise ValueError(f"Could not resolve git-script: {script_name}")
                
                # Validate resolved script info
                is_valid, error_msg = await resolver.validate_script_info(script_info)
                if not is_valid:
                    logger.error(f"❌ Invalid git-script configuration: {error_msg}")
                    raise ValueError(f"Invalid git-script configuration: {error_msg}")
                
                git_url = script_info['git']
                script_path = script_info['script_path']
                version = script_info.get('version', 'main')
                
                # Check if user wants to use the NEW METHOD (2024+ stable automation)
                use_new_method = os.environ.get('BYKILT_USE_NEW_METHOD', 'true').lower() == 'true'
                
                if use_new_method:
                    logger.info("🚀 Using NEW METHOD (2024+) for git-script automation")
                    return await execute_git_script_new_method(
                        script_info, params, headless, save_recording_path, browser_type
                    )
                else:
                    logger.info("⚠️ Using LEGACY METHOD for git-script automation")
                    # Legacy method continues below...
                
                # Create directory for git repository
                repo_dir = os.path.join(tempfile.gettempdir(), 'bykilt_gitscripts', Path(git_url).stem)
                os.makedirs(os.path.dirname(repo_dir), exist_ok=True)
                
                # Clone repository
                repo_dir = await clone_git_repo(git_url, version, repo_dir)
                full_script_path = os.path.join(repo_dir, script_path)
                
                # Apply Chrome executable path patch to the script
                await patch_search_script_for_chrome(full_script_path)
                
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
                        command_template = command_template.replace(placeholder, str(param_value))
                
                # Parse command into parts for subprocess using shlex for safe parsing
                import shlex
                try:
                    command_parts = shlex.split(command_template)
                except ValueError as e:
                    logger.error(f"Failed to parse command template: {e}")
                    # Fallback to simple split
                    command_parts = command_template.split()
                
                # Replace 'python' with current Python executable to ensure virtual environment compatibility
                if command_parts and command_parts[0] == 'python':
                    import sys
                    command_parts[0] = sys.executable
                
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
                
                # Set up environment variables including browser configuration
                env = os.environ.copy()
                
                # Memory monitoring and browser optimization for git-script
                try:
                    from src.utils.memory_monitor import memory_monitor
                    
                    # Log current memory status
                    memory_monitor.log_memory_status()
                    
                    # Get browser configuration from BrowserConfig
                    from src.browser.browser_config import browser_config
                    
                    # Check for browser type override from environment (git-script)
                    override_browser = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE')
                    if override_browser:
                        requested_browser = override_browser
                        logger.info(f"🎯 Using override browser type: {override_browser}")
                    else:
                        requested_browser = browser_config.get_current_browser()
                        logger.info(f"🔍 Using current browser from config: {requested_browser}")
                    
                    # Memory safety check and fallback recommendation
                    is_safe, safety_msg = memory_monitor.is_safe_for_browser(requested_browser)
                    if not is_safe:
                        logger.warning(f"⚠️ Memory safety check failed: {safety_msg}")
                        fallback_browser = memory_monitor.suggest_fallback_browser(requested_browser)
                        
                        if fallback_browser != requested_browser:
                            logger.info(f"🔄 Fallback browser recommended: {requested_browser} → {fallback_browser}")
                            
                            # Apply fallback
                            if fallback_browser == 'headless':
                                logger.info("🔄 Switching to headless mode for memory optimization")
                                if '--headed' in command_parts:
                                    command_parts.remove('--headed')
                                command_parts.append('--headless')
                                current_browser = requested_browser  # Keep original browser type but run headless
                            else:
                                current_browser = fallback_browser
                                # Update browser config temporarily
                                env['BYKILT_OVERRIDE_BROWSER_TYPE'] = fallback_browser
                        else:
                            current_browser = requested_browser
                            logger.warning(f"⚠️ Continuing with {requested_browser} despite memory concerns")
                            
                            # Edge使用時の追加安全策: メモリ不足でも使用する場合は最大限の最適化
                            if requested_browser.lower() in ['edge', 'msedge']:
                                logger.warning("🚨 Forcing Edge usage despite memory concerns - applying maximum optimization")
                                if '--headed' in command_parts:
                                    command_parts.remove('--headed')
                                command_parts.append('--headless')  # 強制的にheadlessモード
                                logger.info("🔧 Forced headless mode for Edge memory optimization")
                    else:
                        current_browser = requested_browser
                        logger.info(f"✅ Memory safety check passed: {safety_msg}")
                    
                    # Get memory-optimized browser arguments
                    optimized_args = memory_monitor.get_optimized_browser_args(current_browser)
                    if optimized_args:
                        # Add optimized arguments to environment for the subprocess using pipe delimiter
                        env['BYKILT_BROWSER_ARGS'] = '|'.join(optimized_args)
                        logger.info(f"🔧 Applied {len(optimized_args)} memory optimization arguments")
                except ImportError:
                    # Fallback to original behavior if memory monitor is not available
                    logger.warning("⚠️ Memory monitor not available, using default browser configuration")
                    from src.browser.browser_config import browser_config
                    
                    override_browser = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE')
                    if override_browser:
                        current_browser = override_browser
                        logger.info(f"🎯 Using override browser type: {override_browser}")
                    else:
                        current_browser = browser_config.get_current_browser()
                        logger.info(f"🔍 Using current browser from config: {current_browser}")
                
                # Continue with browser configuration
                try:
                    from src.browser.browser_config import browser_config
                    browser_settings = browser_config.get_browser_settings(current_browser)
                    
                    # Set browser-specific environment variables for Playwright
                    env['BYKILT_BROWSER_TYPE'] = current_browser
                    logger.info(f"🎯 Browser type set to: {current_browser}")
                    
                    # Set browser executable path if available
                    browser_path = browser_settings.get("path")
                    if browser_path and os.path.exists(browser_path):
                        # Set appropriate environment variable based on browser type
                        if current_browser == 'chrome':
                            env['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = browser_path
                        elif current_browser == 'edge':
                            env['PLAYWRIGHT_EDGE_EXECUTABLE_PATH'] = browser_path
                        else:
                            env['PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH'] = browser_path  # fallback for chromium
                        logger.info(f"🎯 Browser executable path set to: {browser_path}")
                    else:
                        logger.warning(f"⚠️ Browser path not found or invalid: {browser_path}")
                    
                    logger.info(f"🔍 Git-script will use browser: {current_browser} at {browser_path}")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not load browser configuration: {e}")
                    logger.info("Using default Playwright browser settings")
                
                if save_recording_path:
                    # Use unified recording directory resolver
                    from src.utils.recording_dir_resolver import create_or_get_recording_dir
                    unified_recording_path = str(create_or_get_recording_dir(save_recording_path))
                    env['RECORDING_PATH'] = unified_recording_path
                    logger.info(f"Recording enabled, saving to: {unified_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env,
                    cwd=os.path.dirname(full_script_path)
                )
                
                # Get any remaining stdout/stderr (support mocks returning plain tuples)
                communicate_result = process.communicate()
                if inspect.isawaitable(communicate_result):
                    stdout, stderr = await communicate_result
                else:
                    stdout, stderr = communicate_result
                
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
                    
                    # Move generated files from myscript to artifacts directory
                    try:
                        await move_script_files_to_artifacts(script_info, full_script_path, 'git-script')
                        logger.info("✅ Git-script files moved to artifacts directory")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to move git-script files to artifacts: {e}")
                    
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
                
                # Move generated files from myscript to artifacts directory
                try:
                    await move_script_files_to_artifacts(script_info, json_path, 'unlock-future')
                    logger.info("✅ Unlock-future files moved to artifacts directory")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to move unlock-future files to artifacts: {e}")
                
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

                # Look for script in myscript directory (original location)
                script_dir = 'myscript'
                script_path = os.path.join(script_dir, script_name)

                # Check if script exists in myscript directory
                if not os.path.exists(script_path):
                    error_msg = f"Script not found: {script_path}"
                    logger.error(error_msg)
                    return error_msg, None

                logger.info(f"Found script at: {script_path}")
                
                # Get command template
                command_template = script_info.get('command', f'python -m pytest {script_path}')
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
                    # Ensure we use the current Python interpreter
                    if command_parts and command_parts[0] in ('python', 'python3'):
                        import sys as _sys
                        command_parts[0] = _sys.executable
                
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
                    # Use unified recording directory resolver
                    from src.utils.recording_dir_resolver import create_or_get_recording_dir
                    unified_recording_path = str(create_or_get_recording_dir(save_recording_path))
                    env['RECORDING_PATH'] = unified_recording_path
                    logger.info(f"Recording enabled, saving to: {unified_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env
                )
                
                # Get any remaining stdout/stderr
                communicate_result = process.communicate()
                if inspect.isawaitable(communicate_result):
                    stdout, stderr = await communicate_result
                else:
                    stdout, stderr = communicate_result
                
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
                    
                    # Move generated files from myscript to artifacts directory
                    try:
                        await move_script_files_to_artifacts(script_info, script_path, 'script')
                        logger.info("✅ Script files moved to artifacts directory")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to move script files to artifacts: {e}")
                    
                    return success_msg, script_path
            elif script_type == 'action_runner_template':
                # Handle action runner template type
                logger.info(f"Executing action runner template: {script_info.get('name', 'unknown')}")
                
                # Get action script name
                action_script = script_info.get('action_script') or script_info.get('template')
                if not action_script:
                    error_msg = "Action runner template requires 'action_script' or 'template' field"
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
                command_template = command_template.replace('${template}', action_script)
                
                # Replace parameter placeholders (${params.name|default} or ${params.name} format)
                import re
                
                # Pattern to match ${params.name|default} or ${params.name}
                param_pattern = r'\$\{params\.([^}|]+)(?:\|([^}]*))?\}'
                
                def replace_param(match):
                    param_name = match.group(1)
                    default_value = match.group(2) if match.group(2) is not None else ""
                    
                    # Use parameter value if provided, otherwise use default
                    if param_name in params and params[param_name]:
                        param_value = str(params[param_name])
                    else:
                        param_value = default_value
                    
                    # Return parameter value without additional quoting since we split the command later
                    return param_value
                
                command_template = re.sub(param_pattern, replace_param, command_template)
                
                # Split into parts for subprocess execution
                import shlex

                command_parts = shlex.split(command_template, posix=True)
                # Use current Python interpreter for portability
                if command_parts and command_parts[0] in ('python', 'python3'):
                    import sys as _sys
                    command_parts[0] = _sys.executable
                
                # Replace 'python' with current Python executable to ensure virtual environment compatibility
                if command_parts and command_parts[0] == 'python':
                    import sys
                    command_parts[0] = sys.executable
                
                # Add slowmo parameter if specified and not already in command
                slowmo = script_info.get('slowmo')
                if slowmo is not None and '--slowmo' not in command_template:
                    try:
                        slowmo_ms = int(slowmo)
                        command_parts.extend(['--slowmo', str(slowmo_ms)])
                        logger.info(f"Slow motion enabled with {slowmo_ms}ms delay")
                    except ValueError:
                        logger.warning(f"Invalid slowmo value: {slowmo}, ignoring")
                
                # Set up environment variables including browser configuration
                env = os.environ.copy()
                
                # Get browser configuration from BrowserConfig
                try:
                    from src.browser.browser_config import browser_config
                    
                    # Check for browser type override from environment (action_runner_template)
                    override_browser = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE')
                    if override_browser:
                        current_browser = override_browser
                        logger.info(f"🎯 Using override browser type: {override_browser}")
                    else:
                        current_browser = browser_config.get_current_browser()
                        logger.info(f"🔍 Using current browser from config: {current_browser}")
                    
                    browser_settings = browser_config.get_browser_settings(current_browser)
                    
                    # Set browser-specific environment variables for Playwright
                    # Note: Avoid setting PLAYWRIGHT_BROWSERS_PATH or PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
                    # for better compatibility with Playwright's automatic browser discovery
                    
                    # Add browser type for reference only
                    env['BYKILT_BROWSER_TYPE'] = current_browser
                    logger.info(f"🎯 Browser type set to: {current_browser}")
                    logger.info(f"🔍 Using default Playwright browser discovery for action_runner")
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not load browser configuration: {e}")
                    logger.info("Using default Playwright browser settings")
                
                if save_recording_path:
                    # Use unified recording directory resolver
                    from src.utils.recording_dir_resolver import create_or_get_recording_dir
                    unified_recording_path = str(create_or_get_recording_dir(save_recording_path))
                    env['RECORDING_PATH'] = unified_recording_path
                    logger.info(f"Recording enabled, saving to: {unified_recording_path}")
                
                # Execute the command using process_execution
                process, output_lines = await process_execution(
                    command_parts,
                    env=env
                )
                
                # Get any remaining stdout/stderr
                communicate_result = process.communicate()
                if inspect.isawaitable(communicate_result):
                    stdout, stderr = await communicate_result
                else:
                    stdout, stderr = communicate_result
                
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
                    
                    # Move generated files from myscript to artifacts directory
                    try:
                        await move_script_files_to_artifacts(script_info, None, 'action_runner_template')
                        logger.info("✅ Action runner template files moved to artifacts directory")
                    except Exception as e:
                        logger.warning(f"⚠️ Failed to move action runner template files to artifacts: {e}")
                    
                    return success_msg, None
            else:
                logger.error(f"Unsupported script type: {script_type}")
                raise ValueError(f"Unsupported script type: {script_type}")
        else:
            error_msg = "Invalid script_info: missing 'type' field"
            logger.error(error_msg)
            return error_msg, None

    # Note: generic execution path removed (unreachable) to simplify flow
    
    except Exception as e:
        import traceback
        error_msg = f"Error running script: {str(e)}\n{traceback.format_exc()}"
        logger.error(error_msg)
        return error_msg, None
    finally:
        # Clean up browser type override environment variable
        if 'BYKILT_OVERRIDE_BROWSER_TYPE' in os.environ:
            del os.environ['BYKILT_OVERRIDE_BROWSER_TYPE']


async def execute_script(
    script_info: Dict[str, Any],
    params: Dict[str, str],
    headless: bool = False,
    save_recording_path: Optional[str] = None,
    browser_type: Optional[str] = None,
) -> Tuple[str, Optional[str]]:
    """Compatibility wrapper expected by tests; delegates to run_script."""
    return await run_script(
        script_info=script_info,
        params=params,
        headless=headless,
        save_recording_path=save_recording_path,
        browser_type=browser_type,
    )

async def patch_search_script_for_chrome(script_path: str) -> None:
    """
    Patch the search_script.py file to use environment-based browser configuration
    """
    try:
        if not script_path.endswith('search_script.py'):
            return  # Only patch search_script.py
            
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already patched
        if "# BYKILT_PATCHED_COMPLETE" in content:
            logger.info(f"Script {script_path} already fully patched for browser support")
            return
        
        # Complete replacement of browser launch section
        old_browser_launch = """    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, 
            slow_mo=slowmo, 
            args=[
                '--disable-setuid-sandbox',
                '--disable-accelerated-2d-canvas',
                '--no-zygote',
                '--single-process',
                '--window-position=50,50',  # ウィンドウの位置を指定
                '--window-size=1280,720'    # ウィンドウのサイズを指定
            ]
        )  
        # 録画オプションを指定してコンテキストを作成
        context = await browser.new_context(
            record_video_dir=recording_dir,
            record_video_size={"width": 1280, "height": 720}  # 録画解像度
        )
        page = await context.new_page()"""
        
        new_browser_launch = """    # BYKILT_PATCHED_COMPLETE - Environment-based browser configuration with user profile support
    print(f"🔍 BYKILT_BROWSER_TYPE: {os.environ.get('BYKILT_BROWSER_TYPE', 'chromium')}")
    print(f"🔍 PLAYWRIGHT_EDGE_EXECUTABLE_PATH: {os.environ.get('PLAYWRIGHT_EDGE_EXECUTABLE_PATH')}")
    print(f"🔍 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH: {os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')}")
    
    async with async_playwright() as p:
        # Get browser configuration from environment
        browser_type = os.environ.get('BYKILT_BROWSER_TYPE', 'chromium')
        
        # Get user profile configuration
        edge_user_data = os.environ.get('EDGE_USER_DATA')
        chrome_user_data = os.environ.get('CHROME_USER_DATA')
        
        # Base browser arguments (macOS compatible)
        base_args = [
            '--disable-setuid-sandbox',
            '--disable-accelerated-2d-canvas', 
            '--no-zygote',
            '--single-process',
            '--window-position=50,50',
            '--window-size=1280,720'
        ]
        
        # Apply memory-optimized arguments from environment if available
        optimized_args_env = os.environ.get("BYKILT_BROWSER_ARGS")
        if optimized_args_env:
            optimized_args = [arg for arg in optimized_args_env.split('|') if arg.strip()]
            print(f"🔧 Applying {len(optimized_args)} memory optimization arguments")
            # Merge with base args, avoiding duplicates
            for arg in optimized_args:
                if arg not in base_args:
                    base_args.append(arg)
        
        # Browser-specific launch logic with profile support (New Method for 2024+ Chrome/Edge)
        browser = None
        context = None
        
        if browser_type.lower() == 'edge':
            edge_path = os.environ.get('PLAYWRIGHT_EDGE_EXECUTABLE_PATH')
            if edge_user_data and os.path.exists(edge_user_data):
                # NEW METHOD: Create SeleniumProfile inside Edge User Data directory
                selenium_profile_dir = os.path.join(edge_user_data, "SeleniumProfile")
                print(f"🎯 Using Edge with NEW METHOD profile: {selenium_profile_dir}")
                
                # Create SeleniumProfile directory if it doesn't exist
                os.makedirs(selenium_profile_dir, exist_ok=True)
                os.makedirs(os.path.join(selenium_profile_dir, "Default"), exist_ok=True)
                
                # Copy essential profile files for authentication retention
                original_default = os.path.join(edge_user_data, "Default")
                selenium_default = os.path.join(selenium_profile_dir, "Default")
                
                if os.path.exists(original_default):
                    import shutil
                    essential_files = [
                        "Preferences", "Secure Preferences", "Login Data", "Web Data",
                        "Cookies", "Local State", "Bookmarks", "History"
                    ]
                    for file_name in essential_files:
                        src_file = os.path.join(original_default, file_name)
                        dst_file = os.path.join(selenium_default, file_name)
                        if os.path.exists(src_file):
                            try:
                                shutil.copy2(src_file, dst_file)
                                print(f"📋 Copied: {file_name}")
                            except Exception as e:
                                print(f"⚠️ Could not copy {file_name}: {e}")
                
                try:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=selenium_profile_dir,
                        headless=False,
                        slow_mo=slowmo,
                        executable_path=edge_path,
                        args=base_args + [
                            '--profile-directory=Default',
                            '--disable-sync',
                            '--no-first-run',
                            '--disable-background-networking'
                        ],
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720},
                        viewport={"width": 1280, "height": 720}
                    )
                    print(f"✅ Edge launched with user profile successfully (NEW METHOD)")
                except Exception as e:
                    print(f"❌ Failed to launch Edge with profile: {e}")
                    print("🔄 Falling back to Edge without profile")
                    context = None
            
            if context is None:
                # Fallback: launch without profile
                launch_options = {
                    'headless': False,
                    'slow_mo': slowmo,
                    'args': base_args
                }
                if edge_path:
                    launch_options['executable_path'] = edge_path
                    print(f"🎯 Using Microsoft Edge at: {edge_path}")
                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    record_video_dir=recording_dir,
                    record_video_size={"width": 1280, "height": 720}
                )
                print(f"✅ Edge launched without profile")
                
        elif browser_type.lower() == 'chrome':
            chrome_path = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
            if chrome_user_data and os.path.exists(chrome_user_data):
                # NEW METHOD: Create SeleniumProfile inside Chrome User Data directory
                selenium_profile_dir = os.path.join(chrome_user_data, "SeleniumProfile")
                print(f"🎯 Using Chrome with NEW METHOD profile: {selenium_profile_dir}")
                
                # Create SeleniumProfile directory if it doesn't exist
                os.makedirs(selenium_profile_dir, exist_ok=True)
                os.makedirs(os.path.join(selenium_profile_dir, "Default"), exist_ok=True)
                
                # Copy essential profile files for authentication retention
                original_default = os.path.join(chrome_user_data, "Default")
                selenium_default = os.path.join(selenium_profile_dir, "Default")
                
                if os.path.exists(original_default):
                    import shutil
                    essential_files = [
                        "Preferences", "Secure Preferences", "Login Data", "Web Data",
                        "Cookies", "Local State", "Bookmarks", "History"
                    ]
                    for file_name in essential_files:
                        src_file = os.path.join(original_default, file_name)
                        dst_file = os.path.join(selenium_default, file_name)
                        if os.path.exists(src_file):
                            try:
                                shutil.copy2(src_file, dst_file)
                                print(f"📋 Copied: {file_name}")
                            except Exception as e:
                                print(f"⚠️ Could not copy {file_name}: {e}")
                
                try:
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=selenium_profile_dir,
                        headless=False,
                        slow_mo=slowmo,
                        executable_path=chrome_path,
                        args=base_args + [
                            '--profile-directory=Default',
                            '--disable-sync',
                            '--no-first-run',
                            '--disable-background-networking'
                        ],
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720},
                        viewport={"width": 1280, "height": 720}
                    )
                    print(f"✅ Chrome launched with user profile successfully (NEW METHOD)")
                except Exception as e:
                    print(f"❌ Failed to launch Chrome with profile: {e}")
                    print("🔄 Falling back to Chrome without profile")
                    context = None
                    
            if context is None:
                # Fallback: launch without profile
                launch_options = {
                    'headless': False,
                    'slow_mo': slowmo,
                    'args': base_args
                }
                if chrome_path:
                    launch_options['executable_path'] = chrome_path
                    print(f"🎯 Using Google Chrome at: {chrome_path}")
                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    record_video_dir=recording_dir,
                    record_video_size={"width": 1280, "height": 720}
                )
                print(f"✅ Chrome launched without profile")
        else:
            # Default to Chromium
            launch_options = {
                'headless': False,
                'slow_mo': slowmo,
                'args': base_args
            }
            print(f"🔍 Using default Chromium browser")
            browser = await p.chromium.launch(**launch_options)
            context = await browser.new_context(
                record_video_dir=recording_dir,
                record_video_size={"width": 1280, "height": 720}
            )
        
        print(f"🚀 Browser launched successfully with {len(base_args)} arguments")
        
        # Create page from context
        if context.pages:
            # Use existing page if available (from persistent context)
            page = context.pages[0]
            print(f"📄 Using existing page: {page.url}")
        else:
            # Create new page
            page = await context.new_page()
            print(f"📄 Created new page: {page.url}")"""
        
        if old_browser_launch in content:
            content = content.replace(old_browser_launch, new_browser_launch)
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            logger.info(f"✅ Successfully patched {script_path} with complete browser configuration")
        else:
            logger.warning(f"Could not find expected browser launch pattern in {script_path}")
            # Add simple import if missing
            if "import os" not in content:
                content = "import os\n" + content
            content = "# BYKILT_PATCHED_COMPLETE - Enhanced for browser compatibility\n" + content
            
            with open(script_path, 'w', encoding='utf-8') as f:
                f.write(content)
            logger.info(f"✅ Applied basic patch to {script_path}")
            
    except Exception as e:
        logger.error(f"Failed to patch {script_path}: {e}")

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
        import datetime
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

