"""
UI 統合テスト (Phase3)

ModernUI 全体の統合テストスイート。

テスト範囲:
- UI コンポーネント統合
- フィーチャーフラグ連携
- Gradio インターフェース構築

Phase4 拡張予定:
- 実際の Gradio セッションテスト
- WebSocket 統合テスト
- E2E ブラウザテスト

関連:
- src/ui/main_ui.py
- docs/plan/cdp-webui-modernization.md (Section 7.3: Integration Tests)
"""

import pytest
from unittest.mock import patch, MagicMock

from src.ui.main_ui import create_modern_ui


@pytest.mark.local_only
class TestModernUIIntegration:
    """ModernUI 統合テスト。"""

    @patch("src.ui.main_ui.gr")
    def test_build_interface_with_gradio(self, mock_gr):
        """Gradio 使用時のインターフェース構築。"""
        # Gradio モックセットアップ
        mock_blocks = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks
        mock_gr.themes.Soft.return_value = "soft_theme"

        ui = create_modern_ui()
        interface = ui.build_interface()

        # Blocks が構築されたか
        mock_gr.Blocks.assert_called_once()
        assert interface is not None

    @patch("src.ui.main_ui.gr", None)
    def test_build_interface_without_gradio(self):
        """Gradio なしでの構築失敗。"""
        ui = create_modern_ui()
        interface = ui.build_interface()

        assert interface is None

    @patch("src.ui.main_ui.gr")
    @patch.dict(
        "os.environ",
        {
            "RUNNER_ENGINE": "playwright",
            "ENABLE_LLM": "true",
            "UI_MODERN_LAYOUT": "true",
        },
    )
    def test_ui_with_all_flags_enabled(self, mock_gr):
        """全フラグ有効時の UI 構築。"""
        mock_blocks = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_blocks

        ui = create_modern_ui()
        _ = ui.build_interface()  # Interface build test

        # SettingsPanel が Playwright/LLM 有効を検知
        assert ui._settings_panel is not None
        assert ui._trace_viewer is not None
        assert ui._run_history is not None

    @patch("src.ui.main_ui.gr")
    def test_launch_calls_gradio_launch(self, mock_gr):
        """launch() が Gradio.launch() を呼び出すか。"""
        mock_interface = MagicMock()
        mock_gr.Blocks.return_value.__enter__.return_value = mock_interface
        mock_gr.themes.Soft.return_value = "soft_theme"

        ui = create_modern_ui()

        # launch() 実行
        ui.launch(server_name="127.0.0.1", server_port=7861, share=False)

        # Gradio launch が呼ばれたか
        mock_interface.launch.assert_called_once_with(
            server_name="127.0.0.1",
            server_port=7861,
            share=False,
        )


@pytest.mark.local_only
class TestComponentIntegration:
    """コンポーネント間連携テスト。"""

    @patch.dict("os.environ", {"RUNNER_ENGINE": "playwright"})
    def test_settings_panel_reflects_engine_state(self):
        """SettingsPanel がエンジン状態を反映するか。"""
        ui = create_modern_ui()

        # SettingsPanel が FeatureFlagService 経由でエンジン状態取得
        summary = ui._settings_panel.get_status_summary()
        assert "RUNNER_ENGINE: playwright" in summary

    def test_trace_viewer_run_history_independence(self):
        """TraceViewer と RunHistory の独立性。"""
        ui = create_modern_ui()

        # 両コンポーネントが独立したインスタンス
        assert ui._trace_viewer is not ui._run_history
        assert ui._trace_viewer.get_current_trace() is None  # 初期状態
        # 履歴ロード成功 (空でも >= 0)
        assert ui._run_history._history_data is not None


@pytest.mark.local_only
class TestUIVisibilityControl:
    """フィーチャーフラグによる表示制御テスト。"""

    @patch.dict("os.environ", {"UI_TRACE_VIEWER": "false"}, clear=True)
    def test_trace_viewer_hidden_when_flag_disabled(self):
        """UI_TRACE_VIEWER 無効時に TraceViewer 非表示。"""
        ui = create_modern_ui()

        assert ui._trace_viewer._is_visible() is False

    @patch.dict("os.environ", {"UI_TRACE_VIEWER": "true"})
    def test_trace_viewer_visible_when_flag_enabled(self):
        """UI_TRACE_VIEWER 有効時に TraceViewer 表示。"""
        ui = create_modern_ui()

        assert ui._trace_viewer._is_visible() is True

    @patch.dict("os.environ", {}, clear=True)
    def test_run_history_default_visible(self):
        """RunHistory はデフォルトで表示 (フラグなし)。"""
        ui = create_modern_ui()

        assert ui._run_history._is_visible() is True


@pytest.mark.local_only
class TestErrorHandling:
    """エラーハンドリングテスト。"""

    @patch("src.ui.main_ui.gr", None)
    def test_launch_fails_gracefully_without_gradio(self):
        """Gradio なし時の launch() は正常終了。"""
        ui = create_modern_ui()

        # 例外発生せず終了
        try:
            ui.launch()
        except Exception as e:
            pytest.fail(f"launch() raised exception: {e}")

    @patch("src.ui.main_ui.gr")
    def test_build_interface_handles_component_error(self, mock_gr):
        """コンポーネント初期化エラーのハンドリング。"""
        # SettingsPanel 初期化失敗をシミュレート
        with patch(
            "src.ui.main_ui.create_settings_panel", side_effect=Exception("Mock error")
        ):
            try:
                _ = create_modern_ui()  # Expecting exception
                pytest.fail("Expected exception during initialization")
            except Exception as e:
                assert "Mock error" in str(e)
