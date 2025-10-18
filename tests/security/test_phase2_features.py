"""
Phase 2 機能（アクセス制御・監視・監査）のテスト (Issue #62b)

ファイルシステム・ネットワークアクセス制御、実行時監視、監査ログのテスト。
"""
import pytest
import tempfile
from pathlib import Path
from datetime import datetime, timedelta

from src.security.filesystem_access_control import (
    FileSystemAccessControl,
    FileSystemPolicy,
    AccessMode,
    create_default_policy,
    create_strict_policy,
    create_read_only_policy
)
from src.security.network_access_control import (
    NetworkAccessControl,
    NetworkPolicy,
    NetworkProtocol,
    create_default_network_policy,
    create_strict_network_policy,
    create_api_only_policy
)
from src.security.runtime_monitor import (
    SecurityMonitor,
    MonitoringConfig,
    SecurityEvent,
    EventType,
    AlertSeverity,
    record_security_event
)
from src.security.audit_logger import (
    AuditLogger,
    AuditEntry,
    audit_sandbox_execution,
    audit_file_access,
    audit_network_access
)


class TestFileSystemAccessControl:
    """ファイルシステムアクセス制御のテスト"""
    
    def test_default_policy_creation(self):
        """デフォルトポリシーの作成"""
        policy = create_default_policy()
        
        assert policy.default_allow is False
        assert policy.detect_path_traversal is True
        assert len(policy.allowed_paths) > 0
    
    def test_path_allowed_in_workspace(self):
        """ワークスペース内パスの許可"""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = create_strict_policy(tmpdir)
            control = FileSystemAccessControl(policy)
            
            test_file = Path(tmpdir) / "test.txt"
            allowed, reason = control.is_path_allowed(str(test_file), AccessMode.READ)
            
            assert allowed is True
    
    def test_path_denied_outside_workspace(self):
        """ワークスペース外パスの拒否"""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = create_strict_policy(tmpdir)
            control = FileSystemAccessControl(policy)
            
            outside_file = "/etc/passwd"
            allowed, reason = control.is_path_allowed(outside_file, AccessMode.READ)
            
            assert allowed is False
    
    def test_path_traversal_detection(self):
        """パストラバーサル検出"""
        policy = create_default_policy()
        control = FileSystemAccessControl(policy)
        
        malicious_path = "/tmp/../etc/passwd"
        allowed, reason = control.is_path_allowed(malicious_path, AccessMode.READ)
        
        assert allowed is False
        assert "traversal" in reason.lower()
    
    def test_sensitive_path_blocked(self):
        """機密パスのブロック"""
        policy = FileSystemPolicy(default_allow=True)
        control = FileSystemAccessControl(policy)
        
        sensitive_paths = ["/etc/passwd", "/etc/shadow", "~/.ssh/id_rsa"]
        
        for path in sensitive_paths:
            allowed, reason = control.is_path_allowed(path, AccessMode.READ)
            assert allowed is False
    
    def test_read_only_policy(self):
        """読み取り専用ポリシー"""
        with tempfile.TemporaryDirectory() as tmpdir:
            policy = create_read_only_policy([tmpdir])
            control = FileSystemAccessControl(policy)
            
            test_file = Path(tmpdir) / "test.txt"
            
            # 読み取りは許可
            read_allowed, _ = control.is_path_allowed(str(test_file), AccessMode.READ)
            assert read_allowed is True
            
            # 書き込みは拒否
            write_allowed, _ = control.is_path_allowed(str(test_file), AccessMode.WRITE)
            assert write_allowed is False


