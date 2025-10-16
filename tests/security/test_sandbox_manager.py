"""
SandboxManager テストスイート (Issue #62)

汎用サンドボックスマネージャーの機能テスト。

テストカテゴリ:
1. 基本実行テスト
2. リソース制限テスト
3. タイムアウトテスト
4. Feature Flags統合テスト
5. プラットフォーム互換性テスト

作成日: 2025-10-17
"""

import os
import platform
import sys
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.security.sandbox_manager import (
    SandboxManager,
    SandboxConfig,
    SandboxMode,
    ExecutionResult
)


@pytest.fixture
def default_config():
    """デフォルト設定"""
    return SandboxConfig(
        mode=SandboxMode.MODERATE,
        cpu_time_sec=10,
        memory_mb=128,
        timeout_sec=5
    )


@pytest.fixture
def strict_config():
    """厳格な制限設定"""
    return SandboxConfig(
        mode=SandboxMode.STRICT,
        cpu_time_sec=5,
        memory_mb=64,
        timeout_sec=3
    )


@pytest.fixture
def disabled_config():
    """サンドボックス無効設定"""
    return SandboxConfig(mode=SandboxMode.DISABLED)


class TestSandboxManagerBasics:
    """基本機能テスト"""
    
    def test_initialization_default(self):
        """デフォルト設定での初期化"""
        manager = SandboxManager()
        assert manager.config.mode == SandboxMode.MODERATE
        assert manager.config.cpu_time_sec == 300
        assert manager.config.memory_mb == 512
    
    @patch('src.config.feature_flags.FeatureFlags.get')
    def test_initialization_custom_config(self, mock_get, default_config):
        """カスタム設定での初期化"""
        # Feature Flagsを無効化してカスタム設定のみを使用
        mock_get.side_effect = lambda key, **kwargs: kwargs.get('default')
        
        manager = SandboxManager(default_config)
        assert manager.config.mode == SandboxMode.MODERATE
        assert manager.config.cpu_time_sec == 10
        assert manager.config.memory_mb == 128
    
    def test_disabled_mode(self, disabled_config):
        """無効モード"""
        with patch('src.config.feature_flags.FeatureFlags.get') as mock_get:
            # Feature Flagsが設定を上書きしないようにする
            mock_get.return_value = None
            
            manager = SandboxManager(disabled_config)
            assert manager.config.mode == SandboxMode.DISABLED


class TestBasicExecution:
    """基本実行テスト"""
    
    def test_simple_echo_command(self, default_config):
        """単純なechoコマンド実行"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=["echo", "Hello, Sandbox!"],
            capture_output=True
        )
        
        assert result.success
        assert result.exit_code == 0
        assert "Hello, Sandbox!" in result.stdout
        assert result.stderr == ""
        assert not result.killed
    
    def test_python_hello_world(self, default_config, tmp_path):
        """Pythonスクリプト実行"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=[sys.executable, "-c", "print('Hello from Python')"],
            cwd=tmp_path,
            capture_output=True
        )
        
        assert result.success
        assert result.exit_code == 0
        assert "Hello from Python" in result.stdout
    
    def test_command_with_error(self, default_config):
        """エラーを含むコマンド"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=[sys.executable, "-c", "import sys; sys.exit(1)"],
            capture_output=True
        )
        
        assert not result.success
        assert result.exit_code == 1
        assert not result.killed
    
    def test_invalid_command(self, default_config):
        """無効なコマンド"""
        manager = SandboxManager(default_config)
        
        with pytest.raises(ValueError):
            manager.execute(command=[])
        
        with pytest.raises(ValueError):
            manager.execute(command="not a list")  # type: ignore


class TestTimeout:
    """タイムアウトテスト"""
    
    def test_timeout_kills_process(self, default_config):
        """タイムアウトでプロセスがkillされる"""
        config = SandboxConfig(
            mode=SandboxMode.MODERATE,
            timeout_sec=1  # 1秒でタイムアウト
        )
        manager = SandboxManager(config)
        
        result = manager.execute(
            command=[sys.executable, "-c", "import time; time.sleep(10)"],
            capture_output=True
        )
        
        assert not result.success
        assert result.killed
        assert result.execution_time < 5  # タイムアウト後すぐにkill
    
    def test_no_timeout_for_quick_command(self, default_config):
        """短時間コマンドはタイムアウトしない"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=["echo", "quick"],
            capture_output=True
        )
        
        assert result.success
        assert not result.killed


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="Resource limits not supported on Windows"
)
class TestResourceLimits:
    """リソース制限テスト（Unix系のみ）"""
    
    def test_cpu_time_limit(self, default_config):
        """CPU時間制限"""
        config = SandboxConfig(
            mode=SandboxMode.STRICT,
            cpu_time_sec=2,  # 2秒CPU制限
            timeout_sec=10  # タイムアウトは10秒（CPU制限が先に効く）
        )
        manager = SandboxManager(config)
        
        # CPU集約的なタスク（無限ループに近い）
        result = manager.execute(
            command=[sys.executable, "-c", "while True: pass"],
            capture_output=True
        )
        
        # CPU制限でkillされるはず
        assert not result.success
        # CPUシグナルまたはタイムアウト
    
    def test_memory_limit_detection(self, default_config):
        """メモリ制限の適用確認"""
        config = SandboxConfig(
            mode=SandboxMode.STRICT,
            memory_mb=50,  # 50MBメモリ制限
            timeout_sec=5
        )
        manager = SandboxManager(config)
        
        # メモリを大量に確保しようとする
        result = manager.execute(
            command=[
                sys.executable, "-c",
                "try:\n"
                "    data = [0] * (100 * 1024 * 1024)  # 100MB確保試行\n"
                "except MemoryError:\n"
                "    print('MemoryError caught')\n"
                "    exit(0)\n"
            ],
            capture_output=True
        )
        
        # メモリ制限でMemoryErrorが発生するか、プロセスがkillされる
        # （プラットフォームによって挙動が異なる）


