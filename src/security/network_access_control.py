"""
ネットワークアクセス制御 (Issue #62b)

サンドボックス内でのネットワークアクセスを制御する。
ホワイトリストに基づいて接続先を制限。

作成日: 2025-10-17
"""
import re
import logging
from typing import List, Set, Optional, Pattern
from dataclasses import dataclass, field
from urllib.parse import urlparse
from enum import Enum

logger = logging.getLogger(__name__)


class NetworkProtocol(Enum):
    """ネットワークプロトコル"""
    HTTP = "http"
    HTTPS = "https"
    FTP = "ftp"
    SSH = "ssh"
    SMTP = "smtp"
    ALL = "all"


@dataclass
class NetworkRule:
    """ネットワークアクセスルール"""
    host: str  # ホスト名またはIPアドレス（ワイルドカード対応）
    port: Optional[int] = None  # ポート番号（None=全ポート）
    protocol: NetworkProtocol = NetworkProtocol.ALL
    allow: bool = True  # True=許可, False=拒否
    reason: str = ""  # ルールの理由


@dataclass
class NetworkPolicy:
    """ネットワークアクセスポリシー"""
    # 許可ホスト（ホワイトリスト）
    allowed_hosts: List[str] = field(default_factory=list)
    
    # 拒否ホスト（ブラックリスト）
    denied_hosts: List[str] = field(default_factory=list)
    
    # 許可プロトコル
    allowed_protocols: List[NetworkProtocol] = field(default_factory=lambda: [
        NetworkProtocol.HTTP,
        NetworkProtocol.HTTPS
    ])
    
    # 許可ポート範囲
    allowed_ports: List[int] = field(default_factory=list)
    
    # デフォルトポリシー: True=許可, False=拒否
    default_allow: bool = False
    
    # プライベートIPアドレスへのアクセスを許可
    allow_private_ips: bool = False
    
    # localhostへのアクセスを許可
    allow_localhost: bool = False