class TestNetworkAccessControl:
    """ネットワークアクセス制御のテスト"""
    
    def test_default_network_policy(self):
        """デフォルトネットワークポリシー"""
        policy = create_default_network_policy()
        
        assert policy.default_allow is False
        assert NetworkProtocol.HTTPS in policy.allowed_protocols
        assert len(policy.allowed_hosts) > 0
    
    def test_allowed_host(self):
        """許可ホストへのアクセス"""
        policy = NetworkPolicy(
            allowed_hosts=["github.com", "*.openai.com"],
            default_allow=False
        )
        control = NetworkAccessControl(policy)
        
        allowed, _ = control.is_host_allowed("github.com")
        assert allowed is True
        
        # ワイルドカード
        allowed, _ = control.is_host_allowed("api.openai.com")
        assert allowed is True
    
    def test_denied_host(self):
        """拒否ホストへのアクセス"""
        policy = NetworkPolicy(
            allowed_hosts=["github.com"],
            default_allow=False
        )
        control = NetworkAccessControl(policy)
        
        allowed, _ = control.is_host_allowed("evil.com")
        assert allowed is False
    
    def test_metadata_service_blocked(self):
        """メタデータサービスのブロック"""
        policy = NetworkPolicy(default_allow=True)
        control = NetworkAccessControl(policy)
        
        metadata_hosts = [
            "169.254.169.254",  # AWS
            "metadata.google.internal",  # GCP
            "metadata.azure.com"  # Azure
        ]
        
        for host in metadata_hosts:
            allowed, reason = control.is_host_allowed(host)
            assert allowed is False
            assert "metadata" in reason.lower()
    
    def test_localhost_blocked(self):
        """localhostアクセスのブロック"""
        policy = NetworkPolicy(allow_localhost=False, default_allow=True)
        control = NetworkAccessControl(policy)
        
        localhost_variants = ["localhost", "127.0.0.1", "::1"]
        
        for host in localhost_variants:
            allowed, _ = control.is_host_allowed(host)
            assert allowed is False
    
    def test_private_ip_blocked(self):
        """プライベートIPのブロック"""
        policy = NetworkPolicy(allow_private_ips=False, default_allow=True)
        control = NetworkAccessControl(policy)
        
        private_ips = ["10.0.0.1", "192.168.1.1", "172.16.0.1"]
        
        for ip in private_ips:
            allowed, _ = control.is_host_allowed(ip)
            assert allowed is False
    
    def test_dangerous_port_blocked(self):
        """危険なポートのブロック"""
        policy = NetworkPolicy(default_allow=True)
        control = NetworkAccessControl(policy)
        
        dangerous_ports = [22, 23, 3389]  # SSH, Telnet, RDP
        
        for port in dangerous_ports:
            allowed, reason = control.is_host_allowed("example.com", port)
            assert allowed is False
            assert "port" in reason.lower()
    
    def test_url_validation(self):
        """URL検証"""
        policy = NetworkPolicy(
            allowed_hosts=["github.com"],
            allowed_protocols=[NetworkProtocol.HTTPS],
            default_allow=False
        )
        control = NetworkAccessControl(policy)
        
        # 許可されたURL
        allowed, _ = control.validate_url("https://github.com/repo")
        assert allowed is True
        
        # HTTPは拒否（HTTPSのみ許可）
        allowed, _ = control.validate_url("http://github.com/repo")
        assert allowed is False
    
    def test_strict_network_policy(self):
        """厳格ネットワークポリシー（全拒否）"""
        policy = create_strict_network_policy()
        control = NetworkAccessControl(policy)
        
        allowed, _ = control.is_host_allowed("github.com")
        assert allowed is False


class TestSecurityMonitor:
    """セキュリティ監視のテスト"""
    
    def test_monitor_initialization(self):
        """モニター初期化"""
        config = MonitoringConfig()
        monitor = SecurityMonitor(config)
        
        assert monitor.config.enable_alerts is True
        assert monitor.config.enable_event_log is True
    
    def test_event_recording(self):
        """イベント記録"""
        monitor = SecurityMonitor()
        
        event = SecurityEvent(
            event_type=EventType.PROCESS_START,
            severity=AlertSeverity.INFO,
            message="Test process started"
        )
        
        monitor.record_event(event)
        
        stats = monitor.get_statistics()
        assert stats["total_events"] == 1
    
    def test_alert_threshold(self):
        """アラート閾値"""
        config = MonitoringConfig(
            alert_threshold=3,
            alert_window_seconds=60
        )
        monitor = SecurityMonitor(config)
        
        alert_triggered = False
        
        def alert_handler(event):
            nonlocal alert_triggered
            alert_triggered = True
        
        monitor.register_alert_handler(alert_handler)
        
        # 同じイベントを閾値分発生させる
        for i in range(3):
            event = SecurityEvent(
                event_type=EventType.FILE_ACCESS_DENIED,
                severity=AlertSeverity.WARNING,
                message=f"File access denied {i}"
            )
            monitor.record_event(event)
        
        # アラートが発火するはず
        assert alert_triggered is True
    
    def test_event_filtering(self):
        """イベントフィルタリング"""
        monitor = SecurityMonitor()
        
        # 異なるタイプのイベントを記録
        for i in range(5):
            monitor.record_event(SecurityEvent(
                event_type=EventType.PROCESS_START,
                severity=AlertSeverity.INFO,
                message=f"Process {i}"
            ))
        
        for i in range(3):
            monitor.record_event(SecurityEvent(
                event_type=EventType.FILE_ACCESS_DENIED,
                severity=AlertSeverity.WARNING,
                message=f"File denied {i}"
            ))
        
        # タイプでフィルタ
        denied_events = monitor.get_events(event_type=EventType.FILE_ACCESS_DENIED)
        assert len(denied_events) == 3


