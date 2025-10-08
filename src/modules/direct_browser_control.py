import asyncio
import logging
from typing import Dict, Any, List, Optional, Tuple
import json
import os
import tempfile
from pathlib import Path
import shutil
from src.utils.debug_utils import DebugUtils
from src.utils.git_script_automator import GitScriptAutomator
from src.utils.profile_manager import ProfileManager
from src.utils.browser_launcher import BrowserLauncher
from src.utils.timeout_manager import get_timeout_manager, TimeoutScope, TimeoutError, CancellationError, TimeoutManager
from src.core.screenshot_manager import async_capture_page_screenshot
from src.core.element_capture import async_capture_element_value
from src.core.artifact_manager import get_artifact_manager
from src.runtime.run_context import RunContext

logger = logging.getLogger(__name__)


async def _finalize_page_video(page) -> Path | None:
    if not page:
        return None
    try:
        await page.close()
    except Exception as close_exc:  # noqa: BLE001
        logger.warning("video.page_close_fail %s", close_exc)
    try:
        video = getattr(page, "video", None)
        if video:
            video_path_str = await video.path()
            if video_path_str:
                return Path(video_path_str)
    except Exception as video_exc:  # noqa: BLE001
        logger.warning("video.capture_fail %s", video_exc)
    return None


def _register_video_artifact(video_path: Path | None, attempted: bool) -> None:
    if not attempted:
        return
    if video_path and video_path.exists():
        try:
            registered = get_artifact_manager().register_video_file(video_path)
            logger.info("🎞️ Video recorded at %s", registered)
            return
        except Exception as reg_exc:  # noqa: BLE001
            logger.warning("video.register_fail %s", reg_exc)
    logger.warning("Video artifact not found; recording may have failed")


def _build_extract_entry(selector: str, label: str | None = None, fields: List[str] | None = None) -> Dict[str, Any]:
    return {
        "selector": selector,
        "label": label or selector,
        "fields": fields,
    }


