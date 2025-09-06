#!/usr/bin/env python3
"""
プロファイル詳細確認：実際にコピーされたファイルの内容を確認
"""

import os
import json
from pathlib import Path

def check_profile_details():
    """プロファイルファイルの詳細を確認"""
    
    browsers = {
        'Edge': os.environ.get('EDGE_USER_DATA', ''),
        'Chrome': os.environ.get('CHROME_USER_DATA', '')
    }
    
    for browser_name, original_profile in browsers.items():
        print(f"\n{'='*50}")
        print(f"🔍 {browser_name} プロファイル詳細確認")
        print(f"{'='*50}")
        
        test_profile = os.path.join(original_profile, "SeleniumProfile")
        
        if not os.path.exists(test_profile):
            print(f"❌ Test profile not found: {test_profile}")
            continue
        
        # Bookmarks ファイルの確認
        bookmarks_file = os.path.join(test_profile, "Default", "Bookmarks")
        if os.path.exists(bookmarks_file):
            try:
                with open(bookmarks_file, 'r', encoding='utf-8') as f:
                    bookmarks_data = json.load(f)
                
                # ブックマーク数をカウント
                def count_bookmarks(folder):
                    count = 0
                    if 'children' in folder:
                        for item in folder['children']:
                            if item['type'] == 'url':
                                count += 1
                            elif item['type'] == 'folder':
                                count += count_bookmarks(item)
                    return count
                
                bookmark_count = 0
                if 'roots' in bookmarks_data:
                    for root_name, root_data in bookmarks_data['roots'].items():
                        if isinstance(root_data, dict):
                            bookmark_count += count_bookmarks(root_data)
                
                print(f"✅ Bookmarks file found: {bookmark_count} bookmarks")
                
                # いくつかのブックマーク名を表示
                def get_bookmark_names(folder, limit=3):
                    names = []
                    if 'children' in folder and len(names) < limit:
                        for item in folder['children']:
                            if item['type'] == 'url' and len(names) < limit:
                                names.append(item.get('name', 'Unnamed'))
                            elif item['type'] == 'folder' and len(names) < limit:
                                names.extend(get_bookmark_names(item, limit - len(names)))
                    return names
                
                sample_names = []
                if 'roots' in bookmarks_data:
                    for root_name, root_data in bookmarks_data['roots'].items():
                        if isinstance(root_data, dict):
                            sample_names.extend(get_bookmark_names(root_data, 3))
                
                if sample_names:
                    print(f"  📚 Sample bookmarks: {', '.join(sample_names[:3])}")
                
            except Exception as e:
                print(f"⚠️ Error reading bookmarks: {e}")
        else:
            print(f"❌ Bookmarks file not found")
        
        # Preferences ファイルの確認
        prefs_file = os.path.join(test_profile, "Default", "Preferences")
        if os.path.exists(prefs_file):
            try:
                with open(prefs_file, 'r', encoding='utf-8') as f:
                    prefs_data = json.load(f)
                
                print(f"✅ Preferences file found")
                
                # アカウント情報の確認
                if 'account_info' in prefs_data:
                    print(f"  👤 Account info section present")
                
                # プロファイル情報の確認
                if 'profile' in prefs_data:
                    profile_info = prefs_data['profile']
                    if 'name' in profile_info:
                        print(f"  📛 Profile name: {profile_info['name']}")
                    if 'info_cache' in profile_info:
                        print(f"  💾 Profile info cache present")
                
                # 同期設定の確認
                if 'sync' in prefs_data:
                    print(f"  🔄 Sync settings present")
                
            except Exception as e:
                print(f"⚠️ Error reading preferences: {e}")
        else:
            print(f"❌ Preferences file not found")
        
        # Local State ファイルの確認
        local_state_file = os.path.join(test_profile, "Local State")
        if os.path.exists(local_state_file):
            try:
                with open(local_state_file, 'r', encoding='utf-8') as f:
                    local_state_data = json.load(f)
                
                print(f"✅ Local State file found")
                
                # プロファイル情報の確認
                if 'profile' in local_state_data:
                    profiles = local_state_data['profile']
                    if 'info_cache' in profiles:
                        cache = profiles['info_cache']
                        profile_count = len(cache)
                        print(f"  👥 Cached profiles: {profile_count}")
                        
                        for profile_id, profile_data in cache.items():
                            if 'name' in profile_data:
                                print(f"    📛 {profile_id}: {profile_data['name']}")
                
            except Exception as e:
                print(f"⚠️ Error reading Local State: {e}")
        else:
            print(f"❌ Local State file not found")

if __name__ == "__main__":
    check_profile_details()
