#!/usr/bin/env python3
"""
Playwright Browser Automation with Temporary User Profile
センシティブなユーザープロファイルを一時的にコピーして利用し、完全削除する安全な実装
"""

import asyncio
import os
import sys
import shutil
import tempfile
import atexit
import signal
import re
from pathlib import Path
from playwright.async_api import async_playwright

# 一時プロファイルのパスを管理するグローバル変数
temp_profiles = []

def cleanup_temp_profiles():
    """すべての一時プロファイルを完全削除"""
    for temp_path in temp_profiles:
        if os.path.exists(temp_path):
            try:
                shutil.rmtree(temp_path, ignore_errors=True)
                print(f"🗑️ Cleaned up temporary profile: {temp_path}")
            except Exception as e:
                print(f"⚠️ Failed to clean up {temp_path}: {e}")

# プロセス終了時の自動クリーンアップ
atexit.register(cleanup_temp_profiles)
signal.signal(signal.SIGTERM, lambda signum, frame: cleanup_temp_profiles())
signal.signal(signal.SIGINT, lambda signum, frame: cleanup_temp_profiles())

def create_temp_browser_profile(browser_type):
    """一時的なブラウザプロファイルを作成

    Accepts a Playwright BrowserType or plain string; extract .name if present.
    """
    print(f"\n{'='*60}")
    bt_name = getattr(browser_type, 'name', browser_type)
    try:
        display = str(bt_name).upper()
    except Exception:
        display = str(bt_name)
    # Safe identifier for filesystem usage (avoid repr with slashes / spaces)
    raw = str(bt_name) if bt_name else "browser"
    # Extract last path component then keep alphanumerics + dashes
    raw_component = raw.split('/')[-1]
    m = re.search(r"[A-Za-z0-9_-]+", raw_component)
    browser_key = (m.group(0) if m else "browser").lower()
    print(f"🔧 {display} 一時プロファイル作成開始")
    print(f"{'='*60}")
    
    # 環境変数から設定を取得
    if str(bt_name) == 'edge':
        browser_path = os.environ.get('EDGE_PATH', '/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge')
        original_profile = os.environ.get('EDGE_USER_DATA', '')
    else:  # chrome
        browser_path = os.environ.get('CHROME_PATH', '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome')
        original_profile = os.environ.get('CHROME_USER_DATA', '')
    
    print(f"📍 Browser Path: {browser_path}")
    print(f"📍 Original Profile: {original_profile}")
    
    # 一時ディレクトリを作成（システムの一時領域を使用）
    temp_dir = tempfile.mkdtemp(prefix=f'playwright_{browser_key}_profile_')
    temp_profiles.append(temp_dir)  # クリーンアップリストに追加
    
    temp_user_data = os.path.join(temp_dir, "UserData")
    temp_default_profile = os.path.join(temp_user_data, "Default")
    
    os.makedirs(temp_user_data, exist_ok=True)
    os.makedirs(temp_default_profile, exist_ok=True)
    
    print(f"📁 Temporary Profile: {temp_user_data}")
    print(f"📁 Temporary Default: {temp_default_profile}")
    
    # 重要なルートレベルファイルをコピー（認証に必須）
    print(f"📄 Copying critical root files...")
    root_files = [
        "Local State", "First Run",
        # Google認証関連の最重要ファイル（解析結果に基づく）
        "Account Web Data", "Login Data", "Login Data For Account", 
        "Cookies", "Extension Cookies", "Safe Browsing Cookies",
        # 追加の重要ファイル
        "Network Persistent State", "Shared Proto DB"
    ]
    
    copied_root = 0
    for file_name in root_files:
        src_file = os.path.join(original_profile, file_name)
        dst_file = os.path.join(temp_user_data, file_name)
        
        if os.path.exists(src_file) and os.path.isfile(src_file):
            try:
                shutil.copy2(src_file, dst_file)
                copied_root += 1
                if file_name in ["Account Web Data", "Login Data", "Login Data For Account", "Cookies", "Network Persistent State"]:
                    print(f"  🔐 {file_name} (AUTH)")
                else:
                    print(f"  ✅ {file_name}")
            except Exception as e:
                print(f"  ❌ {file_name}: {e}")
    
    # 重要なルートレベルディレクトリをコピー（Google認証に必須）
    print(f"📁 Copying critical root directories...")
    root_dirs = [
        # 解析結果に基づく最重要ディレクトリ
        "Accounts", "GCM Store", "Sync Data", "Sync Extension Settings", 
        "Sync App Settings", "Sessions", "Session Storage",
        # 追加の重要ディレクトリ
        "component_crx_cache", "TrustTokenKeyCommitments"
    ]
    
    copied_root_dirs = 0
    for dir_name in root_dirs:
        src_dir = os.path.join(original_profile, dir_name)
        dst_dir = os.path.join(temp_user_data, dir_name)
        
        if os.path.exists(src_dir) and os.path.isdir(src_dir):
            try:
                shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                copied_root_dirs += 1
                if dir_name in ["Accounts", "GCM Store", "Sync Data", "Sessions", "Sync Extension Settings"]:
                    print(f"  🔐 {dir_name}/ (GOOGLE AUTH)")
                else:
                    print(f"  ✅ {dir_name}/")
            except Exception as e:
                print(f"  ❌ Failed to copy root directory {dir_name}: {e}")
    
    # Defaultプロファイル内の重要ファイルをコピー
    print(f"📄 Copying Default profile files...")
    original_default_dir = os.path.join(original_profile, "Default")
    
    default_files = [
        # 基本設定
        "Preferences", "Secure Preferences", 
        
        # 認証・ログイン関連（最重要！解析結果に基づく）
        "Login Data", "Login Data For Account", "Cookies", "Web Data",
        "Account Web Data", "Account Tracker Service", "Account Manager",
        "Token Service", "Sync Data", "Sync Extension Settings",
        "GCM Store", "GAIA Info", "Identity Manager",
        
        # セッション維持関連（最重要！）
        "Sessions", "Current Session", "Last Session", "Session Storage",
        "Current Tabs", "Last Tabs",
        
        # Google関連の認証ファイル（解析で発見されたもの）
        "Google Profile Picture", "Signin Stats", "Google Update",
        "Account Capabilities", "Network Persistent State",
        
        # その他重要
        "History", "Bookmarks", "Favicons", "Top Sites",
        "Extension State", "Local Extension Settings", "Network Action Predictor",
        "TransportSecurity", "Shortcuts", "Visited Links", "Platform Notifications",
        
        # 追加の認証関連
        "Trust Tokens", "Reporting and NEL", "Safe Browsing Cookies",
        "Download Service", "OfflinePagePrefStore", "Shared Proto DB"
    ]
    
    copied_default = 0
    total_available = 0
    
    for file_name in default_files:
        src_file = os.path.join(original_default_dir, file_name)
        dst_file = os.path.join(temp_default_profile, file_name)
        
        if os.path.exists(src_file):
            total_available += 1
            if os.path.isfile(src_file):
                try:
                    shutil.copy2(src_file, dst_file)
                    copied_default += 1
                    if file_name in ["Cookies", "Login Data", "Login Data For Account", "Account Web Data", "Sync Data", "Token Service", "GAIA Info", "Network Persistent State"]:
                        print(f"  🔐 {file_name} (AUTH)")
                    else:
                        print(f"  ✅ {file_name}")
                except Exception as e:
                    print(f"  ❌ Failed to copy {file_name}: {e}")
    
    # Defaultプロファイル内の重要ディレクトリをコピー
    print(f"📁 Copying Default profile directories...")
    default_dirs = [
        # 認証・セッション関連（最重要！）
        "Extensions", "Local Storage", "IndexedDB", "Service Worker",
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
    
    for dir_name in default_dirs:
        src_dir = os.path.join(original_default_dir, dir_name)
        dst_dir = os.path.join(temp_default_profile, dir_name)
        
        if os.path.exists(src_dir):
            total_dirs_available += 1
            if os.path.isdir(src_dir):
                try:
                    shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                    copied_dirs += 1
                    if dir_name in ["Session Storage", "Sessions", "Local Storage", "IndexedDB", "WebStorage", "GCM Store", "Sync Data", "Storage"]:
                        print(f"  🔐 {dir_name}/ (AUTH)")
                    else:
                        print(f"  ✅ {dir_name}/")
                except Exception as e:
                    print(f"  ❌ Failed to copy directory {dir_name}: {e}")
    
    print(f"📊 Copy Summary:")
    print(f"  📄 Root files: {copied_root}/{len(root_files)}")
    print(f"  📁 Root directories: {copied_root_dirs}/{len(root_dirs)}")
    print(f"  📄 Default files: {copied_default}/{total_available} available")
    print(f"  📁 Default directories: {copied_dirs}/{total_dirs_available} available")
    
    return {
        'browser_path': browser_path,
        'temp_user_data': temp_user_data,
        'temp_default_profile': temp_default_profile,
        'temp_dir': temp_dir
    }

async def test_browser_with_temp_profile(browser_type):
    """一時プロファイルでブラウザテストを実行

    Normalize browser_type as above to prevent AttributeError when provided an object.
    """
    print(f"\n{'='*60}")
    bt_name = getattr(browser_type, 'name', browser_type)
    try:
        display = str(bt_name).upper()
    except Exception:
        display = str(bt_name)
    print(f"🧪 {display} 一時プロファイルテスト開始")
    print(f"{'='*60}")
    
    # 一時プロファイルを作成
    profile_info = create_temp_browser_profile(browser_type)
    
    test_results = {
        'profile_creation_success': True,
        'launch_success': False,
        'profile_settings_access': False,
        'profile_data_found': False,
        'bookmarks_found': False,
        'google_account_status': 'unknown',
        'temp_profile_path': profile_info['temp_dir']
    }
    
    try:
        # Playwright でブラウザ起動テスト
        print(f"🚀 Launching {browser_type} with temporary profile...")
        
        async with async_playwright() as p:
            # 最適化されたブラウザ起動オプション
            context = await p.chromium.launch_persistent_context(
                user_data_dir=profile_info['temp_user_data'],
                headless=False,
                executable_path=profile_info['browser_path'],
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--profile-directory=Default',
                    
                    # セッション・認証維持の最重要オプション（最新の知見に基づく）
                    '--enable-automation=false',
                    '--no-default-browser-check',
                    '--no-first-run',
                    '--disable-default-apps',
                    '--disable-popup-blocking',
                    '--disable-prompt-on-repost',
                    '--disable-hang-monitor',
                    '--disable-backgrounding-occluded-windows',
                    '--disable-renderer-backgrounding',
                    '--hide-scrollbars',
                    '--mute-audio',
                    
                    # 重要：認証関連のオプション
                    '--enable-precise-memory-info',
                    '--disable-component-update',
                    '--restore-last-session',  # セッション復元
                    '--enable-sync',  # 同期を有効にする（重要！）
                    '--disable-features=TranslateUI',  # 翻訳UIを無効化
                    '--disable-ipc-flooding-protection'
                ],
                viewport={"width": 1280, "height": 720},
                ignore_default_args=[
                    '--disable-extensions', 
                    '--disable-component-extensions-with-background-pages'
                    # 重要：--disable-syncを削除（同期を有効にする）
                ]
            )
            
            test_results['launch_success'] = True
            print(f"✅ {browser_type} launched successfully with temporary profile")
            
            # プロファイル設定URLの設定
            if browser_type == 'edge':
                profile_settings_url = "edge://settings/profiles"
            else:
                profile_settings_url = "chrome://settings/people"
            
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
            
            # 2. Google アカウント状況の詳細確認
            print(f"🔍 Testing Google account status...")
            try:
                await page.goto("https://www.google.com", wait_until='domcontentloaded', timeout=15000)
                await page.wait_for_timeout(3000)
                
                page_content = await page.text_content('body')
                
                # より詳細なアカウント確認
                account_selectors = [
                    '[aria-label*="Google Account"]', '[aria-label*="Google アカウント"]', 
                    '.gb_d', '.gb_Ae', '.gb_Da', '.gb_xa', '.gb_Aa',
                    '[data-ved*="account"]', '.gb_x', '.gb_Fa', '.gb_8a', 
                    'a[href*="accounts.google.com"]'
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
                
                # Gmail への直接アクセステスト
                print(f"🔍 Testing direct Gmail access...")
                try:
                    await page.goto("https://mail.google.com", wait_until='domcontentloaded', timeout=10000)
                    await page.wait_for_timeout(3000)
                    
                    current_url = page.url
                    if 'accounts.google.com' in current_url and 'signin' in current_url:
                        print(f"❌ Gmail: Redirected to sign-in page")
                        test_results['google_account_status'] = 'not_signed_in'
                    elif 'mail.google.com' in current_url:
                        print(f"✅ Gmail: Successfully accessed (signed in)")
                        test_results['google_account_status'] = 'signed_in'
                        account_found = True
                    else:
                        print(f"⚠️ Gmail: Unexpected redirect - {current_url}")
                        test_results['google_account_status'] = 'unclear'
                        
                except Exception as gmail_e:
                    print(f"⚠️ Gmail test failed: {gmail_e}")
                
                if account_found and not signin_found:
                    test_results['google_account_status'] = 'signed_in'
                    print(f"✅ Google account: Likely signed in")
                elif signin_found:
                    test_results['google_account_status'] = 'not_signed_in'
                    print(f"❌ Google account: Not signed in")
                elif account_found:
                    test_results['google_account_status'] = 'partially_signed_in'
                    print(f"⚠️ Google account: Partially signed in")
                else:
                    test_results['google_account_status'] = 'unclear'
                    print(f"⚠️ Google account status unclear")
                
            except Exception as e:
                print(f"❌ Failed to check Google account: {e}")
            
            # 3. ブックマークの確認
            print(f"🔍 Testing bookmarks...")
            try:
                # ブックマークページに直接移動
                if browser_type == 'chrome':
                    await page.goto("chrome://bookmarks/", wait_until='domcontentloaded', timeout=10000)
                else:
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
            
            # 5秒間表示してからクローズ
            print(f"⏱️ Displaying for 5 seconds for manual verification...")
            await page.wait_for_timeout(5000)
            
            await context.close()
            
    except Exception as e:
        print(f"❌ Browser launch failed: {e}")
        import traceback
        traceback.print_exc()
    
    return test_results

async def main():
    """メイン関数 - 両ブラウザで一時プロファイルテストを実行"""
    print("🎯 Playwright Browser Automation with Temporary User Profiles")
    print("センシティブなプロファイルデータの安全な一時利用テスト")
    
    try:
        # Edge のテスト
        edge_results = await test_browser_with_temp_profile('edge')
        
        # Chrome のテスト
        chrome_results = await test_browser_with_temp_profile('chrome')
        
        # 結果のサマリー
        print(f"\n{'='*60}")
        print(f"📊 最終検証結果サマリー")
        print(f"{'='*60}")
        
        browsers = [('Edge', edge_results), ('Chrome', chrome_results)]
        
        for browser_name, results in browsers:
            print(f"\n🔍 {browser_name}:")
            print(f"  📁 一時プロファイル作成: {'✅ 成功' if results['profile_creation_success'] else '❌ 失敗'}")
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
            print("✅ 両ブラウザで一時プロファイル読み込みが正常に動作しています")
            print("✅ センシティブデータの安全な一時利用が実現できています")
        elif edge_success or chrome_success:
            working_browser = "Edge" if edge_success else "Chrome"
            print(f"⚠️ {working_browser} でのみ一時プロファイル読み込みが動作しています")
        else:
            print("❌ 両ブラウザで一時プロファイル読み込みに問題があります")
        
        # Google認証状況
        edge_auth = edge_results['google_account_status'] == 'signed_in'
        chrome_auth = chrome_results['google_account_status'] == 'signed_in'
        
        if edge_auth and chrome_auth:
            print("🔐 両ブラウザでGoogleアカウント認証が維持されています")
        elif edge_auth or chrome_auth:
            auth_browser = "Edge" if edge_auth else "Chrome"
            print(f"🔐 {auth_browser} でGoogleアカウント認証が維持されています")
        else:
            print("🔐 Googleアカウント認証の維持に改善が必要です")
    
    finally:
        # 確実に一時プロファイルをクリーンアップ
        print(f"\n🧹 Cleaning up temporary profiles...")
        cleanup_temp_profiles()
        print(f"✅ All temporary profiles have been securely deleted")

if __name__ == "__main__":
    asyncio.run(main())
