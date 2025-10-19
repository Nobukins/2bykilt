#!/usr/bin/env python3
"""
テスト検証スクリプト
修正されたテストおよびスキップされたテストの詳細情報を表示する
"""

import subprocess
import json
import sys

def run_pytest_collection():
    """pytest でテストを収集し、詳細情報を取得"""
    cmd = [
        sys.executable, "-m", "pytest",
        "--collect-only",
        "-q",
        "--quiet",
        "tests/",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt")
    return result.stdout, result.stderr

def analyze_skipped():
    """スキップされたテストを分析"""
    cmd = [
        sys.executable, "-m", "pytest",
        "-v",
        "-m", "local_only",
        "--collect-only",
        "tests/",
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True, cwd="/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt")
    return result.stdout

def main():
    print("=" * 80)
    print("テスト検証レポート")
    print("=" * 80)
    
    print("\n[1] テスト統計を取得中...")
    stdout, stderr = run_pytest_collection()
    
    # 最後の行を取得（統計情報）
    lines = stdout.strip().split('\n')
    if lines:
        for line in lines[-10:]:
            if line.strip():
                print(line)
    
    print("\n[2] local_only テスト情報を取得中...")
    local_only_output = analyze_skipped()
    
    # local_only テスト数を数える
    local_only_count = local_only_output.count("local_only")
    print(f"local_only マーク付きテスト: {local_only_count}")
    
    print("\n[3] 修正されたテストファイルの検証")
    modified_files = [
        "tests/utils/test_diagnostics.py",
        "tests/browser/engine/test_cdp_engine_basic.py",
        "tests/modules/test_direct_browser_control.py",
        "tests/browser/test_browser_manager.py",
        "tests/modules/test_execution_debug_engine.py",
    ]
    
    for file in modified_files:
        print(f"\n  - {file}")
        cmd = [
            sys.executable, "-m", "pytest",
            "--collect-only",
            "-q",
            file,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, cwd="/Users/nobuaki/Documents/Github/copilot-ports/magic-trainings/2bykilt")
        
        # テスト数を解析
        output_lines = result.stdout.strip().split('\n')
        for line in output_lines[-3:]:
            if line.strip():
                print(f"    {line}")

if __name__ == "__main__":
    main()
