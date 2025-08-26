# Security Model (Draft)

最終更新: 2025-08-26

## 概要

2bykilt プロジェクトのセキュリティアーキテクチャとモデルを定義します。多層防御と段階的セキュリティ強化を実現する包括的な安全保障戦略です。

## セキュリティ原則

### 1. 多層防御 (Defense in Depth)
- 複数のセキュリティ層による保護
- 単一障害点の排除
- 段階的な権限制御

### 2. 最小権限の原則 (Principle of Least Privilege)
- 必要最小限の権限のみ付与
- 動的権限管理
- 定期的な権限見直し

### 3. ゼロトラスト (Zero Trust)
- すべてのアクセスを検証
- ネットワーク境界に依存しない
- 継続的な監視と検証

### 4. セキュリティ・バイ・デザイン (Security by Design)
- 設計段階からのセキュリティ考慮
- セキュアなデフォルト設定
- 継続的なセキュリティ評価

## 脅威モデル

### 1. 外部脅威
```yaml
external_threats:
  unauthorized_access:
    description: "不正なシステムアクセス"
    impact: "high"
    likelihood: "medium"
    mitigation:
      - "強力な認証機構"
      - "ネットワーク分離"
      - "侵入検知システム"
      
  data_breach:
    description: "機密データの漏洩"
    impact: "critical"
    likelihood: "low"
    mitigation:
      - "データ暗号化"
      - "アクセス制御"
      - "監査ログ"
      
  malware_injection:
    description: "悪意あるコードの注入"
    impact: "high"
    likelihood: "medium"
    mitigation:
      - "コード検証"
      - "サンドボックス実行"
      - "入力バリデーション"
```

### 2. 内部脅威
```yaml
internal_threats:
  privilege_escalation:
    description: "権限昇格攻撃"
    impact: "high"
    likelihood: "low"
    mitigation:
      - "最小権限原則"
      - "権限監視"
      - "定期的な権限見直し"
      
  insider_threat:
    description: "内部者による不正行為"
    impact: "high"
    likelihood: "low"
    mitigation:
      - "職務分離"
      - "活動監視"
      - "背景調査"
```

### 3. システム脅威
```yaml
system_threats:
  configuration_drift:
    description: "設定の意図しない変更"
    impact: "medium"
    likelihood: "medium"
    mitigation:
      - "設定管理"
      - "変更追跡"
      - "自動復旧"
      
  dependency_vulnerability:
    description: "依存関係の脆弱性"
    impact: "high"
    likelihood: "high"
    mitigation:
      - "定期的な脆弱性スキャン"
      - "依存関係更新"
      - "代替ライブラリ検討"
```

## セキュリティアーキテクチャ

### 1. 認証・認可層
```python
class AuthenticationManager:
    """認証管理"""
    
    def __init__(self):
        self.auth_providers = {
            'local': LocalAuthProvider(),
            'oauth2': OAuth2Provider(),
            'ldap': LDAPProvider()
        }
        self.session_manager = SessionManager()
        
    def authenticate(self, credentials: Dict[str, Any], provider: str = 'local') -> AuthResult:
        """認証実行"""
        if provider not in self.auth_providers:
            raise ValueError(f"Unknown auth provider: {provider}")
        
        auth_provider = self.auth_providers[provider]
        
        try:
            # 認証実行
            user = auth_provider.authenticate(credentials)
            
            # セッション作成
            session = self.session_manager.create_session(user)
            
            # 監査ログ
            audit_logger.info("Authentication successful", extra={
                "user_id": user.id,
                "provider": provider,
                "ip_address": credentials.get('ip_address'),
                "user_agent": credentials.get('user_agent')
            })
            
            return AuthResult(success=True, user=user, session=session)
            
        except AuthenticationError as e:
            # 失敗ログ
            audit_logger.warning("Authentication failed", extra={
                "provider": provider,
                "error": str(e),
                "ip_address": credentials.get('ip_address')
            })
            
            return AuthResult(success=False, error=str(e))

class AuthorizationManager:
    """認可管理"""
    
    def __init__(self):
        self.rbac = RoleBasedAccessControl()
        self.abac = AttributeBasedAccessControl()
        
    def check_permission(
        self,
        user: User,
        resource: str,
        action: str,
        context: Dict[str, Any] = None
    ) -> bool:
        """権限チェック"""
        
        # RBAC チェック
        if self.rbac.has_permission(user.roles, resource, action):
            return True
        
        # ABAC チェック（より詳細な制御）
        if context and self.abac.evaluate_policy(user, resource, action, context):
            return True
        
        # 権限拒否ログ
        audit_logger.warning("Permission denied", extra={
            "user_id": user.id,
            "resource": resource,
            "action": action,
            "context": context
        })
        
        return False
```