class NetworkAccessControl:
    """
    ネットワークアクセス制御
    
    サンドボックス内でのネットワークアクセスを制御する。
    """
    
    # 常に拒否すべきホスト・ドメイン
    ALWAYS_DENIED_HOSTS = [
        "169.254.169.254",  # AWS metadata service
        "metadata.google.internal",  # GCP metadata service
        "metadata.azure.com",  # Azure metadata service
    ]
    
    # プライベートIPアドレス範囲（CIDR表記）
    PRIVATE_IP_RANGES = [
        "10.0.0.0/8",
        "172.16.0.0/12",
        "192.168.0.0/16",
        "127.0.0.0/8",  # localhost
        "169.254.0.0/16",  # link-local
        "::1/128",  # IPv6 localhost
        "fc00::/7",  # IPv6 private
    ]
    
    # 危険なポート
    DANGEROUS_PORTS = [
        22,   # SSH
        23,   # Telnet
        3389, # RDP
        5900, # VNC
    ]
    
    def __init__(self, policy: Optional[NetworkPolicy] = None):
        """
        ネットワークアクセス制御を初期化
        
        Args:
            policy: ネットワークポリシー（省略時はデフォルト）
        """
        self.policy = policy or NetworkPolicy()
        self._compile_patterns()
    
    def _compile_patterns(self):
        """ホストパターンを正規表現にコンパイル"""
        self._allowed_patterns: List[Pattern] = []
        self._denied_patterns: List[Pattern] = []
        
        for host in self.policy.allowed_hosts:
            pattern = self._host_to_pattern(host)
            self._allowed_patterns.append(re.compile(pattern, re.IGNORECASE))
        
        for host in self.policy.denied_hosts:
            pattern = self._host_to_pattern(host)
            self._denied_patterns.append(re.compile(pattern, re.IGNORECASE))
    
    def _host_to_pattern(self, host: str) -> str:
        """
        ホスト名をワイルドカード対応の正規表現パターンに変換
        
        Args:
            host: ホスト名（*をワイルドカードとして使用可能）
            
        Returns:
            正規表現パターン
        """
        # エスケープ
        pattern = re.escape(host)
        # *をワイルドカードとして展開
        pattern = pattern.replace(r'\*', '.*')
        # 完全一致
        return f'^{pattern}$'
    
    def is_host_allowed(
        self,
        host: str,
        port: Optional[int] = None,
        protocol: Optional[NetworkProtocol] = None
    ) -> tuple[bool, str]:
        """
        ホストへのアクセスが許可されているかチェック
        
        Args:
            host: ホスト名またはIPアドレス
            port: ポート番号
            protocol: プロトコル
            
        Returns:
            (許可/拒否, 理由)
        """
        # メタデータサービスなどの常に拒否すべきホスト
        for denied in self.ALWAYS_DENIED_HOSTS:
            if host.lower() == denied.lower():
                logger.warning(f"Access to metadata service denied: {host}")
                return False, f"Metadata service access denied: {denied}"
        
        # localhostチェック
        if not self.policy.allow_localhost:
            if host.lower() in ['localhost', '127.0.0.1', '::1']:
                logger.info(f"Localhost access denied: {host}")
                return False, "Localhost access not allowed"
        
        # プライベートIPチェック
        if not self.policy.allow_private_ips and self._is_private_ip(host):
            logger.info(f"Private IP access denied: {host}")
            return False, "Private IP access not allowed"
        
        # プロトコルチェック
        if protocol and protocol not in self.policy.allowed_protocols:
            logger.info(f"Protocol not allowed: {protocol.value}")
            return False, f"Protocol not allowed: {protocol.value}"
        
        # ポートチェック
        if port:
            if port in self.DANGEROUS_PORTS:
                logger.warning(f"Dangerous port blocked: {port}")
                return False, f"Dangerous port: {port}"
            
            if self.policy.allowed_ports and port not in self.policy.allowed_ports:
                logger.info(f"Port not in allowed list: {port}")
                return False, f"Port not allowed: {port}"
        
        # 明示的に拒否されているホストをチェック
        for pattern in self._denied_patterns:
            if pattern.match(host):
                logger.info(f"Host denied by policy: {host}")
                return False, "Host denied by policy"
        
        # 明示的に許可されているホストをチェック
        for pattern in self._allowed_patterns:
            if pattern.match(host):
                logger.debug(f"Host allowed: {host}")
                return True, "Host allowed by policy"
        
        # デフォルトポリシーを適用
        if self.policy.default_allow:
            logger.debug(f"Host allowed by default: {host}")
            return True, "Allowed by default"
        else:
            logger.info(f"Host denied by default: {host}")
            return False, "Denied by default (whitelist mode)"
    
    def _is_private_ip(self, host: str) -> bool:
        """
        プライベートIPアドレスかチェック
        
        Args:
            host: ホスト名またはIPアドレス
            
        Returns:
            プライベートIPの場合True
        """
        # 簡易実装（完全なCIDR計算は省略）
        if host.startswith("10."):
            return True
        if host.startswith("192.168."):
            return True
        if host.startswith("172."):
            # 172.16.0.0 - 172.31.255.255
            parts = host.split(".")
            if len(parts) >= 2:
                second_octet = int(parts[1])
                if 16 <= second_octet <= 31:
                    return True
        if host.startswith("127."):
            return True
        if host == "localhost":
            return True
        
        return False
    
    def validate_url(self, url: str) -> tuple[bool, str]:
        """
        URLを検証
        
        Args:
            url: チェックするURL
            
        Returns:
            (許可/拒否, 理由)
        """
        try:
            parsed = urlparse(url)
            
            # プロトコルチェック
            protocol_map = {
                "http": NetworkProtocol.HTTP,
                "https": NetworkProtocol.HTTPS,
                "ftp": NetworkProtocol.FTP,
                "ssh": NetworkProtocol.SSH,
                "smtp": NetworkProtocol.SMTP,
            }
            
            protocol = protocol_map.get(parsed.scheme.lower())
            if not protocol:
                return False, f"Unknown protocol: {parsed.scheme}"
            
            # ホストとポートを抽出
            host = parsed.hostname or ""
            port = parsed.port
            
            # ホストチェック
            return self.is_host_allowed(host, port, protocol)
            
        except Exception as e:
            logger.error(f"Failed to parse URL: {url} - {e}")
            return False, f"Invalid URL: {e}"
    
    def validate_connection(
        self,
        host: str,
        port: int,
        protocol: Optional[NetworkProtocol] = None
    ) -> tuple[bool, str]:
        """
        ネットワーク接続を検証
        
        Args:
            host: 接続先ホスト
            port: 接続先ポート
            protocol: プロトコル
            
        Returns:
            (許可/拒否, 理由)
        """
        logger.debug(f"Validating connection to {host}:{port}")
        
        allowed, reason = self.is_host_allowed(host, port, protocol)
        
        if not allowed:
            logger.warning(f"Network connection denied: {host}:{port} - {reason}")
        
        return allowed, reason


def create_default_network_policy() -> NetworkPolicy:
    """
    デフォルトのネットワークポリシーを作成
    
    Returns:
        デフォルトポリシー
    """
    return NetworkPolicy(
        allowed_hosts=[
            "*.github.com",
            "*.githubusercontent.com",
            "api.openai.com",
            "*.anthropic.com",
        ],
        denied_hosts=[],
        allowed_protocols=[NetworkProtocol.HTTP, NetworkProtocol.HTTPS],
        allowed_ports=[],  # 空=全ポート許可
        default_allow=False,  # ホワイトリストモード
        allow_private_ips=False,
        allow_localhost=False
    )


def create_strict_network_policy() -> NetworkPolicy:
    """
    厳格なネットワークポリシーを作成（ネットワークアクセス禁止）
    
    Returns:
        厳格なポリシー
    """
    return NetworkPolicy(
        allowed_hosts=[],  # 何も許可しない
        denied_hosts=["*"],  # 全て拒否
        allowed_protocols=[],
        allowed_ports=[],
        default_allow=False,
        allow_private_ips=False,
        allow_localhost=False
    )


def create_api_only_policy(api_domains: List[str]) -> NetworkPolicy:
    """
    API接続のみ許可するネットワークポリシーを作成
    
    Args:
        api_domains: 許可するAPIドメインリスト
        
    Returns:
        APIのみポリシー
    """
    return NetworkPolicy(
        allowed_hosts=api_domains,
        denied_hosts=[],
        allowed_protocols=[NetworkProtocol.HTTPS],  # HTTPSのみ
        allowed_ports=[443],  # HTTPS標準ポート
        default_allow=False,
        allow_private_ips=False,
        allow_localhost=False
    )
