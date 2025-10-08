from __future__ import annotations

import re
from typing import Iterable

from playwright.async_api import Locator, Page, TimeoutError as PlaywrightTimeoutError
from src.runtime.run_context import RunContext
from src.core.artifact_manager import get_artifact_manager
from src.core.screenshot_manager import async_capture_page_screenshot
from src.core.element_capture import async_capture_element_value
from src.utils.app_logger import logger


async def run_actions(page, query=None, *, capture_artifacts: bool = False, artifact_prefix: str = "nogtips_search", fields: Iterable[str] | None = None):
    """
    nogtipsサイトでの検索アクションを実行
    
    Args:
        page: Playwrightのページオブジェクト
        query: 検索クエリ (文字列)
    """
    print(f"🔍 [nogtips_search] アクション開始 - query: {query}")
    
    # nogtips検索処理
    print(f"🌐 [nogtips_search] サイトへアクセス中...")
    await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=30000)
    print(f"✅ [nogtips_search] サイトアクセス完了")

    await _dismiss_cookie_banner(page)
    
    print(f"🔗 [nogtips_search] nogtipsリンククリック中...")
    await page.get_by_role("link", name="nogtips").click()
    
    print(f"📝 [nogtips_search] LLMs.txtリンククリック中...")
    await page.get_by_role("heading", name="LLMs.txtについて").get_by_role("link").click()
    
    print(f"🔎 [nogtips_search] 検索ボックス検出中...")
    search_box = await _locate_visible_search_box(page)
    await search_box.click()
    
    print(f"⌨️ [nogtips_search] 検索クエリ入力中: {query}")
    await search_box.fill(query)
    
    print(f"⏎ [nogtips_search] Enter キー押下中...")
    await search_box.press("Enter")
    
    # 検索結果を表示
    print(f"⏳ [nogtips_search] 検索結果表示待機中（5秒）...")
    await page.wait_for_timeout(5000)
    
    if capture_artifacts:
        await _capture_search_artifacts(
            page,
            query=query,
            artifact_prefix=artifact_prefix,
            fields=tuple(fields) if fields else None,
        )

    print(f"✅ [nogtips_search] アクション完了")


VISIBLE_SEARCH_BOX_SELECTOR = (
    'input[type="search" i]:visible, '
    'input[name*="search" i]:visible, '
    'input[placeholder*="search" i]:visible, '
    'input[placeholder*="検索" i]:visible'
)


async def _dismiss_cookie_banner(page: Page) -> None:
    candidate_labels = [
        "閉じて承認",
        re.compile(r"承認|同意|Accept|Agree", re.IGNORECASE),
    ]

    for label in candidate_labels:
        locator = page.get_by_role("button", name=label)
        try:
            await locator.first.wait_for(state="visible", timeout=3000)
            await locator.first.click(timeout=2000)
            await page.wait_for_timeout(300)
            return
        except PlaywrightTimeoutError:
            continue


async def _locate_visible_search_box(page: Page, *, timeout: float = 5000) -> Locator:
    candidates = [
        page.get_by_role("searchbox", name=re.compile("検索|search", re.IGNORECASE)),
        page.get_by_placeholder(re.compile("検索|search", re.IGNORECASE)),
        page.locator(VISIBLE_SEARCH_BOX_SELECTOR),
    ]

    for base in candidates:
        locator = base.first
        try:
            await locator.wait_for(state="visible", timeout=timeout)
            await locator.scroll_into_view_if_needed()
            return locator
        except PlaywrightTimeoutError:
            continue

    raise PlaywrightTimeoutError("Visible search box not found on nogtips.wordpress.com")


async def _capture_search_artifacts(page, *, query: str | None, artifact_prefix: str, fields: Iterable[str] | None):
    logger.info("🧾 [nogtips_search] アーティファクト収集中...")

    RunContext.get()
    artifact_manager = get_artifact_manager()

    normalized_prefix = artifact_prefix or "nogtips_search"

    await page.wait_for_timeout(1000)
    try:
        await page.wait_for_selector("main", timeout=5000)
    except Exception as wait_exc:  # noqa: BLE001
        logger.warning("[nogtips_search] main セレクター待機中に警告: %s", wait_exc)

    screenshot_path, _ = await async_capture_page_screenshot(
        page,
        prefix=normalized_prefix,
        image_format="png",
        full_page=True,
    )
    if screenshot_path:
        logger.info("📸 [nogtips_search] スクリーンショット保存: %s", screenshot_path)
    else:
        logger.warning("[nogtips_search] スクリーンショットの保存に失敗")

    element_fields = list(fields) if fields else ["text", "html"]
    selectors = [
        {
            "selector": "main",
            "label": f"{normalized_prefix}_results",
            "fields": element_fields,
        }
    ]

    for selector in selectors:
        capture_path = await async_capture_element_value(
            page,
            selector=selector["selector"],
            label=selector["label"],
            fields=selector["fields"],
        )
        if capture_path:
            logger.info("📝 [nogtips_search] 要素データ保存: %s", capture_path)
        else:
            logger.warning("[nogtips_search] 要素データの保存に失敗: %s", selector["selector"])

    if query:
        logger.info("🔁 [nogtips_search] 検索クエリ: %s", query)