### 2. データ保護層
```python
class DataProtectionManager:
    """データ保護管理"""
    
    def __init__(self):
        self.encryption_key = self._load_encryption_key()
        self.classifier = DataClassifier()
        
    def encrypt_sensitive_data(self, data: Any, classification: str = None) -> EncryptedData:
        """機密データ暗号化"""
        
        # データ分類
        if not classification:
            classification = self.classifier.classify(data)
        
        if classification in ['confidential', 'secret']:
            from cryptography.fernet import Fernet
            f = Fernet(self.encryption_key)
            
            if isinstance(data, str):
                encrypted = f.encrypt(data.encode())
            else:
                import json
                encrypted = f.encrypt(json.dumps(data).encode())
            
            return EncryptedData(
                encrypted_data=encrypted,
                classification=classification,
                encryption_method='fernet',
                created_at=datetime.utcnow()
            )
        
        return EncryptedData(
            encrypted_data=data,  # 暗号化不要
            classification=classification,
            encryption_method='none'
        )
    
    def mask_pii_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """PII データマスキング"""
        pii_fields = [
            'ssn', 'social_security_number', 'passport_number',
            'email', 'phone_number', 'credit_card', 'bank_account'
        ]
        
        masked_data = data.copy()
        
        def mask_recursive(obj, path=""):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    current_path = f"{path}.{key}" if path else key
                    if any(pii in key.lower() for pii in pii_fields):
                        obj[key] = self._mask_value(value)
                    elif isinstance(value, (dict, list)):
                        mask_recursive(value, current_path)
            elif isinstance(obj, list):
                for i, item in enumerate(obj):
                    if isinstance(item, (dict, list)):
                        mask_recursive(item, f"{path}[{i}]")
        
        mask_recursive(masked_data)
        return masked_data
    
    def _mask_value(self, value: Any) -> str:
        """値マスキング"""
        if isinstance(value, str):
            if len(value) <= 4:
                return "*" * len(value)
            else:
                return value[:2] + "*" * (len(value) - 4) + value[-2:]
        else:
            return "***MASKED***"
```

### 3. ネットワークセキュリティ層
```python
class NetworkSecurityManager:
    """ネットワークセキュリティ管理"""
    
    def __init__(self):
        self.firewall_rules = self._load_firewall_rules()
        self.rate_limiter = RateLimiter()
        self.intrusion_detector = IntrusionDetector()
        
    def validate_network_access(
        self,
        source_ip: str,
        destination: str,
        port: int,
        protocol: str = 'tcp'
    ) -> bool:
        """ネットワークアクセス検証"""
        
        # ファイアウォール規則チェック
        if not self._check_firewall_rules(source_ip, destination, port, protocol):
            security_logger.warning("Firewall rule violation", extra={
                "source_ip": source_ip,
                "destination": destination,
                "port": port,
                "protocol": protocol
            })
            return False
        
        # レート制限チェック
        if not self.rate_limiter.check_rate_limit(source_ip):
            security_logger.warning("Rate limit exceeded", extra={
                "source_ip": source_ip,
                "current_rate": self.rate_limiter.get_current_rate(source_ip)
            })
            return False
        
        # 侵入検知
        if self.intrusion_detector.detect_suspicious_activity(source_ip, destination, port):
            security_logger.critical("Suspicious network activity detected", extra={
                "source_ip": source_ip,
                "destination": destination,
                "port": port,
                "detection_rules": self.intrusion_detector.get_triggered_rules()
            })
            return False
        
        return True
    
    def setup_tls_configuration(self) -> Dict[str, Any]:
        """TLS設定"""
        return {
            'min_version': 'TLSv1.2',
            'max_version': 'TLSv1.3',
            'cipher_suites': [
                'TLS_AES_256_GCM_SHA384',
                'TLS_CHACHA20_POLY1305_SHA256',
                'TLS_AES_128_GCM_SHA256',
                'ECDHE-RSA-AES256-GCM-SHA384',
                'ECDHE-RSA-AES128-GCM-SHA256'
            ],
            'verify_mode': 'CERT_REQUIRED',
            'check_hostname': True,
            'cert_reqs': 'ssl.CERT_REQUIRED'
        }
```

## サンドボックス実行

