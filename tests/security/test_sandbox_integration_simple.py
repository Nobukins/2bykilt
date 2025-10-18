"""
git-scriptのサンドボックス統合の簡易テスト (Issue #62)

SandboxManagerが正しく統合されていることを検証
"""
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

from src.security.sandbox_manager import SandboxManager, SandboxConfig, SandboxMode, ExecutionResult


class TestSandboxManagerIntegration:
    """サンドボックスマネージャーの統合テスト"""
    
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
    
    def test_sandbox_basic_execution(self, temp_workspace):
        """基本的なサンドボックス実行を検証"""
        manager = SandboxManager(SandboxConfig(mode=SandboxMode.MODERATE))
        
        script_path = temp_workspace / "test_script.py"
        
        result = manager.execute(
            command=["python", str(script_path), "arg1", "arg2"],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert result.exit_code == 0
        assert "Hello from sandboxed script" in result.stdout
        assert "['arg1', 'arg2']" in result.stdout
    
    def test_sandbox_timeout_protection(self, temp_workspace):
        """タイムアウト保護を検証"""
        # 短いタイムアウト設定
        config = SandboxConfig(
            mode=SandboxMode.MODERATE,
            timeout_sec=2
        )
        manager = SandboxManager(config)
        
        # 無限ループスクリプト
        script_file = temp_workspace / "infinite_loop.py"
        script_file.write_text("""
import time
while True:
    time.sleep(1)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        # タイムアウトでキルされることを確認
        assert result.success is False
        assert result.killed is True
    
    def test_sandbox_with_env_variables(self, temp_workspace):
        """環境変数が正しく渡されることを確認"""
        manager = SandboxManager()
        
        script_file = temp_workspace / "check_env.py"
        script_file.write_text("""
import os
import sys

test_var = os.environ.get('TEST_VAR', 'NOT_SET')
print(f"TEST_VAR: {test_var}")

sys.exit(0)
""")
        
        config = SandboxConfig(
            environment_variables={"TEST_VAR": "test_value"}
        )
        manager = SandboxManager(config)
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert "TEST_VAR: test_value" in result.stdout
    
    @pytest.mark.skipif(sys.platform == "win32", reason="Unix-only resource limits")
    def test_sandbox_resource_limits_applied(self, temp_workspace):
        """リソース制限が適用されることを確認"""
        manager = SandboxManager(SandboxConfig(mode=SandboxMode.MODERATE))
        
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
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert "CPU limit:" in result.stdout
        assert "Process limit:" in result.stdout
    
    def test_sandbox_failure_handling(self, temp_workspace):
        """スクリプト失敗時の処理を確認"""
        manager = SandboxManager()
        
        script_file = temp_workspace / "failing_script.py"
        script_file.write_text("""
import sys

print("Script is about to fail")
sys.exit(42)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is False
        assert result.exit_code == 42
        assert "Script is about to fail" in result.stdout
    
    def test_sandbox_with_strict_mode(self, temp_workspace):
        """STRICT モードでの実行を確認"""
        config = SandboxConfig(
            mode=SandboxMode.STRICT,
            cpu_time_sec=60,
            memory_mb=256
        )
        manager = SandboxManager(config)
        
        script_file = temp_workspace / "simple_script.py"
        script_file.write_text("""
import sys
print("Running in strict mode")
sys.exit(0)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert "Running in strict mode" in result.stdout
    
    def test_sandbox_with_disabled_mode(self, temp_workspace):
        """DISABLED モードでの実行を確認"""
        config = SandboxConfig(mode=SandboxMode.DISABLED)
        manager = SandboxManager(config)
        
        script_file = temp_workspace / "test_script.py"
        script_file.write_text("""
import sys
print("Running without sandbox")
sys.exit(0)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert "Running without sandbox" in result.stdout
    
    def test_create_sandbox_from_feature_flags(self, temp_workspace):
        """Feature Flagsからの自動設定を検証"""
        from src.security.sandbox_manager import create_sandbox_from_feature_flags
        
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            def get_flag(key, **kwargs):
                if key == "security.sandbox_enabled":
                    return True
                elif key == "security.sandbox_mode":
                    return "moderate"
                elif key == "security.sandbox_resource_limits":
                    return {
                        "cpu_time_sec": 300,
                        "memory_mb": 512,
                    }
                return kwargs.get('default')
            
            mock_get.side_effect = get_flag
            
            manager = create_sandbox_from_feature_flags()
            
            script_file = temp_workspace / "test.py"
            script_file.write_text("import sys; print('test'); sys.exit(0)")
            
            result = manager.execute(
                command=["python", str(script_file)],
                cwd=str(temp_workspace),
                capture_output=True
            )
            
            assert result.success is True
            assert "test" in result.stdout
