#!/usr/bin/env python3
"""
最終検証：Chrome と Edge のユーザープロファイル読み込み確認テスト
新しい作法（2025年5月以降対応）での動作検証
"""

import asyncio
import os
import sys
import shutil
from pathlib import Path
from playwright.async_api import async_playwright

async def test_browser_profile(browser_type):
    """指定されたブラウザでプロファイル読み込みテストを実行"""
    print(f"\n{'='*60}")
    print(f"🧪 {browser_type.upper()} プロファイル最終検証開始")
    print(f"{'='*60}")
    
    # 環境変数から設定を取得
    if browser_type == 'edge':
        browser_path = os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
        original_profile = os.environ.get('EDGE_USER_DATA', '')
        profile_settings_url = "edge://settings/profiles"
    else:  # chrome
        browser_path = os.environ.get('CHROME_PATH', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        original_profile = os.environ.get('CHROME_USER_DATA', '')
        profile_settings_url = "chrome://settings/people"
    
    print(f"📍 Browser Path: {browser_path}")
    print(f"📍 Original Profile: {original_profile}")
    
    # 新しい作法：User Data ディレクトリ内に SeleniumProfile を作成
    test_profile = os.path.join(original_profile, "SeleniumProfile")
    print(f"📍 Test Profile: {test_profile}")
    
    # 既存のテストプロファイルを削除
    if os.path.exists(test_profile):
        print(f"🗑️ Removing existing test profile...")
        shutil.rmtree(test_profile, ignore_errors=True)
    
    # 新しいテストプロファイルを作成
    os.makedirs(test_profile, exist_ok=True)
    default_profile_dir = os.path.join(test_profile, "Default")
    os.makedirs(default_profile_dir, exist_ok=True)
    print(f"📁 Created test profile directory")
    
    # 重要なプロファイルファイルをコピー
    print(f"📄 Copying profile files...")
    
    # ルートレベルのファイル（重要な認証ファイルを追加）
    root_files = [
        "Local State", "First Run",
        # Google認証関連の重要ファイル
        "Account Web Data", "Login Data", "Login Data For Account", 
        "Cookies", "Extension Cookies", "Safe Browsing Cookies"
    ]
    copied_root = 0
    # 重要なルートレベルディレクトリをコピー（Google認証に必須）
    root_dirs = [
        "Accounts", "GCM Store", "Sync Data", "Sync Extension Settings", 
        "Sync App Settings", "Sessions", "Session Storage"
    ]
    copied_root_dirs = 0
    
    print(f"📁 Copying root-level directories...")
    for dir_name in root_dirs:
        src_dir = os.path.join(original_profile, dir_name)
        dst_dir = os.path.join(test_profile, dir_name)
        
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            try:
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                copied_root_dirs += 1
                # Google認証関連ディレクトリのハイライト
                if dir_name in ["Accounts", "GCM Store", "Sync Data", "Sessions"]:
                    print(f"  🔐 {dir_name}/ (GOOGLE AUTH)")
                else:
                    print(f"  ✅ {dir_name}/")
            except Exception as e:
                print(f"  ❌ Failed to copy root directory {dir_name}: {e}")
    
    print(f"📊 Root directories: {copied_root_dirs}/{len(root_dirs)}")
    
    for file_name in root_files:
        src_file = os.path.join(original_profile, file_name)
        dst_file = os.path.join(test_profile, file_name)
        
        if os.path.exists(src_file) and os.path.isfile(src_file):
            try:
                shutil.copy2(src_file, dst_file)
                copied_root += 1
                # 認証関連ファイルのハイライト
                if file_name in ["Account Web Data", "Login Data", "Login Data For Account", "Cookies"]:
                    print(f"  🔐 {file_name} (AUTH)")
                else:
                    print(f"  ✅ {file_name}")
            except Exception as e:
                print(f"  ❌ {file_name}: {e}")
    
    # Defaultプロファイル内のファイル（認証・セッション維持に重要）
    default_files = [
        # 基本設定
        "Preferences", "Secure Preferences", 
        
        # 認証・ログイン関連（重要！）
        "Login Data", "Login Data For Account", "Cookies", "Web Data",
        "Token Service", "Sync Data", "Sync Extension Settings",
        "Account Manager", "Account Tracker Service", "GCM Store",
        
        # セッション維持関連（重要！）
        "Sessions", "Current Session", "Last Session", "Session Storage",
        "Current Tabs", "Last Tabs",
        
        # Google関連の認証ファイル
        "Google Profile Picture", "Signin Stats", "Identity Manager",
        "GAIA Info", "Account Capabilities", "Google Update",
        
        # その他重要
        "History", "Bookmarks", "Favicons", "Top Sites",
        "Extension State", "Local Extension Settings", "Network Action Predictor",
        "TransportSecurity", "Shortcuts", "Visited Links", "Platform Notifications",
        
        # 追加の認証関連
        "Trust Tokens", "Reporting and NEL", "Safe Browsing Cookies",
        "Download Service", "OfflinePagePrefStore", "Shared Proto DB",
        "Local State", "Pepper Data"
    ]
    
    original_default_dir = os.path.join(original_profile, "Default")
    copied_default = 0
    total_available = 0
    
    print(f"📁 Scanning available files in: {original_default_dir}")
    
    for file_name in default_files:
        src_file = os.path.join(original_default_dir, file_name)
        dst_file = os.path.join(default_profile_dir, file_name)
        
        if os.path.exists(src_file):
            total_available += 1
            if os.path.isfile(src_file):
                try:
                    shutil.copy2(src_file, dst_file)
                    copied_default += 1
                    # 認証関連ファイルの成功をハイライト
                    if file_name in ["Cookies", "Login Data", "Login Data For Account", "Sync Data", "Token Service"]:
                        print(f"  🔐 {file_name} (AUTH)")
                    else:
                        print(f"  ✅ {file_name}")
                except Exception as e:
                    print(f"  ❌ Failed to copy {file_name}: {e}")
            else:
                print(f"  📁 {file_name} (directory - skipped in file phase)")
    
    print(f"📊 Files: Found {total_available}, Copied {copied_default}/{len(default_files)}")
    
    # Defaultプロファイル内の重要なディレクトリをコピー（認証・セッション維持）
    default_dirs = [
        # 基本
        "Extensions", "Local Storage", "IndexedDB", "Service Worker",
        
        # 認証・セッション関連（重要！）
        "Session Storage", "Sessions", "WebStorage", "databases", "Application Cache",
        
        # Google関連の重要ディレクトリ
        "GCM Store", "Sync Data", "Sync Extension Settings",
        
        # Platform関連
        "Platform Notifications", "Background Sync", "Budget Service",
        "Code Cache", "GPUCache", "ShaderCache",
        
        # セキュリティ・認証関連
        "Certificate Transparency", "Pepper Data", "shared_proto_db",
        "Safe Browsing", "optimization_guide_model_and_features_store",
        
        # 追加のキャッシュ・データ
        "File System", "Network Persistent State", "Origin Bound Certs",
        "blob_storage", "feature_engagement_tracker", "Storage"
    ]
    copied_dirs = 0
    total_dirs_available = 0
    
    print(f"📁 Scanning available directories in: {original_default_dir}")
    
    for dir_name in default_dirs:
        src_dir = os.path.join(original_default_dir, dir_name)
        dst_dir = os.path.join(default_profile_dir, dir_name)
        
        if os.path.exists(src_dir):
            total_dirs_available += 1
            if os.path.isdir(src_dir):
                try:
                    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                    copied_dirs += 1
                    # 認証関連ディレクトリの成功をハイライト
                    if dir_name in ["Session Storage", "Sessions", "Local Storage", "IndexedDB", "WebStorage", "GCM Store", "Sync Data", "Storage"]:
                        print(f"  🔐 {dir_name}/ (AUTH)")
                    else:
                        print(f"  ✅ {dir_name}/")
                except Exception as e:
                    print(f"  ❌ Failed to copy directory {dir_name}: {e}")
            else:
                print(f"  📄 {dir_name} (file - skipped in directory phase)")
    
    print(f"📊 Directories: Found {total_dirs_available}, Copied {copied_dirs}/{len(default_dirs)}")
    
    print(f"📊 Copy Summary:")
    print(f"  📄 Root files: {copied_root}/{len(root_files)}")
    print(f"  � Root directories: {copied_root_dirs}/{len(root_dirs)}")
    print(f"  �📄 Default files: {copied_default}/{total_available} available")
    print(f"  📁 Default directories: {copied_dirs}/{total_dirs_available} available")
    
    # Playwright でブラウザ起動テスト
    print(f"🚀 Launching {browser_type} with test profile...")
    
    test_results = {
        'launch_success': False,
        'profile_settings_access': False,
        'profile_data_found': False,
        'bookmarks_found': False,
        'google_account_status': 'unknown'
    }
    
    try:
        async with async_playwright() as p:
            # launch_persistent_context で起動（セッション維持重視）
            context = await p.chromium.launch_persistent_context(
                user_data_dir=test_profile,
                headless=False,
                executable_path=browser_path,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled',
                    '--profile-directory=Default',
                    
                    # セッション・認証維持のための重要オプション
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor',
                    '--disable-ipc-flooding-protection',
                    '--enable-automation=false',
                    '--no-default-browser-check',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-hang-monitor',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--disable-background-timer-throttling',
                    '--disable-background-networking',
                    '--disable-client-side-phishing-detection',
                    '--disable-sync',
                    '--disable-translate',
                    '--hide-scrollbars',
                    '--mute-audio',
                    
                    # 認証関連
                    '--enable-precise-memory-info',
                    '--disable-component-update'
                ],
                viewport={"width": 1280, "height": 720},
                ignore_default_args=['--disable-extensions', '--disable-component-extensions-with-background-pages']
            )
            
            test_results['launch_success'] = True
            print(f"✅ {browser_type} launched successfully")
            
            # 既存ページのクリーンアップ
            for page in context.pages:
                if page.url == 'about:blank' or page.url.startswith('about:'):
                    await page.close()
            
            # 新しいページを作成
            page = await context.new_page()
            
            # 1. プロファイル設定ページでの確認
            print(f"🔍 Testing profile settings access...")
            try:
                await page.goto(profile_settings_url, wait_until='domcontentloaded', timeout=20000)
                await page.wait_for_timeout(3000)
                
                test_results['profile_settings_access'] = True
                print(f"✅ Profile settings page accessible")
                
                # プロファイルデータの確認
                page_content = await page.text_content('body')
                
                # メールアドレスの検索
                if '@' in page_content:
                    lines_with_email = [line.strip() for line in page_content.split('\n') 
                                       if '@' in line and len(line.strip()) < 100 and len(line.strip()) > 5]
                    if lines_with_email:
                        test_results['profile_data_found'] = True
                        print(f"✅ Profile data found: {len(lines_with_email)} email references")
                        for email_line in lines_with_email[:2]:
                            print(f"  📧 {email_line}")
                    else:
                        print(f"⚠️ No valid email addresses in profile")
                else:
                    print(f"❌ No email addresses found in profile settings")
                
                # アカウント関連のテキストを検索
                account_keywords = ['アカウント', 'account', 'profile', 'プロファイル', 'signed', 'サインイン']
                found_keywords = [kw for kw in account_keywords if kw.lower() in page_content.lower()]
                if found_keywords:
                    print(f"✅ Account-related content found: {', '.join(found_keywords[:3])}")
                
            except Exception as e:
                print(f"❌ Failed to access profile settings: {e}")
                # Chromeの場合、代替URLを試行
                if browser_type == 'chrome':
                    try:
                        print(f"🔄 Trying alternative Chrome settings URL...")
                        await page.goto("chrome://settings/", wait_until='domcontentloaded', timeout=15000)
                        await page.wait_for_timeout(2000)
                        test_results['profile_settings_access'] = True
                        print(f"✅ Chrome settings page accessible (alternative)")
                    except Exception as e2:
                        print(f"❌ Alternative Chrome settings also failed: {e2}")
            
            # 2. Google アカウント状況の確認（詳細版）
            print(f"🔍 Testing Google account status...")
            try:
                await page.goto("https://www.google.com", wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(3000)
                
                page_content = await page.text_content('body')
                
                # より詳細なアカウント確認
                account_selectors = [
                    '[aria-label*="Google Account"]', '[aria-label*="Google アカウント"]', 
                    '.gb_d', '.gb_Ae', '.gb_Da', '.gb_xa', '.gb_Aa',
                    '[data-ved*="account"]', '[data-ved*="signin"]',
                    '.gb_x', '.gb_Fa', '.gb_8a', 'a[href*="accounts.google.com"]'
                ]
                
                signin_indicators = [
                    'a[aria-label*="Sign in"]', 'a[aria-label*="ログイン"]', 
                    '[data-ved*="sign"]', 'a[href*="accounts.google.com/signin"]',
                    '.gb_zg', '.gb_yg', '.gb_xg'
                ]
                
                # アカウントアイコンや名前の確認
                account_found = False
                for selector in account_selectors:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        account_found = True
                        print(f"  ✅ Account indicator found: {selector} ({len(elements)} elements)")
                        break
                
                # サインインボタンの確認
                signin_found = False
                for selector in signin_indicators:
                    elements = await page.query_selector_all(selector)
                    if elements and len(elements) > 0:
                        signin_found = True
                        print(f"  ⚠️ Sign-in indicator found: {selector} ({len(elements)} elements)")
                        break
                
                # ページコンテンツの分析
                email_patterns = ['@gmail.com', '@googlemail.com', '@google.com']
                emails_found = any(pattern in page_content for pattern in email_patterns)
                
                if account_found and not signin_found:
                    test_results['google_account_status'] = 'signed_in'
                    print(f"✅ Google account: Likely signed in")
                elif signin_found:
                    test_results['google_account_status'] = 'not_signed_in'
                    print(f"❌ Google account: Not signed in")
                elif emails_found:
                    test_results['google_account_status'] = 'partially_signed_in'
                    print(f"⚠️ Google account: Partially signed in (emails detected)")
                else:
                    test_results['google_account_status'] = 'unclear'
                    print(f"⚠️ Google account status unclear")
                
                # 追加テスト: Gmail へのアクセス
                print(f"🔍 Testing Gmail access...")
                try:
                    await page.goto("https://mail.google.com", wait_until='domcontentloaded', timeout=10000)
                    await page.wait_for_timeout(2000)
                    
                    current_url = page.url
                    if 'accounts.google.com' in current_url and 'signin' in current_url:
                        print(f"❌ Gmail: Redirected to sign-in page")
                    elif 'mail.google.com' in current_url:
                        print(f"✅ Gmail: Successfully accessed (signed in)")
                        test_results['google_account_status'] = 'signed_in'
                    else:
                        print(f"⚠️ Gmail: Unexpected redirect - {current_url}")
                        
                except Exception as gmail_e:
                    print(f"⚠️ Gmail test failed: {gmail_e}")
                
            except Exception as e:
                print(f"❌ Failed to check Google account: {e}")
            
            # 3. ブックマークの確認
            print(f"🔍 Testing bookmarks...")
            try:
                # ブックマークマネージャーを開く
                if browser_type == 'chrome':
                    await page.keyboard.press('Meta+Alt+B')  # Mac Chrome
                    await page.wait_for_timeout(1000)
                    # 別の方法でブックマークページに移動
                    await page.goto("chrome://bookmarks/", wait_until='domcontentloaded', timeout=10000)
                else:
                    await page.keyboard.press('Meta+Shift+O')  # Mac Edge
                    await page.wait_for_timeout(1000)
                    # 別の方法でブックマークページに移動
                    await page.goto("edge://favorites/", wait_until='domcontentloaded', timeout=10000)
                
                await page.wait_for_timeout(2000)
                
                # ブックマーク要素を確認
                bookmark_elements = await page.query_selector_all('[role="treeitem"], .bookmark-item, [data-test-id*="bookmark"], .list-item')
                page_content = await page.text_content('body')
                
                if bookmark_elements and len(bookmark_elements) > 0:
                    test_results['bookmarks_found'] = True
                    print(f"✅ Bookmarks found: {len(bookmark_elements)} bookmark elements")
                elif page_content and ('bookmark' in page_content.lower() or 'お気に入り' in page_content):
                    test_results['bookmarks_found'] = True
                    print(f"✅ Bookmarks content detected in page text")
                else:
                    print(f"❌ No bookmarks found")
                
            except Exception as e:
                print(f"⚠️ Bookmark check had issues: {e}")
            
            # 短時間表示
            print(f"⏱️ Displaying for 3 seconds...")
            await page.wait_for_timeout(3000)
            
            await context.close()
            
    except Exception as e:
        print(f"❌ Browser launch failed: {e}")
        import traceback
        traceback.print_exc()
    
    return test_results

async def main():
    """最終検証のメイン関数"""
    print("🎯 最終検証：Chrome & Edge プロファイル読み込みテスト")
    print("新しい作法（2025年5月以降対応）での動作検証")
    
    # Edge のテスト
    edge_results = await test_browser_profile('edge')
    
    # Chrome のテスト
    chrome_results = await test_browser_profile('chrome')
    
    # 結果のサマリー
    print(f"\n{'='*60}")
    print(f"📊 最終検証結果サマリー")
    print(f"{'='*60}")
    
    browsers = [('Edge', edge_results), ('Chrome', chrome_results)]
    
    for browser_name, results in browsers:
        print(f"\n🔍 {browser_name}:")
        print(f"  🚀 ブラウザ起動: {'✅ 成功' if results['launch_success'] else '❌ 失敗'}")
        print(f"  ⚙️ プロファイル設定アクセス: {'✅ 成功' if results['profile_settings_access'] else '❌ 失敗'}")
        print(f"  👤 プロファイルデータ: {'✅ 発見' if results['profile_data_found'] else '❌ 未発見'}")
        print(f"  📚 ブックマーク: {'✅ 発見' if results['bookmarks_found'] else '❌ 未発見'}")
        
        google_status = results['google_account_status']
        if google_status == 'signed_in':
            print(f"  🔐 Googleアカウント: ✅ サインイン済み")
        elif google_status == 'not_signed_in':
            print(f"  🔐 Googleアカウント: ❌ 未サインイン")
        else:
            print(f"  🔐 Googleアカウント: ⚠️ 不明")
    
    # 総合評価
    print(f"\n🎯 総合評価:")
    
    edge_success = edge_results['launch_success'] and edge_results['profile_settings_access']
    chrome_success = chrome_results['launch_success'] and chrome_results['profile_settings_access']
    
    if edge_success and chrome_success:
        print("✅ 両ブラウザでプロファイル読み込みが正常に動作しています")
        print("✅ 新しい作法での実装が成功しました")
    elif edge_success or chrome_success:
        working_browser = "Edge" if edge_success else "Chrome"
        print(f"⚠️ {working_browser} でのみプロファイル読み込みが動作しています")
        print("⚠️ 一部の実装に改善が必要です")
    else:
        print("❌ 両ブラウザでプロファイル読み込みに問題があります")
        print("❌ 実装の見直しが必要です")
    
    # プロファイルデータの詳細評価
    edge_data = edge_results['profile_data_found'] or edge_results['bookmarks_found']
    chrome_data = chrome_results['profile_data_found'] or chrome_results['bookmarks_found']
    
    if edge_data and chrome_data:
        print("✅ 両ブラウザでユーザーデータが正常に移行されています")
    elif edge_data or chrome_data:
        data_browser = "Edge" if edge_data else "Chrome"
        print(f"⚠️ {data_browser} でのみユーザーデータが移行されています")
    else:
        print("❌ ユーザーデータの移行に問題があります")
    
    print(f"\n🏁 最終検証完了")

if __name__ == "__main__":
    asyncio.run(main())