### 1. コンテナ分離
```python
class SandboxManager:
    """サンドボックス管理"""
    
    def __init__(self):
        self.container_runtime = ContainerRuntime()
        self.resource_limits = self._load_resource_limits()
        
    def create_sandbox(
        self,
        script_content: str,
        execution_context: Dict[str, Any]
    ) -> SandboxEnvironment:
        """サンドボックス環境作成"""
        
        # セキュリティ制約
        security_config = {
            'read_only_filesystem': True,
            'no_new_privileges': True,
            'drop_capabilities': ['ALL'],
            'add_capabilities': [],  # 必要最小限のみ
            'seccomp_profile': 'default',
            'apparmor_profile': 'default'
        }
        
        # リソース制限
        resource_config = {
            'memory_limit': self.resource_limits.get('memory', '512m'),
            'cpu_limit': self.resource_limits.get('cpu', '0.5'),
            'timeout': self.resource_limits.get('timeout', 300),
            'network_mode': 'none'  # ネットワーク分離
        }
        
        # 一時ディレクトリ
        temp_dir = self._create_temp_directory()
        
        try:
            # コンテナ作成
            container = self.container_runtime.create_container(
                image='python:3.11-alpine',
                command=['python', '-c', script_content],
                security_config=security_config,
                resource_config=resource_config,
                volumes={temp_dir: '/tmp/workspace'},
                environment=self._sanitize_environment(execution_context)
            )
            
            return SandboxEnvironment(
                container=container,
                temp_dir=temp_dir,
                security_config=security_config
            )
            
        except Exception as e:
            self._cleanup_temp_directory(temp_dir)
            raise SandboxCreationError(f"Failed to create sandbox: {e}")
    
    def execute_in_sandbox(
        self,
        sandbox: SandboxEnvironment,
        max_execution_time: int = 300
    ) -> ExecutionResult:
        """サンドボックス内実行"""
        
        start_time = time.time()
        
        try:
            # 実行開始
            result = sandbox.container.run(timeout=max_execution_time)
            
            execution_time = time.time() - start_time
            
            # 実行結果ログ
            security_logger.info("Sandbox execution completed", extra={
                "execution_time": execution_time,
                "exit_code": result.exit_code,
                "stdout_length": len(result.stdout),
                "stderr_length": len(result.stderr)
            })
            
            return ExecutionResult(
                success=result.exit_code == 0,
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.exit_code,
                execution_time=execution_time
            )
            
        except TimeoutError:
            security_logger.warning("Sandbox execution timeout", extra={
                "max_execution_time": max_execution_time
            })
            sandbox.container.kill()
            raise SandboxTimeoutError("Execution timeout exceeded")
            
        finally:
            # クリーンアップ
            self._cleanup_sandbox(sandbox)
```

### 2. ファイルシステム制御
```python
class FileSystemSecurityManager:
    """ファイルシステムセキュリティ管理"""
    
    def __init__(self):
        self.allowed_paths = self._load_allowed_paths()
        self.blocked_paths = self._load_blocked_paths()
        
    def validate_file_access(self, file_path: str, access_type: str) -> bool:
        """ファイルアクセス検証"""
        from pathlib import Path
        
        try:
            # パス正規化
            resolved_path = Path(file_path).resolve()
            path_str = str(resolved_path)
            
            # パストラバーサル検出
            if '..' in file_path or path_str != str(Path(file_path).resolve()):
                security_logger.warning("Path traversal attempt detected", extra={
                    "requested_path": file_path,
                    "resolved_path": path_str
                })
                return False
            
            # ブロックリストチェック
            for blocked_pattern in self.blocked_paths:
                if self._match_path_pattern(path_str, blocked_pattern):
                    security_logger.warning("Blocked path access attempt", extra={
                        "path": path_str,
                        "blocked_pattern": blocked_pattern,
                        "access_type": access_type
                    })
                    return False
            
            # 許可リストチェック
            for allowed_pattern in self.allowed_paths.get(access_type, []):
                if self._match_path_pattern(path_str, allowed_pattern):
                    return True
            
            # デフォルトで拒否
            security_logger.warning("Unauthorized file access attempt", extra={
                "path": path_str,
                "access_type": access_type
            })
            return False
            
        except Exception as e:
            security_logger.error("File access validation error", extra={
                "path": file_path,
                "error": str(e)
            })
            return False
    
    def create_secure_temp_directory(self, prefix: str = "secure_") -> str:
        """セキュアな一時ディレクトリ作成"""
        import tempfile
        import os
        
        # 一時ディレクトリ作成
        temp_dir = tempfile.mkdtemp(prefix=prefix)
        
        # 権限設定（所有者のみアクセス可能）
        os.chmod(temp_dir, 0o700)
        
        security_logger.info("Secure temp directory created", extra={
            "temp_dir": temp_dir,
            "permissions": "0700"
        })
        
        return temp_dir
```

