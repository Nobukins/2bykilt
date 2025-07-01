#!/usr/bin/env python3
"""
action_runner.pyの実行前にデバッグ情報を記録するラッパー
"""
import sys
import os
import subprocess
from datetime import datetime
from pathlib import Path

def main():
    # デバッグ情報を記録
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    debug_info = f"""
=== DEBUG WRAPPER EXECUTION LOG ===
Timestamp: {timestamp}
Working Directory: {os.getcwd()}
Python Executable: {sys.executable}
Python Version: {sys.version}
Arguments: {sys.argv}
Environment Variables:
"""
    
    for key, value in os.environ.items():
        if key.startswith(('PATH', 'PYTHON', 'VIRTUAL_ENV', 'CONDA')):
            debug_info += f"  {key}={value}\n"
    
    debug_info += f"\n=== END DEBUG INFO ===\n"
    
    # ログファイルに記録
    log_dir = Path(__file__).parent.parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / "debug_wrapper.log"
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(debug_info)
    
    # 標準出力にも出力
    print(debug_info)
    
    # 実際のaction_runner.pyを実行
    action_runner_path = Path(__file__).parent / "action_runner.py"
    cmd = [sys.executable, str(action_runner_path)] + sys.argv[1:]
    
    print(f"🔄 Executing: {' '.join(cmd)}")
    
    # action_runner.pyを実行
    result = subprocess.run(cmd, capture_output=False)
    
    print(f"🏁 Process finished with exit code: {result.returncode}")
    
    # 実行結果をログに記録
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(f"Exit Code: {result.returncode}\n")
        f.write("=" * 50 + "\n")
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    main()
