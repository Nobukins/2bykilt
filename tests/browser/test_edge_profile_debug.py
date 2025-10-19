#!/usr/bin/env python3
"""
Edge プロファイルコピーの動作を確認するためのデバッグスクリプト
"""

import os
import pytest
import shutil
from pathlib import Path

@pytest.mark.local_only
def test_edge_profile_copy():
    print("🔍 Edge プロファイル存在確認...")
    
    # Edge のユーザーデータディレクトリをチェック
    edge_user_data = os.environ.get('EDGE_USER_DATA', '/Users/nobuaki/Library/Application Support/Microsoft Edge')
    print(f"Edge User Data: {edge_user_data}")
    
    if not os.path.exists(edge_user_data):
        print(f"❌ Edge ユーザーデータディレクトリが見つかりません: {edge_user_data}")
        return
    
    print(f"✅ Edge ユーザーデータディレクトリが存在します")
    
    # Default プロファイルをチェック
    default_profile = os.path.join(edge_user_data, "Default")
    if not os.path.exists(default_profile):
        print(f"❌ Edge Default プロファイルが見つかりません: {default_profile}")
        return
    
    print(f"✅ Edge Default プロファイルが存在します")
    
    # 重要なファイルの存在確認
    important_files = [
        "Default/Preferences",
        "Default/Bookmarks", 
        "Default/History",
        "Default/Cookies",
        "Default/Login Data",
        "Local State"
    ]
    
    existing_files = []
    missing_files = []
    
    for file_path in important_files:
        full_path = os.path.join(edge_user_data, file_path)
        if os.path.exists(full_path):
            size = os.path.getsize(full_path) if os.path.isfile(full_path) else "directory"
            existing_files.append((file_path, size))
            print(f"✅ {file_path} - {size} bytes" if isinstance(size, int) else f"✅ {file_path} - {size}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path} - Not found")
    
    print(f"\n📊 Summary:")
    print(f"   Existing files: {len(existing_files)}")
    print(f"   Missing files: {len(missing_files)}")
    
    # テスト用コピーを実行
    print(f"\n🔧 Testing profile copy...")
    test_profile_dir = "./tmp/test_edge_profile"
    
    if os.path.exists(test_profile_dir):
        print(f"🗑️ Removing existing test profile: {test_profile_dir}")
        shutil.rmtree(test_profile_dir, ignore_errors=True)
    
    os.makedirs(test_profile_dir, exist_ok=True)
    
    copied_count = 0
    for file_path, _ in existing_files:
        src_file = os.path.join(edge_user_data, file_path)
        dst_file = os.path.join(test_profile_dir, file_path)
        
        try:
            os.makedirs(os.path.dirname(dst_file), exist_ok=True)
            if os.path.isfile(src_file):
                shutil.copy2(src_file, dst_file)
                print(f"📄 Copied: {file_path}")
                copied_count += 1
        except Exception as e:
            print(f"⚠️ Failed to copy {file_path}: {e}")
    
    print(f"\n✅ Test copy completed: {copied_count} files copied to {test_profile_dir}")

if __name__ == "__main__":
    test_edge_profile_copy()
