#!/usr/bin/env python3
"""
Edge プロファイル読み込みテスト用のシンプルなスクリプト
"""

import asyncio
import pytest
import os
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

@pytest.mark.local_only
async def test_edge_with_profile():
    print("🧪 Edge プロファイルテストを開始...")
    
    # 環境変数から設定を取得
    edge_path = os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
    edge_user_data = os.environ.get('EDGE_USER_DATA', '/Users/nobuaki/Library/Application Support/Microsoft Edge')
    
    # テストプロファイルディレクトリ
    test_profile_dir = "./tmp/test_edge_profile_playwright"
    
    print(f"Edge Path: {edge_path}")
    print(f"Original Profile: {edge_user_data}")
    print(f"Test Profile: {test_profile_dir}")
    
    # テストプロファイルを準備
    if os.path.exists(test_profile_dir):
        print(f"🗑️ Removing existing test profile...")
        shutil.rmtree(test_profile_dir, ignore_errors=True)
    
    print(f"📁 Creating test profile directory...")
    os.makedirs(test_profile_dir, exist_ok=True)
    
    # 重要なファイルをコピー
    important_files = [
        "Default/Preferences",
        "Default/Bookmarks", 
        "Default/History",
        "Default/Cookies",
        "Default/Login Data",
        "Default/Web Data",
        "Local State"
    ]
    
    copied_count = 0
    for file_path in important_files:
        src_file = os.path.join(edge_user_data, file_path)
        dst_file = os.path.join(test_profile_dir, file_path)
        
        if os.path.exists(src_file):
            try:
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                if os.path.isfile(src_file):
                    shutil.copy2(src_file, dst_file)
                    print(f"📄 Copied: {file_path}")
                    copied_count += 1
            except Exception as e:
                print(f"⚠️ Failed to copy {file_path}: {e}")
    
    print(f"✅ Copied {copied_count} profile files")
    
    # Playwright でブラウザを起動
    print(f"🚀 Launching Edge with test profile...")
    
    async with async_playwright() as p:
        try:
            # launch_persistent_context を使用してプロファイル付きで起動
            context = await p.chromium.launch_persistent_context(
                user_data_dir=test_profile_dir,
                headless=False,
                executable_path=edge_path,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-default-apps',
                    '--profile-directory=Default'
                ],
                viewport={"width": 1280, "height": 720},
                ignore_default_args=['--disable-extensions']
            )
            
            print("✅ Edge launched successfully with test profile")
            
            # 既存のページを処理
            existing_pages = context.pages
            print(f"📄 Found {len(existing_pages)} existing pages")
            
            for i, page in enumerate(existing_pages):
                url = page.url
                print(f"📄 Page {i}: {url}")
                if url == 'about:blank' or url.startswith('about:'):
                    print(f"🗑️ Closing about:blank page {i}")
                    await page.close()
            
            # 新しいページを作成
            page = await context.new_page()
            print("✅ Created new page")
            
            # Google にアクセスしてアカウント状況を確認
            print("🔍 Checking Google account status...")
            await page.goto("https://www.google.com", wait_until='domcontentloaded')
            await page.wait_for_timeout(3000)
            
            # アカウント状況を確認
            try:
                # プロフィール要素を探す
                profile_elements = await page.query_selector_all('.gb_d, .gb_Ae, [aria-label*="Google Account"]')
                if profile_elements:
                    print("✅ Google account elements found - likely signed in")
                    # プロフィール情報を取得
                    for i, element in enumerate(profile_elements[:2]):
                        try:
                            text = await element.text_content()
                            if text and text.strip():
                                print(f"📄 Profile element {i}: {text[:30]}...")
                        except:
                            pass
                else:
                    print("❌ No Google account elements found - likely not signed in")
                
                # サインインボタンの確認
                sign_in_elements = await page.query_selector_all('a[aria-label*="Sign in"], a[data-ved*="sign"]')
                if sign_in_elements:
                    print("❌ Sign in button found - not signed in")
                else:
                    print("✅ No sign in button found - possibly signed in")
                    
            except Exception as e:
                print(f"⚠️ Error checking account status: {e}")
            
            # ブックマークページに移動
            print("🔍 Checking bookmarks...")
            try:
                await page.goto("edge://favorites/", wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # ブックマーク要素を確認
                bookmark_elements = await page.query_selector_all('[role="treeitem"], .bookmark-item')
                if bookmark_elements:
                    print(f"✅ Found {len(bookmark_elements)} bookmark elements")
                else:
                    print("❌ No bookmarks found")
                    
            except Exception as e:
                print(f"⚠️ Error checking bookmarks: {e}")
            
            # 5秒間表示
            print("⏱️ Displaying for 5 seconds...")
            await page.wait_for_timeout(5000)
            
            print("✅ Test completed successfully")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error during Edge test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edge_with_profile())