def _normalize_from_list(selectors: List[Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in selectors:
        if isinstance(item, dict):
            selector_value = item.get("selector") or item.get("css")
            if selector_value:
                normalized.append(_build_extract_entry(selector_value, item.get("label"), item.get("fields")))
        elif item:
            normalized.append(_build_extract_entry(str(item)))
    return normalized


def _normalize_from_dict(selectors: Dict[Any, Any]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for label_key, selector_value in selectors.items():
        if isinstance(selector_value, str):
            normalized.append(_build_extract_entry(selector_value, str(label_key)))
        elif isinstance(selector_value, dict):
            selector = selector_value.get("selector")
            if selector:
                normalized.append(_build_extract_entry(selector, selector_value.get("label") or str(label_key), selector_value.get("fields")))
    return normalized


def _normalize_extract_entries(options: Dict[str, Any]) -> List[Dict[str, Any]]:
    selectors = options.get("selectors")
    normalized: List[Dict[str, Any]]

    if isinstance(selectors, list):
        normalized = _normalize_from_list(selectors)
    elif isinstance(selectors, dict):
        normalized = _normalize_from_dict(selectors)
    elif selectors:
        normalized = [_build_extract_entry(str(selectors))]
    else:
        normalized = []

    if not normalized:
        fallback_selector = options.get("selector") or "h1"
        normalized.append(_build_extract_entry(fallback_selector))

    return normalized


async def _handle_extract_content(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    options = cmd.get("args", [{}])[0] or {}
    normalized = _normalize_extract_entries(options)
    default_label = options.get("label")
    default_fields = options.get("fields")
    label_usage: Dict[str, int] = {}

    for entry in normalized:
        selector = entry.get("selector")
        if not selector:
            continue
        base_label = entry.get("label") or default_label or selector
        count = label_usage.get(base_label, 0)
        label_usage[base_label] = count + 1
        label = base_label if count == 0 else f"{base_label}_{count}"
        fields = entry.get("fields") or default_fields

        elements = await page.query_selector_all(selector)
        texts = [await element.text_content() for element in elements]
        texts = [t.strip() for t in texts if t and t.strip()]
        logger.info(json.dumps({
            "event": "browser_control.extract",
            "selector": selector,
            "label": label,
            "count": len(texts),
            "preview": texts[:3],
        }, ensure_ascii=False))

        try:
            saved = await async_capture_element_value(
                page,
                selector=selector,
                label=label,
                fields=fields,
            )
            if saved:
                logger.info(f"Saved element capture: {saved}")
        except Exception as capture_exc:  # noqa: BLE001
            logger.warning(
                "element_capture.async_dispatch_fail",
                extra={
                    "event": "element_capture.async_dispatch_fail",
                    "selector": selector,
                    "error": repr(capture_exc),
                },
            )
    return True


async def _handle_screenshot(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    options = cmd.get("args", [{}])[0] or {}
    prefix = options.get("prefix") or options.get("label") or action.get("name", "screenshot")
    image_format = options.get("format", "png")
    full_page = options.get("full_page", False)
    target_path = options.get("path")

    capture_path, _ = await async_capture_page_screenshot(
        page,
        prefix=str(prefix),
        image_format=image_format,
        full_page=full_page,
    )

    if capture_path is None:
        logger.warning("Screenshot capture failed in browser-control flow")
        return False

    logger.info(f"Screenshot captured: {capture_path}")
    if target_path:
        try:
            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(capture_path, target)
            logger.info(f"Screenshot copied to {target}")
        except Exception as copy_exc:  # noqa: BLE001
            logger.warning(
                "screenshot.copy_fail",
                extra={
                    "event": "screenshot.copy_fail",
                    "source": str(capture_path),
                    "target": target_path,
                    "error": repr(copy_exc),
                },
            )
    return True


async def _handle_go_to_url(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    args = cmd.get("args", [])
    if not args:
        return True
    url = args[0]
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.goto(url, wait_until="domcontentloaded"),
            TimeoutScope.NETWORK,
        )
        logger.info(f"Navigated to: {url}")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: go_to_url")
        return False


async def _handle_wait_for_navigation(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.wait_for_load_state("networkidle", timeout=15000),
            TimeoutScope.NETWORK,
        )
        logger.info("Navigation completed")
        return True
    except TimeoutError:
        logger.warning("Navigation wait timed out, continuing")
        return True
    except Exception as exc:  # noqa: BLE001
        logger.error("Navigation wait failed: %s", exc)
        return False


async def _handle_input_text(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    args = cmd.get("args", [])
    if len(args) < 2:
        return True
    selector, value = args[0], args[1]
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.wait_for_selector(selector, timeout=10000),
            TimeoutScope.NETWORK,
        )
        await timeout_manager.apply_timeout_to_coro(
            page.fill(selector, value),
            TimeoutScope.OPERATION,
        )
        logger.info(f"Filled form field '{selector}' with '{value}'")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: input_text %s", selector)
        return False


async def _handle_click_element(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    args = cmd.get("args", [])
    if not args:
        return True
    selector = args[0]
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.wait_for_selector(selector, timeout=10000),
            TimeoutScope.NETWORK,
        )
        await timeout_manager.apply_timeout_to_coro(
            page.click(selector),
            TimeoutScope.OPERATION,
        )
        logger.info(f"Clicked element '{selector}'")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: click_element %s", selector)
        return False


async def _handle_keyboard_press(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    args = cmd.get("args", [])
    if not args:
        return True
    key = args[0]
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.keyboard.press(key),
            TimeoutScope.OPERATION,
        )
        logger.info(f"Pressed key '{key}'")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: keyboard_press %s", key)
        return False


async def _handle_wait_for_element(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    args = cmd.get("args", [])
    if not args:
        return True
    selector = args[0]
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.wait_for_selector(selector, timeout=10000),
            TimeoutScope.NETWORK,
        )
        logger.info(f"Waited for element '{selector}'")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: wait_for_element %s", selector)
        return False


async def _handle_scroll_to_bottom(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    try:
        await timeout_manager.apply_timeout_to_coro(
            page.evaluate("window.scrollTo(0, document.body.scrollHeight);"),
            TimeoutScope.OPERATION,
        )
        logger.info("Scrolled to bottom of page")
        return True
    except TimeoutError:
        logger.error("Browser operation timed out: scroll_to_bottom")
        return False


COMMAND_HANDLERS = {
    "go_to_url": _handle_go_to_url,
    "wait_for_navigation": _handle_wait_for_navigation,
    "input_text": _handle_input_text,
    "click_element": _handle_click_element,
    "keyboard_press": _handle_keyboard_press,
    "extract_content": _handle_extract_content,
    "screenshot": _handle_screenshot,
    "scroll_to_bottom": _handle_scroll_to_bottom,
    "wait_for_element": _handle_wait_for_element,
}


def _cancelled(timeout_manager: TimeoutManager, context: str) -> bool:
    if timeout_manager.is_cancelled():
        logger.warning("Browser control cancelled during %s", context)
        return True
    return False


async def _maybe_sleep_with_cancel(timeout_manager: TimeoutManager, slowmo: int) -> bool:
    if slowmo <= 0:
        return False
    if _cancelled(timeout_manager, "pre-slowmo"):
        return True
    await asyncio.sleep(slowmo / 1000.0)
    return _cancelled(timeout_manager, "slowmo delay")


async def _run_command(page, timeout_manager: TimeoutManager, cmd: Dict[str, Any], action: Dict[str, Any]) -> bool:
    cmd_action = cmd.get("action")
    handler = COMMAND_HANDLERS.get(cmd_action)
    if handler is None:
        logger.warning("Unknown browser-control command: %s", cmd_action)
        return True

    logger.info("Executing: %s %s", cmd_action, cmd.get("args", []))

    return await handler(page, timeout_manager, cmd, action)


async def _run_commands(page, commands: List[Dict[str, Any]], timeout_manager: TimeoutManager, slowmo: int, action: Dict[str, Any]) -> bool:
    for cmd in commands:
        if _cancelled(timeout_manager, "command execution"):
            return False

        try:
            should_continue = await _run_command(page, timeout_manager, cmd, action)
        except TimeoutError:
            logger.error("Browser operation timed out: %s", cmd.get("action"))
            return False
        except CancellationError:
            logger.warning("Browser operation cancelled: %s", cmd.get("action"))
            return False
        except Exception as exc:  # noqa: BLE001
            logger.error("Error executing browser command %s: %s", cmd.get("action"), exc)
            raise

        if not should_continue:
            return False

        if await _maybe_sleep_with_cancel(timeout_manager, slowmo):
            return False

    return True

async def convert_flow_to_commands(flow: List[Dict[str, Any]], params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert YAML flow actions to commands format for direct execution"""
    commands = []
    for step in flow:
        action_type = step.get('action')
        processed_step = {}
        for key, value in step.items():
            if isinstance(value, str) and '{' in value:
                for param_name, param_value in params.items():
                    placeholder = f"${{params.{param_name}}}"
                    if placeholder in value:
                        value = value.replace(placeholder, str(param_value))
            processed_step[key] = value

        cmd = {"action": None, "args": []}
        if action_type == "command" and "url" in processed_step:
            cmd["action"] = "go_to_url"
            cmd["args"] = [processed_step["url"]]
        elif action_type == "click":
            cmd["action"] = "click_element"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "fill_form":
            cmd["action"] = "input_text"
            cmd["args"] = [processed_step["selector"], processed_step["value"]]
        elif action_type == "keyboard_press":
            cmd["action"] = "keyboard_press"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "wait_for_navigation":
            cmd["action"] = "wait_for_navigation"
            cmd["args"] = []
        elif action_type == "wait_for":
            cmd["action"] = "wait_for_element"
            cmd["args"] = [processed_step["selector"]]
        elif action_type == "extract_text":
            cmd["action"] = "extract_content"
            cmd["args"] = [{"selectors": [processed_step.get("selector")]}]
        elif action_type == "extract_content":
            cmd["action"] = "extract_content"
            selector_value = processed_step.get("selector")
            selectors = processed_step.get("selectors")
            if selector_value and not selectors:
                selectors = [selector_value]
            payload = {
                "selectors": selectors,
                "label": processed_step.get("label"),
                "fields": processed_step.get("fields"),
            }
            if processed_step.get("save") is not None:
                payload["save"] = processed_step.get("save")
            cmd["args"] = [payload]
        elif action_type == "screenshot":
            cmd["action"] = "screenshot"
            cmd["args"] = [{
                "path": processed_step.get("path"),
                "prefix": processed_step.get("prefix") or processed_step.get("label"),
                "full_page": processed_step.get("full_page", False),
                "format": processed_step.get("format", "png"),
            }]
        elif action_type == "scroll_to_bottom":
            cmd["action"] = "scroll_to_bottom"
            cmd["args"] = []
        commands.append(cmd)
    return commands

def _merge_recording_params(action: Dict[str, Any], params: Dict[str, Any]) -> None:
    """Merge recording-related parameters into params in-place (idempotent).

    Priority order: explicit param overrides action values. Defaults enable recording unless explicitly disabled.
    """
    recording_params = {
        'save_recording_path': params.get('save_recording_path') or action.get('save_recording_path'),
        'enable_recording': params.get('enable_recording', action.get('enable_recording', True)),
        'run_id': action.get('name', 'browser_control'),
        'run_type': 'browser-control'
    }
    params.update(recording_params)


async def _execute_browser_operation_impl(action: Dict[str, Any], params: Dict[str, Any], timeout_manager: TimeoutManager) -> bool:
    """Execute the browser operation implementation"""
    flow = action.get('flow', [])
    slowmo = action.get('slowmo', 1000)

    rc = RunContext.get()
    params['run_id'] = rc.run_id_base
    artifact_manager = get_artifact_manager()
    artifact_manager.dir.mkdir(parents=True, exist_ok=True)
    default_recording_dir = artifact_manager.dir / "videos"
    default_recording_dir.mkdir(parents=True, exist_ok=True)

    explicit_recording_path = params.get('save_recording_path')
    recording_enabled = params.get('enable_recording', True)
    resolved_recording_path: Path | None = None
    if recording_enabled:
        if explicit_recording_path:
            resolved_recording_path = Path(explicit_recording_path).expanduser().resolve()
            resolved_recording_path.mkdir(parents=True, exist_ok=True)
        else:
            resolved_recording_path = default_recording_dir

    # Get browser type from config if not provided
    browser_type = params.get('browser_type')
    if not browser_type:
        from src.browser.browser_config import BrowserConfig
        browser_config = BrowserConfig()
        browser_type = browser_config.get_current_browser()
        logger.info(f"🔍 Using browser type from config: {browser_type}")

    # Convert flow to command format
    commands = await convert_flow_to_commands(flow, params)
    logger.info(f"Converted flow to {len(commands)} commands: {json.dumps(commands)}")

    # Use new method: GitScriptAutomator with NEW_METHOD
    automator = GitScriptAutomator(browser_type)

    # Create a temporary workspace directory for the automator
    with tempfile.TemporaryDirectory() as temp_workspace:
        # Execute the commands using the browser context
        logger.info(f"🔍 Executing browser-control with NEW_METHOD, browser_type={browser_type}")

        # Initialize recording if enabled (correct logical condition)
        recording_context = None
        if recording_enabled and resolved_recording_path:
            from src.utils.recording_factory import RecordingFactory

            run_context = {
                'run_id': rc.run_id_base,
                'run_type': 'browser-control',
                'save_recording_path': str(resolved_recording_path),
                'enable_recording': True,
            }
            recording_context = RecordingFactory.init_recorder(run_context)

        # Use recording context if available
        context_manager_kwargs = {"headless": params.get('headless', False)}
        if resolved_recording_path:
            context_manager_kwargs["record_video_dir"] = str(resolved_recording_path)

        # Execute with or without recording context
        video_path: Path | None = None
        recording_attempted = resolved_recording_path is not None

        if recording_context:
            async with recording_context:
                async with automator.browser_context(temp_workspace, **context_manager_kwargs) as context:
                    success, video_path = await _execute_with_context(context, commands, timeout_manager, slowmo, action)
        else:
            async with automator.browser_context(temp_workspace, **context_manager_kwargs) as context:
                success, video_path = await _execute_with_context(context, commands, timeout_manager, slowmo, action)

        _register_video_artifact(video_path, recording_attempted)
        return success

async def _execute_with_context(context, commands: List[Dict[str, Any]], timeout_manager: TimeoutManager, slowmo: int, action: Dict[str, Any]) -> Tuple[bool, Path | None]:
    page = None
    success = True
    video_artifact_path: Path | None = None

    try:
        page = await context.new_page()
        success = await _run_commands(page, commands, timeout_manager, slowmo, action)

        if success:
            logger.info("Successfully executed direct browser control for action: %s", action.get('name'))
        else:
            logger.warning("Browser-control flow ended early for action: %s", action.get('name'))

    except Exception:
        logger.error("Error in browser context execution", exc_info=True)
        raise
    finally:
        if page:
            try:
                captured_path = await _finalize_page_video(page)
                if captured_path:
                    video_artifact_path = captured_path
            except Exception as finalize_exc:  # noqa: BLE001
                logger.warning("video.finalize_fail %s", finalize_exc)

    return success, video_artifact_path

async def execute_direct_browser_control(action: Dict[str, Any], **params) -> bool:
    """Execute direct browser control with recording support"""
    logger.info(f"🔍 Executing direct browser control for action: {action['name']}")

    # Normalize / merge recording parameters once
    _merge_recording_params(action, params)

    # Create timeout manager
    timeout_manager = get_timeout_manager()

    try:
        # Execute with operation timeout
        result = await timeout_manager.apply_timeout_to_coro(
            _execute_browser_operation_impl(action, params, timeout_manager),
            TimeoutScope.OPERATION
        )

        if result:
            logger.info(f"✅ Successfully executed direct browser control for action: {action['name']}")
        else:
            logger.warning(f"⚠️ Browser control execution failed for action: {action['name']}")

        return result

    except TimeoutError as e:
        logger.error(f"Browser control action timed out: {e}")
        return False
    except CancellationError as e:
        logger.warning(f"Browser control action cancelled: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error executing direct browser control: {e}")
        return False
