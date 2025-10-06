"""
FeatureFlagService

バックエンドのフィーチャーフラグ状態を UI へ反映するためのサービス層。

Phase3 スコープ:
- 環境変数ベースのフラグ読み取り
- runner.engine, ui.modern_layout, ENABLE_LLM などの状態取得

Phase4 拡張予定:
- リアルタイムフラグ更新（Webhook/polling）
- フラグ変更履歴トラッキング
- UI からのフラグトグル（管理者権限）

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.4)
"""

import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field

from src.config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


@dataclass
class FeatureFlagState:
    """フィーチャーフラグの現在状態"""
    runner_engine: str = "playwright"  # playwright | cdp
    enable_llm: bool = False
    ui_modern_layout: bool = False
    ui_trace_viewer: bool = False
    ui_run_history: bool = True
    ui_realtime_updates: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class FeatureFlagService:
    """
    フィーチャーフラグ管理サービス
    
    環境変数や設定ファイルからフラグ状態を読み取り、
    UI コンポーネントへ提供します。
    """
    
    def __init__(self):
        self._cache: Optional[FeatureFlagState] = None
    
    def get_current_state(self, force_refresh: bool = False) -> FeatureFlagState:
        """
        現在のフラグ状態を取得
        
        Args:
            force_refresh: キャッシュを無視して再読み込み
            
        Returns:
            FeatureFlagState: フラグ状態
        """
        if self._cache is None or force_refresh:
            self._cache = self._load_from_environment()
        
        return self._cache
    
    def _load_from_environment(self) -> FeatureFlagState:
        """
        環境変数からフラグ状態をロード
        
        Returns:
            FeatureFlagState: 読み取った状態
        """
        metadata: Dict[str, Any] = {"source": "feature_flags"}

        try:
            runner_engine = str(
                FeatureFlags.get("runner.engine", expected_type=str, default="playwright")
            ).lower()
            if runner_engine not in {"playwright", "cdp"}:
                runner_engine = "playwright"

            # Prefer environment variable ENABLE_LLM if set; else feature flag; final fallback False
            import os
            if "ENABLE_LLM" in os.environ:
                enable_llm = os.environ.get("ENABLE_LLM", "false").lower() == "true"
            else:
                enable_llm = bool(FeatureFlags.get("enable_llm", expected_type=bool, default=False))
            ui_modern_layout = bool(
                FeatureFlags.get("ui.modern_layout", expected_type=bool, default=False)
            )
            ui_trace_viewer = bool(
                FeatureFlags.get("ui.trace_viewer", expected_type=bool, default=False)
            )
            ui_run_history = bool(
                FeatureFlags.get("ui.run_history", expected_type=bool, default=True)
            )
            ui_realtime_updates = bool(
                FeatureFlags.get("ui.realtime_updates", expected_type=bool, default=True)
            )

        except Exception as exc:  # pragma: no cover - defensive fallback
            import os

            metadata.update(
                {
                    "source": "environment_fallback",
                    "error": repr(exc),
                }
            )
            runner_engine = os.getenv("RUNNER_ENGINE", "playwright").lower()
            enable_llm = os.getenv("ENABLE_LLM", "false").lower() == "true"
            ui_modern_layout = os.getenv("UI_MODERN_LAYOUT", "false").lower() == "true"
            ui_trace_viewer = os.getenv("UI_TRACE_VIEWER", "false").lower() == "true"
            ui_run_history = os.getenv("UI_RUN_HISTORY", "true").lower() == "true"
            ui_realtime_updates = os.getenv("UI_REALTIME_UPDATES", "true").lower() == "true"

        state = FeatureFlagState(
            runner_engine=runner_engine,
            enable_llm=enable_llm,
            ui_modern_layout=ui_modern_layout,
            ui_trace_viewer=ui_trace_viewer,
            ui_run_history=ui_run_history,
            ui_realtime_updates=ui_realtime_updates,
            metadata=metadata,
        )

        logger.debug(
            "Loaded feature flags",
            extra={
                "event": "feature_flags.loaded",
                "engine": state.runner_engine,
                "enable_llm": state.enable_llm,
                "ui_modern_layout": state.ui_modern_layout,
                "ui_trace_viewer": state.ui_trace_viewer,
                "ui_run_history": state.ui_run_history,
                "ui_realtime_updates": state.ui_realtime_updates,
            },
        )
        return state
    
    def is_engine_available(self, engine_type: str) -> bool:
        """
        指定エンジンが利用可能か確認
        
        Args:
            engine_type: "playwright" | "cdp"
            
        Returns:
            bool: 利用可否
        """
        try:
            from src.browser.engine.loader import EngineLoader
            available = EngineLoader.list_available_engines()
            return engine_type in available
        except Exception as e:
            logger.warning(f"Failed to check engine availability: {e}")
            return False
    
    def get_ui_visibility_config(self) -> Dict[str, bool]:
        """
        UI コンポーネントの表示/非表示設定を取得
        
        Returns:
            Dict: {component_name: visible}
        """
        state = self.get_current_state()
        
        return {
            "trace_viewer": state.ui_trace_viewer,
            "run_history": state.ui_run_history and state.ui_modern_layout,
            "engine_selector": True,  # 常に表示
            "llm_status": True,  # ENABLE_LLM 状態を常に表示
            "settings_panel": state.ui_modern_layout,
            "realtime_updates": state.ui_realtime_updates,
        }


# シングルトンインスタンス
_service_instance: Optional[FeatureFlagService] = None


def get_feature_flag_service() -> FeatureFlagService:
    """
    FeatureFlagService のグローバルインスタンスを取得
    
    Returns:
        FeatureFlagService: サービスインスタンス
    """
    global _service_instance
    
    if _service_instance is None:
        _service_instance = FeatureFlagService()
        logger.debug("Created FeatureFlagService singleton")
    
    return _service_instance
