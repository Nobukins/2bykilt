#!/usr/bin/env python3
"""
新しい作法でのEdge プロファイルコピーとテスト
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

import pytest

@pytest.mark.local_only
async def test_edge_new_method():
    print("🧪 Edge 新しい作法テストを開始...")
    
    # 環境変数から設定を取得
    edge_path = os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
    original_edge_profile = os.environ.get('EDGE_USER_DATA', '/Users/nobuaki/Library/Application Support/Microsoft Edge')
    
    print(f"Edge Path: {edge_path}")
    print(f"Original Profile: {original_edge_profile}")
    
    # 新しい作法：Edge フォルダ内に SeleniumProfile を作成
    edge_app_dir = os.path.dirname(original_edge_profile)  # ~/Library/Application Support/Microsoft Edge
    edge_test_profile = os.path.join(edge_app_dir, "SeleniumProfile")
    
    print(f"Edge app directory: {edge_app_dir}")
    print(f"New Edge test profile: {edge_test_profile}")
    
    # 既存のテストプロファイルがあれば削除
    if os.path.exists(edge_test_profile):
        print(f"🗑️ Removing existing test profile...")
        shutil.rmtree(edge_test_profile, ignore_errors=True)
    
    # 新しいテストプロファイルディレクトリを作成
    os.makedirs(edge_test_profile, exist_ok=True)
    
    # Defaultプロファイル用のディレクトリを作成
    default_profile_dir = os.path.join(edge_test_profile, "Default")
    os.makedirs(default_profile_dir, exist_ok=True)
    print(f"📁 Created Edge test profile directory: {edge_test_profile}")
    
    # ルートレベルのファイルをコピー
    root_files = ["Local State", "First Run"]
    
    copied_root = 0
    for file_name in root_files:
        src_file = os.path.join(original_edge_profile, file_name)
        dst_file = os.path.join(edge_test_profile, file_name)
        
        if os.path.exists(src_file) and os.path.isfile(src_file):
            try:
                shutil.copy2(src_file, dst_file)
                print(f"📄 Copied Edge root file: {file_name}")
                copied_root += 1
            except Exception as e:
                print(f"⚠️ Failed to copy Edge root file {file_name}: {e}")
    
    # Defaultプロファイル内のファイルをコピー
    default_files = [
        "Preferences", "Secure Preferences", "Login Data", "Web Data", 
        "History", "Bookmarks", "Cookies", "Favicons", "Top Sites"
    ]
    
    original_default_dir = os.path.join(original_edge_profile, "Default")
    copied_default = 0
    
    for file_name in default_files:
        src_file = os.path.join(original_default_dir, file_name)
        dst_file = os.path.join(default_profile_dir, file_name)
        
        if os.path.exists(src_file) and os.path.isfile(src_file):
            try:
                shutil.copy2(src_file, dst_file)
                print(f"📄 Copied Edge Default file: {file_name}")
                copied_default += 1
            except Exception as e:
                print(f"⚠️ Failed to copy Edge Default file {file_name}: {e}")
    
    print(f"✅ Profile copy summary (new method):")
    print(f"   📄 Root files copied: {copied_root}")
    print(f"   📄 Default files copied: {copied_default}")
    
    # Playwright でブラウザを起動（新しい作法）
    print(f"🚀 Launching Edge with new method profile...")
    
    async with async_playwright() as p:
        try:
            # launch_persistent_context を使用してプロファイル付きで起動
            context = await p.chromium.launch_persistent_context(
                user_data_dir=edge_test_profile,  # 新しい作法のパス
                headless=False,
                executable_path=edge_path,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-default-apps',
                    '--profile-directory=Default'  # 明示的にDefaultプロファイルを指定
                ],
                viewport={"width": 1280, "height": 720},
                ignore_default_args=['--disable-extensions']
            )
            
            print("✅ Edge launched successfully with new method profile")
            
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
            
            # アカウント状況を詳しく確認
            try:
                # Googleアカウント要素を探す
                account_elements = await page.query_selector_all('[aria-label*="Google アカウント"], [aria-label*="Google Account"], .gb_d, .gb_Ae')
                signin_elements = await page.query_selector_all('a[aria-label*="ログイン"], a[aria-label*="Sign in"], [data-ved*="sign"]')
                
                print(f"🔍 Account elements found: {len(account_elements)}")
                print(f"🔍 Sign-in elements found: {len(signin_elements)}")
                
                if account_elements and len(account_elements) > 0:
                    print("✅ Google account elements detected - likely signed in")
                    for i, element in enumerate(account_elements[:2]):
                        try:
                            text = await element.text_content()
                            if text and text.strip():
                                print(f"📄 Account element {i}: {text[:50]}...")
                        except:
                            pass
                elif signin_elements and len(signin_elements) > 0:
                    print("❌ Sign-in elements found - likely NOT signed in")
                else:
                    print("⚠️ Account status unclear")
                    
            except Exception as e:
                print(f"⚠️ Error checking account status: {e}")
            
            # ブックマークページに移動
            print("🔍 Checking bookmarks...")
            try:
                await page.goto("edge://favorites/", wait_until='domcontentloaded')
                await page.wait_for_timeout(2000)
                
                # ブックマーク要素を確認
                bookmark_elements = await page.query_selector_all('[role="treeitem"], .bookmark-item, .bookmark')
                print(f"✅ Found {len(bookmark_elements)} bookmark elements")
                    
            except Exception as e:
                print(f"⚠️ Error checking bookmarks: {e}")
            
            # 5秒間表示
            print("⏱️ Displaying for 5 seconds...")
            await page.wait_for_timeout(5000)
            
            print("✅ New method test completed successfully")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error during Edge new method test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edge_new_method())
