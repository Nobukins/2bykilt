"""
LLMServiceGateway (Phase4 完全実装)

ENABLE_LLM=true 時に AI モジュールを隔離ランタイム（サンドボックス/サイドカー）
経由で実行するためのゲートウェイインターフェース。

Phase1-2 実装内容:
- インターフェース定義とスタブ実装
- ENABLE_LLM=false 時のバイパス機構

Phase3-4 拡張内容:
- ✅ Docker サンドボックス統合 (DockerLLMSandbox)
- ✅ 実際の LLM 推論実装
- シークレット管理統合（Vault連携 - Phase4 後半）
- 監査ログフック
- レート制限とネットワークポリシー

関連:
- docs/security/SECURITY_MODEL.md
- docs/plan/cdp-webui-modernization.md (Section 5.6)
- src/llm/docker_sandbox.py
"""

import os
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class LLMServiceError(Exception):
    """LLM サービスエラーの基底クラス"""
    pass


class LLMServiceGateway(ABC):
    """
    LLM サービスゲートウェイ抽象クラス
    
    ENABLE_LLM フラグによって挙動を切り替え、
    有効時はサンドボックス経由で LLM 機能を提供します。
    """
    
    @abstractmethod
    async def initialize(self) -> None:
        """
        ゲートウェイを初期化
        
        - ENABLE_LLM=true: サンドボックス/サイドカー起動
        - ENABLE_LLM=false: no-op（バイパス）
        
        Raises:
            LLMServiceError: 初期化失敗時
        """
        pass
    
    @abstractmethod
    async def invoke_llm(self, prompt: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        LLM を呼び出し
        
        Args:
            prompt: プロンプト文字列
            config: LLM 設定（model, temperature 等）
            
        Returns:
            Dict: レスポンス {"text": "...", "usage": {...}}
            
        Raises:
            LLMServiceError: 呼び出し失敗時
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        ゲートウェイをシャットダウン
        
        サンドボックス/サイドカーがあれば停止します。
        """
        pass
    
    @abstractmethod
    def is_enabled(self) -> bool:
        """
        LLM 機能が有効かチェック
        
        Returns:
            bool: ENABLE_LLM=true かつ依存パッケージ利用可能
        """
        pass


class LLMServiceGatewayStub(LLMServiceGateway):
    """
    LLMServiceGateway のスタブ実装 (Phase1-2)
    
    ENABLE_LLM=false 時や、Phase3 で本格実装が完成するまでの
    暫定実装として機能します。
    """
    
    def __init__(self):
        self._enabled = os.getenv("ENABLE_LLM", "false").lower() == "true"
        self._initialized = False
    
    async def initialize(self) -> None:
        """
        スタブ初期化
        
        Phase1-2 ではログ出力のみ。Phase3 でサンドボックス起動ロジック追加。
        """
        logger.info(f"Initializing LLMServiceGateway (ENABLE_LLM={self._enabled})")
        
        if not self._enabled:
            logger.info("LLM service disabled, gateway will bypass all calls")
            self._initialized = True
            return
        
        # Phase3 で実装予定:
        #   - サンドボックス/サイドカーコンテナ起動
        #   - シークレット取得（Vault連携）
        #   - ネットワークポリシー適用
        #   - 監査ログ初期化
        
        logger.warning("LLM service enabled but sandbox not yet implemented (Phase3)")
        self._initialized = True
    
    async def invoke_llm(self, prompt: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        LLM 呼び出しスタブ
        
        Phase1-2 では常にダミーレスポンスを返します。
        Phase3 でサンドボックス経由の実際の LLM API 呼び出しを実装。
        """
        if not self._initialized:
            raise LLMServiceError("Gateway not initialized, call initialize() first")
        
        if not self._enabled:
            logger.debug("LLM disabled, returning empty response")
            return {
                "text": "",
                "usage": {},
                "disabled": True
            }
        
        # Phase3 実装予定:
        #   - サンドボックスへリクエスト送信
        #   - レート制限チェック
        #   - 監査ログ記録
        #   - シークレットマスキング
        
        logger.warning(f"LLM invocation stubbed (prompt length: {len(prompt)})")
        return {
            "text": "(LLM response placeholder - Phase3 implementation pending)",
            "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": 10},
            "stub": True
        }
    
    async def shutdown(self) -> None:
        """スタブシャットダウン"""
        logger.info("Shutting down LLMServiceGateway")
        
        if self._enabled:
            # Phase3 実装予定: サンドボックス/サイドカー停止
            logger.debug("Sandbox shutdown logic not yet implemented (Phase3)")
        
        self._initialized = False
    
    def is_enabled(self) -> bool:
        """LLM 機能有効状態を確認"""
        return self._enabled


