"""Artifacts Admin Panel (Issue #277)

Provides a Gradio UI for viewing and managing artifacts (screenshots, videos, element extracts).
This panel displays all artifacts organized by run ID with preview and download capabilities.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import gradio as gr

from src.services.artifacts_service import (
    list_artifacts,
    get_artifact_summary,
    ListArtifactsParams,
    ArtifactType,
)

logger = logging.getLogger(__name__)

# Constants for byte conversion
BYTES_TO_MB = 1024 * 1024
BYTES_TO_KB = 1024


def create_artifacts_panel() -> gr.Blocks:
    """Create the Artifacts admin panel component.

    Returns:
        Gradio Blocks component for the artifacts panel
    """
    with gr.Blocks() as panel:
        gr.Markdown("""
## 📦 Artifacts Management

この画面では、実行中に生成されたすべてのアーティファクト（スクリーンショット、動画、要素抽出データ）を一覧表示します。

### アーティファクトの種類
- **video**: ブラウザ操作の録画ファイル
- **screenshot**: 画面キャプチャ画像
- **element_capture**: DOM要素から抽出したデータ

### 機能
- Run ID でフィルタリング
- アーティファクトタイプでフィルタリング
- プレビュー表示（画像・動画）
- ダウンロードリンク
""")

        # Summary section
        with gr.Row():
            summary_display = gr.Markdown("**Summary:** データを読み込んでいません")
            refresh_summary_btn = gr.Button("🔄 サマリー更新", variant="secondary", scale=0)

        # Filter section
        with gr.Accordion("🔍 フィルターオプション", open=True):
            with gr.Row():
                run_id_filter = gr.Textbox(
                    label="Run ID",
                    placeholder="全て表示する場合は空白のままにします",
                    info="特定のRun IDでフィルタリング",
                )
                artifact_type_filter = gr.Dropdown(
                    choices=["all", "video", "screenshot", "element_capture"],
                    value="all",
                    label="アーティファクトタイプ",
                )
            
            with gr.Row():
                limit_slider = gr.Slider(
                    minimum=10,
                    maximum=100,
                    value=50,
                    step=10,
                    label="表示件数",
                    info="一度に表示するアーティファクトの最大数",
                )
                apply_filter_btn = gr.Button("フィルター適用", variant="primary")

        # Status message
        status_msg = gr.Markdown("**Status:** フィルターを適用してアーティファクトを読み込んでください")

        # Artifacts table
        artifacts_table = gr.Dataframe(
            headers=["Run ID", "Type", "Created At", "Size", "Path"],
            label="Artifacts 一覧",
            interactive=False,
            wrap=True,
            column_widths=["15%", "15%", "20%", "10%", "40%"],
        )

        # Preview section
        with gr.Accordion("👁️ プレビュー", open=False):
            selected_artifact_path = gr.Textbox(label="選択中のアーティファクト", interactive=False)
            
            with gr.Tabs():
                with gr.TabItem("画像プレビュー"):
                    image_preview = gr.Image(label="Screenshot Preview", type="filepath")
                
                with gr.TabItem("動画プレビュー"):
                    video_preview = gr.Video(label="Video Preview")
                
                with gr.TabItem("JSONデータ"):
                    json_preview = gr.JSON(label="Element Capture Data")
            
            download_link = gr.HTML(value="<p>アーティファクトを選択してダウンロードリンクを表示</p>")

        def load_artifacts(run_id: str, artifact_type: str, limit: int) -> Tuple[List[List[str]], str, str]:
            """Load and display artifacts based on filters."""
            try:
                params = ListArtifactsParams(
                    run_id=run_id if run_id.strip() else None,
                    artifact_type=artifact_type,  # type: ignore
                    limit=limit,
                    offset=0,
                )
                
                page = list_artifacts(params)
                
                if not page.items:
                    return [], "⚠️ フィルター条件に一致するアーティファクトが見つかりません", ""
                
                # Format table data
                rows = []
                for item in page.items:
                    # Format created_at
                    try:
                        created_dt = datetime.fromisoformat(item.created_at.replace('Z', '+00:00'))
                        created_str = created_dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:  # noqa: BLE001
                        created_str = item.created_at[:19] if len(item.created_at) > 19 else item.created_at
                    
                    # Format size
                    size_str = format_file_size(item.size) if item.size else "N/A"
                    
                    # Truncate path for display
                    display_path = item.path
                    if len(display_path) > 60:
                        display_path = "..." + display_path[-57:]
                    
                    rows.append([
                        item.run_id[:16] + "..." if len(item.run_id) > 16 else item.run_id,
                        item.type,
                        created_str,
                        size_str,
                        display_path,
                    ])
                
                status = f"✅ {len(page.items)} 個のアーティファクトを読み込みました"
                if page.has_next:
                    status += f" (合計: {page.total_count}+)"
                
                # Generate summary
                summary = get_artifact_summary(run_id if run_id.strip() else None)
                summary_text = format_summary(summary)
                
                logger.info(f"Artifacts loaded: {len(page.items)} items")
                
                return rows, status, summary_text
                
            except FileNotFoundError:
                error_msg = "❌ アーティファクトディレクトリが見つかりません"
                return [], error_msg, ""
            except Exception as e:
                error_msg = f"❌ エラーが発生しました: {str(e)}"
                logger.error(f"Failed to load artifacts: {e}", exc_info=True)
                return [], error_msg, ""

        def format_summary(summary: Dict[str, Any]) -> str:
            """Format summary data for display."""
            total = summary.get("total", 0)
            by_type = summary.get("by_type", {})
            total_size = summary.get("total_size_bytes", 0)
            
            size_str = format_file_size(total_size)
            
            return f"""
