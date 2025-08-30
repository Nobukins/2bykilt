async def run_actions(page, query=None):
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
    
    print(f"🔘 [nogtips_search] 承認ボタンクリック中...")
    await page.get_by_role("button", name="閉じて承認").click()
    
    print(f"🔗 [nogtips_search] nogtipsリンククリック中...")
    await page.get_by_role("link", name="nogtips").click()
    
    print(f"📝 [nogtips_search] LLMs.txtリンククリック中...")
    await page.get_by_role("heading", name="LLMs.txtについて").get_by_role("link").click()
    
    print(f"🔎 [nogtips_search] 検索ボックスクリック中...")
    await page.get_by_role("searchbox", name="検索:").click()
    
    print(f"⌨️ [nogtips_search] 検索クエリ入力中: {query}")
    await page.get_by_role("searchbox", name="検索:").fill(query)
    
    print(f"⏎ [nogtips_search] Enter キー押下中...")
    await page.get_by_role("searchbox", name="検索:").press("Enter")
    
    # 検索結果を表示
    print(f"⏳ [nogtips_search] 検索結果表示待機中（5秒）...")
    await page.wait_for_timeout(5000)
    
    print(f"✅ [nogtips_search] アクション完了")
