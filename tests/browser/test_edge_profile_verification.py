#!/usr/bin/env python3
"""
Edge プロファイルの個人アカウント表示を確認するテスト
edge://settings/profiles での検証を含む
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

async def test_edge_profile_verification():
    print("🧪 Edge プロファイル検証テストを開始...")
    
    # 環境変数から設定を取得
    edge_path = os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
    original_edge_profile = os.environ.get('EDGE_USER_DATA', '/Users/nobuaki/Library/Application Support/Microsoft Edge')
    
    print(f"Edge Path: {edge_path}")
    print(f"Original Profile: {original_edge_profile}")
    
    # 新しい作法：Edge フォルダ内（元のUser Dataディレクトリ内）に SeleniumProfile を作成
    edge_test_profile = os.path.join(original_edge_profile, "SeleniumProfile")
    
    print(f"Edge User Data directory: {original_edge_profile}")
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
    
    # より詳細なプロファイルファイルをコピー
    # ルートレベルのファイル
    root_files = ["Local State", "First Run"]
    
    # Defaultプロファイル内のファイル（より多くのアカウント関連ファイルを含む）
    default_files = [
        "Preferences", "Secure Preferences", 
        "Login Data", "Login Data For Account",
        "Web Data", "History", "Bookmarks", "Cookies", 
        "Favicons", "Top Sites", "Sessions", "Current Session", "Last Session",
        "Sync Data", "Extension State", "Local Extension Settings",
        "Platform Notifications", "Network Action Predictor",
        "TransportSecurity", "Shortcuts", "Visited Links"
    ]
    
    # Defaultプロファイル内のディレクトリ
    default_dirs = [
        "Extensions", "Local Storage", "Session Storage", "IndexedDB", 
        "databases", "Service Worker", "storage", "blob_storage"
    ]
    
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
    
    # Defaultプロファイル内のディレクトリをコピー
    copied_dirs = 0
    for dir_name in default_dirs:
        src_dir = os.path.join(original_default_dir, dir_name)
        dst_dir = os.path.join(default_profile_dir, dir_name)
        
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            try:
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                print(f"📁 Copied Edge Default directory: {dir_name}")
                copied_dirs += 1
            except Exception as e:
                print(f"⚠️ Failed to copy Edge Default directory {dir_name}: {e}")
    
    print(f"✅ Profile copy summary (enhanced method):")
    print(f"   📄 Root files copied: {copied_root}")
    print(f"   📄 Default files copied: {copied_default}")
    print(f"   📁 Default directories copied: {copied_dirs}")
    
    # Playwright でブラウザを起動（新しい作法）
    print(f"🚀 Launching Edge with enhanced profile...")
    
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
                    '--profile-directory=Default',  # 明示的にDefaultプロファイルを指定
                    '--disable-sync',  # 同期を無効化してローカルプロファイルを使用
                    '--no-first-run'
                ],
                viewport={"width": 1280, "height": 720},
                ignore_default_args=['--disable-extensions']
            )
            
            print("✅ Edge launched successfully with enhanced profile")
            
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
            
            # 🔍 重要：edge://settings/profiles でプロファイル情報を確認
            print("🔍 Checking Edge profile settings...")
            try:
                await page.goto("edge://settings/profiles", wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)  # ページ読み込み待機
                
                # プロファイル関連の要素を確認
                profile_elements = await page.query_selector_all('[role="heading"], .profile-name, .account-name, [data-test-id*="profile"], [aria-label*="プロファイル"], [aria-label*="Profile"]')
                
                print(f"🔍 Profile settings elements found: {len(profile_elements)}")
                
                if profile_elements:
                    print("✅ Profile settings page loaded successfully")
                    for i, element in enumerate(profile_elements[:5]):  # 最初の5つの要素を確認
                        try:
                            text = await element.text_content()
                            if text and text.strip():
                                print(f"📄 Profile element {i}: {text[:80]}...")
                        except:
                            pass
                else:
                    print("❌ No profile elements found in settings")
                
                # アカウント情報を具体的に探す
                account_elements = await page.query_selector_all('[role="button"]:has-text("アカウント"), [role="button"]:has-text("Account"), .account-info, .user-info')
                
                if account_elements:
                    print(f"✅ Found {len(account_elements)} account-related elements")
                    for i, element in enumerate(account_elements[:3]):
                        try:
                            text = await element.text_content()
                            if text and text.strip():
                                print(f"📄 Account element {i}: {text[:80]}...")
                        except:
                            pass
                else:
                    print("❌ No account elements found")
                
                # ページ全体のテキストからアカウント情報を検索
                page_content = await page.text_content('body')
                if '@' in page_content:
                    lines_with_email = [line.strip() for line in page_content.split('\n') if '@' in line and len(line.strip()) < 100]
                    if lines_with_email:
                        print("✅ Found potential email addresses in profile:")
                        for email_line in lines_with_email[:3]:
                            print(f"📧 {email_line}")
                    else:
                        print("❌ No email addresses detected in profile settings")
                else:
                    print("❌ No email addresses found in page content")
                
            except Exception as e:
                print(f"❌ Error accessing Edge profile settings: {e}")
            
            # Google にアクセスしてアカウント状況も確認
            print("🔍 Checking Google account status...")
            try:
                await page.goto("https://www.google.com", wait_until='domcontentloaded')
                await page.wait_for_timeout(3000)
                
                # Googleアカウント要素を探す
                account_elements = await page.query_selector_all('[aria-label*="Google アカウント"], [aria-label*="Google Account"], .gb_d, .gb_Ae, [data-ved*="account"]')
                signin_elements = await page.query_selector_all('a[aria-label*="ログイン"], a[aria-label*="Sign in"], [data-ved*="sign"]')
                
                print(f"🔍 Google account elements found: {len(account_elements)}")
                print(f"🔍 Google sign-in elements found: {len(signin_elements)}")
                
                if account_elements and len(account_elements) > 0:
                    print("✅ Google account elements detected - likely signed in")
                    for i, element in enumerate(account_elements[:2]):
                        try:
                            text = await element.text_content()
                            if text and text.strip():
                                print(f"📄 Google account element {i}: {text[:50]}...")
                        except:
                            pass
                elif signin_elements and len(signin_elements) > 0:
                    print("❌ Sign-in elements found - likely NOT signed in to Google")
                else:
                    print("⚠️ Google account status unclear")
                    
            except Exception as e:
                print(f"⚠️ Error checking Google account status: {e}")
            
            # 10秒間表示して確認
            print("⏱️ Displaying for 10 seconds for manual verification...")
            await page.wait_for_timeout(10000)
            
            print("✅ Profile verification test completed")
            await context.close()
            
        except Exception as e:
            print(f"❌ Error during Edge profile verification test: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_edge_profile_verification())
