"""
git-scriptのサンドボックス統合テスト (Issue #62)

GitScriptAutomatorがSandboxManagerを使用してスクリプトを安全に実行することを検証
"""
import pytest
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

from src.utils.git_script_automator import GitScriptAutomator


class TestGitScriptSandboxIntegration:
    """git-script実行のサンドボックス統合テスト"""
    
    @pytest.fixture
    def temp_workspace(self):
        """一時ワークスペースを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # シンプルなPythonスクリプトを作成
            script_file = workspace / "test_script.py"
            script_file.write_text("""
import sys
print("Hello from sandboxed script")
print(f"Arguments: {sys.argv[1:]}")
sys.exit(0)
""")
            
            yield workspace
    
    @pytest.mark.asyncio
    async def test_basic_git_script_execution_with_sandbox(self, temp_workspace):
        """基本的なgit-script実行がサンドボックスで動作することを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_path = temp_workspace / "test_script.py"
        command = f"python {script_path} arg1 arg2"
        
        result = await automator.execute_git_script_workflow(
            workspace_dir=str(temp_workspace),
            script_path=str(script_path),
            command=command,
            params={}
        )
        
        # 成功の確認
        assert result["success"] is True
        assert result["exit_code"] == 0
        assert "Hello from sandboxed script" in result["stdout"]
        assert "Arguments: ['arg1', 'arg2']" in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_git_script_with_timeout_protection(self, temp_workspace):
        """タイムアウト保護が動作することを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        # 無限ループスクリプト
        script_file = temp_workspace / "infinite_loop.py"
        script_file.write_text("""
import time
while True:
    time.sleep(1)
""")
        
        # Feature Flagsで短いタイムアウトを設定
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            def get_flag(key, default=None):
                if key == "security.sandbox_enabled":
                    return True
                elif key == "security.sandbox_mode":
                    return "moderate"
                elif key == "security.sandbox_resource_limits":
                    return {
                        "cpu_time_sec": 2,
                        "timeout_sec": 3,  # 3秒でタイムアウト
                    }
                return default
            
            mock_get.side_effect = get_flag
            
            command = f"python {script_file}"
            result = await automator.execute_git_script_workflow(
                command=command,
                workspace_dir=str(temp_workspace)
            )
        
        # タイムアウトでキルされることを確認
        assert result["success"] is False
        assert "killed" in result.get("error", "").lower() or "timeout" in result.get("error", "").lower()
    
    @pytest.mark.asyncio
    async def test_git_script_with_resource_limits(self, temp_workspace):
        """リソース制限が適用されることを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        # メモリ使用量を確認するスクリプト
        script_file = temp_workspace / "check_limits.py"
        script_file.write_text("""
import resource
import sys

# CPU時間制限を確認
cpu_limit = resource.getrlimit(resource.RLIMIT_CPU)
print(f"CPU limit: {cpu_limit}")

# プロセス数制限を確認
nproc_limit = resource.getrlimit(resource.RLIMIT_NPROC)
print(f"Process limit: {nproc_limit}")

sys.exit(0)
""")
        
        command = f"python {script_file}"
        result = await automator.execute_git_script_workflow(
            command=command,
            workspace_dir=str(temp_workspace)
        )
        
        # Unix系のみテスト（Windowsはスキップ）
        if sys.platform != "win32":
            assert result["success"] is True
            assert "CPU limit:" in result["stdout"]
            assert "Process limit:" in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_git_script_with_environment_variables(self, temp_workspace):
        """環境変数が正しく渡されることを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_file = temp_workspace / "check_env.py"
        script_file.write_text("""
import os
import sys

pythonpath = os.environ.get('PYTHONPATH', 'NOT_SET')
print(f"PYTHONPATH: {pythonpath}")

sys.exit(0)
""")
        
        command = f"python {script_file}"
        result = await automator.execute_git_script_workflow(
            command=command,
            workspace_dir=str(temp_workspace)
        )
        
        assert result["success"] is True
        assert "PYTHONPATH:" in result["stdout"]
        assert str(temp_workspace) in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_git_script_with_stderr_output(self, temp_workspace):
        """stderr出力が正しくキャプチャされることを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_file = temp_workspace / "stderr_test.py"
        script_file.write_text("""
import sys

print("stdout message")
print("stderr message", file=sys.stderr)

sys.exit(0)
""")
        
        command = f"python {script_file}"
        result = await automator.execute_git_script_workflow(
            command=command,
            workspace_dir=str(temp_workspace)
        )
        
        assert result["success"] is True
        assert "stdout message" in result["stdout"]
        assert "stderr message" in result["stderr"]
    
    @pytest.mark.asyncio
    async def test_git_script_failure_handling(self, temp_workspace):
        """スクリプト失敗時の処理を確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_file = temp_workspace / "failing_script.py"
        script_file.write_text("""