class TestAuditLogger:
    """監査ログのテスト"""
    
    def test_audit_logger_creation(self):
        """監査ロガー作成"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_file)
            
            assert logger.log_file == log_file
    
    def test_sandbox_execution_logging(self):
        """サンドボックス実行のログ記録"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_file)
            
            logger.log_sandbox_execution(
                command=["python", "test.py"],
                workspace="/tmp/workspace",
                result="success",
                exit_code=0,
                execution_time=1.23,
                resource_usage={"cpu_time": 1.0, "memory_mb": 100}
            )
            
            # ログファイルが作成されたか確認
            assert log_file.exists()
            
            # エントリを読み込み
            entries = logger.read_recent_entries(limit=10)
            assert len(entries) == 1
            assert entries[0]["action"] == "sandbox_execute"
            assert entries[0]["result"] == "success"
    
    def test_file_access_logging(self):
        """ファイルアクセスのログ記録"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_file)
            
            logger.log_file_access(
                path="/tmp/test.txt",
                operation="read",
                result="denied",
                reason="Not in allowed paths"
            )
            
            entries = logger.read_recent_entries()
            assert len(entries) == 1
            assert entries[0]["metadata"]["operation"] == "read"
            assert entries[0]["result"] == "denied"
    
    def test_audit_statistics(self):
        """監査統計"""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_file = Path(tmpdir) / "audit.jsonl"
            logger = AuditLogger(log_file)
            
            # 複数のエントリを記録
            for i in range(5):
                logger.log_sandbox_execution(
                    command=["test"],
                    workspace="/tmp",
                    result="success",
                    exit_code=0,
                    execution_time=1.0
                )
            
            stats = logger.get_statistics()
            assert stats["total_entries"] == 5
            assert "sandbox_execute" in stats["by_action"]


class TestIntegration:
    """統合テスト"""
    
    def test_full_security_stack(self):
        """完全なセキュリティスタック"""
        # ファイルシステム制御
        with tempfile.TemporaryDirectory() as workspace:
            fs_policy = create_strict_policy(workspace)
            fs_control = FileSystemAccessControl(fs_policy)
            
            # ネットワーク制御
            net_policy = create_strict_network_policy()
            net_control = NetworkAccessControl(net_policy)
            
            # 監視
            monitor = SecurityMonitor()
            
            # 監査
            audit_log = Path(workspace) / "audit.jsonl"
            auditor = AuditLogger(audit_log)
            
            # ワークスペース内のファイルアクセス
            test_file = Path(workspace) / "test.txt"
            allowed, _ = fs_control.is_path_allowed(str(test_file))
            assert allowed is True
            
            # 外部ファイルアクセス拒否
            allowed, reason = fs_control.is_path_allowed("/etc/passwd")
            assert allowed is False
            
            # 監視イベント記録
            monitor.record_event(SecurityEvent(
                event_type=EventType.FILE_ACCESS_DENIED,
                severity=AlertSeverity.WARNING,
                message="Access to /etc/passwd denied"
            ))
            
            # 監査ログ記録
            auditor.log_file_access(
                path="/etc/passwd",
                operation="read",
                result="denied",
                reason=reason
            )
            
            # 検証
            assert monitor.get_statistics()["total_events"] > 0
            assert audit_log.exists()
