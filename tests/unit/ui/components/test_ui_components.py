"""
UI コンポーネントユニットテスト (Phase3)

SettingsPanel, TraceViewer, RunHistory のテストスイート。

テスト範囲:
- コンポーネントレンダリング
- フィーチャーフラグによる表示制御
- データ処理ロジック

Phase4 拡張予定:
- Gradio セッション統合テスト
- スナップショットテスト

関連:
- src/ui/components/
- docs/plan/cdp-webui-modernization.md (Section 7: Testing Strategy)
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.config.feature_flags import FeatureFlags, _reset_feature_flags_for_tests
from src.ui.components import create_run_history, create_settings_panel, create_trace_viewer
@pytest.fixture(autouse=True)
def reset_feature_flags():
    _reset_feature_flags_for_tests()
    FeatureFlags.clear_all_overrides()
    yield
    FeatureFlags.clear_all_overrides()



class TestSettingsPanel:
    """SettingsPanel コンポーネントテスト。"""

    @patch("src.ui.components.settings_panel.gr", None)
    def test_render_without_gradio(self):
        """Gradio 未インストール時のレンダリング。"""
        panel = create_settings_panel()
        with pytest.raises(RuntimeError):
            panel.render()

    @patch.dict(
        "os.environ",
        {
            "RUNNER_ENGINE": "playwright",
            "ENABLE_LLM": "true",
        },
    )
    def test_get_status_summary(self):
        """ステータスサマリ生成。"""
        panel = create_settings_panel()
        summary = panel.get_status_summary()

        assert "Engine=playwright" in summary
        assert "LLM=ON" in summary


class TestTraceViewer:
    """TraceViewer コンポーネントテスト。"""

    def test_extract_metadata_with_metadata_json(self):
        """metadata.json 含む ZIP からメタデータ抽出。"""
        viewer = create_trace_viewer()

        # 一時 ZIP ファイル作成 (テストデータ)
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            import zipfile

            with zipfile.ZipFile(tmp_zip.name, "w") as zf:
                metadata = {
                    "engine_type": "Playwright",
                    "actions_count": 5,
                }
                zf.writestr("metadata.json", json.dumps(metadata))

            # メタデータ抽出
            result = viewer._extract_metadata(Path(tmp_zip.name))

            assert result["file_name"] == Path(tmp_zip.name).name
            assert "file_size_kb" in result
            assert result.get("engine_type") == "Playwright"
            assert result.get("actions_count") == 5

            # クリーンアップ
            Path(tmp_zip.name).unlink()

    def test_extract_metadata_without_metadata_json(self):
        """metadata.json なし ZIP からの推測抽出。"""
        viewer = create_trace_viewer()

        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_zip:
            import zipfile

            with zipfile.ZipFile(tmp_zip.name, "w") as zf:
                zf.writestr("screenshot_1.png", b"fake image")
                zf.writestr("screenshot_2.png", b"fake image")

            result = viewer._extract_metadata(Path(tmp_zip.name))

            assert "artifacts" in result
            assert result["actions_count"] == 2  # screenshot 2 件

            Path(tmp_zip.name).unlink()

    def test_is_visible_enabled(self):
        """UI_TRACE_VIEWER 有効時の表示判定。"""
        FeatureFlags.set_override("ui.trace_viewer", True)
        viewer = create_trace_viewer()
        assert viewer._is_visible() is True

    def test_is_visible_disabled(self):
        """UI_TRACE_VIEWER 無効時の表示判定。"""
        FeatureFlags.set_override("ui.trace_viewer", False)
        viewer = create_trace_viewer()
        assert viewer._is_visible() is False


class TestRunHistory:
    """RunHistory コンポーネントテスト。"""

    def test_load_empty_history(self):
        """空履歴ファイルのロード。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump([], tmp)
            tmp.flush()

            history = create_run_history(history_file=Path(tmp.name))
            assert len(history._history_data) == 0

            Path(tmp.name).unlink()

    def test_load_history_with_entries(self):
        """エントリ含む履歴ファイルのロード。"""
        test_data = [
            {
                "timestamp": "2025-06-01T12:00:00Z",
                "status": "success",
                "command_summary": "Test command",
                "duration_sec": 1.5,
            }
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(test_data, tmp)
            tmp.flush()

            history = create_run_history(history_file=Path(tmp.name))
            assert len(history._history_data) == 1
            assert history._history_data[0]["status"] == "success"

            Path(tmp.name).unlink()

    def test_filter_history_success_only(self):
        """成功のみフィルタ。"""
        test_data = [
            {"status": "success", "command_summary": "cmd1", "duration_sec": 1.0},
            {"status": "failure", "command_summary": "cmd2", "duration_sec": 2.0},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(test_data, tmp)
            tmp.flush()

            history = create_run_history(history_file=Path(tmp.name))
            filtered = history._apply_filter("success")

            assert len(filtered) == 1
            assert filtered[0]["status"] == "success"

            Path(tmp.name).unlink()

    def test_get_stats_summary(self):
        """統計サマリ生成。"""
        test_data = [
            {"status": "success", "duration_sec": 1.0},
            {"status": "success", "duration_sec": 2.0},
            {"status": "failure", "duration_sec": 0.5},
        ]

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump(test_data, tmp)
            tmp.flush()

            history = create_run_history(history_file=Path(tmp.name))
            summary = history._get_stats_summary()

            assert "総実行回数: 3" in summary
            assert "成功率: 66.7%" in summary  # 2/3 = 66.7%
            assert "平均実行時間:" in summary

            Path(tmp.name).unlink()

    def test_add_entry(self):
        """新規エントリ追加。"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as tmp:
            json.dump([], tmp)
            tmp.flush()

            history = create_run_history(history_file=Path(tmp.name))
            history.add_entry(
                status="success",
                command_summary="New command",
                duration_sec=3.14,
            )

            assert len(history._history_data) == 1
            assert history._history_data[0]["command_summary"] == "New command"

            Path(tmp.name).unlink()
