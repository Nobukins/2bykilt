# search_script.py 
import pytest
from playwright.async_api import async_playwright, Page, expect
import asyncio
import os
import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 録画パスユーティリティをインポート
try:
    from src.utils.recording_path_utils import get_recording_path
except ImportError:
    # フォールバック: 基本的な録画パス設定
    def get_recording_path(fallback_relative_path="./tmp/record_videos"):
        import platform
        recording_dir = os.environ.get("RECORDING_PATH", "").strip()
        if not recording_dir:
            if platform.system() == "Windows":
                recording_dir = os.path.join(os.path.expanduser("~"), "Documents", "2bykilt", "recordings")
            else:
                recording_dir = fallback_relative_path
        try:
            os.makedirs(recording_dir, exist_ok=True)
            return recording_dir
        except Exception:
            import tempfile
            return tempfile.gettempdir()

pytest_plugins = ["pytest_asyncio"]  # Add this line to enable async test support

async def show_countdown_overlay(page, seconds=5):
    """
    ブラウザを閉じる前に画面いっぱいのカウントダウンオーバーレイを表示する
    """
    # JavaScriptでカウントダウンオーバーレイを作成して表示
    await page.evaluate(f"""() => {{
        // すでに存在するオーバーレイを削除
        const existingOverlay = document.getElementById('countdown-overlay');
        if (existingOverlay) existingOverlay.remove();
        
        // オーバーレイ要素を作成
        const overlay = document.createElement('div');
        overlay.id = 'countdown-overlay';
        overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.7);
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            z-index: 10000;
            color: white;
            font-family: Arial, sans-serif;
        `;
        
        // カウントダウン表示用の要素
        const counterDisplay = document.createElement('div');
        counterDisplay.style.cssText = `
            font-size: 120px;
            font-weight: bold;
        `;
        counterDisplay.textContent = '{seconds}';
        
        // 「自動操作中」のテキスト
        const statusText = document.createElement('div');
        statusText.style.cssText = `
            font-size: 36px;
            margin-top: 20px;
        `;
        statusText.textContent = '自動操作が完了します';
        
        // 要素を追加
        overlay.appendChild(counterDisplay);
        overlay.appendChild(statusText);
        document.body.appendChild(overlay);
    }}""")
    
    # カウントダウンを実行
    for i in range(seconds, -1, -1):
        await page.evaluate(f"""(count) => {{
            const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
            if (counterDisplay) counterDisplay.textContent = count;
        }}""", i)
        await page.wait_for_timeout(1000)  # 1秒待機
    
    # "closing..."のメッセージを表示
    await page.evaluate("""() => {
        const counterDisplay = document.querySelector('#countdown-overlay > div:first-child');
        const statusText = document.querySelector('#countdown-overlay > div:last-child');
        if (counterDisplay) counterDisplay.textContent = 'closing...';
        if (statusText) statusText.textContent = 'ブラウザを終了しています';
    }""")
    await page.wait_for_timeout(1000)  # 閉じる前に1秒待機

