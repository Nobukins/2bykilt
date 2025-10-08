#!/usr/bin/env python3
"""Action runner template for artifact capture flows.

This template supports multiple variants:
  * demo  - reuse myscript/bin/demo_artifact_capture.py to generate artifacts
  * nogtips - run the nogtips search automation with artifact capture enabled

Both variants verify that the expected artifacts (screenshot, element capture,
video) were persisted by reusing helpers from
``tests/integration/test_artifact_capture.py``.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path
from typing import Iterable

# Ensure project root is in sys.path for imports when run as action_runner_template
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from playwright.async_api import async_playwright

from src.runtime.run_context import RunContext
from src.core.artifact_manager import get_artifact_manager
from src.utils.app_logger import logger
from tests.integration.test_artifact_capture import _assert_artifacts_created


def _parse_fields(raw_fields: Iterable[str] | None) -> list[str] | None:
    if not raw_fields:
        return None
    values: list[str] = []
    for field in raw_fields:
        candidate = field.strip()
        if candidate:
            values.append(candidate)
    return values or None


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run artifact capture variants")
    parser.add_argument("--variant", choices=("demo", "nogtips"), default="demo")
    parser.add_argument("--query", help="Query value for nogtips variant")
    parser.add_argument("--prefix", help="Artifact prefix override")
    parser.add_argument(
        "--fields",
        nargs="*",
        help="Fields to capture for element extraction (e.g. text html value)",
    )
    parser.add_argument(
        "--browser",
        choices=("chromium", "firefox", "webkit"),
        default="chromium",
        help="Playwright browser type to launch",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run the browser in headed mode (default: headless)",
    )
    parser.add_argument(
        "--url",
        help="Override URL for demo variant (default: https://www.wikipedia.org)",
    )
    parser.add_argument(
        "--selector",
        help="Override selector for demo variant (default: .central-featured-lang strong)",
    )
    return parser


async def _run_demo_variant(args: argparse.Namespace) -> None:
    from myscript.bin.demo_artifact_capture import run_demo

    RunContext.get()
    artifact_manager = get_artifact_manager()

    fields = _parse_fields(args.fields)
    await run_demo(
        url=args.url or "https://www.wikipedia.org",
        selector=args.selector or ".central-featured-lang strong",
        prefix=args.prefix or "demo_capture",
        browser=args.browser,
        headless=not args.headed,
        fields=fields,
    )

    artifact_base = artifact_manager.dir.parent.parent
    _assert_artifacts_created(artifact_base)


async def _run_nogtips_variant(args: argparse.Namespace) -> None:
    from myscript.actions.nogtips_search import run_actions
    from myscript.bin.demo_artifact_capture import _finalize_video_capture, _register_video_artifact

    RunContext.get()
    artifact_manager = get_artifact_manager()
    recording_dir = artifact_manager.dir / "videos"
    recording_dir.mkdir(parents=True, exist_ok=True)

    fields = _parse_fields(args.fields) or ["text", "html"]
    artifact_prefix = args.prefix or "nogtips_capture"

    async with async_playwright() as playwright:
        browser_factory = getattr(playwright, args.browser)
        browser = await browser_factory.launch(headless=not args.headed)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 720},
            record_video_dir=str(recording_dir),
            record_video_size={"width": 1280, "height": 720},
        )
        page = await context.new_page()

        await run_actions(
            page,
            query=args.query,
            capture_artifacts=True,
            artifact_prefix=artifact_prefix,
            fields=fields,
        )

        video_path = await _finalize_video_capture(page)
        await context.close()
        await browser.close()

    _register_video_artifact(artifact_manager, video_path)
    artifact_base = artifact_manager.dir.parent.parent
    _assert_artifacts_created(artifact_base)


async def _run_variant(args: argparse.Namespace) -> None:
    if args.variant == "demo":
        await _run_demo_variant(args)
    elif args.variant == "nogtips":
        await _run_nogtips_variant(args)
    else:  # pragma: no cover - defensive guard
        raise ValueError(f"Unsupported variant: {args.variant}")


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    logger.info(f"🚀 Starting artifact capture runner: {args.variant}")

    try:
        asyncio.run(_run_variant(args))
    except Exception:  # noqa: BLE001
        logger.exception("Artifact capture runner failed")
        raise
    else:
        logger.info(f"✅ Artifact capture runner completed: {args.variant}")


if __name__ == "__main__":
    main()
