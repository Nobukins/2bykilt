"""
実行履歴 UI コンポーネント (Phase3)

unlock-future コマンドの実行履歴をタイムライン形式で表示する Gradio コンポーネント。

Phase3 スコープ:
- 実行履歴リスト表示 (実行時刻、成功/失敗、コマンド概要)
- フィルタリング (成功/失敗/全て)
- 詳細表示ポップアップ (モーダル風)

Phase4 拡張予定:
- リアルタイム更新 (実行中の履歴に自動追加)
- トレースファイルへのリンク (TraceViewer と連携)
- エクスポート機能 (CSV/JSON)
- 統計ダッシュボード (成功率、平均実行時間)

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3: UI Modularization)
- src/browser/unlock_future_adapter.py (実行ログ生成元)
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, List, Dict, Any, Optional, Literal
import json
import logging

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore

if TYPE_CHECKING:
    import gradio as gradio_typing

from ..services.feature_flag_service import get_feature_flag_service

logger = logging.getLogger(__name__)

FilterType = Literal["all", "success", "failure"]


class RunHistory:
    """
    実行履歴 Gradio コンポーネント。

    Phase3 実装:
    - 履歴データの読み込み (JSON ファイル)
    - タイムライン表示
    - フィルタリング機能

    Attributes:
        _flag_service: FeatureFlagService インスタンス
        _history_data: 履歴データリスト
        _history_file: 履歴 JSON ファイルパス
    """

    def __init__(self, history_file: Optional[Path] = None):
        """
        Args:
            history_file: 履歴 JSON ファイルパス (デフォルトは logs/run_history.json)
        """
        self._flag_service = get_feature_flag_service()
        self._history_file = history_file or Path("logs/run_history.json")
        self._history_data: List[Dict[str, Any]] = []
        self._current_filter: FilterType = "all"

        # 履歴ファイル読み込み
        self._load_history()

    def render(self) -> Optional["gradio_typing.Column"]:
        """
        Gradio UI レンダリング。

        Returns:
            gr.Column: 実行履歴 UI カラム

        Phase3 UI 構成:
        - フィルタラジオボタン (全て/成功/失敗)
        - 履歴データフレーム
        - 詳細表示ボタン

        Phase4 拡張予定:
        - リアルタイム更新トグル
        - トレースリンク
        - エクスポートボタン
        """
        if gr is None:
            logger.warning("Gradio not installed, cannot render RunHistory")
            return None

        if not self._is_visible():
            return None

        self._flag_service.get_current_state(force_refresh=True)
        visibility = self._flag_service.get_ui_visibility_config()
        realtime_enabled = visibility.get("realtime_updates", True)

        with gr.Column() as col:
            gr.Markdown("## 📜 実行履歴")

            # フィルタ
            with gr.Row():
                filter_radio = gr.Radio(
                    choices=["全て", "成功のみ", "失敗のみ"],
                    value="全て",
                    label="フィルタ",
                )
                refresh_btn = gr.Button("🔄 更新", size="sm")

            # 履歴データフレーム
            history_df = gr.Dataframe(
                headers=["実行時刻", "ステータス", "コマンド概要", "実行時間 (秒)"],
                datatype=["str", "str", "str", "number"],
                value=self._format_history_data(self._current_filter),
                interactive=False,
                wrap=True,
            )

            # 統計情報
            stats_md = gr.Markdown(value=self._get_stats_summary())

            realtime_signal = gr.Textbox(visible=False, elem_id="run-history-ws-signal")

            if realtime_enabled:
                gr.HTML(
                    """
