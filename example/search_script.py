# search_script.py
from playwright.sync_api import sync_playwright, Page, expect
import pytest
import os

def test_linkedin_search(request) -> None:
    query = request.config.getoption("--query")
    if not query:
        pytest.skip("No query provided. Use --query to specify a search term.")

    # Playwrightのコンテキストで録画設定を追加
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # headlessはコマンドラインで制御
        context = browser.new_context(
            record_video_dir="./tmp/record_videos/" if os.getenv("ENABLE_RECORDING", "false") == "true" else None,
            record_video_size={"width": 1280, "height": 720}
        )
        page = context.new_page()

        ## Example 01 - LinkedIn検索処理
        page.goto("https://jp.linkedin.com/in/nobukins")
        page.get_by_role("link", name="LinkedIn").click()
        page.get_by_label("プライマリ").get_by_role("link", name="求人").click()
        page.get_by_role("button", name="閉じる").click()
        page.get_by_role("combobox", name="役職または会社を検索").click()
        page.get_by_role("combobox", name="役職または会社を検索").fill("AI")
        page.get_by_role("option", name="人工知能 (AI)").click()

        ## Example 02 - Beatport検索とTop10の連続再生
        # page.goto("https://www.beatport.com/")
        # page.get_by_role("button", name="I Accept").click()
        # page.get_by_test_id("header-search-input").click()
        # page.get_by_test_id("header-search-input").fill(query)
        # page.goto("https://www.beatport.com/genre/minimal-deep-tech/14")
        # page.locator(".CollectionControls-style__Controls-sc-3a6a5b4a-0 > .Play-style__Control-sc-bdba3bac-0").first.click()

        # Listen for music 10sec!
        page.wait_for_timeout(10000)

        expect(page).to_have_title(re.compile(query, re.IGNORECASE))

        # 録画を保存
        if context.video:
            video_path = page.video.path()
            print(f"Video saved at: {video_path}")
        context.close()
        browser.close()