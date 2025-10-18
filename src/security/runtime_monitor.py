"""
実行時監視とアラート (Issue #62b)

サンドボックス実行の監視とセキュリティイベントのアラート。

作成日: 2025-10-17
"""
import time
import logging
import threading
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """アラート重要度"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class EventType(Enum):
    """イベントタイプ"""
    PROCESS_START = "process_start"
    PROCESS_END = "process_end"
    PROCESS_KILLED = "process_killed"
    TIMEOUT = "timeout"
    RESOURCE_LIMIT = "resource_limit"
    SYSCALL_DENIED = "syscall_denied"
    FILE_ACCESS_DENIED = "file_access_denied"
    NETWORK_ACCESS_DENIED = "network_access_denied"
    PATH_TRAVERSAL = "path_traversal"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"


@dataclass
class SecurityEvent:
    """セキュリティイベント"""
    event_type: EventType
    severity: AlertSeverity
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    process_id: Optional[int] = None
    user: Optional[str] = None


@dataclass
class MonitoringConfig:
    """監視設定"""
    # アラート送信を有効化
    enable_alerts: bool = True
    
    # イベントログを有効化
    enable_event_log: bool = True
    
    # リアルタイム監視を有効化
    enable_realtime_monitoring: bool = True
    
    # アラート閾値（同じイベントタイプが指定回数発生したら通知）
    alert_threshold: int = 3
    
    # アラート時間窓（秒）
    alert_window_seconds: int = 300  # 5分
    
    # 監視対象イベントタイプ
    monitored_events: List[EventType] = field(default_factory=lambda: [
        EventType.PROCESS_KILLED,
        EventType.TIMEOUT,
        EventType.RESOURCE_LIMIT,
        EventType.SYSCALL_DENIED,
        EventType.FILE_ACCESS_DENIED,
        EventType.NETWORK_ACCESS_DENIED,
        EventType.PATH_TRAVERSAL,
    ])
    
    # 重大度でフィルタリング（この重要度以上のみ通知）
    min_severity: AlertSeverity = AlertSeverity.WARNING


class SecurityMonitor:
    """
    セキュリティ監視システム
    
    サンドボックス実行を監視し、セキュリティイベントを検出・アラート。
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        セキュリティモニターを初期化
        
        Args:
            config: 監視設定
        """
        self.config = config or MonitoringConfig()
        
        # イベントストレージ
        self._events: List[SecurityEvent] = []
        self._event_counts: Dict[EventType, List[datetime]] = defaultdict(list)
        
        # アラートハンドラー
        self._alert_handlers: List[Callable[[SecurityEvent], None]] = []
        
        # スレッドセーフなロック
        self._lock = threading.Lock()
        
        # 統計情報
        self._stats = {
            "total_events": 0,
            "alerts_sent": 0,
            "events_by_type": defaultdict(int),
            "events_by_severity": defaultdict(int),
        }
        
        logger.info("Security monitor initialized")
    
    def record_event(self, event: SecurityEvent):
        """
        セキュリティイベントを記録
        
        Args:
            event: セキュリティイベント
        """
        with self._lock:
            # イベントを保存
            if self.config.enable_event_log:
                self._events.append(event)
            
            # カウンターを更新
            self._event_counts[event.event_type].append(event.timestamp)
            
            # 統計を更新
            self._stats["total_events"] += 1
            self._stats["events_by_type"][event.event_type.value] += 1
            self._stats["events_by_severity"][event.severity.value] += 1
            
            # ログ出力
            self._log_event(event)
            
            # アラートチェック
            if self.config.enable_alerts and self._should_alert(event):
                self._send_alert(event)
    
    def _log_event(self, event: SecurityEvent):
        """イベントをログ出力"""
        log_msg = f"[{event.severity.value.upper()}] {event.event_type.value}: {event.message}"
        
        if event.severity == AlertSeverity.CRITICAL:
            logger.critical(log_msg, extra={"details": event.details})
        elif event.severity == AlertSeverity.ERROR:
            logger.error(log_msg, extra={"details": event.details})
        elif event.severity == AlertSeverity.WARNING:
            logger.warning(log_msg, extra={"details": event.details})
        else:
            logger.info(log_msg, extra={"details": event.details})
    
    def _should_alert(self, event: SecurityEvent) -> bool:
        """
        アラートを送信すべきか判定
        
        Args:
            event: セキュリティイベント
            
        Returns:
            アラート送信が必要な場合True
        """
        # 監視対象イベントか
        if event.event_type not in self.config.monitored_events:
            return False
        
        # 重要度フィルタ
        severity_order = [
            AlertSeverity.INFO,
            AlertSeverity.WARNING,
            AlertSeverity.ERROR,
            AlertSeverity.CRITICAL
        ]
        
        if severity_order.index(event.severity) < severity_order.index(self.config.min_severity):
            return False
        
        # 閾値チェック（時間窓内での発生回数）
        now = event.timestamp
        window_start = now - timedelta(seconds=self.config.alert_window_seconds)
        
        recent_events = [
            ts for ts in self._event_counts[event.event_type]
            if ts >= window_start
        ]
        
        if len(recent_events) >= self.config.alert_threshold:
            logger.warning(
                f"Alert threshold reached for {event.event_type.value}: "
                f"{len(recent_events)} events in {self.config.alert_window_seconds}s"
            )
            return True
        
        # CRITICAL は即座にアラート
        if event.severity == AlertSeverity.CRITICAL:
            return True
        
        return False
    
    def _send_alert(self, event: SecurityEvent):
        """
        アラートを送信
        
        Args:
            event: セキュリティイベント
        """
        logger.warning(f"🚨 ALERT: {event.event_type.value} - {event.message}")
        
        # 登録されたハンドラーを実行
        for handler in self._alert_handlers:
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Alert handler failed: {e}")
        
        self._stats["alerts_sent"] += 1
    
    def register_alert_handler(self, handler: Callable[[SecurityEvent], None]):
        """
        アラートハンドラーを登録
        
        Args:
            handler: アラートハンドラー関数
        """
        self._alert_handlers.append(handler)
        logger.info(f"Alert handler registered: {handler.__name__}")
    
    def get_events(
        self,
        event_type: Optional[EventType] = None,
        severity: Optional[AlertSeverity] = None,
        since: Optional[datetime] = None,
        limit: Optional[int] = None
    ) -> List[SecurityEvent]:
        """
        イベントを取得
        
        Args:
            event_type: イベントタイプでフィルタ
            severity: 重要度でフィルタ
            since: この時刻以降のイベントのみ
            limit: 最大取得数
            
        Returns:
            フィルタされたイベントリスト
        """
        with self._lock:
            events = self._events.copy()
        
        # フィルタリング
        if event_type:
            events = [e for e in events if e.event_type == event_type]
        
        if severity:
            events = [e for e in events if e.severity == severity]
        
        if since:
            events = [e for e in events if e.timestamp >= since]
        
        # 新しい順にソート
        events.sort(key=lambda e: e.timestamp, reverse=True)
        
        # 制限
        if limit:
            events = events[:limit]
        
        return events
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        統計情報を取得
        
        Returns:
            統計情報の辞書
        """
        with self._lock:
            return {
                **self._stats,
                "event_store_size": len(self._events),
                "alert_handlers": len(self._alert_handlers),
            }
    
    def clear_events(self, older_than: Optional[datetime] = None):
        """
        イベントをクリア
        
        Args:
            older_than: この時刻より古いイベントを削除（None=全削除）
        """
        with self._lock:
            if older_than:
                self._events = [e for e in self._events if e.timestamp >= older_than]
                logger.info(f"Cleared events older than {older_than}")
            else:
                self._events.clear()
                self._event_counts.clear()
                logger.info("All events cleared")


