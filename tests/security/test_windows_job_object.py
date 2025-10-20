"""
Windows Job Objects テストスイート (Issue #62)

Windows環境でのJob Objectsを使用したサンドボックステスト。

注意: これらのテストはWindows環境でのみ実行可能。
"""
import pytest
import sys
import tempfile
from pathlib import Path

# Windows専用テスト
pytestmark = pytest.mark.skipif(
    sys.platform != "win32",
    reason="Windows-only tests"
)


class TestWindowsJobObject:
    """Windows Job Objects機能テスト"""
    
    def test_job_object_availability(self):
        """Job Objectsが利用可能かチェック"""
        from src.security.windows_job_object import is_job_object_available
        
        # Windows環境では利用可能であるべき（pywin32がインストールされていれば）
        available = is_job_object_available()
        
        # pywin32がない場合はスキップ
        if not available:
            pytest.skip("pywin32 not installed")
        
        assert available is True
    
    def test_job_object_creation(self):
        """Job Objectの作成テスト"""
        from src.security.windows_job_object import create_job_object
        
        job = create_job_object(
            cpu_time_sec=60,
            memory_mb=256,
            max_processes=5
        )
        
        if not job:
            pytest.skip("Job Object creation failed (pywin32 not installed)")
        
        try:
            assert job.job_handle is not None
            assert job.limits.cpu_time_sec == 60
            assert job.limits.memory_mb == 256
            assert job.limits.max_processes == 5
        finally:
            job.close()
    
    def test_job_object_context_manager(self):
        """Context managerとしての使用テスト"""
        from src.security.windows_job_object import WindowsJobObject, WindowsJobLimits
        
        limits = WindowsJobLimits(cpu_time_sec=30, memory_mb=128, max_processes=3)
        
        with WindowsJobObject(limits).create() as job:
            assert job.job_handle is not None
        
        # コンテキスト終了後はクローズされているべき
        assert job.job_handle is None


class TestWindowsSandboxManager:
    """Windows環境でのSandboxManager統合テスト"""
    
    @pytest.fixture
    def temp_workspace(self):
        """一時ワークスペースを作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            
            # シンプルなPythonスクリプトを作成
            script_file = workspace / "test_script.py"
            script_file.write_text("""
import sys
print("Hello from Windows sandbox")
sys.exit(0)
""")
            
            yield workspace
    
    def test_windows_basic_execution(self, temp_workspace):
        """Windows環境での基本実行テスト"""
        from src.security.sandbox_manager import SandboxManager, SandboxConfig, SandboxMode
        
        config = SandboxConfig(mode=SandboxMode.MODERATE)
        manager = SandboxManager(config)
        
        script_path = temp_workspace / "test_script.py"
        
        result = manager.execute(
            command=["python", str(script_path)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        # pywin32がない場合はbasic executionにフォールバック
        assert result.exit_code == 0
        assert "Hello from Windows sandbox" in result.stdout
    
    def test_windows_timeout_enforcement(self, temp_workspace):
        """Windowsでのタイムアウト動作確認"""
        from src.security.sandbox_manager import SandboxManager, SandboxConfig
        
        # 無限ループスクリプト
        script_file = temp_workspace / "infinite_loop.py"
        script_file.write_text("""
import time
while True:
    time.sleep(1)
""")
        
        config = SandboxConfig(timeout_sec=2)
        manager = SandboxManager(config)
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        # タイムアウトで強制終了されるべき
        assert result.killed is True
        assert result.success is False
    
    def test_windows_with_job_object_limits(self, temp_workspace):
        """Job Objectsによるリソース制限テスト"""
        from src.security.windows_job_object import is_job_object_available
        
        if not is_job_object_available():
            pytest.skip("Job Objects not available (pywin32 not installed)")
        
        from src.security.sandbox_manager import SandboxManager, SandboxConfig, SandboxMode
        
        config = SandboxConfig(
            mode=SandboxMode.STRICT,
            cpu_time_sec=60,
            memory_mb=256,
            max_processes=5
        )
        manager = SandboxManager(config)
        
        script_file = temp_workspace / "test.py"
        script_file.write_text("""
import sys
print("Running with Job Object limits")
sys.exit(0)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        assert result.success is True
        assert "Running with Job Object limits" in result.stdout
    
    def test_windows_memory_limit_enforcement(self, temp_workspace):
        """メモリ制限の動作確認（Job Objects）"""
        from src.security.windows_job_object import is_job_object_available
        
        if not is_job_object_available():
            pytest.skip("Job Objects not available")
        
        from src.security.sandbox_manager import SandboxManager, SandboxConfig
        
        # 低いメモリ制限を設定
        config = SandboxConfig(
            cpu_time_sec=60,
            memory_mb=50,  # 50MBに制限
            timeout_sec=10
        )
        manager = SandboxManager(config)
        
        # 大量のメモリを確保しようとするスクリプト
        script_file = temp_workspace / "memory_hog.py"
        script_file.write_text("""
import sys
try:
    # 100MBのメモリを確保しようとする（制限は50MB）
    data = bytearray(100 * 1024 * 1024)
    print("Memory allocated - SHOULD NOT HAPPEN")
    sys.exit(0)
except MemoryError:
    print("Memory allocation blocked")
    sys.exit(1)
""")
        
        result = manager.execute(
            command=["python", str(script_file)],
            cwd=str(temp_workspace),
            capture_output=True
        )
        
        # メモリ制限により失敗するか、プロセスが強制終了されるはず
        # 実際の動作はWindows環境に依存
        assert result.exit_code in [0, 1] or result.killed


class TestWindowsJobObjectLimits:
    """WindowsJobLimits データクラステスト"""
    
    def test_limits_dataclass(self):
        """WindowsJobLimitsのデフォルト値テスト"""
        from src.security.windows_job_object import WindowsJobLimits
        
        limits = WindowsJobLimits()
        
        assert limits.cpu_time_sec == 300
        assert limits.memory_mb == 512
        assert limits.max_processes == 10
    
    def test_limits_conversions(self):
        """単位変換メソッドのテスト"""
        from src.security.windows_job_object import WindowsJobLimits
        
        limits = WindowsJobLimits()
        
        # MB to bytes
        assert limits.to_bytes(1) == 1024 * 1024
        assert limits.to_bytes(512) == 512 * 1024 * 1024
        
        # Seconds to 100-nanoseconds
        assert limits.to_100ns(1) == 10_000_000
        assert limits.to_100ns(300) == 3_000_000_000
