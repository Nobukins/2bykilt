async def run_actions(page, query=None):
    """
    # Auto-generated from playwright codegen
    """
    await page.goto("https://www.yahoo.co.jp/")
    await page.get_by_role("link", name="九州～東北で警報級大雨恐れ 警戒").click()
    await page.get_by_role("link", name="雨雲レーダー 出典：Yahoo!天気・災害").click()
    await page.wait_for_timeout(3000)