# グローバルモニターインスタンス（シングルトン）
_global_monitor: Optional[SecurityMonitor] = None
_monitor_lock = threading.Lock()


def get_security_monitor() -> SecurityMonitor:
    """
    グローバルセキュリティモニターを取得（シングルトン）
    
    Returns:
        セキュリティモニターインスタンス
    """
    global _global_monitor
    
    with _monitor_lock:
        if _global_monitor is None:
            _global_monitor = SecurityMonitor()
        
        return _global_monitor


def record_security_event(
    event_type: EventType,
    severity: AlertSeverity,
    message: str,
    **details
):
    """
    セキュリティイベントを記録（便利関数）
    
    Args:
        event_type: イベントタイプ
        severity: 重要度
        message: メッセージ
        **details: 追加詳細情報
    """
    monitor = get_security_monitor()
    
    event = SecurityEvent(
        event_type=event_type,
        severity=severity,
        message=message,
        details=details
    )
    
    monitor.record_event(event)


# 便利な記録関数
def record_process_start(command: List[str], pid: int):
    """プロセス開始を記録"""
    record_security_event(
        EventType.PROCESS_START,
        AlertSeverity.INFO,
        f"Process started: {' '.join(command)}",
        command=command,
        pid=pid
    )


def record_process_killed(reason: str, pid: int):
    """プロセス強制終了を記録"""
    record_security_event(
        EventType.PROCESS_KILLED,
        AlertSeverity.WARNING,
        f"Process killed: {reason}",
        reason=reason,
        pid=pid
    )


def record_access_denied(access_type: str, target: str, reason: str):
    """アクセス拒否を記録"""
    event_map = {
        "file": EventType.FILE_ACCESS_DENIED,
        "network": EventType.NETWORK_ACCESS_DENIED,
        "syscall": EventType.SYSCALL_DENIED,
    }
    
    event_type = event_map.get(access_type, EventType.SUSPICIOUS_ACTIVITY)
    
    record_security_event(
        event_type,
        AlertSeverity.WARNING,
        f"{access_type.capitalize()} access denied: {target}",
        target=target,
        reason=reason
    )
