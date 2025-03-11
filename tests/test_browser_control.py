import pytest
from playwright.async_api import async_playwright, Page, expect
import asyncio
import logging
from typing import Optional, TypedDict

logger = logging.getLogger(__name__)

def pytest_addoption(parser):
    parser.addoption("--selector", action="store", help="Element selector")
    parser.addoption("--action", action="store", help="Action to perform")
    parser.addoption("--value", action="store", default="", help="Value for action")
    parser.addoption("--slowmo", action="store", type=int, default=0)
    parser.addoption("--url", action="store", default="", help="URL to navigate to")

class ActionResult(TypedDict):
    success: bool
    action: str
    selector: Optional[str]
    value: Optional[str]
    error: Optional[str]

@pytest.mark.asyncio
async def test_browser_control(request) -> None:
    # Get test parameters
    selector = request.config.getoption("--selector")
    action = request.config.getoption("--action")
    value = request.config.getoption("--value")
    slowmo = request.config.getoption("--slowmo")
    url = request.config.getoption("--url")

    if not action:
        pytest.skip("No action specified")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, slow_mo=slowmo)
        context = await browser.new_context()
        page = await context.new_page()

        try:
            # Navigate to URL if provided
            if url:
                await page.goto(url)
                logger.info(f"Navigated to {url}")

            # Execute requested action
            result = await execute_action(page, action, selector, value)
            
            # Wait for any animations or transitions
            await page.wait_for_timeout(1000)
            
            return result

        except Exception as e:
            logger.error(f"Browser action failed: {str(e)}")
            pytest.fail(f"Browser action failed: {str(e)}")

        finally:
            await context.close()
            await browser.close()

async def execute_action(page: Page, action: str, selector: Optional[str], value: Optional[str]) -> ActionResult:
    """Execute browser action and return result"""
    try:
        if action == "click_element":
            await page.click(selector)
            return {"success": True, "action": "click", "selector": selector, "value": None, "error": None}

        elif action == "input_text":
            await page.fill(selector, value)
            return {"success": True, "action": "input", "selector": selector, "value": value, "error": None}

        elif action == "scroll_action":
            await page.evaluate(f"document.querySelector('{selector}').scrollIntoView()")
            return {"success": True, "action": "scroll", "selector": selector, "value": None, "error": None}

        elif action == "go_to_url":
            await page.goto(value)
            return {"success": True, "action": "navigate", "selector": None, "value": value, "error": None}

        elif action == "wait_for_element":
            await page.wait_for_selector(selector)
            return {"success": True, "action": "wait", "selector": selector, "value": None, "error": None}

        elif action == "extract_text":
            text = await page.inner_text(selector)
            return {"success": True, "action": "extract", "selector": selector, "value": text, "error": None}

        elif action == "take_screenshot":
            await page.screenshot(path=value if value else "screenshot.png")
            return {"success": True, "action": "screenshot", "selector": None, "value": value, "error": None}

        else:
            raise ValueError(f"Unsupported action: {action}")

    except Exception as e:
        logger.error(f"Action execution failed: {str(e)}")
        return {
            "success": False,
            "action": action,
            "error": str(e),
            "selector": selector,
            "value": value
        }

async def run_browser_test(action: str, selector: str = None, value: str = None, url: str = None) -> ActionResult:
    """Helper function to run browser tests"""
    args = [
        "pytest",
        __file__,
        f"--action={action}"
    ]
    if selector:
        args.append(f"--selector={selector}")
    if value:
        args.append(f"--value={value}")
    if url:
        args.append(f"--url={url}")
    
    return await pytest.main(args)

if __name__ == "__main__":
    pytest.main([__file__])