"""
システムコールフィルター (Issue #62)

Linux seccomp-bpfを使用したシステムコール制限。

機能:
- システムコールホワイトリスト/ブラックリスト
- seccomp-bpfフィルターの動的生成
- プロファイル管理（strict/moderate/permissive）

使用例:
    from src.security.syscall_filter import SyscallFilter, SyscallProfile
    
    filter = SyscallFilter(profile=SyscallProfile.STRICT)
    filter.apply()  # 現在のプロセスに適用

Note:
    - Linux専用（macOS/Windowsでは無視される）
    - seccomp-bpf適用後は制限を緩和できない（one-way）
    - 子プロセスに継承される

関連:
- Issue #62: 実行サンドボックス機能制限
- src/security/sandbox_manager.py: SandboxManager統合

作成日: 2025-10-17
"""

import logging
import platform
import sys
from enum import Enum
from typing import List, Optional, Set

logger = logging.getLogger(__name__)


class SyscallProfile(Enum):
    """システムコール制限プロファイル"""
    STRICT = "strict"          # 最小限のsyscallのみ許可
    MODERATE = "moderate"      # 一般的なsyscallを許可
    PERMISSIVE = "permissive"  # ネットワーク以外を許可


class SyscallFilter:
    """
    システムコールフィルター（Linux seccomp-bpf）
    
    seccompを使用して、プロセスが実行できるシステムコールを制限します。
    
    Attributes:
        profile: 適用するプロファイル
        allowed_syscalls: 許可するシステムコールのセット
        denied_syscalls: 拒否するシステムコールのセット
    """
    
    # STRICTプロファイル: 最小限のsyscall
    STRICT_SYSCALLS = {
        # ファイルI/O
        "read", "write", "open", "openat", "close", "stat", "fstat", "lstat",
        "access", "faccessat", "readlink", "readlinkat",
        
        # メモリ管理
        "brk", "mmap", "munmap", "mprotect", "mremap",
        
        # プロセス管理
        "exit", "exit_group", "wait4", "waitid",
        
        # 基本システム情報
        "getpid", "getppid", "getuid", "geteuid", "getgid", "getegid",
        "gettimeofday", "clock_gettime", "time",
        
        # シグナル
        "rt_sigaction", "rt_sigprocmask", "rt_sigreturn",
        
        # その他必須
        "arch_prctl", "set_tid_address", "set_robust_list",
        "futex", "getrandom"
    }
    
    # MODERATEプロファイル: 一般的なsyscall
    MODERATE_SYSCALLS = STRICT_SYSCALLS | {
        # 追加ファイル操作
        "lseek", "pread64", "pwrite64", "readv", "writev",
        "dup", "dup2", "dup3", "pipe", "pipe2",
        "fcntl", "ioctl", "flock",
        
        # ディレクトリ操作
        "getcwd", "chdir", "fchdir", "mkdir", "mkdirat", "rmdir",
        "getdents", "getdents64",
        
        # プロセス/スレッド
        "clone", "fork", "vfork", "execve", "execveat",
        "sched_yield", "sched_getaffinity", "sched_setaffinity",
        
        # リソース管理
        "getrlimit", "setrlimit", "prlimit64",
        "getrusage", "times",
        
        # 環境変数
        "getenv", "setenv", "unsetenv"
    }
    
    # PERMISSIVEプロファイル: ネットワーク以外
    PERMISSIVE_SYSCALLS = MODERATE_SYSCALLS | {
        # 追加I/O
        "sendfile", "splice", "tee", "vmsplice",
        "copy_file_range",
        
        # IPC
        "mq_open", "mq_timedsend", "mq_timedreceive", "mq_notify", "mq_getsetattr",
        "msgget", "msgsnd", "msgrcv", "msgctl",
        "semget", "semop", "semctl", "semtimedop",
        "shmget", "shmat", "shmdt", "shmctl",
        
        # メモリ高度操作
        "madvise", "mincore", "mlock", "munlock", "mlockall", "munlockall",
        
        # ファイルシステム
        "chmod", "fchmod", "chown", "fchown", "lchown",
        "link", "linkat", "unlink", "unlinkat", "symlink", "symlinkat",
        "rename", "renameat", "renameat2"
    }
    
    # 常に拒否するsyscall（危険な操作）
    ALWAYS_DENIED_SYSCALLS = {
        # ネットワーク（別途許可リストで管理）
        "socket", "connect", "bind", "listen", "accept", "accept4",
        "sendto", "recvfrom", "sendmsg", "recvmsg",
        "setsockopt", "getsockopt", "shutdown",
        
        # システム管理
        "reboot", "kexec_load", "kexec_file_load",
        "init_module", "finit_module", "delete_module",
        "mount", "umount", "umount2", "pivot_root",
        
        # セキュリティ
        "ptrace", "process_vm_readv", "process_vm_writev",
        "kcmp", "perf_event_open",
        
        # 特権操作
        "setuid", "setgid", "setreuid", "setregid",
        "setresuid", "setresgid", "setfsuid", "setfsgid",
        "capget", "capset"
    }
    
    def __init__(
        self,
        profile: SyscallProfile = SyscallProfile.MODERATE,
        custom_allowed: Optional[List[str]] = None,
        custom_denied: Optional[List[str]] = None
    ):
        """
        Args:
            profile: 適用するプロファイル
            custom_allowed: カスタム許可syscallリスト（プロファイルに追加）
            custom_denied: カスタム拒否syscallリスト（プロファイルから除外）
        """
        self.profile = profile
        self._platform = platform.system()
        
        # プロファイルに応じた許可syscallを設定
        if profile == SyscallProfile.STRICT:
            self.allowed_syscalls = self.STRICT_SYSCALLS.copy()
        elif profile == SyscallProfile.MODERATE:
            self.allowed_syscalls = self.MODERATE_SYSCALLS.copy()
        elif profile == SyscallProfile.PERMISSIVE:
            self.allowed_syscalls = self.PERMISSIVE_SYSCALLS.copy()
        else:
            self.allowed_syscalls = self.MODERATE_SYSCALLS.copy()
        
        # カスタム設定を適用
        if custom_allowed:
            self.allowed_syscalls.update(custom_allowed)
        
        if custom_denied:
            self.allowed_syscalls -= set(custom_denied)
        
        # 常に拒否するsyscallを除外
        self.allowed_syscalls -= self.ALWAYS_DENIED_SYSCALLS
        
        self.denied_syscalls = self.ALWAYS_DENIED_SYSCALLS.copy()
        
        logger.debug(
            f"SyscallFilter initialized: profile={profile.value}, "
            f"allowed={len(self.allowed_syscalls)}, denied={len(self.denied_syscalls)}"
        )
    
    def apply(self) -> bool:
        """
        現在のプロセスにseccompフィルターを適用
        
        Returns:
            bool: 適用成功時True、スキップ時False
        
        Note:
            - Linux以外ではスキップされる
            - 適用後は制限を緩和できない（one-way）
        """
        if self._platform != "Linux":
            logger.debug(f"Seccomp not supported on {self._platform}, skipping")
            return False
        
        try:
            # seccompライブラリのインポート
            import seccomp
            
            logger.info(f"Applying seccomp filter: profile={self.profile.value}")
            
            # seccompフィルターを作成
            filter = seccomp.SyscallFilter(defaction=seccomp.ERRNO(1))  # デフォルトで拒否
            
            # 許可syscallを追加
            for syscall_name in self.allowed_syscalls:
                try:
                    syscall_num = seccomp.resolve_syscall(syscall_name)
                    filter.add_rule(seccomp.ALLOW, syscall_num)
                except ValueError:
                    # syscallが存在しない場合（アーキテクチャ依存）
                    logger.debug(f"Syscall not found: {syscall_name}")
            
            # フィルターをロード
            filter.load()
            
            logger.info(
                f"Seccomp filter applied successfully: "
                f"{len(self.allowed_syscalls)} syscalls allowed"
            )
            return True
            
        except ImportError:
            logger.warning(
                "seccomp library not available. Install with: pip install seccomp"
            )
            return False
        except Exception as e:
            logger.error(f"Failed to apply seccomp filter: {e}", exc_info=True)
            return False
    
    def get_profile_info(self) -> dict:
        """プロファイル情報を取得"""
        return {
            "profile": self.profile.value,
            "platform": self._platform,
            "allowed_count": len(self.allowed_syscalls),
            "denied_count": len(self.denied_syscalls),
            "supported": self._platform == "Linux"
        }
    
    @classmethod
    def create_preexec_fn(
        cls,
        profile: SyscallProfile = SyscallProfile.MODERATE,
        custom_allowed: Optional[List[str]] = None,
        custom_denied: Optional[List[str]] = None
    ):
        """
        subprocess.Popen用のpreexec_fn関数を生成
        
        Args:
            profile: 適用するプロファイル
            custom_allowed: カスタム許可syscallリスト
            custom_denied: カスタム拒否syscallリスト
        
        Returns:
            callable: preexec_fn関数
        
        使用例:
            import subprocess
            from src.security.syscall_filter import SyscallFilter, SyscallProfile
            
            preexec_fn = SyscallFilter.create_preexec_fn(SyscallProfile.STRICT)
            subprocess.Popen(
                ["python", "script.py"],
                preexec_fn=preexec_fn
            )
        """
        def preexec_fn():
            """子プロセス起動前に実行される関数"""
            try:
                filter = cls(profile, custom_allowed, custom_denied)
                filter.apply()
            except Exception:
                # preexec_fn内の例外はログに出力されないため、
                # 失敗しても継続（リソース制限は別途適用される）
                pass
        
        return preexec_fn


