"""
Windows Job Objects サンドボックス実装 (Issue #62)

Windows環境でのリソース制限をJob Objectsを使用して実装。

参考:
- https://docs.microsoft.com/en-us/windows/win32/api/jobapi2/
- https://docs.microsoft.com/en-us/windows/win32/procthread/job-objects

作成日: 2025-10-17
"""
import sys
import logging
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Windows専用モジュールのインポート
if sys.platform == "win32":
    try:
        import win32job
        import win32api
        import win32con
        import win32process
        import pywintypes
        WINDOWS_JOB_AVAILABLE = True
    except ImportError:
        logger.warning("pywin32 not available, Windows Job Objects will not be used")
        WINDOWS_JOB_AVAILABLE = False
else:
    WINDOWS_JOB_AVAILABLE = False


@dataclass
class WindowsJobLimits:
    """Windows Job Objectの制限設定"""
    cpu_time_sec: int = 300  # CPU時間制限（秒）
    memory_mb: int = 512  # メモリ制限（MB）
    max_processes: int = 10  # 最大プロセス数
    
    def to_bytes(self, mb: int) -> int:
        """MBをバイトに変換"""
        return mb * 1024 * 1024
    
    def to_100ns(self, seconds: int) -> int:
        """秒を100ナノ秒単位に変換（Windows時間単位）"""
        return seconds * 10_000_000


class WindowsJobObject:
    """
    Windows Job Object ラッパークラス
    
    リソース制限を適用したJob Objectを作成・管理する。
    """
    
    def __init__(self, limits: WindowsJobLimits):
        """
        Job Objectを初期化
        
        Args:
            limits: リソース制限設定
        """
        self.limits = limits
        self.job_handle = None
        
        if not WINDOWS_JOB_AVAILABLE:
            raise RuntimeError("Windows Job Objects not available (pywin32 not installed)")
    
    def create(self) -> "WindowsJobObject":
        """
        Job Objectを作成してリソース制限を設定
        
        Returns:
            self (for method chaining)
        """
        if not WINDOWS_JOB_AVAILABLE:
            raise RuntimeError("Windows Job Objects not available")
        
        try:
            # Job Objectを作成
            self.job_handle = win32job.CreateJobObject(None, "")
            
            # 基本制限情報を設定
            info = win32job.QueryInformationJobObject(
                self.job_handle,
                win32job.JobObjectBasicLimitInformation
            )
            
            # CPU時間制限
            info['PerProcessUserTimeLimit'] = self.limits.to_100ns(self.limits.cpu_time_sec)
            
            # プロセス数制限
            info['ActiveProcessLimit'] = self.limits.max_processes
            
            # 制限フラグを設定
            info['LimitFlags'] = (
                win32job.JOB_OBJECT_LIMIT_PROCESS_TIME |
                win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS |
                win32job.JOB_OBJECT_LIMIT_DIE_ON_UNHANDLED_EXCEPTION |
                win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            )
            
            # 基本制限を適用
            win32job.SetInformationJobObject(
                self.job_handle,
                win32job.JobObjectBasicLimitInformation,
                info
            )
            
            # 拡張制限情報（メモリ制限）
            try:
                ext_info = win32job.QueryInformationJobObject(
                    self.job_handle,
                    win32job.JobObjectExtendedLimitInformation
                )
                
                # メモリ制限
                ext_info['ProcessMemoryLimit'] = self.limits.to_bytes(self.limits.memory_mb)
                ext_info['JobMemoryLimit'] = self.limits.to_bytes(self.limits.memory_mb * 2)
                
                # 拡張制限フラグを追加
                ext_info['BasicLimitInformation']['LimitFlags'] |= (
                    win32job.JOB_OBJECT_LIMIT_PROCESS_MEMORY |
                    win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
                )
                
                # 拡張制限を適用
                win32job.SetInformationJobObject(
                    self.job_handle,
                    win32job.JobObjectExtendedLimitInformation,
                    ext_info
                )
                
                logger.info(f"Windows Job Object created with limits: "
                          f"CPU={self.limits.cpu_time_sec}s, "
                          f"Memory={self.limits.memory_mb}MB, "
                          f"Processes={self.limits.max_processes}")
                
            except Exception as e:
                logger.warning(f"Failed to set extended limits: {e}")
            
            return self
            
        except Exception as e:
            logger.error(f"Failed to create Windows Job Object: {e}")
            if self.job_handle:
                self.close()
            raise
    
    def assign_process(self, process_handle) -> bool:
        """
        プロセスをJob Objectに割り当て
        
        Args:
            process_handle: プロセスハンドル
            
        Returns:
            成功した場合True
        """
        if not self.job_handle:
            raise RuntimeError("Job Object not created")
        
        try:
            win32job.AssignProcessToJobObject(self.job_handle, process_handle)
            logger.debug(f"Process assigned to Job Object")
            return True
        except pywintypes.error as e:
            logger.error(f"Failed to assign process to Job Object: {e}")
            return False
    
    def close(self):
        """Job Objectをクローズ"""
        if self.job_handle:
            try:
                # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSEが設定されているため、
                # ハンドルをクローズすると全プロセスが終了する
                win32api.CloseHandle(self.job_handle)
                logger.debug("Job Object closed")
            except Exception as e:
                logger.error(f"Failed to close Job Object: {e}")
            finally:
                self.job_handle = None
    
    def __enter__(self):
        """Context managerのenter"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context managerのexit"""
        self.close()


def is_job_object_available() -> bool:
    """
    Windows Job Objectsが利用可能かチェック
    
    Returns:
        利用可能な場合True
    """
    return WINDOWS_JOB_AVAILABLE


def create_job_object(
    cpu_time_sec: int = 300,
    memory_mb: int = 512,
    max_processes: int = 10
) -> Optional[WindowsJobObject]:
    """
    Job Objectを作成（簡易ヘルパー関数）
    
    Args:
        cpu_time_sec: CPU時間制限（秒）
        memory_mb: メモリ制限（MB）
        max_processes: 最大プロセス数
        
    Returns:
        作成されたJob Object、または失敗時None
    """
    if not is_job_object_available():
        logger.warning("Windows Job Objects not available")
        return None
    
    try:
        limits = WindowsJobLimits(
            cpu_time_sec=cpu_time_sec,
            memory_mb=memory_mb,
            max_processes=max_processes
        )
        return WindowsJobObject(limits).create()
    except Exception as e:
        logger.error(f"Failed to create Job Object: {e}")
        return None
