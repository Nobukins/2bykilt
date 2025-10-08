async def run_actions(page, query=None):
    """
    # Auto-generated from playwright codegen
    """
    await page.goto("https://www.yahoo.co.jp/")
    await page.get_by_role("link", name="台風 9日明け方-朝に伊豆諸島接近").click()
    await page.wait_for_timeout(3000)