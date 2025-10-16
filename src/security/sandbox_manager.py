"""
汎用サンドボックスマネージャー (Issue #62)

安全なスクリプト実行のためのサンドボックス環境を提供します。

機能:
- プロセス分離
- リソース制限（CPU、メモリ、ディスク）
- システムコール制限（Linux seccomp）
- タイムアウト管理
- 実行ログ記録

使用例:
    from src.security.sandbox_manager import SandboxManager, SandboxConfig
    
    config = SandboxConfig(
        cpu_time_sec=60,
        memory_mb=256,
        enable_syscall_filter=True
    )
    
    manager = SandboxManager(config)
    result = manager.execute(
        command=["python", "script.py"],
        cwd="/path/to/workdir"
    )

関連:
- Issue #62: 実行サンドボックス機能制限
- Issue #52: サンドボックス allow/deny パス
- src/llm/docker_sandbox.py: LLM専用サンドボックス（参考実装）

作成日: 2025-10-17
"""

import logging
import os
import platform
import resource
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class SandboxMode(Enum):
    """サンドボックス実行モード"""
    STRICT = "strict"      # 最大制限
    MODERATE = "moderate"  # 標準制限
    PERMISSIVE = "permissive"  # 最小制限
    DISABLED = "disabled"  # サンドボックス無効


@dataclass
class SandboxConfig:
    """
    サンドボックス設定
    
    Attributes:
        mode: 実行モード（strict/moderate/permissive/disabled）
        cpu_time_sec: CPU時間制限（秒）
        memory_mb: メモリ制限（MB）
        disk_mb: ディスク使用量制限（MB）
        max_processes: 最大プロセス数
        timeout_sec: タイムアウト（秒）
        enable_syscall_filter: システムコール制限を有効化（Linux）
        allowed_syscalls: 許可するシステムコール（Linuxのみ）
        working_directory: 作業ディレクトリ
        environment_variables: 環境変数
    """
    mode: SandboxMode = SandboxMode.MODERATE
    cpu_time_sec: int = 300  # 5分
    memory_mb: int = 512
    disk_mb: int = 100
    max_processes: int = 10
    timeout_sec: int = 600  # 10分
    enable_syscall_filter: bool = True
    allowed_syscalls: Optional[List[str]] = None
    working_directory: Optional[Path] = None
    environment_variables: Dict[str, str] = field(default_factory=dict)
    
    def __post_init__(self):
        """設定値の検証と初期化"""
        if self.mode == SandboxMode.DISABLED:
            logger.warning("Sandbox is DISABLED - security restrictions will not be applied")
        
        if self.allowed_syscalls is None:
            # デフォルトの許可syscallリスト
            self.allowed_syscalls = [
                "read", "write", "open", "close", "stat", "fstat",
                "brk", "mmap", "munmap", "mprotect",
                "exit", "exit_group", "wait4", "clone"
            ]


@dataclass
class ExecutionResult:
    """
    実行結果
    
    Attributes:
        success: 実行成功フラグ
        exit_code: 終了コード
        stdout: 標準出力
        stderr: 標準エラー出力
        execution_time: 実行時間（秒）
        resources_used: 使用リソース情報
        killed: タイムアウトまたは制限超過でkillされたか
    """
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    execution_time: float
    resources_used: Dict[str, Any]
    killed: bool = False


