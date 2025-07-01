#!/usr/bin/env python3
"""
Windows環境対応のaction_runner起動スクリプト
仮想環境のPythonパスとモジュールパスを確実に設定してaction_runner.pyを実行
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def setup_windows_environment():
    """Windows環境での実行環境を設定"""
    if platform.system() != "Windows":
        return os.environ.copy()
    
    env = os.environ.copy()
    
    # プロジェクトルートディレクトリを取得
    script_dir = Path(__file__).resolve().parent
    project_root = script_dir.parent.parent
    
    # PYTHONPATHを設定
    python_paths = [
        str(project_root),
        str(script_dir),
        str(project_root / "src"),
        str(project_root / "tmp" / "myscript")
    ]
    
    env['PYTHONPATH'] = ";".join(python_paths)
    
    # 仮想環境の情報を継承
    if 'VIRTUAL_ENV' in os.environ:
        env['VIRTUAL_ENV'] = os.environ['VIRTUAL_ENV']
    
    if 'CONDA_DEFAULT_ENV' in os.environ:
        env['CONDA_DEFAULT_ENV'] = os.environ['CONDA_DEFAULT_ENV']
    
    print(f"[Windows Environment Setup]")
    print(f"   Python: {sys.executable}")
    print(f"   PYTHONPATH: {env['PYTHONPATH']}")
    print(f"   Working Dir: {script_dir}")
    
    return env

def main():
    """メイン実行関数"""
    # コマンドライン引数をそのまま action_runner.py に渡す
    action_runner_path = Path(__file__).parent / "action_runner.py"
    
    # Windows環境の設定
    env = setup_windows_environment()
    
    # コマンド構築
    cmd = [sys.executable, str(action_runner_path)] + sys.argv[1:]
    
    print(f"[Executing]: {' '.join(cmd)}")
    
    try:
        # subprocess で実行
        result = subprocess.run(
            cmd,
            env=env,
            cwd=Path(__file__).parent,
            check=False  # エラーでも例外を発生させない
        )
        
        # 終了コードを返す
        sys.exit(result.returncode)
        
    except Exception as e:
        print(f"❌ Failed to execute action_runner: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
