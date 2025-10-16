"""
トレースビューア UI コンポーネント (Phase4 拡張)

ブラウザ自動化のトレースファイル (.zip) を読み込み、Playwright Trace Viewer
を Gradio 上に埋め込み表示するコンポーネント。

実装範囲:
- トレース ZIP のアップロードとメタデータ解析
- Playwright Trace Viewer (iframe) の自動埋め込み
- セッション管理 (短時間キャッシュ)

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3: UI Modularization)
- docs/engine/browser-engine-contract.md (トレースファイル仕様)
- src/browser/engine/playwright_engine.py (トレース生成元)
"""

from __future__ import annotations

import json
import logging
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple

try:
    import gradio as gr
except ImportError:  # pragma: no cover - optional dependency
    gr = None  # type: ignore

if TYPE_CHECKING:
    import gradio as gradio_typing

from ..services import (
    get_feature_flag_service,
    prepare_playwright_trace_session,
    prune_playwright_trace_sessions,
)

logger = logging.getLogger(__name__)

VIEWER_HEIGHT_PX = 720
_VIEWER_PLACEHOLDER = """
<div class="trace-viewer-placeholder">
  <p>Playwright トレースを選択すると、ここに再生ビューアが表示されます。</p>
</div>
"""


class TraceViewer:
    """Gradio UI コンポーネント: Playwright トレースビューア"""

    def __init__(self) -> None:
        self._flag_service = get_feature_flag_service()
        self._trace_path: Optional[Path] = None
        self._metadata: Dict[str, Any] = {}

    def render(self) -> "gradio_typing.Column":  # pragma: no cover - UI composition
        if gr is None:
            logger.warning("Gradio not installed, cannot render TraceViewer")
            return None  # type: ignore

        with gr.Column(visible=self._is_visible()) as col:
            gr.Markdown("## 🎬 トレースビューア")

            with gr.Row():
                trace_file = gr.File(
                    label="トレース ZIP ファイル",
                    file_types=[".zip"],
                    type="filepath",
                )

            metadata_display = gr.Code(
                label="トレースメタデータ",
                value="{}",
                language="json",
                interactive=False,
            )

            viewer_frame = gr.HTML(
                value=_VIEWER_PLACEHOLDER,
                label="トレース再生ビューア",
            )

            status_message = gr.Markdown(value="")

            trace_file.change(
                fn=self._load_trace,
                inputs=[trace_file],
                outputs=[metadata_display, viewer_frame, status_message],
            )

        return col

    def get_current_trace(self) -> Optional[Path]:
        """現在読み込み済みのトレースパスを返す"""
        return self._trace_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_visible(self) -> bool:
        # フラグのキャッシュを常に最新化し、テスト環境や UI セッションの
        # 切り替えに追随できるようにする。
        self._flag_service.get_current_state(force_refresh=True)
        visibility = self._flag_service.get_ui_visibility_config()
        return visibility.get("trace_viewer", False)

    def _load_trace(
        self, trace_path: Optional[str]
    ) -> Tuple[str, str, str]:
        if not trace_path:
            return "{}", _VIEWER_PLACEHOLDER, ""

        try:
            zip_path = Path(trace_path)
            if not zip_path.exists():
                logger.warning("Trace file not found: %s", trace_path)
                import json
                return (
                    json.dumps({"error": "ファイルが見つかりません"}, indent=2, ensure_ascii=False),
                    _VIEWER_PLACEHOLDER,
                    "",
                )

            metadata = self._extract_metadata(zip_path)
            self._trace_path = zip_path

            viewer_html, status, enriched_metadata = self._maybe_prepare_viewer(
                zip_path, metadata
            )
            self._metadata = enriched_metadata

            logger.info("Trace loaded: %s", zip_path.name)
            import json
            return json.dumps(enriched_metadata, indent=2, ensure_ascii=False), viewer_html, status

        except Exception as exc:  # pragma: no cover - defensive
            logger.error(
                "Failed to load trace",
                exc_info=True,
                extra={"error": repr(exc)},
            )
            import json
            return (
                json.dumps({"error": f"トレース読み込み失敗: {exc}"}, indent=2, ensure_ascii=False),
                _VIEWER_PLACEHOLDER,
                "",
            )

    def _maybe_prepare_viewer(
        self, zip_path: Path, metadata: Dict[str, Any]
    ) -> Tuple[str, str, Dict[str, Any]]:
        prune_playwright_trace_sessions()
        updated_metadata = dict(metadata)
        updated_metadata.setdefault("viewer", {})

        if not self._looks_like_playwright_trace(zip_path):
            updated_metadata["viewer"].update(
                {
                    "embedded": False,
                    "reason": "not_playwright_trace",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return (
                _VIEWER_PLACEHOLDER,
                "ℹ️ Playwright トレース形式ではないため埋め込みをスキップしました。",
                updated_metadata,
            )

        try:
            session = prepare_playwright_trace_session(zip_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.warning(
                "Failed to prepare Playwright trace session",
                extra={
                    "event": "trace_viewer.playwright.session.fail",
                    "error": repr(exc),
                    "trace_path": str(zip_path),
                },
            )
            updated_metadata["viewer"].update(
                {
                    "embedded": False,
                    "reason": f"session_error:{exc}",
                    "checked_at": datetime.now(timezone.utc).isoformat(),
                }
            )
            return (
                _VIEWER_PLACEHOLDER,
                f"⚠️ Playwright トレースの埋め込みに失敗しました: {exc}",
                updated_metadata,
            )

        iframe_html = self._build_iframe_html(session.viewer_url())
        status = (
            "✅ Playwright トレースを自動的に読み込みました。"
            "ビューアは最新のセッションのみ保持されます。"
        )
        updated_metadata["viewer"].update(
            {
                "embedded": True,
                "session_id": session.session_id,
                "viewer_url": session.viewer_url(),
                "prepared_at": datetime.now(timezone.utc).isoformat(),
            }
        )
        return iframe_html, status, updated_metadata

    @staticmethod
    def _build_iframe_html(viewer_url: str) -> str:
        return (
            "<div class=\"trace-viewer-frame\">"
            f"<iframe src=\"{viewer_url}\" width=\"100%\" height=\"{VIEWER_HEIGHT_PX}\" "
            "allowfullscreen style=\"border:1px solid var(--border-color,#e5e7eb);\"></iframe>"
            "</div>"
        )

    @staticmethod
    def _looks_like_playwright_trace(zip_path: Path) -> bool:
        if zip_path.suffix.lower() not in {".zip", ".trace", ".trace.zip"}:
            return False
        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = set(zf.namelist())
        except zipfile.BadZipFile:
            return False
        return bool({"trace.trace", "resources"} & names)

    def _extract_metadata(self, zip_path: Path) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {
            "file_name": zip_path.name,
            "file_size_kb": round(zip_path.stat().st_size / 1024, 2),
            "loaded_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                names = zf.namelist()
                metadata["artifacts"] = names
                metadata.setdefault("urls", [])
                metadata.setdefault("actions_count", 0)

                if "metadata.json" in names:
                    with zf.open("metadata.json") as fp:
                        metadata.update(json.load(fp))

                if "trace.trace" in names:
                    metadata["playwright_trace"] = True

                if not metadata.get("actions_count"):
                    metadata["actions_count"] = len(
                        [name for name in names if "screenshot" in name]
                    )

        except Exception as exc:
            logger.warning("Failed to extract metadata", exc_info=False)
            metadata["parse_error"] = repr(exc)

        return metadata


def create_trace_viewer() -> TraceViewer:
    return TraceViewer()
