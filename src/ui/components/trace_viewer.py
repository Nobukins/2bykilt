"""
トレースビューア UI コンポーネント (Phase3)

ブラウザ自動化のトレースファイル (.zip) を読み込み、表示する Gradio コンポーネント。

Phase3 スコープ:
- トレース ZIP ファイルの読み込み UI
- トレースメタデータ表示 (実行時間、URL、アクション数)
- プレースホルダメッセージ ("Phase4 で Playwright Inspector 埋め込み予定")

Phase4 拡張予定:
- Playwright Trace Viewer の iframe 埋め込み
- トレース再生コントロール (再生/一時停止)
- アクションログとスクリーンショットのタイムライン同期

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3: UI Modularization)
- docs/engine/browser-engine-contract.md (トレースファイル仕様)
- src/browser/engine/playwright_engine.py (トレース生成元)
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any
import zipfile
import json
import logging

try:
    import gradio as gr
except ImportError:
    gr = None  # type: ignore

from ..services.feature_flag_service import get_feature_flag_service

logger = logging.getLogger(__name__)


class TraceViewer:
    """
    トレースビューア Gradio コンポーネント。

    Phase3 実装:
    - トレースファイル選択 UI
    - メタデータ解析と表示
    - Phase4 への拡張ノート表示

    Attributes:
        _flag_service: FeatureFlagService インスタンス
        _trace_path: 読み込み済みトレース ZIP パス
        _metadata: トレースメタデータ (実行時間、URL など)
    """

    def __init__(self):
        self._flag_service = get_feature_flag_service()
        self._trace_path: Optional[Path] = None
        self._metadata: Dict[str, Any] = {}

    def render(self) -> "gr.Column":
        """
        Gradio UI レンダリング。

        Returns:
            gr.Column: トレースビューア UI カラム

        Phase3 UI 構成:
        - トレース ZIP ファイルアップロード
        - メタデータ表示エリア
        - Phase4 プレースホルダメッセージ

        Phase4 拡張予定:
        - iframe 埋め込みエリア
        - 再生コントロールボタン
        """
        if gr is None:
            logger.warning("Gradio not installed, cannot render TraceViewer")
            return None  # type: ignore

        with gr.Column(visible=self._is_visible()) as col:
            gr.Markdown("## 🎬 トレースビューア")

            # トレースファイル選択
            with gr.Row():
                trace_file = gr.File(
                    label="トレース ZIP ファイル",
                    file_types=[".zip"],
                    type="filepath",
                )

            # メタデータ表示
            metadata_display = gr.JSON(
                label="トレースメタデータ",
                value={},
            )

            # Phase4 プレースホルダ
            gr.Markdown(
                """
                **Phase4 実装予定:**
                - Playwright Trace Viewer 埋め込み
                - アクションタイムライン同期
                - スクリーンショットプレビュー
                - ネットワークログ表示

                現在は ZIP ファイル内のメタデータのみ表示可能です。
                """
            )

            # イベントハンドラ
            trace_file.change(
                fn=self._load_trace,
                inputs=[trace_file],
                outputs=[metadata_display],
            )

        return col

    def _is_visible(self) -> bool:
        """
        トレースビューアの表示可否判定。

        UI_TRACE_VIEWER フラグに基づく。

        Returns:
            bool: 表示可否
        """
        visibility = self._flag_service.get_ui_visibility_config()
        return visibility.get("trace_viewer", False)

    def _load_trace(self, trace_path: Optional[str]) -> Dict[str, Any]:
        """
        トレース ZIP ファイル読み込み。

        Args:
            trace_path: アップロードされたトレース ZIP パス

        Returns:
            Dict[str, Any]: トレースメタデータ
                - engine_type: エンジンタイプ (Playwright/CDP)
                - created_at: 作成日時
                - duration_ms: 実行時間 (ミリ秒)
                - actions_count: アクション数
                - urls: 訪問した URL リスト
                - artifacts: アーティファクトファイル名

        Phase3 実装:
        - ZIP 内の metadata.json 読み込み
        - 基本統計情報の抽出

        Phase4 拡張予定:
        - Playwright trace 形式の直接解析
        - CDP trace イベントのパース
        """
        if not trace_path:
            return {}

        try:
            zip_path = Path(trace_path)
            if not zip_path.exists():
                logger.warning(f"Trace file not found: {trace_path}")
                return {"error": "ファイルが見つかりません"}

            metadata = self._extract_metadata(zip_path)
            self._trace_path = zip_path
            self._metadata = metadata

            logger.info(f"Trace loaded: {zip_path.name}")
            return metadata

        except Exception as e:
            logger.error(f"Failed to load trace: {e}", exc_info=True)
            return {"error": f"トレース読み込み失敗: {str(e)}"}

    def _extract_metadata(self, zip_path: Path) -> Dict[str, Any]:
        """
        ZIP ファイルからメタデータ抽出。

        Args:
            zip_path: トレース ZIP パス

        Returns:
            Dict[str, Any]: メタデータ辞書

        実装:
        - metadata.json が存在すればパース
        - なければ ZIP 内ファイルから推測
        """
        metadata: Dict[str, Any] = {
            "file_name": zip_path.name,
            "file_size_kb": zip_path.stat().st_size / 1024,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                # metadata.json を探す
                if "metadata.json" in zf.namelist():
                    with zf.open("metadata.json") as f:
                        json_data = json.load(f)
                        metadata.update(json_data)
                else:
                    # ファイルリストから推測
                    metadata["artifacts"] = zf.namelist()
                    metadata["actions_count"] = len(
                        [n for n in zf.namelist() if "screenshot" in n]
                    )

        except Exception as e:
            logger.warning(f"Failed to extract metadata: {e}")
            metadata["parse_error"] = str(e)

        return metadata

    def get_current_trace(self) -> Optional[Path]:
        """
        現在読み込み済みのトレースパス取得。

        Returns:
            Optional[Path]: トレース ZIP パス (未読み込みなら None)
        """
        return self._trace_path


def create_trace_viewer() -> TraceViewer:
    """
    TraceViewer インスタンス作成ファクトリ。

    Returns:
        TraceViewer: 新規インスタンス

    使用例:
        viewer = create_trace_viewer()
        viewer_ui = viewer.render()
    """
    return TraceViewer()
