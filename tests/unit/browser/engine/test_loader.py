"""
EngineLoader ユニットテスト

フィーチャーフラグに基づくエンジンローディングと
レジストリ機構を検証します。

実行:
    pytest tests/unit/browser/engine/test_loader.py -v
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from src.browser.engine.loader import EngineLoader
from src.browser.engine.browser_engine import BrowserEngine, EngineType


class TestEngineLoader:
    """EngineLoader テスト"""
    
    def test_load_playwright_engine_explicit(self):
        """明示的に Playwright エンジンをロード"""
        engine = EngineLoader.load_engine("playwright")
        
        assert engine is not None
        assert engine.engine_type == EngineType.PLAYWRIGHT
    
    def test_load_engine_from_env_var(self):
        """環境変数からエンジンタイプを取得"""
        with patch.dict(os.environ, {"RUNNER_ENGINE": "playwright"}):
            engine = EngineLoader.load_engine()
            
            assert engine is not None
            assert engine.engine_type == EngineType.PLAYWRIGHT
    
    def test_load_engine_default(self):
        """デフォルトエンジン（playwright）をロード"""
        with patch.dict(os.environ, {}, clear=True):
            # RUNNER_ENGINE 未設定時はデフォルト
            engine = EngineLoader.load_engine()
            
            assert engine is not None
            assert engine.engine_type == EngineType.PLAYWRIGHT
    
    def test_load_unsupported_engine(self):
        """未サポートエンジンでエラー"""
        with pytest.raises(ValueError, match="Unsupported engine type"):
            EngineLoader.load_engine("unknown_engine")
    
    def test_list_available_engines(self):
        """利用可能なエンジンリストを取得"""
        engines = EngineLoader.list_available_engines()
        
        assert "playwright" in engines
        # フェーズ2 で "cdp" も追加される
    
    def test_register_custom_engine(self):
        """カスタムエンジンを動的登録"""
        class CustomEngine(BrowserEngine):
            async def launch(self, context):
                pass
            async def navigate(self, url, wait_until="domcontentloaded"):
                pass
            async def dispatch(self, action):
                pass
            async def capture_artifacts(self, artifact_types):
                return {}
            async def shutdown(self, capture_final_state=True):
                pass
        
        EngineLoader.register_engine("custom", CustomEngine)
        
        engine = EngineLoader.load_engine("custom")
        assert isinstance(engine, CustomEngine)