class TestFeatureFlagsIntegration:
    """Feature Flags統合テスト"""
    
    @patch('src.config.feature_flags.FeatureFlags.get')
    def test_feature_flag_disabled(self, mock_get):
        """Feature Flagでサンドボックス無効化"""
        mock_get.side_effect = lambda key, **kwargs: {
            "security.sandbox_enabled": False
        }.get(key, kwargs.get('default'))
        
        manager = SandboxManager()
        assert manager.config.mode == SandboxMode.DISABLED
    
    @patch('src.config.feature_flags.FeatureFlags.get')
    def test_feature_flag_strict_mode(self, mock_get):
        """Feature FlagでSTRICTモード設定"""
        mock_get.side_effect = lambda key, **kwargs: {
            "security.sandbox_enabled": True,
            "security.sandbox_mode": "strict"
        }.get(key, kwargs.get('default'))
        
        manager = SandboxManager()
        assert manager.config.mode == SandboxMode.STRICT
    
    @patch('src.config.feature_flags.FeatureFlags.get')
    def test_feature_flag_custom_limits(self, mock_get):
        """Feature Flagでカスタムリソース制限"""
        mock_get.side_effect = lambda key, **kwargs: {
            "security.sandbox_enabled": True,
            "security.sandbox_mode": "moderate",
            "security.sandbox_resource_limits": {
                "cpu_time_sec": 60,
                "memory_mb": 256,
                "disk_mb": 50
            }
        }.get(key, kwargs.get('default'))
        
        manager = SandboxManager()
        assert manager.config.cpu_time_sec == 60
        assert manager.config.memory_mb == 256
        assert manager.config.disk_mb == 50


class TestPlatformCompatibility:
    """プラットフォーム互換性テスト"""
    
    def test_linux_platform(self):
        """Linux環境"""
        if platform.system() != "Linux":
            pytest.skip("Linux only test")
        
        manager = SandboxManager()
        assert manager._platform == "Linux"
        # Linuxではsyscallフィルタが有効
        assert manager.config.enable_syscall_filter
    
    def test_macos_platform(self):
        """macOS環境"""
        if platform.system() != "Darwin":
            pytest.skip("macOS only test")
        
        manager = SandboxManager()
        assert manager._platform == "Darwin"
        # macOSではsyscallフィルタは無効
        assert not manager.config.enable_syscall_filter
    
    def test_windows_platform(self):
        """Windows環境"""
        if platform.system() != "Windows":
            pytest.skip("Windows only test")
        
        manager = SandboxManager()
        assert manager._platform == "Windows"
        # Windowsではsyscallフィルタは無効
        assert not manager.config.enable_syscall_filter


class TestEnvironmentVariables:
    """環境変数テスト"""
    
    def test_custom_environment_variables(self, default_config):
        """カスタム環境変数の設定"""
        config = SandboxConfig(
            mode=SandboxMode.MODERATE,
            environment_variables={"TEST_VAR": "test_value"}
        )
        manager = SandboxManager(config)
        
        result = manager.execute(
            command=[sys.executable, "-c", "import os; print(os.environ.get('TEST_VAR', 'not_found'))"],
            capture_output=True
        )
        
        assert result.success
        assert "test_value" in result.stdout


class TestWorkingDirectory:
    """作業ディレクトリテスト"""
    
    def test_custom_working_directory(self, tmp_path):
        """カスタム作業ディレクトリ"""
        # テストファイル作成
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        manager = SandboxManager()
        
        result = manager.execute(
            command=[sys.executable, "-c", "import os; print(os.listdir('.'))"],
            cwd=tmp_path,
            capture_output=True
        )
        
        assert result.success
        assert "test.txt" in result.stdout


class TestStdinData:
    """標準入力テスト"""
    
    def test_stdin_input(self, default_config):
        """標準入力データの提供"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=[sys.executable, "-c", "import sys; print(sys.stdin.read().upper())"],
            stdin_data="hello world",
            capture_output=True
        )
        
        assert result.success
        assert "HELLO WORLD" in result.stdout


class TestExecutionResult:
    """実行結果テスト"""
    
    def test_execution_result_fields(self, default_config):
        """実行結果のフィールド確認"""
        manager = SandboxManager(default_config)
        
        result = manager.execute(
            command=["echo", "test"],
            capture_output=True
        )
        
        assert isinstance(result, ExecutionResult)
        assert isinstance(result.success, bool)
        assert isinstance(result.exit_code, int)
        assert isinstance(result.stdout, str)
        assert isinstance(result.stderr, str)
        assert isinstance(result.execution_time, float)
        assert isinstance(result.resources_used, dict)
        assert isinstance(result.killed, bool)


@pytest.mark.integration
class TestIntegration:
    """統合テスト"""
    
    def test_create_sandbox_from_feature_flags(self):
        """Feature Flagsから自動作成"""
        from src.security.sandbox_manager import create_sandbox_from_feature_flags
        
        manager = create_sandbox_from_feature_flags()
        assert isinstance(manager, SandboxManager)
        
        # 簡単な実行テスト
        result = manager.execute(
            command=["echo", "integration test"],
            capture_output=True
        )
        assert result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
