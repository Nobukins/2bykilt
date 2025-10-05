"""
LLMServiceGateway スタブ (Phase1-2 基盤)

ENABLE_LLM=true 時に AI モジュールを隔離ランタイム（サンドボックス/サイドカー）
経由で実行するためのゲートウェイインターフェース。

Phase1-2 スコープ:
- インターフェース定義とスタブ実装
- ENABLE_LLM=false 時のバイパス機構

Phase3-4 拡張予定:
- 実際のサンドボックス/サイドカー起動ロジック
- シークレット管理統合（Vault連携）
- 監査ログフック
- レート制限とネットワークポリシー

関連:
- docs/security/SECURITY_MODEL.md
- docs/plan/cdp-webui-modernization.md (Section 5.6)
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


# シングルトンインスタンス（Phase1-2 では簡易実装）
_gateway_instance: Optional[LLMServiceGateway] = None


def get_llm_gateway() -> LLMServiceGateway:
    """
    LLMServiceGateway のグローバルインスタンスを取得
    
    Returns:
        LLMServiceGateway: ゲートウェイインスタンス（スタブまたは実装）
    """
    global _gateway_instance
    
    if _gateway_instance is None:
        # Phase3 で環境変数や設定に応じて実装クラスを切り替え
        _gateway_instance = LLMServiceGatewayStub()
        logger.debug("Created LLMServiceGateway singleton (stub)")
    
    return _gateway_instance


def reset_llm_gateway():
    """
    ゲートウェイインスタンスをリセット（テスト用）
    """
    global _gateway_instance
    _gateway_instance = None
