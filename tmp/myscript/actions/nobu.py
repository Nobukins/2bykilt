async def run_actions(page, query=None):
    """
    # Auto-generated from playwright codegen
    """
    await page.goto("https://www.google.com/")
    await page.get_by_role("img").nth(1).click()
    await page.get_by_role("combobox", name="検索").click()
    await page.get_by_role("combobox", name="検索").fill("Nobukins")
    await page.wait_for_timeout(3000)