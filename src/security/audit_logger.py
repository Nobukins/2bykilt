"""
監査ログ詳細化 (Issue #62b)

サンドボックス実行の詳細な監査ログ記録。

作成日: 2025-10-17
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class AuditAction(Enum):
    """監査アクション"""
    SANDBOX_CREATE = "sandbox_create"
    SANDBOX_EXECUTE = "sandbox_execute"
    SANDBOX_COMPLETE = "sandbox_complete"
    SANDBOX_FAIL = "sandbox_fail"
    FILE_ACCESS = "file_access"
    NETWORK_ACCESS = "network_access"
    RESOURCE_LIMIT_HIT = "resource_limit_hit"
    POLICY_VIOLATION = "policy_violation"


@dataclass
class AuditEntry:
    """監査エントリ"""
    timestamp: str  # ISO 8601形式
    action: str
    result: str  # success, denied, error
    user: Optional[str] = None
    process_id: Optional[int] = None
    command: Optional[List[str]] = None
    workspace: Optional[str] = None
    exit_code: Optional[int] = None
    execution_time: Optional[float] = None
    resource_usage: Optional[Dict[str, Any]] = None
    security_violations: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.security_violations is None:
            self.security_violations = []
        if self.metadata is None:
            self.metadata = {}


class AuditLogger:
    """
    監査ログ記録システム
    
    サンドボックス実行の詳細な監査ログを記録。
    """
    
    def __init__(self, log_file: Optional[Path] = None):
        """
        監査ロガーを初期化
        
        Args:
            log_file: ログファイルパス（省略時はデフォルト）
        """
        self.log_file = log_file or Path("logs/sandbox_audit.jsonl")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Audit logger initialized: {self.log_file}")
    
    def log(self, entry: AuditEntry):
        """
        監査エントリを記録
        
        Args:
            entry: 監査エントリ
        """
        try:
            # JSON Lines形式で追記
            with open(self.log_file, "a", encoding="utf-8") as f:
                json_line = json.dumps(asdict(entry), ensure_ascii=False)
                f.write(json_line + "\n")
            
            logger.debug(f"Audit entry logged: {entry.action}")
            
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
    
    def log_sandbox_execution(
        self,
        command: List[str],
        workspace: str,
        result: str,
        exit_code: int,
        execution_time: float,
        resource_usage: Optional[Dict[str, Any]] = None,
        security_violations: Optional[List[str]] = None,
        process_id: Optional[int] = None,
        **metadata
    ):
        """
        サンドボックス実行を記録
        
        Args:
            command: 実行コマンド
            workspace: ワークスペースパス
            result: 実行結果 (success/denied/error)
            exit_code: 終了コード
            execution_time: 実行時間（秒）
            resource_usage: リソース使用状況
            security_violations: セキュリティ違反リスト
            process_id: プロセスID
            **metadata: 追加メタデータ
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=AuditAction.SANDBOX_EXECUTE.value,
            result=result,
            process_id=process_id,
            command=command,
            workspace=workspace,
            exit_code=exit_code,
            execution_time=execution_time,
            resource_usage=resource_usage or {},
            security_violations=security_violations or [],
            metadata=metadata
        )
        
        self.log(entry)
    
    def log_file_access(
        self,
        path: str,
        operation: str,
        result: str,
        reason: str = "",
        **metadata
    ):
        """
        ファイルアクセスを記録
        
        Args:
            path: ファイルパス
            operation: 操作 (read/write/execute)
            result: 結果 (success/denied)
            reason: 理由
            **metadata: 追加メタデータ
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=AuditAction.FILE_ACCESS.value,
            result=result,
            metadata={
                "path": path,
                "operation": operation,
                "reason": reason,
                **metadata
            }
        )
        
        self.log(entry)
    
    def log_network_access(
        self,
        host: str,
        port: Optional[int],
        protocol: str,
        result: str,
        reason: str = "",
        **metadata
    ):
        """
        ネットワークアクセスを記録
        
        Args:
            host: ホスト名
            port: ポート番号
            protocol: プロトコル
            result: 結果 (success/denied)
            reason: 理由
            **metadata: 追加メタデータ
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=AuditAction.NETWORK_ACCESS.value,
            result=result,
            metadata={
                "host": host,
                "port": port,
                "protocol": protocol,
                "reason": reason,
                **metadata
            }
        )
        
        self.log(entry)
    
    def log_policy_violation(
        self,
        violation_type: str,
        details: str,
        **metadata
    ):
        """
        ポリシー違反を記録
        
        Args:
            violation_type: 違反タイプ
            details: 詳細
            **metadata: 追加メタデータ
        """
        entry = AuditEntry(
            timestamp=datetime.now().isoformat(),
            action=AuditAction.POLICY_VIOLATION.value,
            result="violation",
            metadata={
                "violation_type": violation_type,
                "details": details,
                **metadata
            }
        )
        
        self.log(entry)
    
    def read_recent_entries(
        self,
        limit: int = 100,
        action_filter: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        最近の監査エントリを読み込み
        
        Args:
            limit: 最大取得数
            action_filter: アクションでフィルタ
            
        Returns:
            監査エントリのリスト
        """
        if not self.log_file.exists():
            return []
        
        try:
            entries = []
            
            with open(self.log_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # 新しい順に処理
            for line in reversed(lines):
                if len(entries) >= limit:
                    break
                
                try:
                    entry = json.loads(line.strip())
                    
                    # フィルタ適用
                    if action_filter and entry.get("action") != action_filter:
                        continue
                    
                    entries.append(entry)
                    
                except json.JSONDecodeError:
                    continue
            
            return entries
            
        except Exception as e:
            logger.error(f"Failed to read audit log: {e}")
            return []
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        監査ログの統計情報を取得
        
        Returns:
            統計情報
        """
        if not self.log_file.exists():
            return {"total_entries": 0}
        
        try:
            action_counts = {}
            result_counts = {}
            total = 0
            
            with open(self.log_file, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        total += 1
                        
                        action = entry.get("action", "unknown")
                        result = entry.get("result", "unknown")
                        
                        action_counts[action] = action_counts.get(action, 0) + 1
                        result_counts[result] = result_counts.get(result, 0) + 1
                        
                    except json.JSONDecodeError:
                        continue
            
            return {
                "total_entries": total,
                "by_action": action_counts,
                "by_result": result_counts,
                "log_file": str(self.log_file),
                "log_size_kb": self.log_file.stat().st_size / 1024
            }
            
        except Exception as e:
            logger.error(f"Failed to get audit statistics: {e}")
            return {"error": str(e)}


# グローバル監査ロガー（シングルトン）
_global_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """
    グローバル監査ロガーを取得（シングルトン）
    
    Returns:
        監査ロガーインスタンス
    """
    global _global_audit_logger
    
    if _global_audit_logger is None:
        _global_audit_logger = AuditLogger()
    
    return _global_audit_logger


# 便利な記録関数

def audit_sandbox_execution(
    command: List[str],
    workspace: str,
    result: str,
    exit_code: int,
    execution_time: float,
    **kwargs
):
    """サンドボックス実行を監査ログに記録"""
    logger_instance = get_audit_logger()
    logger_instance.log_sandbox_execution(
        command=command,
        workspace=workspace,
        result=result,
        exit_code=exit_code,
        execution_time=execution_time,
        **kwargs
    )


def audit_file_access(path: str, operation: str, result: str, reason: str = ""):
    """ファイルアクセスを監査ログに記録"""
    logger_instance = get_audit_logger()
    logger_instance.log_file_access(
        path=path,
        operation=operation,
        result=result,
        reason=reason
    )


def audit_network_access(
    host: str,
    port: Optional[int],
    protocol: str,
    result: str,
    reason: str = ""
):
    """ネットワークアクセスを監査ログに記録"""
    logger_instance = get_audit_logger()
    logger_instance.log_network_access(
        host=host,
        port=port,
        protocol=protocol,
        result=result,
        reason=reason
    )


def audit_policy_violation(violation_type: str, details: str):
    """ポリシー違反を監査ログに記録"""
    logger_instance = get_audit_logger()
    logger_instance.log_policy_violation(
        violation_type=violation_type,
        details=details
    )