## セキュリティ監視

### 1. セキュリティイベント監視
```python
class SecurityEventMonitor:
    """セキュリティイベント監視"""
    
    def __init__(self):
        self.event_handlers = {
            'authentication_failure': self._handle_auth_failure,
            'permission_denied': self._handle_permission_denied,
            'suspicious_activity': self._handle_suspicious_activity,
            'data_access': self._handle_data_access
        }
        self.alert_manager = AlertManager()
        
    def monitor_security_events(self):
        """セキュリティイベント監視開始"""
        
        # ログ監視
        log_monitor = LogMonitor()
        log_monitor.add_pattern_handler(
            pattern=r'Authentication failed',
            handler=lambda event: self.handle_event('authentication_failure', event)
        )
        
        # ネットワーク監視
        network_monitor = NetworkMonitor()
        network_monitor.add_anomaly_handler(
            handler=lambda event: self.handle_event('suspicious_activity', event)
        )
        
        # ファイルアクセス監視
        file_monitor = FileAccessMonitor()
        file_monitor.add_access_handler(
            handler=lambda event: self.handle_event('data_access', event)
        )
        
    def handle_event(self, event_type: str, event_data: Dict[str, Any]):
        """セキュリティイベント処理"""
        
        if event_type in self.event_handlers:
            handler = self.event_handlers[event_type]
            
            try:
                handler(event_data)
            except Exception as e:
                logger.error(f"Security event handler error: {e}")
    
    def _handle_auth_failure(self, event_data: Dict[str, Any]):
        """認証失敗処理"""
        ip_address = event_data.get('ip_address')
        failure_count = event_data.get('failure_count', 1)
        
        # 閾値チェック
        if failure_count >= 5:
            # IP ブロック
            self._block_ip_address(ip_address, duration_minutes=30)
            
            # アラート送信
            self.alert_manager.send_alert(
                severity='high',
                title='Multiple authentication failures',
                message=f'IP {ip_address} has {failure_count} consecutive failures',
                details=event_data
            )
    
    def _handle_suspicious_activity(self, event_data: Dict[str, Any]):
        """不審な活動処理"""
        activity_type = event_data.get('activity_type')
        risk_score = event_data.get('risk_score', 0)
        
        if risk_score >= 8:  # 高リスク
            # 即座にアラート
            self.alert_manager.send_alert(
                severity='critical',
                title='High-risk suspicious activity detected',
                message=f'Activity type: {activity_type}, Risk score: {risk_score}',
                details=event_data
            )
            
            # 自動対応
            self._initiate_incident_response(event_data)
```

### 2. 脆弱性管理
```python
class VulnerabilityManager:
    """脆弱性管理"""
    
    def __init__(self):
        self.scanners = {
            'dependency': DependencyScanner(),
            'code': CodeScanner(),
            'container': ContainerScanner()
        }
        self.vulnerability_db = VulnerabilityDatabase()
        
    def run_security_scan(self, scan_types: List[str] = None) -> SecurityScanResult:
        """セキュリティスキャン実行"""
        
        if not scan_types:
            scan_types = ['dependency', 'code', 'container']
        
        results = {}
        
        for scan_type in scan_types:
            if scan_type in self.scanners:
                scanner = self.scanners[scan_type]
                
                try:
                    scan_result = scanner.scan()
                    results[scan_type] = scan_result
                    
                    # 高危険度脆弱性の即座な通知
                    critical_vulns = [
                        v for v in scan_result.vulnerabilities 
                        if v.severity == 'critical'
                    ]
                    
                    if critical_vulns:
                        self._notify_critical_vulnerabilities(scan_type, critical_vulns)
                        
                except Exception as e:
                    logger.error(f"Security scan failed for {scan_type}: {e}")
                    results[scan_type] = ScanResult(success=False, error=str(e))
        
        return SecurityScanResult(
            scan_date=datetime.utcnow(),
            results=results,
            overall_score=self._calculate_security_score(results)
        )
    
    def create_remediation_plan(
        self,
        vulnerabilities: List[Vulnerability]
    ) -> RemediationPlan:
        """修復計画作成"""
        
        # 優先度順にソート
        sorted_vulns = sorted(
            vulnerabilities,
            key=lambda v: (v.severity_score, v.exploitability_score),
            reverse=True
        )
        
        remediation_tasks = []
        
        for vuln in sorted_vulns:
            task = RemediationTask(
                vulnerability=vuln,
                priority=self._calculate_priority(vuln),
                estimated_effort=self._estimate_effort(vuln),
                recommended_actions=self._get_recommended_actions(vuln),
                due_date=self._calculate_due_date(vuln)
            )
            remediation_tasks.append(task)
        
        return RemediationPlan(
            created_at=datetime.utcnow(),
            tasks=remediation_tasks,
            total_vulnerabilities=len(vulnerabilities),
            estimated_completion=self._estimate_total_completion_time(remediation_tasks)
        )
```