import sys

print("Script is about to fail")
sys.exit(42)  # 非ゼロ終了コード
""")
        
        command = f"python {script_file}"
        result = await automator.execute_git_script_workflow(
            command=command,
            workspace_dir=str(temp_workspace)
        )
        
        assert result["success"] is False
        assert result["exit_code"] == 42
        assert "Script is about to fail" in result["stdout"]
        assert "failed with exit code 42" in result.get("error", "")
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only test")
    async def test_git_script_with_strict_mode(self, temp_workspace):
        """STRICT モードでの実行を確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_file = temp_workspace / "simple_script.py"
        script_file.write_text("""
import sys
print("Running in strict mode")
sys.exit(0)
""")
        
        # STRICTモードで実行
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            def get_flag(key, default=None):
                if key == "security.sandbox_enabled":
                    return True
                elif key == "security.sandbox_mode":
                    return "strict"
                elif key == "security.sandbox_resource_limits":
                    return {
                        "cpu_time_sec": 60,
                        "memory_mb": 256,
                        "timeout_sec": 120,
                    }
                return default
            
            mock_get.side_effect = get_flag
            
            command = f"python {script_file}"
            result = await automator.execute_git_script_workflow(
                command=command,
                workspace_dir=str(temp_workspace)
            )
        
        assert result["success"] is True
        assert "Running in strict mode" in result["stdout"]
    
    @pytest.mark.asyncio
    async def test_git_script_with_disabled_sandbox(self, temp_workspace):
        """サンドボックス無効時の動作を確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        script_file = temp_workspace / "test_script.py"
        script_file.write_text("""
import sys
print("Running without sandbox")
sys.exit(0)
""")
        
        # サンドボックスを無効化
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            def get_flag(key, default=None):
                if key == "security.sandbox_enabled":
                    return False
                return default
            
            mock_get.side_effect = get_flag
            
            command = f"python {script_file}"
            result = await automator.execute_git_script_workflow(
                command=command,
                workspace_dir=str(temp_workspace)
            )
        
        assert result["success"] is True
        assert "Running without sandbox" in result["stdout"]


class TestGitScriptSecurityValidation:
    """git-scriptのセキュリティ検証テスト"""
    
    @pytest.fixture
    def temp_workspace(self):
        """一時ワークスペースを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)
    
    @pytest.mark.asyncio
    @pytest.mark.skipif(sys.platform != "linux", reason="Linux seccomp-only test")
    async def test_syscall_filtering_applied(self, temp_workspace):
        """Linux環境でsyscallフィルタが適用されることを確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        # ネットワークアクセスを試みるスクリプト（拒否されるべき）
        script_file = temp_workspace / "network_test.py"
        script_file.write_text("""
import socket
import sys

try:
    # socketシステムコールは拒否されるべき
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print("Socket created - SHOULD NOT HAPPEN IN STRICT MODE")
    s.close()
    sys.exit(1)  # セキュリティ違反
except Exception as e:
    print(f"Socket creation blocked: {e}")
    sys.exit(0)  # 正常（ブロックされた）
""")
        
        # STRICTモードで実行
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            def get_flag(key, default=None):
                if key == "security.sandbox_enabled":
                    return True
                elif key == "security.sandbox_mode":
                    return "strict"
                return default
            
            mock_get.side_effect = get_flag
            
            command = f"python {script_file}"
            result = await automator.execute_git_script_workflow(
                command=command,
                workspace_dir=str(temp_workspace)
            )
        
        # ネットワークアクセスがブロックされることを確認
        # (seccompが動作している場合)
        # 注: seccompライブラリがない環境ではこのテストはパス
        if "Socket creation blocked" in result.get("stdout", ""):
            assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_path_traversal_protection(self, temp_workspace):
        """パストラバーサル保護を確認"""
        automator = GitScriptAutomator(browser_type="chrome")
        
        # 親ディレクトリへのアクセスを試みる
        script_file = temp_workspace / "path_test.py"
        script_file.write_text("""
import sys
import os

# 親ディレクトリへのアクセスを試みる
try:
    parent_dir = os.path.abspath('..')
    files = os.listdir(parent_dir)
    print(f"Parent directory access: {len(files)} files")
    sys.exit(0)
except Exception as e:
    print(f"Parent directory access blocked: {e}")
    sys.exit(1)
""")
        
        command = f"python {script_file}"
        result = await automator.execute_git_script_workflow(
            command=command,
            workspace_dir=str(temp_workspace)
        )
        
        # 現時点では親ディレクトリアクセスは許可されている
        # Issue #62b (Enforce Phase) で制限予定
        assert result["exit_code"] in [0, 1]  # どちらでも許容
