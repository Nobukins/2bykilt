"""
UI サービス層ユニットテスト (Phase3)

FeatureFlagService のテストスイート。

テスト範囲:
- 環境変数からのフラグ読み込み
- UI 表示設定生成
- エンジン可用性判定

関連:
- src/ui/services/feature_flag_service.py
- docs/plan/cdp-webui-modernization.md (Section 7: Testing Strategy)
"""

import pytest
from unittest.mock import patch
from src.ui.services.feature_flag_service import (
    FeatureFlagService,
    get_feature_flag_service,
)


class TestFeatureFlagService:
    """FeatureFlagService ユニットテスト。"""

    @patch.dict(
        "os.environ",
        {
            "RUNNER_ENGINE": "playwright",
            "ENABLE_LLM": "true",
            "UI_MODERN_LAYOUT": "true",
            "UI_TRACE_VIEWER": "true",
        },
    )
    def test_load_flags_all_enabled(self):
        """全フラグ有効時のロード。"""
        service = FeatureFlagService()
        state = service.get_current_state()

        assert state.runner_engine == "playwright"
        assert state.enable_llm is True
        assert state.ui_modern_layout is True
        assert state.ui_trace_viewer is True

    @patch.dict("os.environ", {}, clear=True)
    def test_load_flags_defaults(self):
        """デフォルト値のロード (環境変数なし)。"""
        service = FeatureFlagService()
        state = service.get_current_state()

        assert state.runner_engine == "playwright"  # デフォルト
        assert state.enable_llm is False
        assert state.ui_modern_layout is False
        assert state.ui_trace_viewer is False

    @patch.dict("os.environ", {"RUNNER_ENGINE": "cdp"})
    def test_is_engine_available_cdp(self):
        """CDP エンジン可用性判定。"""
        service = FeatureFlagService()

        assert service.is_engine_available("cdp") is True
        assert service.is_engine_available("playwright") is False

    @patch.dict("os.environ", {"UI_TRACE_VIEWER": "true"})
    def test_ui_visibility_config(self):
        """UI 表示設定生成。"""
        service = FeatureFlagService()
        config = service.get_ui_visibility_config()

        assert config["trace_viewer"] is True
        assert config["run_history"] is True  # デフォルトで表示

    @patch.dict("os.environ", {"RUNNER_ENGINE": "invalid"})
    def test_invalid_engine_fallback(self):
        """不正なエンジン値のフォールバック。"""
        service = FeatureFlagService()
        state = service.get_current_state()

        # 不正値は "playwright" にフォールバック
        assert state.runner_engine == "playwright"  # フォールバックを検証
        # 実際の使用時に検証される想定

    def test_singleton_pattern(self):
        """シングルトンパターン検証。"""
        service1 = get_feature_flag_service()
        service2 = get_feature_flag_service()

        assert service1 is service2
