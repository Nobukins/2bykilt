#!/usr/bin/env python3
"""
Chrome認証ファイル深度調査：Googleアカウントログイン維持の決定的解決
"""

import os
import sqlite3
import json
from pathlib import Path

def analyze_chrome_auth_files():
    """Chrome認証ファイルの詳細解析"""
    chrome_profile = os.environ.get('CHROME_USER_DATA', '/Users/nobuaki/Library/Application Support/Google/Chrome')
    default_dir = os.path.join(chrome_profile, "Default")
    
    print(f"🔍 Chrome認証ファイル深度解析")
    print(f"Target: {default_dir}")
    
    # 1. Cookiesファイルの詳細解析
    cookies_file = os.path.join(default_dir, "Cookies")
    if os.path.exists(cookies_file):
        try:
            print(f"\n🍪 Cookies Database Analysis:")
            # SQLiteファイルを直接読む（注意：ブラウザが閉じている時のみ）
            conn = sqlite3.connect(f"file:{cookies_file}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Google関連のクッキーを検索
            cursor.execute("""
                SELECT host_key, name, value, encrypted_value, expires_utc
                FROM cookies 
                WHERE host_key LIKE '%google%' OR host_key LIKE '%gmail%'
                ORDER BY expires_utc DESC
                LIMIT 10
            """)
            
            google_cookies = cursor.fetchall()
            print(f"  📊 Google cookies found: {len(google_cookies)}")
            
            for cookie in google_cookies[:3]:
                host, name, value, encrypted, expires = cookie
                value_info = "encrypted" if encrypted else "plain"
                print(f"    🍪 {host}: {name} ({value_info})")
            
            conn.close()
            
        except Exception as e:
            print(f"  ⚠️ Cookie analysis failed: {e}")
    
    # 2. Login Dataファイルの詳細解析
    login_data_file = os.path.join(default_dir, "Login Data")
    if os.path.exists(login_data_file):
        try:
            print(f"\n🔑 Login Data Analysis:")
            conn = sqlite3.connect(f"file:{login_data_file}?mode=ro", uri=True)
            cursor = conn.cursor()
            
            # Google関連のログインデータを検索
            cursor.execute("""
                SELECT origin_url, username_value, password_value
                FROM logins 
                WHERE origin_url LIKE '%google%' OR origin_url LIKE '%gmail%'
                LIMIT 5
            """)
            
            google_logins = cursor.fetchall()
            print(f"  📊 Google logins found: {len(google_logins)}")
            
            for login in google_logins:
                url, username, password = login
                print(f"    🔑 {url}: {username} (password encrypted)")
            
            conn.close()
            
        except Exception as e:
            print(f"  ⚠️ Login data analysis failed: {e}")
    
    # 3. Preferencesファイルの詳細解析
    prefs_file = os.path.join(default_dir, "Preferences")
    if os.path.exists(prefs_file):
        try:
            print(f"\n⚙️ Preferences Analysis:")
            with open(prefs_file, 'r', encoding='utf-8') as f:
                prefs = json.load(f)
            
            # Google認証関連の設定を探す
            auth_related_keys = []
            
            def find_auth_keys(obj, prefix=""):
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{prefix}.{key}" if prefix else key
                        if any(keyword in key.lower() for keyword in ['auth', 'sign', 'token', 'gaia', 'account', 'google', 'sync']):
                            auth_related_keys.append((current_path, type(value).__name__))
                        if isinstance(value, (dict, list)):
                            find_auth_keys(value, current_path)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        if isinstance(item, (dict, list)):
                            find_auth_keys(item, f"{prefix}[{i}]")
            
            find_auth_keys(prefs)
            
            print(f"  📊 Auth-related preference keys found: {len(auth_related_keys)}")
            for key_path, value_type in auth_related_keys[:10]:
                print(f"    ⚙️ {key_path}: {value_type}")
            
            # 特に重要なキーを確認
            important_paths = [
                'signin', 'account_info', 'sync', 'gaia_cookie', 'oauth2',
                'profile.info_cache', 'profile.gaia_info_picture_url'
            ]
            
            for path in important_paths:
                keys = path.split('.')
                current = prefs
                try:
                    for key in keys:
                        current = current[key]
                    print(f"    🔍 {path}: Present")
                except KeyError:
                    pass
            
        except Exception as e:
            print(f"  ⚠️ Preferences analysis failed: {e}")
    
    # 4. 重要だが見逃されがちなファイルの確認
    print(f"\n📁 Hidden Critical Files Search:")
    
    critical_files = [
        # Chrome固有の認証ファイル
        "Account Web Data", "Account Tracker Service",
        "GAIA Info", "Identity Manager", "Google Update",
        "Token Service", "GCM Store", "Accounts",
        
        # セッション関連
        "Current Session", "Last Session", "Current Tabs", "Last Tabs",
        
        # 同期関連
        "Sync Data Backup", "Sync Extension Settings",
        
        # その他の認証関連
        "Network Persistent State", "OfflinePagePrefStore",
        "Shared Proto DB", "Safe Browsing Network",
    ]
    
    found_critical = []
    
    # デフォルトディレクトリ内を検索
    for item in critical_files:
        file_path = os.path.join(default_dir, item)
        if os.path.exists(file_path):
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path) / 1024
                found_critical.append(('FILE', item, f"{size:.1f} KB"))
            else:
                found_critical.append(('DIR', item, "directory"))
    
    # ルートディレクトリ内も検索
    for item in critical_files:
        file_path = os.path.join(chrome_profile, item)
        if os.path.exists(file_path) and item not in [x[1] for x in found_critical]:
            if os.path.isfile(file_path):
                size = os.path.getsize(file_path) / 1024
                found_critical.append(('ROOT_FILE', item, f"{size:.1f} KB"))
            else:
                found_critical.append(('ROOT_DIR', item, "directory"))
    
    print(f"  📊 Critical files found: {len(found_critical)}")
    for file_type, name, info in found_critical:
        icon = "📄" if "FILE" in file_type else "📁"
        location = "ROOT" if "ROOT" in file_type else "DEFAULT"
        print(f"    {icon} {name} ({location}): {info}")

if __name__ == "__main__":
    analyze_chrome_auth_files()
