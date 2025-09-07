#!/usr/bin/env python3
"""
統合 action_runner ランチャー
- クロスプラットフォーム対応（Windows/macOS/Linux）
- デバッグログ機能
- 環境設定の自動調整
- action_runner.py の確実な実行
"""

import os
import sys
import subprocess
import platform
from pathlib import Path
from datetime import datetime

class ActionRunnerLauncher:
    def __init__(self):
        self.script_dir = Path(__file__).resolve().parent
        self.project_root = self.script_dir.parent.parent
        self.is_windows = platform.system() == "Windows"
        self.is_macos = platform.system() == "Darwin"
        self.is_linux = platform.system() == "Linux"
        
        # ログファイル設定
        self.log_dir = self.project_root / "logs"
        self.log_dir.mkdir(exist_ok=True)
        self.debug_log = self.log_dir / "action_runner_launcher.log"
        
    def log_message(self, message):
        """ログメッセージを標準出力とファイルに記録"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        formatted_message = f"[{timestamp}] {message}"
        
        print(formatted_message)
        print(formatted_message, file=sys.stderr)
        sys.stdout.flush()
        sys.stderr.flush()
        
        try:
            with open(self.debug_log, "a", encoding="utf-8") as f:
                f.write(f"{formatted_message}\n")
                f.flush()
        except Exception as e:
            print(f"ログファイル書き込みエラー: {e}", file=sys.stderr)
    
    def setup_environment(self):
        """プラットフォーム別の実行環境を設定"""
        env = os.environ.copy()
        
        # PYTHONPATHを設定
        python_paths = [
            str(self.project_root),
            str(self.script_dir),
            str(self.project_root / "src"),
            str(self.project_root / "tmp" / "myscript")
        ]
        
        if self.is_windows:
            env['PYTHONPATH'] = ";".join(python_paths)
        else:
            env['PYTHONPATH'] = ":".join(python_paths)
        
        # 仮想環境の情報を継承
        venv_vars = ['VIRTUAL_ENV', 'CONDA_DEFAULT_ENV', 'VIRTUAL_ENV_PROMPT']
        for var in venv_vars:
            if var in os.environ:
                env[var] = os.environ[var]
        
        self.log_message(f"🔧 [launcher] 環境設定完了")
        self.log_message(f"   プラットフォーム: {platform.system()}")
        self.log_message(f"   Python: {sys.executable}")
        self.log_message(f"   PYTHONPATH: {env['PYTHONPATH']}")
        self.log_message(f"   作業ディレクトリ: {self.script_dir}")
        
        return env
    
    def log_execution_info(self):
        """実行情報をデバッグログに記録"""
        debug_info = f"""
=== ACTION RUNNER LAUNCHER EXECUTION LOG ===
Timestamp: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Platform: {platform.system()} {platform.release()}
Architecture: {platform.machine()}
Working Directory: {os.getcwd()}
Script Directory: {self.script_dir}
Project Root: {self.project_root}
Python Executable: {sys.executable}
Python Version: {sys.version}
Arguments: {sys.argv}

Environment Variables:"""
        
        for key, value in os.environ.items():
            if key.startswith(('PATH', 'PYTHON', 'VIRTUAL_ENV', 'CONDA')):
                debug_info += f"\n  {key}={value}"
        
        debug_info += "\n=== END EXECUTION INFO ===\n"
        
        self.log_message(debug_info)
    
    def find_action_runner(self):
        """action_runner.pyのパスを確認"""
        action_runner_path = self.script_dir / "action_runner.py"
        
        if not action_runner_path.exists():
            self.log_message(f"❌ [launcher] action_runner.py が見つかりません: {action_runner_path}")
            return None
        
        self.log_message(f"✅ [launcher] action_runner.py を発見: {action_runner_path}")
        return action_runner_path
    
    def run(self):
        """メイン実行関数"""
        self.log_message(f"🚀 [launcher] ACTION RUNNER LAUNCHER 開始")
        self.log_message(f"📋 [launcher] 引数: {sys.argv}")
        
        # 実行情報をログに記録
        self.log_execution_info()
        
        # action_runner.pyを確認
        action_runner_path = self.find_action_runner()
        if not action_runner_path:
            sys.exit(1)
        
        # 環境設定
        env = self.setup_environment()
        
        # コマンド構築
        cmd = [sys.executable, str(action_runner_path)] + sys.argv[1:]
        self.log_message(f"🔄 [launcher] 実行コマンド: {' '.join(cmd)}")
        
        try:
            # action_runner.pyを実行
            self.log_message(f"▶️ [launcher] action_runner.py 実行開始...")
            result = subprocess.run(
                cmd,
                env=env,
                cwd=self.script_dir,
                check=False  # エラーでも例外を発生させない
            )
            
            self.log_message(f"🏁 [launcher] action_runner.py 実行完了 - 終了コード: {result.returncode}")
            
            # 実行結果をログに記録
            with open(self.debug_log, "a", encoding="utf-8") as f:
                f.write(f"Exit Code: {result.returncode}\n")
                f.write("=" * 50 + "\n")
            
            sys.exit(result.returncode)
            
        except Exception as e:
            self.log_message(f"❌ [launcher] action_runner.py 実行失敗: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)

def main():
    """エントリーポイント"""
    launcher = ActionRunnerLauncher()
    launcher.run()

if __name__ == "__main__":
    main()