**Summary:**
- **Total Artifacts:** {total}
- **Videos:** {by_type.get('video', 0)}
- **Screenshots:** {by_type.get('screenshot', 0)}
- **Element Captures:** {by_type.get('element_capture', 0)}
- **Total Size:** {size_str}
"""

        def format_file_size(size_bytes: int | None) -> str:
            """Format file size for human-readable display."""
            if size_bytes is None:
                return "N/A"
            
            if size_bytes < BYTES_TO_KB:
                return f"{size_bytes} B"
            elif size_bytes < BYTES_TO_MB:
                return f"{size_bytes / BYTES_TO_KB:.1f} KB"
            else:
                return f"{size_bytes / BYTES_TO_MB:.1f} MB"

        def show_artifact_preview(evt: gr.SelectData, current_run_id: str, current_type: str, current_limit: int) -> Tuple[str, Any, Any, Any, str]:
            """Show preview for selected artifact."""
            try:
                if evt.index[0] < 0:
                    return "", None, None, None, "<p>アーティファクトを選択してください</p>"
                
                # Reload artifacts to get the selected one
                params = ListArtifactsParams(
                    run_id=current_run_id if current_run_id.strip() else None,
                    artifact_type=current_type,  # type: ignore
                    limit=current_limit,
                    offset=0,
                )
                
                page = list_artifacts(params)
                
                if evt.index[0] >= len(page.items):
                    return "", None, None, None, "<p>選択が無効です</p>"
                
                item = page.items[evt.index[0]]
                artifact_path = item.path
                
                if not os.path.exists(artifact_path):
                    return artifact_path, None, None, None, f"<p>❌ ファイルが見つかりません: {artifact_path}</p>"
                
                # Generate download link
                download_html = f"""
                <div style="padding: 10px; border: 1px solid #ddd; border-radius: 5px;">
                    <p><strong>ファイル:</strong> {os.path.basename(artifact_path)}</p>
                    <p><strong>パス:</strong> <code>{artifact_path}</code></p>
                    <button onclick="navigator.clipboard.writeText('{artifact_path}')" 
                            style="padding: 8px 16px; background: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                        📋 パスをコピー
                    </button>
                </div>
                """
                
                # Determine preview type
                if item.type == "screenshot":
                    return artifact_path, artifact_path, None, None, download_html
                elif item.type == "video":
                    return artifact_path, None, artifact_path, None, download_html
                elif item.type == "element_capture":
                    # Check file extension
                    file_ext = os.path.splitext(artifact_path)[1].lower()
                    
                    if file_ext == ".json":
                        # JSON preview
                        import json
                        try:
                            with open(artifact_path, 'r', encoding='utf-8') as f:
                                data = json.load(f)
                            return artifact_path, None, None, data, download_html
                        except Exception:  # noqa: BLE001
                            return artifact_path, None, None, {"error": "Failed to load JSON"}, download_html
                    
                    elif file_ext in {".txt", ".csv"}:
                        # Text/CSV preview - read as plain text
                        try:
                            with open(artifact_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                            
                            # Wrap in a dictionary for JSON display component
                            preview_data = {
                                "file_type": file_ext[1:],
                                "content": content,
                                "lines": len(content.splitlines()),
                            }
                            return artifact_path, None, None, preview_data, download_html
                        except Exception as e:  # noqa: BLE001
                            return artifact_path, None, None, {"error": f"Failed to load {file_ext}: {str(e)}"}, download_html
                    else:
                        # Unknown format
                        return artifact_path, None, None, {"error": f"Unsupported format: {file_ext}"}, download_html
                else:
                    return artifact_path, None, None, None, download_html
                
            except Exception as e:
                logger.error(f"Failed to show artifact preview: {e}", exc_info=True)
                return "", None, None, None, f"<p>❌ エラー: {str(e)}</p>"

        def refresh_summary_only(run_id: str) -> str:
            """Refresh only the summary display."""
            try:
                summary = get_artifact_summary(run_id if run_id.strip() else None)
                return format_summary(summary)
            except Exception as e:
                return f"**Summary:** エラー - {str(e)}"

        # Event handlers
        apply_filter_btn.click(
            fn=load_artifacts,
            inputs=[run_id_filter, artifact_type_filter, limit_slider],
            outputs=[artifacts_table, status_msg, summary_display]
        )

        refresh_summary_btn.click(
            fn=refresh_summary_only,
            inputs=[run_id_filter],
            outputs=[summary_display]
        )

        artifacts_table.select(
            fn=show_artifact_preview,
            inputs=[run_id_filter, artifact_type_filter, limit_slider],
            outputs=[selected_artifact_path, image_preview, video_preview, json_preview, download_link]
        )

        # Load initial summary on panel load
        panel.load(
            fn=refresh_summary_only,
            inputs=[run_id_filter],
            outputs=[summary_display]
        )

    return panel


__all__ = ["create_artifacts_panel"]
