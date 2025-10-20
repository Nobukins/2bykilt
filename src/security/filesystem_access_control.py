"""
ファイルシステムアクセス制御 (Issue #62b)

サンドボックス内でのファイルシステムアクセスを制御する。
allow/denyパスリストに基づいてアクセスを制限。

作成日: 2025-10-17
"""
import os
import logging
from pathlib import Path
from typing import List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AccessMode(Enum):
    """ファイルアクセスモード"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    ALL = "all"


@dataclass
class PathAccessRule:
    """パスアクセスルール"""
    path: str  # パスパターン (glob対応)
    mode: AccessMode = AccessMode.ALL
    allow: bool = True  # True=許可, False=拒否
    reason: str = ""  # ルールの理由


@dataclass
class FileSystemPolicy:
    """ファイルシステムアクセスポリシー"""
    # 許可パス（デフォルトで許可されるパス）
    allowed_paths: List[str] = field(default_factory=list)
    
    # 拒否パス（デフォルトで拒否されるパス）
    denied_paths: List[str] = field(default_factory=list)
    
    # デフォルトポリシー: True=許可, False=拒否
    default_allow: bool = True
    
    # 読み取り専用モード
    read_only: bool = False
    
    # パストラバーサル検出
    detect_path_traversal: bool = True
    
    # シンボリックリンク追跡を許可
    follow_symlinks: bool = False


class FileSystemAccessControl:
    """
    ファイルシステムアクセス制御
    
    サンドボックス内でのファイルアクセスを制御する。
    """
    
    # システムで常に拒否すべきパス
    ALWAYS_DENIED_PATHS = [
        "/etc/passwd",
        "/etc/shadow",
        "/etc/sudoers",
        "~/.ssh/",
        "~/.aws/",
        "~/.config/gcloud/",
        "/proc/*/mem",
        "/sys/kernel/",
        "C:\\Windows\\System32\\config\\",
        "C:\\Windows\\System32\\drivers\\",
    ]
    
    # システムで読み取り専用にすべきパス
    SYSTEM_READ_ONLY_PATHS = [
        "/etc/",
        "/usr/",
        "/lib/",
        "/lib64/",
        "C:\\Windows\\",
        "C:\\Program Files\\",
    ]
    
    def __init__(self, policy: Optional[FileSystemPolicy] = None):
        """
        ファイルシステムアクセス制御を初期化
        
        Args:
            policy: アクセスポリシー（省略時はデフォルト）
        """
        self.policy = policy or FileSystemPolicy()
        self._normalize_paths()
    
    def _normalize_paths(self):
        """パスを正規化（絶対パス、~展開）"""
        self.policy.allowed_paths = [
            os.path.abspath(os.path.expanduser(p))
            for p in self.policy.allowed_paths
        ]
        self.policy.denied_paths = [
            os.path.abspath(os.path.expanduser(p))
            for p in self.policy.denied_paths
        ]
    
    def is_path_allowed(
        self,
        path: str,
        mode: AccessMode = AccessMode.READ
    ) -> tuple[bool, str]:
        """
        パスへのアクセスが許可されているかチェック
        
        Args:
            path: チェックするパス
            mode: アクセスモード
            
        Returns:
            (許可/拒否, 理由)
        """
        # パスを正規化
        try:
            abs_path = os.path.abspath(os.path.expanduser(path))
            real_path = os.path.realpath(abs_path) if self.policy.follow_symlinks else abs_path
        except Exception as e:
            return False, f"Invalid path: {e}"
        
        # パストラバーサル検出
        if self.policy.detect_path_traversal and self._is_path_traversal(path):
            logger.warning(f"Path traversal detected: {path}")
            return False, "Path traversal detected"
        
        # 常に拒否されるパスをチェック
        for denied in self.ALWAYS_DENIED_PATHS:
            denied_abs = os.path.abspath(os.path.expanduser(denied))
            if real_path.startswith(denied_abs):
                logger.warning(f"Access to sensitive path denied: {real_path}")
                return False, f"Sensitive system path: {denied}"
        
        # 読み取り専用モード
        if self.policy.read_only and mode in [AccessMode.WRITE, AccessMode.ALL]:
            logger.info(f"Write access denied (read-only mode): {real_path}")
            return False, "Read-only mode enabled"
        
        # システム読み取り専用パスへの書き込みチェック
        for readonly_path in self.SYSTEM_READ_ONLY_PATHS:
            readonly_abs = os.path.abspath(os.path.expanduser(readonly_path))
            if real_path.startswith(readonly_abs) and mode in [AccessMode.WRITE, AccessMode.ALL]:
                return False, f"System read-only path: {readonly_path}"
        
        # 明示的に拒否されているパスをチェック
        for denied in self.policy.denied_paths:
            if real_path.startswith(denied):
                logger.info(f"Access denied by policy: {real_path}")
                return False, f"Denied by policy: {denied}"
        
        # 明示的に許可されているパスをチェック
        for allowed in self.policy.allowed_paths:
            if real_path.startswith(allowed):
                logger.debug(f"Access allowed: {real_path}")
                return True, "Allowed by policy"
        
        # デフォルトポリシーを適用
        if self.policy.default_allow:
            logger.debug(f"Access allowed by default: {real_path}")
            return True, "Allowed by default"
        else:
            logger.info(f"Access denied by default: {real_path}")
            return False, "Denied by default"
    
    def _is_path_traversal(self, path: str) -> bool:
        """
        パストラバーサル攻撃を検出
        
        Args:
            path: チェックするパス
            
        Returns:
            パストラバーサルが検出された場合True
        """
        # 危険なパターン
        dangerous_patterns = [
            "..",
            "%2e%2e",
            "..%2f",
            "..\\",
            "%252e%252e",
        ]
        
        path_lower = path.lower()
        return any(pattern in path_lower for pattern in dangerous_patterns)
    
    def validate_file_operation(
        self,
        operation: str,
        path: str,
        mode: AccessMode = AccessMode.READ
    ) -> tuple[bool, str]:
        """
        ファイル操作を検証
        
        Args:
            operation: 操作名（open, read, write等）
            path: 操作対象パス
            mode: アクセスモード
            
        Returns:
            (許可/拒否, 理由)
        """
        logger.debug(f"Validating {operation} on {path} (mode={mode.value})")
        
        allowed, reason = self.is_path_allowed(path, mode)
        
        if not allowed:
            logger.warning(f"File operation denied: {operation} on {path} - {reason}")
        
        return allowed, reason
    
    def get_safe_workspace(self, workspace_dir: str) -> str:
        """
        安全なワークスペースディレクトリを取得
        
        Args:
            workspace_dir: 基底ワークスペースディレクトリ
            
        Returns:
            検証済みの安全なワークスペースパス
        """
        abs_workspace = os.path.abspath(workspace_dir)
        
        # ワークスペースが許可パスに含まれているか確認
        allowed, reason = self.is_path_allowed(abs_workspace, AccessMode.ALL)
        
        if not allowed:
            raise PermissionError(f"Workspace directory not allowed: {reason}")
        
        return abs_workspace


def create_default_policy() -> FileSystemPolicy:
    """
    デフォルトのファイルシステムポリシーを作成
    
    Returns:
        デフォルトポリシー
    """
    import tempfile
    
    return FileSystemPolicy(
        allowed_paths=[
            tempfile.gettempdir(),  # /tmp または C:\Temp
            "./",  # カレントディレクトリ
        ],
        denied_paths=[
            "~/.ssh/",
            "~/.aws/",
            "/etc/",
        ],
        default_allow=False,  # デフォルトは拒否
        read_only=False,
        detect_path_traversal=True,
        follow_symlinks=False
    )


def create_strict_policy(workspace_dir: str) -> FileSystemPolicy:
    """
    厳格なファイルシステムポリシーを作成
    
    Args:
        workspace_dir: ワークスペースディレクトリ
        
    Returns:
        厳格なポリシー
    """
    return FileSystemPolicy(
        allowed_paths=[
            os.path.abspath(workspace_dir),  # ワークスペースのみ
        ],
        denied_paths=[],
        default_allow=False,  # ワークスペース以外は拒否
        read_only=False,
        detect_path_traversal=True,
        follow_symlinks=False
    )


def create_read_only_policy(allowed_dirs: List[str]) -> FileSystemPolicy:
    """
    読み取り専用ファイルシステムポリシーを作成
    
    Args:
        allowed_dirs: 読み取りを許可するディレクトリリスト
        
    Returns:
        読み取り専用ポリシー
    """
    return FileSystemPolicy(
        allowed_paths=[os.path.abspath(d) for d in allowed_dirs],
        denied_paths=[],
        default_allow=False,
        read_only=True,  # 読み取り専用
        detect_path_traversal=True,
        follow_symlinks=False
    )
