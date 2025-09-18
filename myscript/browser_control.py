
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
        page.goto("https://nogtips.wordpress.com/", wait_until="domcontentloaded", timeout=30000)
        locator = page.locator("#eu-cookie-law > form > input")
        expect(locator).to_be_visible(timeout=10000)
        locator.click()
        locator = page.locator("#search-2 > form > label > input")
        expect(locator).to_be_visible(timeout=10000)
        locator.click()
        locator = page.locator("#search-2 > form > label > input")
        expect(locator).to_be_visible(timeout=10000)
        locator.fill("${params.query}")
        page.keyboard.press("Enter")
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