# シングルトンインスタンス（Phase4 で Docker 実装追加）
_gateway_instance: Optional[LLMServiceGateway] = None


class DockerLLMServiceGateway(LLMServiceGateway):
    """
    Docker サンドボックス統合 LLM Gateway (Phase4)
    
    DockerLLMSandbox を使用して安全な LLM 実行を提供。
    
    Phase4 機能:
    - Docker コンテナでの LLM 分離実行
    - ネットワーク制限、リソース制限
    - Seccomp/AppArmor セキュリティプロファイル
    """
    
    def __init__(self):
        super().__init__()
        self._sandbox = None
        self._enabled = os.getenv("ENABLE_LLM", "false").lower() == "true"
        self._initialized = False
    
    async def initialize(self) -> None:
        """Docker サンドボックス初期化"""
        if not self._enabled:
            logger.info("ENABLE_LLM=false, skipping Docker sandbox initialization")
            self._initialized = True
            return
        
        try:
            from .docker_sandbox import DockerLLMSandbox
            
            logger.info("Initializing Docker LLM sandbox (Phase4)")
            
            self._sandbox = DockerLLMSandbox(
                image="python:3.11-slim",
                network_mode="none",  # 完全ネットワーク分離
                memory_limit="512m",
                enable_seccomp=True,
                enable_apparmor=True
            )
            
            await self._sandbox.start()
            logger.info("Docker LLM sandbox initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize Docker sandbox: {e}", exc_info=True)
            raise LLMServiceError(f"Sandbox initialization failed: {e}") from e
        
        self._initialized = True
    
    async def invoke_llm(
        self,
        prompt: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Docker サンドボックス経由で LLM 呼び出し"""
        if not self._initialized:
            raise LLMServiceError("Gateway not initialized")
        
        if not self._enabled:
            logger.info("ENABLE_LLM=false, skipping LLM invocation")
            return {
                "text": "(LLM disabled)",
                "usage": {"prompt_tokens": 0, "completion_tokens": 0},
                "bypass": True
            }
        
        try:
            logger.info(f"Invoking LLM via Docker sandbox (prompt length: {len(prompt)})")
            
            # サンドボックス経由で LLM 実行
            result = await self._sandbox.invoke_llm(
                prompt=prompt,
                model=context.get("model", "gpt-3.5-turbo") if context else "gpt-3.5-turbo",
                max_tokens=context.get("max_tokens", 1000) if context else 1000,
                temperature=context.get("temperature", 0.7) if context else 0.7
            )
            
            logger.info(f"LLM invocation successful (tokens={result.get('usage', {}).get('total_tokens')})")
            
            return {
                "text": result.get("response", ""),
                "usage": result.get("usage", {}),
                "model": result.get("model"),
                "sandbox_metrics": self._sandbox.get_metrics() if self._sandbox else {}
            }
            
        except Exception as e:
            logger.error(f"LLM invocation failed: {e}", exc_info=True)
            raise LLMServiceError(f"LLM invocation failed: {e}") from e
    
    async def shutdown(self) -> None:
        """Docker サンドボックスシャットダウン"""
        logger.info("Shutting down DockerLLMServiceGateway")
        
        if self._sandbox:
            try:
                await self._sandbox.stop()
                logger.info("Docker sandbox stopped successfully")
            except Exception as e:
                logger.warning(f"Failed to stop sandbox: {e}")
        
        self._sandbox = None
        self._initialized = False
    
    def is_enabled(self) -> bool:
        """LLM 機能有効状態を確認"""
        return self._enabled


def get_llm_gateway(use_docker: bool = True) -> LLMServiceGateway:
    """
    LLMServiceGateway のグローバルインスタンスを取得
    
    Args:
        use_docker: Docker サンドボックス使用 (Phase4)
    
    Returns:
        LLMServiceGateway: ゲートウェイインスタンス
    """
    global _gateway_instance
    
    if _gateway_instance is None:
        # Phase4: ENABLE_LLM=true かつ Docker 利用可能なら DockerLLMServiceGateway
        enable_llm = os.getenv("ENABLE_LLM", "false").lower() == "true"
        
        if enable_llm and use_docker:
            try:
                _gateway_instance = DockerLLMServiceGateway()
                logger.debug("Created DockerLLMServiceGateway singleton (Phase4)")
            except Exception as e:
                logger.warning(f"Failed to create Docker gateway, falling back to stub: {e}")
                _gateway_instance = LLMServiceGatewayStub()
        else:
            _gateway_instance = LLMServiceGatewayStub()
            logger.debug("Created LLMServiceGatewayStub singleton")
    
    return _gateway_instance


def reset_llm_gateway():
    """
    ゲートウェイインスタンスをリセット（テスト用）
    """
    global _gateway_instance
    _gateway_instance = None
