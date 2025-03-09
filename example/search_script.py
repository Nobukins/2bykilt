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


        ## Example 01 - 人材検索検索処理
        # page.goto("https://socialnetworksite")
        # page.get_by_role("link", name="SiteName").click()
        # page.get_by_role("combobox", name="検索").click()
        # page.get_by_role("combobox", name="検索").fill("AI")
        # page.get_by_role("option", name="人工知能 (AI)").click()

        ## Example 02 - musicportalsite検索とTop10の連続再生
        # page.goto("https:/musicportalsite/")
        # page.get_by_role("button", name="I Accept").click()
        # page.get_by_test_id("header-search-input").click()
        # page.get_by_test_id("header-search-input").fill(query)
        # page.goto("https://musicportalsite/genre/xxx")
        # page.locator(".Xxxxx-xxxx > .XXXX").first.click()

        # Listen for music 10sec!
        page.wait_for_timeout(10000)

        expect(page).to_have_title(re.compile(query, re.IGNORECASE))

        # 録画を保存
        if context.video:
            video_path = page.video.path()
            print(f"Video saved at: {video_path}")
        context.close()
        browser.close()