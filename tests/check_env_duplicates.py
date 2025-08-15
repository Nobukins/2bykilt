#!/usr/bin/env python3
"""
.env ファイルの重複環境変数をチェックするスクリプト
"""

import os
from collections import defaultdict

def check_env_duplicates(file_path=".env"):
    """環境変数の重複をチェック"""
    duplicates = defaultdict(list)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            # コメント行や空行をスキップ
            if not line or line.startswith('#'):
                continue
            
            # 環境変数の定義行をチェック
            if '=' in line:
                var_name = line.split('=')[0].strip()
                var_value = line.split('=', 1)[1].strip()
                duplicates[var_name].append((line_num, var_value))
    
    print("=== .env ファイルの重複チェック結果 ===")
    found_duplicates = False
    
    for var_name, occurrences in duplicates.items():
        if len(occurrences) > 1:
            found_duplicates = True
            print(f"\n⚠️ 重複: {var_name}")
            for line_num, value in occurrences:
                print(f"  行 {line_num}: {var_name}={value}")
    
    if not found_duplicates:
        print("✅ 重複した環境変数は見つかりませんでした")
    
    return duplicates

if __name__ == "__main__":
    check_env_duplicates()