## セキュリティ運用

### 1. インシデント対応
```yaml
incident_response_procedure:
  detection:
    - "自動監視システムによる検知"
    - "ユーザー報告"
    - "第三者機関からの通知"
    
  classification:
    critical:
      - "データ漏洩"
      - "システム侵入"
      - "サービス停止"
    high:
      - "不正アクセス試行"
      - "マルウェア検出"
      - "権限昇格"
    medium:
      - "設定異常"
      - "ログ異常"
      - "パフォーマンス異常"
      
  response_timeline:
    critical: "15分以内"
    high: "1時間以内"
    medium: "4時間以内"
    low: "24時間以内"
    
  escalation:
    level1: "セキュリティチーム"
    level2: "インフラチーム + マネジメント"
    level3: "経営陣 + 法務 + 広報"
```

### 2. セキュリティ KPI
```python
class SecurityMetrics:
    """セキュリティメトリクス"""
    
    def __init__(self):
        self.metrics = {
            'vulnerability_metrics': VulnerabilityMetrics(),
            'incident_metrics': IncidentMetrics(),
            'compliance_metrics': ComplianceMetrics()
        }
    
    def generate_security_dashboard(self) -> Dict[str, Any]:
        """セキュリティダッシュボード生成"""
        
        return {
            'overall_security_score': self._calculate_overall_score(),
            'vulnerability_summary': {
                'critical': self._count_vulnerabilities('critical'),
                'high': self._count_vulnerabilities('high'),
                'medium': self._count_vulnerabilities('medium'),
                'low': self._count_vulnerabilities('low')
            },
            'incident_summary': {
                'open_incidents': self._count_open_incidents(),
                'mttr_hours': self._calculate_mttr(),
                'incidents_this_month': self._count_monthly_incidents()
            },
            'compliance_status': {
                'policies_compliant': self._count_compliant_policies(),
                'total_policies': self._count_total_policies(),
                'compliance_percentage': self._calculate_compliance_percentage()
            },
            'security_controls': {
                'authentication_enabled': True,
                'encryption_enabled': True,
                'monitoring_enabled': True,
                'backup_enabled': True
            }
        }
```

## コンプライアンス

### 1. データ保護規制対応
```yaml
compliance_frameworks:
  gdpr:
    description: "EU General Data Protection Regulation"
    requirements:
      - "データ最小化原則"
      - "明示的同意"
      - "データポータビリティ"
      - "忘れられる権利"
      - "プライバシー・バイ・デザイン"
      
  ccpa:
    description: "California Consumer Privacy Act"
    requirements:
      - "データ開示権"
      - "削除権"
      - "オプトアウト権"
      - "プライバシーポリシー"
      
  sox:
    description: "Sarbanes-Oxley Act"
    requirements:
      - "内部統制"
      - "監査証跡"
      - "職務分離"
      - "データ保持"
```

### 2. セキュリティ評価
```python
def conduct_security_assessment() -> SecurityAssessment:
    """セキュリティ評価実施"""
    
    assessment = SecurityAssessment()
    
    # 技術的評価
    assessment.technical_score = evaluate_technical_controls()
    
    # 運用的評価
    assessment.operational_score = evaluate_operational_controls()
    
    # コンプライアンス評価
    assessment.compliance_score = evaluate_compliance_status()
    
    # 総合スコア
    assessment.overall_score = (
        assessment.technical_score * 0.4 +
        assessment.operational_score * 0.3 +
        assessment.compliance_score * 0.3
    )
    
    # 推奨事項
    assessment.recommendations = generate_security_recommendations(assessment)
    
    return assessment
```

## 改訂履歴

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0.0 | 2025-01-27 | 初期ドラフト作成 | Copilot Agent |

---

包括的なセキュリティモデルにより、安全で信頼性の高いシステム運用を実現してください。