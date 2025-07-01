#!/usr/bin/env python3
"""
プロファイル詳細スキャン：認証関連ファイルの完全調査
"""

import os
import json
from pathlib import Path

def scan_profile_for_auth_files():
    """認証関連ファイルの詳細スキャン"""
    
    browsers = {
        'Chrome': os.environ.get('CHROME_USER_DATA', '/Users/nobuaki/Library/Application Support/Google/Chrome'),
        'Edge': os.environ.get('EDGE_USER_DATA', '/Users/nobuaki/Library/Application Support/Microsoft Edge')
    }
    
    for browser_name, profile_path in browsers.items():
        print(f"\n{'='*60}")
        print(f"🔍 {browser_name} 認証ファイル詳細スキャン")
        print(f"{'='*60}")
        
        default_dir = os.path.join(profile_path, "Default")
        
        if not os.path.exists(default_dir):
            print(f"❌ Default profile not found: {default_dir}")
            continue
        
        print(f"📁 Scanning: {default_dir}")
        
        # 認証・ログイン関連のキーワード
        auth_keywords = [
            'login', 'auth', 'token', 'session', 'sync', 'account', 'gaia',
            'cookie', 'credential', 'signin', 'oauth', 'identity', 'gcm'
        ]
        
        # すべてのファイルとディレクトリをスキャン
        all_items = []
        try:
            for root, dirs, files in os.walk(default_dir):
                rel_root = os.path.relpath(root, default_dir)
                
                # ディレクトリ
                for d in dirs:
                    full_path = os.path.join(root, d)
                    rel_path = os.path.join(rel_root, d) if rel_root != '.' else d
                    all_items.append(('DIR', rel_path, full_path))
                
                # ファイル
                for f in files:
                    full_path = os.path.join(root, f)
                    rel_path = os.path.join(rel_root, f) if rel_root != '.' else f
                    size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                    all_items.append(('FILE', rel_path, full_path, size))
        
        except Exception as e:
            print(f"❌ Error scanning directory: {e}")
            continue
        
        # 認証関連アイテムを抽出
        auth_items = []
        for item in all_items:
            item_name = item[1].lower()
            if any(keyword in item_name for keyword in auth_keywords):
                auth_items.append(item)
        
        print(f"\n🔐 認証関連ファイル・ディレクトリ ({len(auth_items)} 個):")
        for item in sorted(auth_items):
            if item[0] == 'FILE':
                size_kb = item[3] / 1024
                print(f"  📄 {item[1]} ({size_kb:.1f} KB)")
            else:
                print(f"  📁 {item[1]}/")
        
        # Google関連のファイルを特別に確認
        print(f"\n🔍 Google関連ファイルの詳細確認:")
        
        # 重要なGoogle認証ファイル
        important_files = [
            "Cookies", "Login Data", "Login Data For Account", "Web Data",
            "Preferences", "Secure Preferences", "Sync Data"
        ]
        
        for file_name in important_files:
            file_path = os.path.join(default_dir, file_name)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path) / 1024
                print(f"  ✅ {file_name}: {size:.1f} KB")
                
                # Cookiesファイルの内容を確認（Googleドメインのクッキー）
                if file_name == "Cookies" and size > 1:
                    try:
                        # SQLite database - ここでは簡単にサイズのみ確認
                        print(f"    🍪 Cookie database size suggests active sessions")
                    except Exception as e:
                        print(f"    ⚠️ Cookie check failed: {e}")
                
                # Login Dataの確認
                elif "Login Data" in file_name and size > 1:
                    print(f"    🔑 Login database contains credentials")
                
                # Preferencesの確認
                elif file_name == "Preferences":
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            prefs = json.load(f)
                        
                        # アカウント関連設定を確認
                        if 'account_info' in prefs:
                            print(f"    👤 Account info present in preferences")
                        
                        if 'sync' in prefs:
                            sync_data = prefs['sync']
                            if 'sync_disabled' in sync_data:
                                disabled = sync_data['sync_disabled']
                                print(f"    🔄 Sync disabled: {disabled}")
                        
                        # プロファイル情報
                        if 'profile' in prefs:
                            profile_data = prefs['profile']
                            if 'info_cache' in profile_data:
                                print(f"    📋 Profile cache present")
                        
                    except Exception as e:
                        print(f"    ⚠️ Preferences check failed: {e}")
            else:
                print(f"  ❌ {file_name}: Not found")
        
        # Sync Data ディレクトリの確認
        sync_dir = os.path.join(default_dir, "Sync Data")
        if os.path.exists(sync_dir):
            try:
                sync_files = os.listdir(sync_dir)
                print(f"  📁 Sync Data/: {len(sync_files)} files")
                for sf in sync_files[:5]:  # 最初の5個のみ表示
                    print(f"    📄 {sf}")
            except Exception as e:
                print(f"  ⚠️ Sync Data scan failed: {e}")

if __name__ == "__main__":
    scan_profile_for_auth_files()