@pytest.mark.asyncio  # This mark will now be recognized
async def test_text_search(request) -> None:
    query = request.config.getoption("--query")
    slowmo = request.config.getoption("--slowmo", default=0)  # Use Playwright's standard --slowmo option
    browser_type = request.config.getoption("--browser-type")
    browser_executable = request.config.getoption("--browser-executable")
    use_profile = request.config.getoption("--use-profile")
    custom_profile_path = request.config.getoption("--profile-path")
    
    if not query:
        pytest.skip("No query provided. Use --query to specify a search term.")

    # 録画ディレクトリの設定（改良されたクロスプラットフォーム対応）
    recording_dir = get_recording_path("./tmp/record_videos")
    
    # 環境変数からブラウザ設定を取得（pytest引数が優先）
    if not browser_type:
        browser_type = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE') or os.environ.get('BYKILT_BROWSER_TYPE', 'chrome')
    
    # ブラウザタイプに応じて実行ファイルパスを設定
    if not browser_executable:
        if browser_type == 'edge':
            browser_executable = os.environ.get('EDGE_PATH') or "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        elif browser_type == 'chrome':
            browser_executable = os.environ.get('CHROME_PATH') or os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH') or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        else:
            browser_executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
    
    # ユーザープロファイル設定を取得
    chrome_user_data = custom_profile_path or os.environ.get('CHROME_USER_DATA')
    edge_user_data = custom_profile_path or os.environ.get('EDGE_USER_DATA')
    
    # プロファイル競合を回避するため、実際のプロファイルをコピーしてテスト用に使用
    if use_profile and not custom_profile_path:
        import shutil
        import tempfile
        
        # 実際のプロファイルディレクトリを取得
        original_chrome_profile = os.environ.get('CHROME_USER_DATA') or os.path.expanduser("~/Library/Application Support/Google/Chrome")
        original_edge_profile = os.environ.get('EDGE_USER_DATA') or os.path.expanduser("~/Library/Application Support/Microsoft Edge")
        
        print(f"🔍 Original Chrome profile path: {original_chrome_profile}")
        print(f"🔍 Original Edge profile path: {original_edge_profile}")
        print(f"🔍 Chrome profile exists: {os.path.exists(original_chrome_profile)}")
        print(f"🔍 Edge profile exists: {os.path.exists(original_edge_profile)}")
        
        # テストプロファイルディレクトリを作成
        test_profile_base = os.path.join(os.getcwd(), "tmp", "test_profiles")
        os.makedirs(test_profile_base, exist_ok=True)
        
        if browser_type == 'chrome' and os.path.exists(original_chrome_profile):
            print(f"🔧 Setting up Chrome test profile with new method...")
            
            # 新しい作法：Chrome User Data ディレクトリ内に SeleniumProfile を作成
            chrome_test_profile = os.path.join(original_chrome_profile, "SeleniumProfile")
            
            print(f"📁 Chrome User Data directory: {original_chrome_profile}")
            print(f"📁 New Chrome test profile: {chrome_test_profile}")
            
            # 既存のテストプロファイルがあれば削除
            if os.path.exists(chrome_test_profile):
                print(f"🗑️ Removing existing Chrome test profile: {chrome_test_profile}")
                shutil.rmtree(chrome_test_profile, ignore_errors=True)
            
            # 新しいテストプロファイルディレクトリを作成
            os.makedirs(chrome_test_profile, exist_ok=True)
            
            # Defaultプロファイル用のディレクトリを作成
            default_profile_dir = os.path.join(chrome_test_profile, "Default")
            os.makedirs(default_profile_dir, exist_ok=True)
            print(f"📁 Created Chrome test profile directory: {chrome_test_profile}")

            try:
                # 重要なプロファイルファイルをコピー（新しい作法対応）
                # ルートレベルのファイル（テストプロファイルのルートにコピー）
                root_files = [
                    "Local State",
                    "First Run"
                ]
                
                # Defaultプロファイル内のファイル（Default/以下にコピー）
                default_files = [
                    "Preferences",
                    "Secure Preferences", 
                    "Login Data",
                    "Web Data",
                    "History",
                    "Bookmarks",
                    "Cookies",
                    "Favicons",
                    "Top Sites",
                    "Sessions",
                    "Current Session",
                    "Last Session",
                    "Current Tabs",
                    "Last Tabs",
                    "Extension Cookies",
                    "Extension State",
                    "Shortcuts",
                    "Visited Links", 
                    "Network Action Predictor",
                    "TransportSecurity",
                    "AutofillStrikeDatabase",
                    "Download Service",
                    "Login Data For Account",
                    "Platform Notifications", 
                    "Sync Data",
                    "Zero Suggest",
                    "heavy_ad_intervention_opt_out.db",
                    "persisted_state.pb",
                ]
                
                # Defaultプロファイル内のディレクトリ（Default/以下にコピー）
                default_dirs = [
                    "Extensions",
                    "Extension Rules",
                    "Extension State",
                    "Extensions Temp",
                    "Local Storage",
                    "Session Storage", 
                    "IndexedDB",
                    "databases",
                    "File System",
                    "Local Extension Settings",
                    "Sync Extension Settings",
                    "Service Worker",
                    "Platform Notifications",
                    "storage",
                    "blob_storage",
                    "Download Service",
                    "shared_proto_db",
                    "optimization_guide_model_store",
                ]
                
                copied_files = 0
                skipped_files = 0
                
                # ルートレベルのファイルをコピー
                for file_name in root_files:
                    src_file = os.path.join(original_chrome_profile, file_name)
                    dst_file = os.path.join(chrome_test_profile, file_name)
                    
                    if os.path.exists(src_file) and os.path.isfile(src_file):
                        try:
                            shutil.copy2(src_file, dst_file)
                            print(f"📄 Copied Chrome root file: {file_name}")
                            copied_files += 1
                        except Exception as e:
                            print(f"⚠️ Failed to copy Chrome root file {file_name}: {e}")
                            skipped_files += 1
                    else:
                        print(f"⚠️ Chrome root file not found: {file_name}")
                        skipped_files += 1
                
                # Defaultプロファイル内のファイルをコピー
                original_default_dir = os.path.join(original_chrome_profile, "Default")
                for file_name in default_files:
                    src_file = os.path.join(original_default_dir, file_name)
                    dst_file = os.path.join(default_profile_dir, file_name)
                    
                    if os.path.exists(src_file) and os.path.isfile(src_file):
                        try:
                            shutil.copy2(src_file, dst_file)
                            print(f"📄 Copied Chrome Default file: {file_name}")
                            copied_files += 1
                        except Exception as e:
                            print(f"⚠️ Failed to copy Chrome Default file {file_name}: {e}")
                            skipped_files += 1
                    else:
                        print(f"⚠️ Chrome Default file not found: {file_name}")
                        skipped_files += 1
                
                # Defaultプロファイル内のディレクトリをコピー
                copied_dirs = 0
                skipped_dirs = 0
                for dir_name in default_dirs:
                    src_dir = os.path.join(original_default_dir, dir_name)
                    dst_dir = os.path.join(default_profile_dir, dir_name)
                    
                    if os.path.exists(src_dir) and os.path.isdir(src_dir):
                        try:
                            shutil.copytree(src_dir, dst_dir, dirs_exist_ok=True)
                            print(f"📁 Copied Chrome Default directory: {dir_name}")
                            copied_dirs += 1
                        except Exception as e:
                            print(f"⚠️ Failed to copy Chrome Default directory {dir_name}: {e}")
                            skipped_dirs += 1
                    else:
                        print(f"⚠️ Chrome Default directory not found: {dir_name}")
                        skipped_dirs += 1
                
                print(f"✅ Chrome profile copy summary (new method):")
                print(f"   📄 Files copied: {copied_files}")
                print(f"   📄 Files skipped: {skipped_files}")  
                print(f"   📁 Directories copied: {copied_dirs}")
                print(f"   📁 Directories skipped: {skipped_dirs}")
                
                chrome_user_data = chrome_test_profile
                print(f"✅ Created Chrome test profile with new method: {chrome_test_profile}")
                
            except Exception as e:
                print(f"⚠️ Failed to copy Chrome profile: {e}")
                # フォールバックとして空のプロファイルを使用
                chrome_user_data = chrome_test_profile
                
        elif browser_type == 'edge' and os.path.exists(original_edge_profile):
            print(f"🔧 Setting up Edge test profile with new method...")
            
            # 新しい作法：Edge User Data ディレクトリ内に SeleniumProfile を作成
            edge_test_profile = os.path.join(original_edge_profile, "SeleniumProfile")
            
            print(f"📁 Edge User Data directory: {original_edge_profile}")
            print(f"📁 New Edge test profile: {edge_test_profile}")
            
            # 既存のテストプロファイルがあれば削除
            if os.path.exists(edge_test_profile):
                print(f"🗑️ Removing existing Edge test profile: {edge_test_profile}")
                shutil.rmtree(edge_test_profile, ignore_errors=True)
            
            # 新しいテストプロファイルディレクトリを作成
            os.makedirs(edge_test_profile, exist_ok=True)
            
            # Defaultプロファイル用のディレクトリを作成
            default_profile_dir = os.path.join(edge_test_profile, "Default")
            os.makedirs(default_profile_dir, exist_ok=True)
            print(f"📁 Created Edge test profile directory: {edge_test_profile}")

            try:
                # 重要なプロファイルファイルをコピー（新しい作法対応 - Google アカウント情報を含む）
                # ルートレベルのファイル（テストプロファイルのルートにコピー）
                root_files = [
                    "Local State",
                    "First Run"
                ]
                
                # Defaultプロファイル内のファイル（Default/以下にコピー）
                default_files = [
                    "Preferences",
                    "Secure Preferences", 
                    "Login Data", 
                    "Login Data For Account",
                    "Web Data",
                    "History",
                    "Bookmarks",
                    "Cookies",
                    "Favicons",
                    "Top Sites",
                    "Sessions",
                    "Current Session",
                    "Last Session",
                    "Current Tabs",
                    "Last Tabs",
                    "Session Storage",
                    "Sync Data",
                    "Sync Extension Settings",
                    "GCM Store",
                    "GCMSTORE",
                    "Extensions",
                    "Extension Cookies",
                    "Extension State",
                    "Local Extension Settings",
                    "Network Action Predictor",
                    "TransportSecurity",
                    "Platform Notifications", 
                    "AutofillStrikeDatabase",
                    "shared_proto_db",
                    "optimization_guide_model_store",
                    "Download Service",
                    "Visited Links",
                    "Shortcuts",
                    "Zero Suggest",
                    "heavy_ad_intervention_opt_out.db",
                    "persisted_state.pb",
                ]
                
                # Defaultプロファイル内のディレクトリ（Default/以下にコピー）
                default_dirs = [
                    "Extensions",
                    "Extension Rules",
                    "Extension State",
                    "Extensions Temp",
                    "Local Storage",
                    "Session Storage", 
                    "IndexedDB",
                    "databases",
                    "File System",
                    "Local Extension Settings",
                    "Sync Extension Settings",
                    "Service Worker",
                    "Platform Notifications",
                    "storage",
                    "blob_storage",
                    "Download Service",
                    "shared_proto_db",
                    "optimization_guide_model_store",
                ]
                
                copied_files = 0
                skipped_files = 0
                
                # ルートレベルのファイルをコピー
                for file_name in root_files:
                    src_file = os.path.join(original_edge_profile, file_name)
                    dst_file = os.path.join(edge_test_profile, file_name)
                    
                    if os.path.exists(src_file) and os.path.isfile(src_file):
                        try:
                            shutil.copy2(src_file, dst_file)
                            print(f"📄 Copied Edge root file: {file_name}")
                            copied_files += 1
                        except Exception as e:
                            print(f"⚠️ Failed to copy Edge root file {file_name}: {e}")
                            skipped_files += 1
                    else:
                        print(f"⚠️ Edge root file not found: {file_name}")
                        skipped_files += 1
                
                # Defaultプロファイル内のファイルをコピー
                original_default_dir = os.path.join(original_edge_profile, "Default")
                for file_name in default_files:
                    src_file = os.path.join(original_default_dir, file_name)
                    dst_file = os.path.join(default_profile_dir, file_name)
                    
                    if os.path.exists(src_file) and os.path.isfile(src_file):
                        try:
                            shutil.copy2(src_file, dst_file)
                            print(f"📄 Copied Edge Default file: {file_name}")
                            copied_files += 1
                        except Exception as e:
                            print(f"⚠️ Failed to copy Edge Default file {file_name}: {e}")
                            skipped_files += 1
                    else:
                        print(f"⚠️ Edge Default file not found: {file_name}")
                        skipped_files += 1
                
                # Defaultプロファイル内のディレクトリをコピー
                copied_dirs = 0
                skipped_dirs = 0
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
                            skipped_dirs += 1
                    else:
                        print(f"⚠️ Edge Default directory not found: {dir_name}")
                        skipped_dirs += 1
                
                print(f"✅ Edge profile copy summary (new method):")
                print(f"   📄 Files copied: {copied_files}")
                print(f"   📄 Files skipped: {skipped_files}")  
                print(f"   📁 Directories copied: {copied_dirs}")
                print(f"   📁 Directories skipped: {skipped_dirs}")
                
                edge_user_data = edge_test_profile
                print(f"✅ Created Edge test profile with new method: {edge_test_profile}")
                
            except Exception as e:
                print(f"❌ Failed to copy Edge profile: {e}")
                # フォールバックとして空のプロファイルを使用
                edge_user_data = edge_test_profile
        else:
            if browser_type == 'edge':
                print(f"⚠️ Original Edge profile not found at: {original_edge_profile}")
                # 新しい作法で空のテストプロファイルを作成
                edge_user_data_base = os.environ.get('EDGE_USER_DATA', '')
                edge_test_profile = os.path.join(edge_user_data_base, "SeleniumProfile")
                os.makedirs(os.path.join(edge_test_profile, "Default"), exist_ok=True)
                edge_user_data = edge_test_profile
                print(f"📁 Created empty Edge profile with new method: {edge_test_profile}")
            elif browser_type == 'chrome':
                print(f"⚠️ Original Chrome profile not found at: {original_chrome_profile}")
                # 新しい作法で空のテストプロファイルを作成
                chrome_user_data_base = os.environ.get('CHROME_USER_DATA', '')
                chrome_test_profile = os.path.join(chrome_user_data_base, "SeleniumProfile")
                os.makedirs(os.path.join(chrome_test_profile, "Default"), exist_ok=True)
                chrome_user_data = chrome_test_profile
                print(f"📁 Created empty Chrome profile with new method: {chrome_test_profile}")
    
    print(f"🔍 Using browser type: {browser_type}")
    print(f"🔍 Use profile: {use_profile}")
    if browser_executable:
        print(f"🔍 Using browser executable: {browser_executable}")
    if browser_type == 'chrome' and chrome_user_data and use_profile:
        print(f"🔍 Using Chrome user profile: {chrome_user_data}")
    elif browser_type == 'edge' and edge_user_data and use_profile:
        print(f"🔍 Using Edge user profile: {edge_user_data}")
    
    async with async_playwright() as p:
        # ブラウザタイプに応じた起動
        if browser_type == 'chrome' and browser_executable:
            # ChromeまたはChromium（独自のパス）
            chrome_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--window-position=50,50',
                '--window-size=1280,720',
                '--disable-blink-features=AutomationControlled',  # 自動化検出を回避
                '--disable-extensions-except=',  # 拡張機能を無効化（ただしユーザープロファイルの場合は一部許可）
                '--disable-default-apps'
            ]
            
            # ユーザープロファイルを使用する場合は launch_persistent_context を使用
            if chrome_user_data and os.path.exists(chrome_user_data) and use_profile:
                print(f"✅ Using Chrome user profile: {chrome_user_data}")
                try:
                    print("🔧 Attempting to launch persistent context...")
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=chrome_user_data,
                        headless=False,
                        slow_mo=slowmo,
                        args=chrome_args + [
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-features=TranslateUI',
                            '--no-first-run',
                            '--disable-background-networking',
                            '--force-new-profile-instance',  # 新しいプロファイルインスタンスを強制
                            '--enable-profile-shortcut-manager',  # プロファイル管理を有効化
                            '--disable-sync',  # 同期を無効化してローカルプロファイルを使用
                            '--profile-directory=Default'  # Defaultプロファイルを明示的に指定
                        ],
                        executable_path=browser_executable,
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720},
                        viewport={"width": 1280, "height": 720},
                        ignore_default_args=['--disable-extensions', '--disable-component-extensions-with-background-pages'],  # 拡張機能を有効化
                    )
                    print("✅ Persistent context launched successfully")
                    
                    # 初期状態をログ出力
                    existing_pages = context.pages
                    print(f"📄 Found {len(existing_pages)} existing pages")
                    for i, existing_page in enumerate(existing_pages):
                        try:
                            url = existing_page.url
                            print(f"📄 Page {i}: {url}")
                            # about:blankページは閉じる
                            if url == 'about:blank' or url.startswith('about:'):
                                print(f"🗑️ Closing about:blank page {i}")
                                await existing_page.close()
                            else:
                                print(f"📄 Keeping non-blank page {i}: {url}")
                        except Exception as e:
                            print(f"❌ Error handling existing page {i}: {e}")
                    
                    # 新しいページを作成
                    print("🔧 Creating new page...")
                    page = await context.new_page()
                    print(f"✅ Created new page: {page.url}")
                    browser = None  # persistent contextの場合、browserオブジェクトは使用しない
                    print(f"✅ Launched Chrome with user profile")
                except Exception as e:
                    print(f"❌ Failed to launch with user profile: {e}")
                    print("🔄 Falling back to launch without profile")
                    # フォールバック: プロファイルなしで起動
                    launch_options = {
                        'headless': False, 
                        'slow_mo': slowmo, 
                        'args': chrome_args,
                        'executable_path': browser_executable
                    }
                    browser = await p.chromium.launch(**launch_options)
                    context = await browser.new_context(
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720}
                    )
                    page = await context.new_page()
                    print(f"✅ Launched Chrome without user profile (fallback)")
            else:
                # プロファイルなしの場合は通常のlaunchを使用
                launch_options = {
                    'headless': False, 
                    'slow_mo': slowmo, 
                    'args': chrome_args,
                    'executable_path': browser_executable
                }
                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    record_video_dir=recording_dir,
                    record_video_size={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                print(f"✅ Launched Chrome without user profile")
            
        elif browser_type == 'edge' and browser_executable:
            # Microsoft Edge
            edge_args = [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--window-position=50,50',
                '--window-size=1280,720',
                '--disable-blink-features=AutomationControlled',  # 自動化検出を回避
                '--disable-default-apps'
            ]
            
            # ユーザープロファイルを使用する場合は launch_persistent_context を使用
            if edge_user_data and os.path.exists(edge_user_data) and use_profile:
                print(f"✅ Using Edge user profile: {edge_user_data}")
                try:
                    print("🔧 Attempting to launch Edge persistent context...")
                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=edge_user_data,
                        headless=False,
                        slow_mo=slowmo,
                        args=edge_args + [
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--disable-features=TranslateUI',
                            '--no-first-run',
                            '--disable-background-networking',
                            '--force-new-profile-instance',  # 新しいプロファイルインスタンスを強制
                            '--enable-profile-shortcut-manager',  # プロファイル管理を有効化
                            '--disable-sync',  # 同期を無効化してローカルプロファイルを使用
                            '--profile-directory=Default'  # Defaultプロファイルを明示的に指定
                        ],
                        executable_path=browser_executable,
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720},
                        viewport={"width": 1280, "height": 720},
                        ignore_default_args=['--disable-extensions', '--disable-component-extensions-with-background-pages'],  # 拡張機能を有効化
                    )
                    print("✅ Edge persistent context launched successfully")
                    
                    # 初期状態をログ出力
                    existing_pages = context.pages
                    print(f"📄 Found {len(existing_pages)} existing pages")
                    for i, existing_page in enumerate(existing_pages):
                        try:
                            url = existing_page.url
                            print(f"📄 Page {i}: {url}")
                            # about:blankページは閉じる
                            if url == 'about:blank' or url.startswith('about:'):
                                print(f"🗑️ Closing about:blank page {i}")
                                await existing_page.close()
                            else:
                                print(f"📄 Keeping non-blank page {i}: {url}")
                        except Exception as e:
                            print(f"❌ Error handling existing page {i}: {e}")
                    
                    # 新しいページを作成
                    print("🔧 Creating new page...")
                    page = await context.new_page()
                    print(f"✅ Created new page: {page.url}")
                    browser = None  # persistent contextの場合、browserオブジェクトは使用しない
                    print(f"✅ Launched Edge with user profile")
                except Exception as e:
                    print(f"❌ Failed to launch with user profile: {e}")
                    print("🔄 Falling back to launch without profile")
                    # フォールバック: プロファイルなしで起動
                    launch_options = {
                        'headless': False, 
                        'slow_mo': slowmo, 
                        'args': edge_args,
                        'executable_path': browser_executable
                    }
                    browser = await p.chromium.launch(**launch_options)
                    context = await browser.new_context(
                        record_video_dir=recording_dir,
                        record_video_size={"width": 1280, "height": 720}
                    )
                    page = await context.new_page()
                    print(f"✅ Launched Edge without user profile (fallback)")
            else:
                # プロファイルなしの場合は通常のlaunchを使用
                launch_options = {
                    'headless': False, 
                    'slow_mo': slowmo, 
                    'args': edge_args,
                    'executable_path': browser_executable
                }
                browser = await p.chromium.launch(**launch_options)
                context = await browser.new_context(
                    record_video_dir=recording_dir,
                    record_video_size={"width": 1280, "height": 720}
                )
                page = await context.new_page()
                print(f"✅ Launched Edge without user profile")
        elif browser_type == 'firefox':
            # Firefox
            launch_options = {
                'headless': False, 
                'slow_mo': slowmo, 
                'args': ['--width=1280', '--height=720']
            }
            browser = await p.firefox.launch(**launch_options)
            context = await browser.new_context(
                record_video_dir=recording_dir,
                record_video_size={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            print(f"✅ Launched Firefox")
        elif browser_type == 'webkit':
            # WebKit (Safari)
            launch_options = {
                'headless': False, 
                'slow_mo': slowmo
            }
            browser = await p.webkit.launch(**launch_options)
            context = await browser.new_context(
                record_video_dir=recording_dir,
                record_video_size={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            print(f"✅ Launched WebKit (Safari)")
        else:
            # デフォルト：Chromium
            default_launch_options = {
                'headless': False, 
                'slow_mo': slowmo, 
                'args': [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--window-position=50,50',
                    '--window-size=1280,720'
                ]
            }
            browser = await p.chromium.launch(**default_launch_options)
            context = await browser.new_context(
                record_video_dir=recording_dir,
                record_video_size={"width": 1280, "height": 720}
            )
            page = await context.new_page()
            print(f"✅ Launched default Chromium")
        
        # ページが完全に初期化されるまで待機
        print(f"🔍 Initial page URL: {page.url}")
        if page.url == 'about:blank':
            print("⚠️ Page is still about:blank, attempting to navigate...")
            try:
                # about:blankから脱出するため、まず簡単なページに移動
                await page.goto("data:text/html,<html><body><h1>Ready for automation</h1></body></html>")
                await page.wait_for_timeout(1000)
                print("✅ Successfully navigated away from about:blank")
            except Exception as e:
                print(f"❌ Failed to navigate from about:blank: {e}")
        
        await page.wait_for_timeout(3000)
        print("🔍 Page initialized, preparing automation overlay...")
        
        # 開始時に自動操作中であることを示すオーバーレイを表示
        await page.evaluate("""() => {
            const overlay = document.createElement('div');
            overlay.id = 'automation-indicator';
            overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;'+
                'background:rgba(76,175,80,0.8);padding:10px;text-align:center;'+
                'font-weight:bold;color:white;font-size:18px;';
            overlay.textContent = '🤖 自動操作中 - テスト実行中です';
            document.body.appendChild(overlay);
            
            // ウィンドウにフォーカスを強制
            window.focus();
        }""")

        # ページが読み込まれるまで少し待機
        await page.wait_for_timeout(2000)
        print("🔍 Page ready, starting navigation...")

        # プロファイル読み込み状況をチェック（プロファイル使用時のみ）
        if use_profile:
            print("🔍 Checking profile loading status...")
            await check_profile_status(page, browser_type)
            print("✅ Profile check completed, continuing with test...")

        # nogtips検索処理
        await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=30000)
        await page.get_by_role("button", name="閉じて承認").click()
        await page.get_by_role("link", name="nogtips").click()
        await page.get_by_role("heading", name="LLMs.txtについて").get_by_role("link").click()
        await page.get_by_role("searchbox", name="検索:").click()
        await page.get_by_role("searchbox", name="検索:").fill(query)
        await page.get_by_role("searchbox", name="検索:").press("Enter")

        await page.wait_for_timeout(5000)  # 検索結果を少し表示

        # ブラウザを閉じる前にカウントダウン表示
        await show_countdown_overlay(page, 5)  # 5秒カウントダウン

        await context.close()
        if browser:
            await browser.close()

@pytest.mark.asyncio
async def test_nogtips_simple(request) -> None:
    """シンプルなnogtips検索テスト関数（779-785行目のスタイルを採用）"""
    query = request.config.getoption("--query")
    slowmo = request.config.getoption("--slowmo", default=0)
    
    if not query:
        pytest.skip("No query provided. Use --query to specify a search term.")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, 
            slow_mo=slowmo, 
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context()
        page = await context.new_page()
        
        try:
            # nogtips.wordpress.comにアクセス（779行目のスタイル）
            await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=30000)
            
            # 検索ボックスを操作（779-785行目のシンプルなスタイル）
            # await page.get_by_role("button", name="閉じて承認").click()
            await page.get_by_role("link", name="nogtips").click()
            await page.get_by_role("heading", name="LLMs.txtについて").get_by_role("link").click()
            await page.get_by_role("searchbox", name="検索:").click()
            await page.get_by_role("searchbox", name="検索:").fill(query)
            await page.get_by_role("searchbox", name="検索:").press("Enter")
            
            # 結果を表示
            await page.wait_for_timeout(5000)
            
        except Exception as e:
            print(f"❌ nogtips search failed: {e}")
            raise
        
        finally:
            await context.close()
            await browser.close()

async def test_nogtips_search(request) -> None:
    """nogtips.wordpress.com検索テスト関数"""
    query = request.config.getoption("--query")
    slowmo = request.config.getoption("--slowmo", default=0)
    browser_type = request.config.getoption("--browser-type")
    browser_executable = request.config.getoption("--browser-executable")
    use_profile = request.config.getoption("--use-profile")
    custom_profile_path = request.config.getoption("--profile-path")
    
    if not query:
        pytest.skip("No query provided. Use --query to specify a search term.")

    # 録画ディレクトリの設定
    recording_dir = get_recording_path("./tmp/record_videos")
    
    # 環境変数からブラウザ設定を取得
    if not browser_type:
        browser_type = os.environ.get('BYKILT_OVERRIDE_BROWSER_TYPE') or os.environ.get('BYKILT_BROWSER_TYPE', 'chrome')
    
    # ブラウザタイプに応じて実行ファイルパスを設定
    if not browser_executable:
        if browser_type == 'edge':
            browser_executable = os.environ.get('EDGE_PATH') or "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"
        elif browser_type == 'chrome':
            browser_executable = os.environ.get('CHROME_PATH') or os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH') or "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        else:
            browser_executable = os.environ.get('PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH')
    
    # ユーザープロファイル設定を取得
    chrome_user_data = custom_profile_path or os.environ.get('CHROME_USER_DATA')
    edge_user_data = custom_profile_path or os.environ.get('EDGE_USER_DATA')
    
    print(f"🔍 Using browser type: {browser_type}")
    print(f"🔍 Use profile: {use_profile}")
    print(f"🔍 nogtips.wordpress.com search query: {query}")
    
    async with async_playwright() as p:
        # ブラウザ起動設定
        launch_options = {
            'headless': False, 
            'slow_mo': slowmo, 
            'args': [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--window-position=50,50',
                '--window-size=1280,720',
                '--disable-blink-features=AutomationControlled'
            ]
        }
        
        if browser_type == 'chrome' and browser_executable:
            browser = await p.chromium.launch(**launch_options, executable_path=browser_executable)
        elif browser_type == 'edge' and browser_executable:
            browser = await p.chromium.launch(**launch_options, executable_path=browser_executable)
        else:
            browser = await p.chromium.launch(**launch_options)
        
        context = await browser.new_context(
            record_video_dir=recording_dir,
            record_video_size={"width": 1280, "height": 720}
        )
        page = await context.new_page()
        
        try:
            # nogtips.wordpress.comにアクセス
            print("🔍 Navigating to nogtips.wordpress.com...")
            await page.goto("https://nogtips.wordpress.com", wait_until='domcontentloaded', timeout=60000)
            
            # 自動操作中であることを示すオーバーレイを表示
            await page.evaluate("""() => {
                const overlay = document.createElement('div');
                overlay.id = 'automation-indicator';
                overlay.style.cssText = 'position:fixed;top:0;left:0;right:0;z-index:9999;'+
                    'background:rgba(0,119,181,0.8);padding:10px;text-align:center;'+
                    'font-weight:bold;color:white;font-size:18px;';
                overlay.textContent = '🤖 nogtips.wordpress.com検索テスト実行中';
                document.body.appendChild(overlay);
            }""")
            
            await page.wait_for_timeout(3000)
            
            # 検索ボックスを探して入力（nogtipsスタイルで安定した操作）
            print(f"🔍 Searching for: {query}")
            
            # nogtips.wordpress.comの検索ボックスを操作（安定したスタイルを採用）
            print("🔎 Finding nogtips.wordpress.com search box...")
            
            # 複数のセレクタで検索ボックスを探す
            search_selectors = [
                'input[type="search"]',
                'input[name="q"]',
                'input[name="query"]',
                'input[name="search"]',
                'input[placeholder*="検索" i]',
                'input[placeholder*="search" i]',
                '.search-input',
                '.search-box input',
                '#search-input',
                '#search-box input'
            ]
            
            search_box = None
            for selector in search_selectors:
                try:
                    search_box = await page.query_selector(selector)
                    if search_box:
                        print(f"✅ Found search box with selector: {selector}")
                        break
                except:
                    continue
            
            if not search_box:
                # フォールバックとしてrole="searchbox"を使用
                try:
                    search_box = await page.get_by_role("searchbox").first
                    print("✅ Found search box with role='searchbox'")
                except:
                    pass
            
            if not search_box:
                print("❌ Could not find search box on nogtips.wordpress.com")
                # ページのスクリーンショットを撮ってデバッグ
                await page.screenshot(path=os.path.join(recording_dir, "nogtips_no_search_box.png"))
                raise Exception("Search box not found on nogtips.wordpress.com")
            
            print("� Clicking search box...")
            await search_box.click()
            
            print(f"⌨️ Filling search query: {query}")
            await search_box.fill(query)
            
            print("⏎ Pressing Enter...")
            await search_box.press("Enter")
            
            print("✅ Search query submitted")
            
            # 検索結果が表示されるまで待機
            await page.wait_for_timeout(5000)
            
            # 検索結果の確認
            try:
                # nogtips.wordpress.comの検索結果セレクタ（適宜調整）
                results_selectors = [
                    '.search-result',
                    '.result-item',
                    '.search-item',
                    '[data-testid*="result"]',
                    '.content-item',
                    'article',
                    '.post',
                    '.entry'
                ]
                
                results_count = 0
                for selector in results_selectors:
                    try:
                        elements = await page.query_selector_all(selector)
                        if elements:
                            results_count = len(elements)
                            print(f"📊 Found {results_count} search results with selector: {selector}")
                            break
                    except:
                        continue
                
                if results_count == 0:
                    print("📊 Could not count search results or no results found")
            except Exception as e:
                print(f"📊 Could not count search results: {e}")
            
            # 結果を表示するために少し待機
            await page.wait_for_timeout(3000)
            
            print("✅ nogtips.wordpress.com search test completed successfully")
            
        except Exception as e:
            print(f"❌ nogtips.wordpress.com search test failed: {e}")
            # エラーが発生してもスクリーンショットを撮る
            try:
                await page.screenshot(path=os.path.join(recording_dir, "nogtips_error.png"))
                print("📸 Error screenshot saved")
            except:
                pass
            raise
        
        finally:
            # ブラウザを閉じる前にカウントダウン表示
            await show_countdown_overlay(page, 3)
            
            await context.close()
            await browser.close()

async def edge_profile_verification():
    """Edge プロファイル検証用の関数（pytestの自動実行を防ぐため名前変更）"""
    # この関数は手動での検証専用です
    # 通常のテスト実行では呼び出されません
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--browser-type", default="chrome", choices=["chrome", "edge"])
    parser.add_argument("--use-profile", action="store_true")
    parser.add_argument("--profile-path", default="")
    parser.add_argument("--query", default="test edge profile")
    
    # pytest実行時の引数競合を回避するため、明示的に空のリストを渡す
    args = parser.parse_args([])
    
    # テスト用にEdgeの設定を強制
    args.browser_type = "edge"
    args.use_profile = True
    args.query = "test edge profile"
    
    # 環境変数を設定
    os.environ["BROWSER_TYPE"] = args.browser_type
    os.environ["USE_PROFILE"] = "true" if args.use_profile else "false"
    if args.profile_path:
        os.environ["PROFILE_PATH"] = args.profile_path
    
    print(f"🧪 Testing {args.browser_type} with profile={args.use_profile}")
    print(f"🔍 Query: {args.query}")
    
    # MockRequestオブジェクトを作成
    class MockRequest:
        def __init__(self):
            self.config = MockConfig()
    
    class MockConfig:
        def getoption(self, name, default=None):
            if name == "--browser-type":
                return args.browser_type
            elif name == "--use-profile":
                return args.use_profile
            elif name == "--profile-path":
                return args.profile_path
            elif name == "--query":
                return args.query
            elif name == "--slowmo":
                return 0  # デフォルトのslowmo値
            return default
    
    mock_request = MockRequest()
    # 注意：この関数は手動検証用のため、通常は呼び出されません
    # await test_text_search(mock_request)

async def check_profile_status(page, browser_type):
    """
    ブラウザのプロファイル読み込み状況をチェックし、ログ出力する
    """
    print(f"🔍 Checking {browser_type} profile status...")
    
    try:
        # ブラウザのプロファイル設定ページをチェック（最も重要）
        print("🔧 Checking browser profile settings...")
        if browser_type == 'edge':
            profile_url = "edge://settings/profiles"
        elif browser_type == 'chrome':
            profile_url = "chrome://settings/people"
        else:
            profile_url = "chrome://settings/people"
            
        await page.goto(profile_url, wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)  # ページ読み込みを待機
        
        # プロファイル関連の要素を確認
        profile_elements = await page.query_selector_all('[role="heading"], .profile-name, .account-name, [data-test-id*="profile"], [aria-label*="プロファイル"], [aria-label*="Profile"]')
        
        print(f"🔍 Profile settings elements found: {len(profile_elements)}")
        
        if profile_elements:
            print(f"✅ {browser_type} profile settings page loaded successfully")
            for i, element in enumerate(profile_elements[:3]):  # 最初の3つの要素を確認
                try:
                    text = await element.text_content()
                    if text and text.strip():
                        print(f"📄 Profile element {i}: {text[:60]}...")
                except:
                    pass
        else:
            print(f"❌ No profile elements found in {browser_type} settings")
        
        # アカウント情報を具体的に探す
        account_elements = await page.query_selector_all('[role="button"]:has-text("アカウント"), [role="button"]:has-text("Account"), .account-info, .user-info, [aria-label*="アカウント"], [aria-label*="Account"]')
        
        if account_elements:
            print(f"✅ Found {len(account_elements)} account-related elements")
            for i, element in enumerate(account_elements[:2]):
                try:
                    text = await element.text_content()
                    if text and text.strip():
                        print(f"📄 Account element {i}: {text[:60]}...")
                except:
                    pass
        else:
            print("❌ No account elements found in profile settings")
        
        # ページ全体のテキストからアカウント情報を検索
        page_content = await page.text_content('body')
        if '@' in page_content:
            lines_with_email = [line.strip() for line in page_content.split('\n') if '@' in line and len(line.strip()) < 100 and len(line.strip()) > 5]
            if lines_with_email:
                print("✅ Found potential email addresses in profile:")
                for email_line in lines_with_email[:2]:
                    print(f"📧 {email_line}")
            else:
                print("❌ No valid email addresses detected in profile settings")
        else:
            print("❌ No email addresses found in page content")
        
        # Google にアクセスしてログイン状況を確認
        print("🔧 Navigating to Google to check account status...")
        await page.goto("https://www.google.com", wait_until='domcontentloaded', timeout=30000)
        await page.wait_for_timeout(3000)  # ページ読み込みを待機
        
        # Google アカウントのサインイン状態を確認
        try:
            # サインインボタンの存在を確認
            sign_in_button = await page.query_selector('a[aria-label*="Sign in"], a[data-ved*="sign"], .gb_Ae')
            if sign_in_button:
                print("❌ Google account: NOT signed in (Sign in button found)")
            else:
                # プロフィール画像やアカウント情報を確認
                profile_elements = await page.query_selector_all('.gb_Ae, .gb_d, [aria-label*="Google Account"], [data-ved*="account"]')
                if profile_elements:
                    print("✅ Google account: Likely signed in (Profile elements found)")
                    # プロフィール要素の詳細を取得
                    for i, element in enumerate(profile_elements[:3]):  # 最初の3つの要素を確認
                        try:
                            text = await element.text_content()
                            if text:
                                print(f"📄 Profile element {i}: {text[:50]}...")
                        except:
                            pass
                else:
                    print("⚠️ Google account: Status unclear (No clear indicators found)")
        except Exception as e:
            print(f"⚠️ Error checking Google account status: {e}")
        
        # ブックマークを確認（Chrome/Edge共通のショートカット Ctrl+Shift+O）
        print("🔧 Checking bookmarks...")
        try:
            # ブックマークマネージャーを開く
            await page.keyboard.press('Meta+Shift+O' if browser_type == 'chrome' else 'Ctrl+Shift+O')
            await page.wait_for_timeout(2000)
            
            # ブックマークがあるかチェック
            bookmark_elements = await page.query_selector_all('[role="treeitem"], .bookmark-item, [data-test-id*="bookmark"]')
            if bookmark_elements:
                print(f"✅ Bookmarks: Found {len(bookmark_elements)} bookmark elements")
            else:
                print("❌ Bookmarks: No bookmarks found")
                
            # ブックマークマネージャーを閉じる
            await page.keyboard.press('Escape')
            await page.wait_for_timeout(1000)
        except Exception as e:
            print(f"⚠️ Error checking bookmarks: {e}")
        
        print(f"✅ Profile status check completed for {browser_type}")
        
    except Exception as e:
        print(f"❌ Error during profile status check: {e}")