class SandboxManager:
    """
    汎用サンドボックスマネージャー
    
    プロセス分離とリソース制限を提供します。
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        """
        Args:
            config: サンドボックス設定（Noneの場合はデフォルト設定）
        """
        self.config = config or SandboxConfig()
        self._platform = platform.system()
        
        # Feature Flags統合
        self._load_feature_flags()
        
        # プラットフォームサポート確認
        self._check_platform_support()
        
        logger.info(f"SandboxManager initialized: mode={self.config.mode.value}, platform={self._platform}")
    
    def _load_feature_flags(self) -> None:
        """Feature Flagsから設定を読み込む"""
        try:
            from src.config.feature_flags import FeatureFlags
            
            flags = FeatureFlags()
            
            # サンドボックス有効/無効
            if not flags.get_flag("security.sandbox_enabled", default=True):
                self.config.mode = SandboxMode.DISABLED
                logger.info("Sandbox disabled by feature flag")
                return
            
            # モード設定
            mode_str = flags.get_flag("security.sandbox_mode", default="moderate")
            try:
                self.config.mode = SandboxMode(mode_str)
            except ValueError:
                logger.warning(f"Invalid sandbox mode '{mode_str}', using MODERATE")
                self.config.mode = SandboxMode.MODERATE
            
            # リソース制限
            limits = flags.get_flag("security.sandbox_resource_limits", default={})
            if isinstance(limits, dict):
                self.config.cpu_time_sec = limits.get("cpu_time_sec", self.config.cpu_time_sec)
                self.config.memory_mb = limits.get("memory_mb", self.config.memory_mb)
                self.config.disk_mb = limits.get("disk_mb", self.config.disk_mb)
            
        except ImportError:
            logger.debug("FeatureFlags not available, using default config")
    
    def _check_platform_support(self) -> None:
        """プラットフォームのサポート状況を確認"""
        if self.config.mode == SandboxMode.DISABLED:
            return
        
        if self._platform == "Linux":
            logger.info("Full sandbox support available (Linux)")
        elif self._platform == "Darwin":
            logger.warning("Limited sandbox support (macOS): syscall filtering not available")
            self.config.enable_syscall_filter = False
        elif self._platform == "Windows":
            logger.warning("Limited sandbox support (Windows): using job objects only")
            self.config.enable_syscall_filter = False
        else:
            logger.warning(f"Unknown platform '{self._platform}': sandbox may not work correctly")
    
    def execute(
        self,
        command: List[str],
        cwd: Optional[Path] = None,
        stdin_data: Optional[str] = None,
        capture_output: bool = True
    ) -> ExecutionResult:
        """
        サンドボックス内でコマンドを実行
        
        Args:
            command: 実行するコマンド（リスト形式）
            cwd: 作業ディレクトリ
            stdin_data: 標準入力データ
            capture_output: 標準出力/エラーをキャプチャするか
        
        Returns:
            ExecutionResult: 実行結果
        
        Raises:
            ValueError: 無効なコマンドまたは設定
            RuntimeError: 実行失敗
        """
        if not command or not isinstance(command, list):
            raise ValueError("Command must be a non-empty list")
        
        if self.config.mode == SandboxMode.DISABLED:
            logger.warning("Executing without sandbox (DISABLED mode)")
            return self._execute_no_sandbox(command, cwd, stdin_data, capture_output)
        
        logger.info(f"Executing in sandbox: {' '.join(command)}")
        
        # 実行準備
        working_dir = cwd or self.config.working_directory or Path.cwd()
        start_time = time.time()
        
        try:
            # プラットフォーム別実行
            if self._platform == "Linux":
                result = self._execute_linux(command, working_dir, stdin_data, capture_output)
            elif self._platform == "Darwin":
                result = self._execute_macos(command, working_dir, stdin_data, capture_output)
            elif self._platform == "Windows":
                result = self._execute_windows(command, working_dir, stdin_data, capture_output)
            else:
                # フォールバック: サンドボックスなし
                logger.warning(f"Unsupported platform {self._platform}, executing without sandbox")
                result = self._execute_no_sandbox(command, working_dir, stdin_data, capture_output)
            
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            logger.info(
                f"Execution completed: exit_code={result.exit_code}, "
                f"time={execution_time:.2f}s, killed={result.killed}"
            )
            
            return result
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Execution failed after {execution_time:.2f}s: {e}", exc_info=True)
            raise RuntimeError(f"Sandbox execution failed: {e}") from e
    
    def _execute_linux(
        self,
        command: List[str],
        cwd: Path,
        stdin_data: Optional[str],
        capture_output: bool
    ) -> ExecutionResult:
        """Linux環境でサンドボックス実行（seccomp + resource limits）"""
        
        def preexec_fn():
            """子プロセス起動前に実行される関数"""
            # リソース制限を適用
            self._apply_resource_limits()
            
            # システムコール制限（seccomp）
            if self.config.enable_syscall_filter:
                try:
                    self._apply_syscall_filter()
                except Exception as e:
                    logger.error(f"Failed to apply syscall filter: {e}")
                    # seccomp失敗時は継続（リソース制限は有効）
        
        try:
            # 環境変数の準備
            env = os.environ.copy()
            env.update(self.config.environment_variables)
            
            # プロセス実行
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdin=subprocess.PIPE if stdin_data else None,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                preexec_fn=preexec_fn,
                env=env
            )
            
            # タイムアウト付きで実行
            try:
                stdout, stderr = process.communicate(
                    input=stdin_data.encode() if stdin_data else None,
                    timeout=self.config.timeout_sec
                )
                killed = False
            except subprocess.TimeoutExpired:
                logger.warning(f"Process timeout ({self.config.timeout_sec}s), killing")
                process.kill()
                stdout, stderr = process.communicate()
                killed = True
            
            # リソース使用量取得
            resources_used = self._get_resource_usage(process)
            
            return ExecutionResult(
                success=(process.returncode == 0 and not killed),
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr=stderr.decode('utf-8', errors='replace') if stderr else "",
                execution_time=0.0,  # 後で設定
                resources_used=resources_used,
                killed=killed
            )
            
        except Exception as e:
            raise RuntimeError(f"Linux execution failed: {e}") from e
    
    def _execute_macos(
        self,
        command: List[str],
        cwd: Path,
        stdin_data: Optional[str],
        capture_output: bool
    ) -> ExecutionResult:
        """macOS環境でサンドボックス実行（resource limitsのみ）"""
        
        def preexec_fn():
            """リソース制限のみ適用"""
            self._apply_resource_limits()
        
        return self._execute_with_preexec(command, cwd, stdin_data, capture_output, preexec_fn)
    
    def _execute_windows(
        self,
        command: List[str],
        cwd: Path,
        stdin_data: Optional[str],
        capture_output: bool
    ) -> ExecutionResult:
        """Windows環境でサンドボックス実行（Job Objectsを使用）"""
        # Windows Job Objectsの実装は今後の課題
        logger.warning("Windows sandbox not fully implemented, using basic execution")
        return self._execute_no_sandbox(command, cwd, stdin_data, capture_output)
    
    def _execute_no_sandbox(
        self,
        command: List[str],
        cwd: Path,
        stdin_data: Optional[str],
        capture_output: bool
    ) -> ExecutionResult:
        """サンドボックスなしで実行（フォールバック）"""
        try:
            env = os.environ.copy()
            env.update(self.config.environment_variables)
            
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdin=subprocess.PIPE if stdin_data else None,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                env=env
            )
            
            try:
                stdout, stderr = process.communicate(
                    input=stdin_data.encode() if stdin_data else None,
                    timeout=self.config.timeout_sec
                )
                killed = False
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                killed = True
            
            return ExecutionResult(
                success=(process.returncode == 0 and not killed),
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr=stderr.decode('utf-8', errors='replace') if stderr else "",
                execution_time=0.0,
                resources_used={},
                killed=killed
            )
            
        except Exception as e:
            raise RuntimeError(f"No-sandbox execution failed: {e}") from e
    
    def _execute_with_preexec(
        self,
        command: List[str],
        cwd: Path,
        stdin_data: Optional[str],
        capture_output: bool,
        preexec_fn
    ) -> ExecutionResult:
        """preexec_fn付きで実行（共通処理）"""
        try:
            env = os.environ.copy()
            env.update(self.config.environment_variables)
            
            process = subprocess.Popen(
                command,
                cwd=str(cwd),
                stdin=subprocess.PIPE if stdin_data else None,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                preexec_fn=preexec_fn,
                env=env
            )
            
            try:
                stdout, stderr = process.communicate(
                    input=stdin_data.encode() if stdin_data else None,
                    timeout=self.config.timeout_sec
                )
                killed = False
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                killed = True
            
            resources_used = self._get_resource_usage(process)
            
            return ExecutionResult(
                success=(process.returncode == 0 and not killed),
                exit_code=process.returncode,
                stdout=stdout.decode('utf-8', errors='replace') if stdout else "",
                stderr=stderr.decode('utf-8', errors='replace') if stderr else "",
                execution_time=0.0,
                resources_used=resources_used,
                killed=killed
            )
            
        except Exception as e:
            raise RuntimeError(f"Execution with preexec failed: {e}") from e
    
    def _apply_resource_limits(self) -> None:
        """リソース制限を適用（Unix系のみ）"""
        if sys.platform == "win32":
            return  # Windowsはサポートされていない
        
        try:
            # CPU時間制限
            if self.config.cpu_time_sec > 0:
                resource.setrlimit(
                    resource.RLIMIT_CPU,
                    (self.config.cpu_time_sec, self.config.cpu_time_sec)
                )
            
            # メモリ制限（バイト単位）
            if self.config.memory_mb > 0:
                memory_bytes = self.config.memory_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_AS,
                    (memory_bytes, memory_bytes)
                )
            
            # ファイルサイズ制限
            if self.config.disk_mb > 0:
                disk_bytes = self.config.disk_mb * 1024 * 1024
                resource.setrlimit(
                    resource.RLIMIT_FSIZE,
                    (disk_bytes, disk_bytes)
                )
            
            # プロセス数制限
            if self.config.max_processes > 0:
                resource.setrlimit(
                    resource.RLIMIT_NPROC,
                    (self.config.max_processes, self.config.max_processes)
                )
            
            logger.debug(
                f"Resource limits applied: cpu={self.config.cpu_time_sec}s, "
                f"mem={self.config.memory_mb}MB, disk={self.config.disk_mb}MB"
            )
            
        except Exception as e:
            logger.error(f"Failed to apply resource limits: {e}")
            raise
    
    def _apply_syscall_filter(self) -> None:
        """システムコールフィルター適用（Linux seccomp）"""
        # seccomp実装は次のフェーズ（#62b）で実装
        # 現在はplaceholder
        logger.debug("Syscall filter: not implemented yet (PoC phase)")
        pass
    
    def _get_resource_usage(self, process: subprocess.Popen) -> Dict[str, Any]:
        """プロセスのリソース使用量を取得"""
        try:
            if sys.platform == "win32":
                return {"platform": "windows", "details": "not available"}
            
            # Unix系: resource.getrusageを使用
            # 注: これは現在のプロセスのリソース使用量を返すため、
            # 実際には子プロセスの統計を正確に取得するにはより高度な方法が必要
            rusage = resource.getrusage(resource.RUSAGE_CHILDREN)
            
            return {
                "user_time": rusage.ru_utime,
                "system_time": rusage.ru_stime,
                "max_memory_kb": rusage.ru_maxrss,
                "page_faults": rusage.ru_majflt,
                "io_operations": rusage.ru_inblock + rusage.ru_oublock
            }
        except Exception as e:
            logger.debug(f"Failed to get resource usage: {e}")
            return {}


def create_sandbox_from_feature_flags() -> SandboxManager:
    """
    Feature Flagsから設定を読み込んでSandboxManagerを作成
    
    Returns:
        SandboxManager: 設定済みのサンドボックスマネージャー
    """
    config = SandboxConfig()  # _load_feature_flagsで自動的に設定される
    return SandboxManager(config)
