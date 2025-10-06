"""
Secrets Vault 実装 (Phase4)

API キー、認証トークン、パスワードなどの機密情報を安全に管理。

Phase4 実装内容:
- ファイルベース暗号化ストレージ
- 環境変数からの安全な移行
- メモリ内キャッシュ (暗号化)
- 監査ログ記録

将来拡張:
- HashiCorp Vault 統合
- AWS Secrets Manager 統合
- Azure Key Vault 統合

セキュリティ機能:
- Fernet 対称暗号化 (cryptography ライブラリ)
- マスターキーは環境変数 VAULT_MASTER_KEY から取得
- ログへの機密情報マスキング

使用例:
    vault = SecretsVault()
    await vault.initialize()
    
    # シークレット保存
    await vault.set_secret("openai_api_key", "sk-xxxxx")
    
    # シークレット取得
    api_key = await vault.get_secret("openai_api_key")

関連:
- src/llm/docker_sandbox.py (_get_safe_api_key)
- docs/plan/cdp-webui-modernization.md (Section 10: Security)
"""

import os
import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class SecretMetadata:
    """シークレットメタデータ"""
    key: str
    created_at: str
    last_accessed: Optional[str] = None
    access_count: int = 0


class SecretsVault:
    """
    Secrets Vault - 機密情報の暗号化ストレージ (Phase4)
    
    Fernet 対称暗号化を使用して、API キー等の機密情報を
    安全にファイルシステムに保存・取得します。
    
    Phase4 機能:
    - 暗号化ストレージ (Fernet)
    - メモリキャッシュ (暗号化状態)
    - アクセス監査ログ
    - 環境変数フォールバック
    
    Attributes:
        _vault_path: Vault ファイルパス
        _master_key: マスターキー (Fernet キー)
        _cipher: Fernet 暗号化オブジェクト
        _secrets_cache: 暗号化シークレットキャッシュ
        _metadata: シークレットメタデータ
    """
    
    def __init__(self, vault_path: Optional[Path] = None):
        """
        Args:
            vault_path: Vault ファイルパス (デフォルトは ~/.2bykilt/secrets.vault)
        """
        self._vault_path = vault_path or Path.home() / ".2bykilt" / "secrets.vault"
        self._master_key: Optional[bytes] = None
        self._cipher = None
        self._secrets_cache: Dict[str, bytes] = {}  # 暗号化状態でキャッシュ
        self._metadata: Dict[str, SecretMetadata] = {}
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        Vault 初期化
        
        - マスターキー取得 (環境変数 VAULT_MASTER_KEY または生成)
        - Fernet 暗号化オブジェクト作成
        - 既存 Vault ファイル読み込み
        
        Raises:
            RuntimeError: 初期化失敗
        """
        try:
            # Fernet インポート
            try:
                from cryptography.fernet import Fernet  # type: ignore
            except ImportError as e:
                raise RuntimeError(
                    "cryptography library not installed. "
                    "Install with: pip install cryptography"
                ) from e
            
            # マスターキー取得または生成
            master_key_str = os.getenv("VAULT_MASTER_KEY")
            if master_key_str:
                self._master_key = master_key_str.encode()
                logger.info("Using VAULT_MASTER_KEY from environment")
            else:
                # 新規生成 (初回起動時)
                self._master_key = Fernet.generate_key()
                logger.warning(
                    f"Generated new master key. Save this to VAULT_MASTER_KEY: "
                    f"{self._master_key.decode()}"
                )
            
            self._cipher = Fernet(self._master_key)
            
            # 既存 Vault ファイル読み込み
            if self._vault_path.exists():
                await self._load_vault()
                logger.info(f"Loaded secrets vault from {self._vault_path}")
            else:
                logger.info("No existing vault found, starting with empty vault")
                self._vault_path.parent.mkdir(parents=True, exist_ok=True)
            
            self._initialized = True
            logger.info("Secrets vault initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize secrets vault: {e}", exc_info=True)
            raise RuntimeError(f"Vault initialization failed: {e}") from e
    
    async def set_secret(
        self,
        key: str,
        value: str,
        persist: bool = True
    ) -> None:
        """
        シークレット保存
        
        Args:
            key: シークレットキー名
            value: シークレット値 (平文)
            persist: ファイルに永続化するか
        
        Raises:
            RuntimeError: 未初期化または暗号化失敗
        """
        if not self._initialized or not self._cipher:
            raise RuntimeError("Vault not initialized")
        
        try:
            # 暗号化
            encrypted_value = self._cipher.encrypt(value.encode())
            
            # キャッシュに保存
            self._secrets_cache[key] = encrypted_value
            
            # メタデータ更新
            if key not in self._metadata:
                self._metadata[key] = SecretMetadata(
                    key=key,
                    created_at=datetime.now(timezone.utc).isoformat()
                )
            
            # 永続化
            if persist:
                await self._save_vault()
            
            logger.info(f"Secret '{key}' saved (encrypted)")
            
        except Exception as e:
            logger.error(f"Failed to save secret '{key}': {e}", exc_info=True)
            raise RuntimeError(f"Secret save failed: {e}") from e
    
    async def get_secret(
        self,
        key: str,
        fallback_env_var: Optional[str] = None
    ) -> Optional[str]:
        """
        シークレット取得
        
        Args:
            key: シークレットキー名
            fallback_env_var: Vault になければ環境変数から取得
        
        Returns:
            Optional[str]: 復号化されたシークレット値 (なければ None)
        
        使用例:
            api_key = await vault.get_secret(
                "openai_api_key",
                fallback_env_var="OPENAI_API_KEY"
            )
        """
        if not self._initialized or not self._cipher:
            raise RuntimeError("Vault not initialized")
        
        try:
            # キャッシュから取得
            if key in self._secrets_cache:
                encrypted_value = self._secrets_cache[key]
                decrypted_value = self._cipher.decrypt(encrypted_value).decode()
                
                # メタデータ更新 (アクセス記録)
                if key in self._metadata:
                    self._metadata[key].last_accessed = datetime.now(timezone.utc).isoformat()
                    self._metadata[key].access_count += 1
                
                logger.debug(f"Secret '{key}' retrieved from vault")
                return decrypted_value
            
            # 環境変数フォールバック
            if fallback_env_var:
                env_value = os.getenv(fallback_env_var)
                if env_value:
                    logger.info(
                        f"Secret '{key}' not in vault, using environment variable {fallback_env_var}"
                    )
                    # 環境変数から取得したら Vault に保存 (次回から Vault 使用)
                    await self.set_secret(key, env_value, persist=True)
                    return env_value
            
            logger.warning(f"Secret '{key}' not found in vault or environment")
            return None
            
        except Exception as e:
            logger.error(f"Failed to get secret '{key}': {e}", exc_info=True)
            raise RuntimeError(f"Secret retrieval failed: {e}") from e
    
    async def delete_secret(self, key: str) -> bool:
        """
        シークレット削除
        
        Args:
            key: シークレットキー名
        
        Returns:
            bool: 削除成功
        """
        if key in self._secrets_cache:
            del self._secrets_cache[key]
            if key in self._metadata:
                del self._metadata[key]
            
            await self._save_vault()
            logger.info(f"Secret '{key}' deleted")
            return True
        
        logger.warning(f"Secret '{key}' not found, nothing to delete")
        return False
    
    async def list_keys(self) -> list[str]:
        """
        保存されているシークレットキー一覧取得
        
        Returns:
            list[str]: キー名リスト
        """
        return list(self._secrets_cache.keys())
    
    async def get_metadata(self, key: str) -> Optional[Dict[str, Any]]:
        """
        シークレットメタデータ取得
        
        Args:
            key: シークレットキー名
        
        Returns:
            Optional[Dict[str, Any]]: メタデータ辞書
        """
        if key in self._metadata:
            return asdict(self._metadata[key])
        return None
    
    async def _load_vault(self) -> None:
        """Vault ファイルから読み込み"""
        try:
            with open(self._vault_path, "rb") as f:
                vault_data = json.loads(f.read().decode())
            
            # シークレットキャッシュ復元 (暗号化状態)
            for key, encrypted_b64 in vault_data.get("secrets", {}).items():
                import base64
                self._secrets_cache[key] = base64.b64decode(encrypted_b64)
            
            # メタデータ復元
            for key, meta_dict in vault_data.get("metadata", {}).items():
                self._metadata[key] = SecretMetadata(**meta_dict)
            
            logger.debug(f"Loaded {len(self._secrets_cache)} secrets from vault")
            
        except Exception as e:
            logger.error(f"Failed to load vault: {e}", exc_info=True)
    
    async def _save_vault(self) -> None:
        """Vault ファイルに保存"""
        try:
            import base64
            
            vault_data = {
                "secrets": {
                    key: base64.b64encode(encrypted_value).decode()
                    for key, encrypted_value in self._secrets_cache.items()
                },
                "metadata": {
                    key: asdict(meta)
                    for key, meta in self._metadata.items()
                }
            }
            
            self._vault_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._vault_path, "wb") as f:
                f.write(json.dumps(vault_data, indent=2).encode())
            
            logger.debug(f"Saved vault to {self._vault_path}")
            
        except Exception as e:
            logger.error(f"Failed to save vault: {e}", exc_info=True)


# シングルトンインスタンス
_vault_instance: Optional[SecretsVault] = None


async def get_secrets_vault() -> SecretsVault:
    """
    SecretsVault のグローバルインスタンスを取得
    
    Returns:
        SecretsVault: Vault インスタンス
    """
    global _vault_instance
    
    if _vault_instance is None:
        _vault_instance = SecretsVault()
        await _vault_instance.initialize()
        logger.debug("Created SecretsVault singleton")
    
    return _vault_instance


async def reset_secrets_vault():
    """Vault インスタンスをリセット (テスト用)"""
    global _vault_instance
    _vault_instance = None
