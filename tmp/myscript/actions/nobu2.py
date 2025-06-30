async def run_actions(page, query=None):
    """
    # Auto-generated from playwright codegen
    """
    await page.goto("https://www.yahoo.co.jp/")
    await page.get_by_role("searchbox", name="検索したいキーワードを入力してください").click()
    await page.get_by_role("searchbox", name="検索したいキーワードを入力してください").fill("Nobukins")
    await page.get_by_role("searchbox", name="検索したいキーワードを入力してください").press("Enter")
    await page.get_by_role("link", name="Nobuaki Ogawa - AXA Japan").click()
    await page.wait_for_timeout(3000)