def is_seccomp_available() -> bool:
    """
    seccomp機能が利用可能かチェック
    
    Returns:
        bool: 利用可能な場合True
    """
    if platform.system() != "Linux":
        return False
    
    try:
        import seccomp
        return True
    except ImportError:
        return False


def get_syscall_name(syscall_number: int) -> Optional[str]:
    """
    システムコール番号から名前を取得
    
    Args:
        syscall_number: システムコール番号
    
    Returns:
        Optional[str]: システムコール名（見つからない場合None）
    """
    if not is_seccomp_available():
        return None
    
    try:
        import seccomp
        # seccompライブラリにはresolve_syscall()の逆関数がないため、
        # 代替実装が必要（今後の拡張）
        return None
    except Exception:
        return None


def validate_syscall_list(syscalls: List[str]) -> tuple[List[str], List[str]]:
    """
    システムコールリストの検証
    
    Args:
        syscalls: 検証するsyscallリスト
    
    Returns:
        tuple[List[str], List[str]]: (有効なsyscall, 無効なsyscall)
    """
    if not is_seccomp_available():
        return [], syscalls
    
    try:
        import seccomp
        
        valid = []
        invalid = []
        
        for syscall_name in syscalls:
            try:
                seccomp.resolve_syscall(syscall_name)
                valid.append(syscall_name)
            except ValueError:
                invalid.append(syscall_name)
        
        return valid, invalid
        
    except Exception:
        return [], syscalls
