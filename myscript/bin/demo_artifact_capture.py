#!/usr/bin/env python3
"""Demo automation script for screenshots and element capture.

This script launches a Playwright browser, runs a simple search flow, captures a
full-page screenshot, and exports highlighted result elements via the
`async_capture_element_value` helper introduced in Issue #34.

It is intentionally hands-off so that `llms.txt` can trigger it as a scripted
automation (`demo-artifact-capture`). Advanced users can run it directly and
provide custom arguments for the target URL, selector, or browser type.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Iterable

from playwright.async_api import async_playwright

# Ensure project modules are importable when executed from repo root or elsewhere
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.runtime.run_context import RunContext  # noqa: E402
from src.core.artifact_manager import get_artifact_manager  # noqa: E402
from src.core.screenshot_manager import async_capture_page_screenshot  # noqa: E402
from src.core.element_capture import async_capture_element_value  # noqa: E402
from src.utils.app_logger import logger  # noqa: E402


def _sanitize_cli_value(value: str | None) -> str | None:
    """Handle unresolved llms.txt placeholders (e.g., "${params.url}")."""
    if value is None:
        return None
    if value.startswith("${") and value.endswith("}"):
        return None
    return value


def _parse_fields(raw: Iterable[str] | None) -> list[str] | None:
    if not raw:
        return None
    values = []
    for item in raw:
        sanitized = _sanitize_cli_value(item)
        if sanitized:
            values.append(sanitized)
    return values or None


async def _finalize_video_capture(page) -> Path | None:
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


def _register_video_artifact(artifact_manager, video_artifact_path: Path | None) -> None:
    if video_artifact_path and video_artifact_path.exists():
        try:
            registered = artifact_manager.register_video_file(video_artifact_path)
            logger.info("🎞️ Video recorded at %s", registered)
            return
        except Exception as video_reg_exc:  # noqa: BLE001
            logger.warning("video.register_fail %s", video_reg_exc)
    logger.warning("Video artifact not found; recording may have failed")


async def run_demo(url: str, selector: str, prefix: str, browser: str, headless: bool, fields: list[str] | None) -> None:
    # Initialize run context to ensure artifact directories are provisioned and consistent.
    RunContext.get()
    artifact_manager = get_artifact_manager()
    recording_dir = artifact_manager.dir / "videos"
    recording_dir.mkdir(parents=True, exist_ok=True)

    logger.info("🚀 Starting demo automation run")
    logger.info("Target URL: %s", url)
    logger.info("Capture selector: %s", selector)

    async with async_playwright() as p:
        browser_launcher = getattr(p, browser)
        launched_browser = await browser_launcher.launch(headless=headless)
        context = await launched_browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(recording_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)

        screenshot_path, _ = await async_capture_page_screenshot(
            page,
            prefix=prefix,
            image_format="png",
            full_page=True,
        )
        if screenshot_path:
            logger.info("📸 Screenshot stored at %s", screenshot_path)
        else:
            logger.warning("Screenshot capture returned no path")

        capture_path = await async_capture_element_value(
            page,
            selector=selector,
            label=f"{prefix}_element",
            fields=fields or ["text", "html"],
        )
        if capture_path:
            logger.info("📝 Element data saved at %s", capture_path)
        else:
            logger.warning("Element capture yielded no output")

        video_artifact_path = await _finalize_video_capture(page)
        await context.close()
        await launched_browser.close()

    _register_video_artifact(artifact_manager, video_artifact_path)
    logger.info("✅ Demo automation completed")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Demo artifact capture automation")
    parser.add_argument(
        "--url",
        default="https://www.wikipedia.org",
        help="Target URL to open (default: https://www.wikipedia.org)",
    )
    parser.add_argument(
        "--selector",
        default=".central-featured-lang strong",
        help="CSS selector to capture (default: Wikipedia language heading)",
    )
    parser.add_argument(
        "--prefix",
        default="demo_capture",
        help="Prefix for screenshot and element artifact names",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Playwright browser type (default: chromium)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode",
    )
    parser.add_argument(
        "--fields",
        nargs="*",
        help="Fields to capture for the selector (e.g., text html value)",
    )
    return parser


async def _async_main(args: argparse.Namespace) -> None:
    def _parse_fields_string(raw: str | None) -> list[str] | None:
        if not raw:
            return None
        candidates = [part.strip() for part in raw.replace(",", " ").split()]
        return _parse_fields([c for c in candidates if c])

    env_url = _sanitize_cli_value(os.environ.get("DEMO_CAPTURE_URL"))
    env_selector = _sanitize_cli_value(os.environ.get("DEMO_CAPTURE_SELECTOR"))
    env_prefix = _sanitize_cli_value(os.environ.get("DEMO_CAPTURE_PREFIX"))
    env_fields = _parse_fields_string(os.environ.get("DEMO_CAPTURE_FIELDS"))

    url = env_url or _sanitize_cli_value(args.url) or "https://www.wikipedia.org"
    selector = env_selector or _sanitize_cli_value(args.selector) or ".central-featured-lang strong"
    prefix = env_prefix or _sanitize_cli_value(args.prefix) or "demo_capture"
    fields = env_fields or _parse_fields(args.fields)

    env_browser = _sanitize_cli_value(os.environ.get("DEMO_CAPTURE_BROWSER"))
    env_headless = _sanitize_cli_value(os.environ.get("DEMO_CAPTURE_HEADLESS"))
    headless = bool(args.headless or (env_headless and env_headless.lower() in {"1", "true", "yes"}))
    browser = env_browser or args.browser

    await run_demo(
        url=url,
        selector=selector,
        prefix=prefix,
        browser=browser,
        headless=headless,
        fields=fields,
    )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(_async_main(args))


if __name__ == "__main__":
    main()
