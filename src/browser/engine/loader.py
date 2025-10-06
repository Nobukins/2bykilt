"""
エンジンローダー

フィーチャーフラグまたは環境変数に基づいて適切な BrowserEngine 実装を
動的にロードします。

使用例:
    # 環境変数 RUNNER_ENGINE=playwright が設定されている場合
    engine = EngineLoader.load_engine()
    
    # 明示的にエンジンタイプを指定
    engine = EngineLoader.load_engine("cdp")
"""

import os
import logging
from typing import Optional
from .browser_engine import BrowserEngine, EngineType

logger = logging.getLogger(__name__)


class EngineLoader:
    """フィーチャーフラグに基づいてエンジンをロード"""
    
    _ENGINE_REGISTRY = {}
    
    @classmethod
    def register_engine(cls, engine_type: str, engine_class):
        """
        エンジン実装を登録（プラグイン機構用）
        
        Args:
            engine_type: エンジンタイプ識別子
            engine_class: BrowserEngine を継承したクラス
        """
        cls._ENGINE_REGISTRY[engine_type] = engine_class
        logger.info(f"Registered engine: {engine_type} -> {engine_class.__name__}")
    
    @classmethod
    def load_engine(cls, engine_type: Optional[str] = None) -> BrowserEngine:
        """
        エンジンインスタンスを生成
        
        Args:
            engine_type: "playwright" or "cdp" (Noneの場合は環境変数から取得)
            
        Returns:
            BrowserEngine: ロードされたエンジン
            
        Raises:
            ValueError: 未サポートのエンジンタイプまたはエンジン未登録
        """
        # エンジンタイプ決定（優先順: 引数 > 環境変数 > デフォルト）
        if engine_type is None:
            engine_type = os.getenv("RUNNER_ENGINE", "playwright")
        
        # エンジンタイプ正規化
        engine_type = engine_type.lower().strip()
        
        # レジストリから取得
        if engine_type not in cls._ENGINE_REGISTRY:
            # 遅延インポートによる自動登録を試行
            cls._lazy_register_engines()
        
        if engine_type not in cls._ENGINE_REGISTRY:
            available = ", ".join(cls._ENGINE_REGISTRY.keys()) or "(none registered)"
            raise ValueError(
                f"Unsupported engine type: '{engine_type}'. "
                f"Available engines: {available}"
            )
        
        engine_class = cls._ENGINE_REGISTRY[engine_type]
        logger.info(f"Loading engine: {engine_type} ({engine_class.__name__})")
        
        # エンジンインスタンス生成
        try:
            engine_enum = EngineType(engine_type)
        except ValueError:
            # EngineType Enum に存在しない場合でもレジストリがあれば許可
            logger.warning(f"Engine type '{engine_type}' not in EngineType enum, using custom implementation")
            # 暫定的に PLAYWRIGHT をフォールバック
            engine_enum = EngineType.PLAYWRIGHT
        
        return engine_class(engine_enum)
    
    @classmethod
    def _lazy_register_engines(cls):
        """
        利用可能なエンジンを遅延インポートして登録
        
        フェーズ1: PlaywrightEngine のみ
        フェーズ2: CDPEngine 追加
        """
        # PlaywrightEngine 登録試行
        try:
            from .playwright_engine import PlaywrightEngine
            cls.register_engine("playwright", PlaywrightEngine)
        except ImportError as e:
            logger.warning(f"PlaywrightEngine not available: {e}")
        
        # CDPEngine 登録試行（フェーズ2で実装）
        try:
            from .cdp_engine import CDPEngine
            cls.register_engine("cdp", CDPEngine)
        except ImportError:
            logger.debug("CDPEngine not yet implemented (Phase2)")
    
    @classmethod
    def list_available_engines(cls) -> list:
        """
        利用可能なエンジンのリストを取得
        
        Returns:
            list: エンジンタイプ識別子のリスト
        """
        cls._lazy_register_engines()
        return list(cls._ENGINE_REGISTRY.keys())