<script>
(function() {
  const textbox = document.querySelector('#run-history-ws-signal textarea');
  if (!textbox) { return; }
  function connect() {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${proto}://${window.location.host}/ws/run-history`);
    ws.onmessage = (event) => {
      textbox.value = event.data;
      textbox.dispatchEvent(new Event('input', { bubbles: true }));
    };
    ws.onclose = () => {
      setTimeout(connect, 3000);
    };
  }
  connect();
})();
</script>
                    """,
                    elem_id="run-history-ws-script",
                )

            # イベントハンドラ
            filter_radio.change(
                fn=self._filter_history,
                inputs=[filter_radio],
                outputs=[history_df],
            )

            refresh_btn.click(
                fn=self._refresh_history,
                outputs=[history_df, stats_md],
            )

            if realtime_enabled:
                realtime_signal.change(
                    fn=self._handle_realtime_update,
                    inputs=[realtime_signal],
                    outputs=[history_df, stats_md],
                )

        return col

    def _is_visible(self) -> bool:
        """
        実行履歴の表示可否判定。

        UI_MODERN_LAYOUT フラグに基づく (Phase3 では常時表示)。

        Returns:
            bool: 表示可否
        """
        self._flag_service.get_current_state(force_refresh=True)
        visibility = self._flag_service.get_ui_visibility_config()
        return visibility.get("run_history", True)  # デフォルトで表示

    def _load_history(self) -> None:
        """
        履歴ファイルから JSON 読み込み。

        履歴ファイル形式:
        [
            {
                "timestamp": "2025-06-01T12:34:56Z",
                "status": "success",
                "command_summary": "navigate to https://example.com",
                "duration_sec": 2.34,
                "trace_path": "artifacts/trace_20250601_123456.zip"
            },
            ...
        ]
        """
        try:
            if self._history_file.exists():
                with open(self._history_file, "r", encoding="utf-8") as f:
                    self._history_data = json.load(f)
                logger.info(f"Loaded {len(self._history_data)} history entries")
            else:
                logger.info("No history file found, starting with empty history")
                self._history_data = []

        except Exception as e:
            logger.error(f"Failed to load history: {e}", exc_info=True)
            self._history_data = []

    def _format_history_data(self, filter_type: FilterType) -> List[List[Any]]:
        """
        履歴データを Gradio Dataframe 形式に変換。

        Args:
            filter_type: フィルタタイプ ("all"/"success"/"failure")

        Returns:
            List[List[Any]]: データフレーム用行リスト
        """
        filtered = self._apply_filter(filter_type)

        rows = []
        for entry in filtered:
            timestamp = entry.get("timestamp", "不明")
            status = "✅ 成功" if entry.get("status") == "success" else "❌ 失敗"
            summary = entry.get("command_summary", "")
            duration = entry.get("duration_sec", 0.0)

            rows.append([timestamp, status, summary, duration])

        return rows

    def _apply_filter(self, filter_type: FilterType) -> List[Dict[str, Any]]:
        """
        フィルタ適用。

        Args:
            filter_type: フィルタタイプ

        Returns:
            List[Dict[str, Any]]: フィルタ済み履歴
        """
        if filter_type == "all":
            return self._history_data
        elif filter_type == "success":
            return [e for e in self._history_data if e.get("status") == "success"]
        elif filter_type == "failure":
            return [e for e in self._history_data if e.get("status") != "success"]
        return self._history_data

    def _filter_history(self, filter_label: str) -> List[List[Any]]:
        """
        フィルタラジオボタンのコールバック。

        Args:
            filter_label: ラジオボタンラベル ("全て"/"成功のみ"/"失敗のみ")

        Returns:
            List[List[Any]]: フィルタ済みデータフレーム
        """
        filter_type = self._map_filter_label(filter_label)
        self._current_filter = filter_type
        return self._format_history_data(filter_type)

    def _refresh_history(self) -> tuple:
        """
        履歴更新ボタンのコールバック。

        Returns:
            tuple: (更新後データフレーム, 統計サマリ Markdown)
        """
        self._load_history()
        data = self._format_history_data(self._current_filter)
        stats = self._get_stats_summary()
        return data, stats

    def _handle_realtime_update(self, payload: str) -> tuple:
        if not payload:
            return (
                gr.update(),
                gr.update(value=self._get_stats_summary()),
            )

        try:
            data = json.loads(payload)
            entries = data.get("entries", [])
        except json.JSONDecodeError:
            logger.warning("Invalid realtime payload, skipping update")
            return (
                gr.update(),
                gr.update(value=self._get_stats_summary()),
            )

        self._history_data = entries
        rows = self._format_history_data(self._current_filter)
        stats = data.get("stats") or {}
        stats_md = self._format_stats_from_payload(stats)
        return rows, stats_md

    def _get_stats_summary(self) -> str:
        """
        統計サマリ Markdown 生成。

        Returns:
            str: Markdown 形式の統計情報

        統計内容:
        - 総実行回数
        - 成功率
        - 平均実行時間
        """
        if not self._history_data:
            return "**統計:** 履歴データなし"

        total = len(self._history_data)
        success = len([e for e in self._history_data if e.get("status") == "success"])
        success_rate = (success / total * 100) if total > 0 else 0.0

        durations = [e.get("duration_sec", 0.0) for e in self._history_data]
        avg_duration = sum(durations) / len(durations) if durations else 0.0

        return (
            f"**統計:** 総実行回数: {total} | "
            f"成功率: {success_rate:.1f}% | "
            f"平均実行時間: {avg_duration:.2f} 秒"
        )

    def _format_stats_from_payload(self, stats: Dict[str, Any]) -> str:
        total = stats.get("total", 0)
        success_rate = stats.get("success_rate", 0.0)
        avg_duration = stats.get("avg_duration", 0.0)
        return (
            f"**統計:** 総実行回数: {total} | "
            f"成功率: {success_rate:.1f}% | "
            f"平均実行時間: {avg_duration:.2f} 秒"
        )

    @staticmethod
    def _map_filter_label(filter_label: str) -> FilterType:
        filter_map = {
            "全て": "all",
            "成功のみ": "success",
            "失敗のみ": "failure",
        }
        return filter_map.get(filter_label, "all")

    def add_entry(
        self,
        status: Literal["success", "failure"],
        command_summary: str,
        duration_sec: float,
        trace_path: Optional[Path] = None,
    ) -> None:
        """
        新規実行エントリを履歴に追加 (Phase4 で使用)。

        Args:
            status: 実行ステータス
            command_summary: コマンド概要
            duration_sec: 実行時間 (秒)
            trace_path: トレースファイルパス (オプション)

        実装:
        - 履歴データリストに追加
        - JSON ファイルに永続化
        """
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
            "command_summary": command_summary,
            "duration_sec": duration_sec,
        }

        if trace_path:
            entry["trace_path"] = str(trace_path)

        self._history_data.append(entry)

        # ファイル保存
        try:
            self._history_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._history_file, "w", encoding="utf-8") as f:
                json.dump(self._history_data, f, indent=2, ensure_ascii=False)
            logger.info(f"Added history entry: {command_summary}")
        except Exception as e:
            logger.error(f"Failed to save history: {e}", exc_info=True)


def create_run_history(history_file: Optional[Path] = None) -> RunHistory:
    """
    RunHistory インスタンス作成ファクトリ。

    Args:
        history_file: 履歴 JSON ファイルパス (オプション)

    Returns:
        RunHistory: 新規インスタンス

    使用例:
        history = create_run_history()
        history_ui = history.render()
    """
    return RunHistory(history_file=history_file)
