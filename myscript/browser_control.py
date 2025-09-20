
import pytest
from playwright.sync_api import expect, Page, Browser
import json
import os

# NOTE:
# pytest-playwright defines core fixtures like `browser` with session scope. If we
# provide custom overriding fixtures (browser_context_args, browser_type_launch_args)
# with a narrower (module/function) scope, pytest raises ScopeMismatch when the
# session-scoped fixture chain attempts to access them. Therefore these MUST be
# session-scoped. See Issue #220 / PR #235.

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
def test_browser_control(page: Page):
    try:
        # Basic browser control test - verify page is accessible
        assert page is not None
        print("✅ Browser control test passed - page is accessible")
        
        # Test basic page operations
        title = page.title()
        print(f"📄 Page title: {title}")
        
        # Process automation flow if defined
        flow = [{'action': 'navigate', 'url': 'https://example.com'}]
        if flow:
            print(f"🔄 Processing {len(flow)} automation steps...")
            for step in flow:
                action = step.get('action')
                print(f"🔄 Executing action: {action}")
                
                # Handle URL navigation
                if action == 'navigate':
                    url = step['url']
                    print(f"🌐 Navigating to: {url}")
                    if 'wait_until' in step:
                        page.goto(url, wait_until=step["wait_until"], timeout=30000)
                    else:
                        page.goto(url)
                    
                    if step.get('wait_for'):
                        escaped_selector = step['wait_for'].replace('"', '\"').replace("'", "\'")
                        expect(page.locator(escaped_selector)).to_be_visible(timeout=10000)
                
                # Handle waiting for selector
                elif action == 'wait_for_selector':
                    selector = step['selector']
                    escaped_selector = selector.replace('"', '\"').replace("'", "\'")
                    timeout = step.get('timeout', 10000)
                    print(f"⏳ Waiting for selector: {selector}")
                    expect(page.locator(escaped_selector)).to_be_visible(timeout=timeout)
                
                # Handle element clicking
                elif action == 'click':
                    selector = step['selector']
                    escaped_selector = selector.replace('"', '\"').replace("'", "\'")
                    print(f"👆 Clicking selector: {selector}")
                    locator = page.locator(escaped_selector)
                    expect(locator).to_be_visible(timeout=10000)
                    locator.click()
                    
                    if step.get('wait_for_navigation', False):
                        page.wait_for_load_state("networkidle")
                
                # Handle waiting for navigation
                elif action == 'wait_for_navigation':
                    print("⏳ Waiting for navigation...")
                    page.wait_for_load_state("networkidle")
                
                # Handle form filling
                elif action in ['fill', 'fill_form']:
                    selector = step['selector']
                    value = step['value']
                    escaped_selector = selector.replace('"', '\"').replace("'", "\'")
                    escaped_value = value.replace('"', '\"').replace("'", "\'")
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
                    for selector in selectors:
                        escaped_selector = selector.replace('"', '\"').replace("'", "\'")
                        elements = page.query_selector_all(escaped_selector)
                        texts = []
                        for element in elements:
                            text = element.text_content()
                            if text and text.strip():
                                texts.append(text.strip())
                        content[selector] = texts
                    print("Extracted content:", json.dumps(content, indent=2))
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
