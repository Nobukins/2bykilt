async def run_actions(page, query=None):
    """
    nogtipsサイトでの検索アクションを実行
    
    Args:
        page: Playwrightのページオブジェクト
        query: 検索クエリ (文字列)
    """
    # nogtips検索処理
    await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=30000)
    await page.get_by_role("button", name="閉じて承認").click()
    await page.get_by_role("link", name="nogtips").click()
    await page.get_by_role("heading", name="LLMs.txtについて").get_by_role("link").click()
    await page.get_by_role("searchbox", name="検索:").click()
    await page.get_by_role("searchbox", name="検索:").fill(query)
    await page.get_by_role("searchbox", name="検索:").press("Enter")
    
    # 検索結果を表示
    await page.wait_for_timeout(5000)
