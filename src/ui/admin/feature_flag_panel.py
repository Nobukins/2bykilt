"""Feature Flag Admin Panel (Issue #272)

Provides a Gradio UI for viewing and understanding feature flags.
This panel displays all feature flags with their current values, 
descriptions, and configuration sources.

Note: Currently read-only. Toggle functionality would require
app restart and is deferred to future enhancement.
"""
import logging
from typing import Dict, Any, List, Tuple
import gradio as gr

from src.config.feature_flags import FeatureFlags

logger = logging.getLogger(__name__)


def create_feature_flag_admin_panel() -> gr.Blocks:
    """Create the Feature Flag admin panel component.
    
    Returns:
        Gradio Blocks component for the admin panel
    """
    with gr.Blocks() as panel:
        gr.Markdown("""
## 🎛️ Feature Flag Management

この画面では、現在設定されているすべてのFeature Flagsを一覧表示します。
各フラグの**現在値**、**デフォルト値**、**説明**、**設定ソース**を確認できます。

### 設定ソース
- **runtime**: プログラム実行中に一時的に設定された値
- **environment**: 環境変数で設定された値
- **file**: 設定ファイル (`config/feature_flags.yaml`) から読み込まれたデフォルト値

### フラグの有効化・無効化
フラグの変更は環境変数または設定ファイルで行い、アプリケーションの再起動が必要です。

**環境変数での設定例:**
```bash
# フラグ名 "enable_llm" を有効化
export BYKILT_FLAG_ENABLE_LLM=true
# または簡易形式
export ENABLE_LLM=true

# アプリケーション再起動
python bykilt.py
```

**設定ファイルでの設定:**
`config/feature_flags.yaml` を編集し、アプリケーションを再起動してください。
""")
        
        # Refresh button
        refresh_btn = gr.Button("🔄 最新情報に更新", variant="secondary")
        
        # Status message
        status_msg = gr.Markdown("")
        
        # Flags table
        flags_table = gr.Dataframe(
            headers=["フラグ名", "現在値", "デフォルト値", "型", "設定ソース", "説明"],
            label="Feature Flags 一覧",
            interactive=False,
            wrap=True,
            column_widths=["20%", "10%", "10%", "8%", "12%", "40%"],
        )
        
        # Search/Filter section
        with gr.Accordion("🔍 検索とフィルター", open=False):
            search_input = gr.Textbox(
                label="フラグ名で検索",
                placeholder="例: enable_llm, artifacts.*, ui.*",
                info="フラグ名の一部を入力してフィルタリング。* でワイルドカード検索可能。"
            )
            filter_source = gr.Dropdown(
                choices=["すべて", "runtime", "environment", "file"],
                value="すべて",
                label="設定ソースでフィルター"
            )
            filter_type = gr.Dropdown(
                choices=["すべて", "bool", "int", "str"],
                value="すべて",
                label="型でフィルター"
            )
            apply_filter_btn = gr.Button("フィルター適用", variant="primary")
        
        # Detailed flag view (modal-like)
        with gr.Accordion("📋 フラグ詳細", open=False):
            selected_flag_name = gr.Textbox(label="選択中のフラグ", interactive=False)
            selected_flag_details = gr.JSON(label="詳細情報")
        
        def load_flags() -> Tuple[List[List[str]], str]:
            """Load all feature flags and return formatted data."""
            try:
                all_flags = FeatureFlags.get_all_flags()
                
                if not all_flags:
                    return [], "⚠️ フラグが読み込まれていません"
                
                # Format for table display
                rows = []
                for name, metadata in sorted(all_flags.items()):
                    rows.append([
                        name,
                        str(metadata.get("value", "")),
                        str(metadata.get("default", "")),
                        metadata.get("type", ""),
                        metadata.get("source", ""),
                        metadata.get("description", "")[:100] + ("..." if len(metadata.get("description", "")) > 100 else ""),
                    ])
                
                status = f"✅ {len(rows)} 個のフラグが読み込まれました"
                logger.info(f"Feature flags loaded: {len(rows)} flags")
                
                return rows, status
                
            except Exception as e:
                error_msg = f"❌ フラグの読み込みに失敗: {str(e)}"
                logger.error(f"Failed to load feature flags: {e}", exc_info=True)
                return [], error_msg
        
        def filter_flags(search: str, source_filter: str, type_filter: str) -> Tuple[List[List[str]], str]:
            """Filter flags based on search criteria."""
            try:
                all_flags = FeatureFlags.get_all_flags()
                
                if not all_flags:
                    return [], "⚠️ フラグが読み込まれていません"
                
                filtered_rows = []
                
                for name, metadata in sorted(all_flags.items()):
                    # Apply search filter
                    if search:
                        search_lower = search.lower().replace("*", "")
                        if search_lower not in name.lower():
                            continue
                    
                    # Apply source filter
                    if source_filter != "すべて" and metadata.get("source") != source_filter:
                        continue
                    
                    # Apply type filter
                    if type_filter != "すべて" and metadata.get("type") != type_filter:
                        continue
                    
                    filtered_rows.append([
                        name,
                        str(metadata.get("value", "")),
                        str(metadata.get("default", "")),
                        metadata.get("type", ""),
                        metadata.get("source", ""),
                        metadata.get("description", "")[:100] + ("..." if len(metadata.get("description", "")) > 100 else ""),
                    ])
                
                status = f"🔍 {len(filtered_rows)} 個のフラグが見つかりました (全体: {len(all_flags)} 個)"
                logger.info(f"Feature flags filtered: {len(filtered_rows)} / {len(all_flags)} flags")
                
                return filtered_rows, status
                
            except Exception as e:
                error_msg = f"❌ フィルター処理に失敗: {str(e)}"
                logger.error(f"Failed to filter feature flags: {e}", exc_info=True)
                return [], error_msg
        
        def show_flag_details(evt: gr.SelectData) -> Tuple[str, Dict]:
            """Show detailed information for selected flag."""
            try:
                if not evt.value:
                    return "", {}
                
                # Get flag name from selected row (first column)
                flag_name = evt.value
                
                # Get full metadata
                metadata = FeatureFlags.get_flag_metadata(flag_name)
                
                if metadata is None:
                    return flag_name, {"error": "フラグが見つかりません"}
                
                return flag_name, metadata
                
            except Exception as e:
                logger.error(f"Failed to show flag details: {e}", exc_info=True)
                return "", {"error": str(e)}
        
        # Event handlers
        refresh_btn.click(
            fn=load_flags,
            inputs=[],
            outputs=[flags_table, status_msg]
        )
        
        apply_filter_btn.click(
            fn=filter_flags,
            inputs=[search_input, filter_source, filter_type],
            outputs=[flags_table, status_msg]
        )
        
        flags_table.select(
            fn=show_flag_details,
            inputs=[],
            outputs=[selected_flag_name, selected_flag_details]
        )
        
        # Load initial data
        panel.load(
            fn=load_flags,
            inputs=[],
            outputs=[flags_table, status_msg]
        )
    
    return panel


def get_feature_flags_summary() -> Dict[str, Any]:
    """Get a summary of feature flags for diagnostic purposes.
    
    Returns:
        Dictionary with flag counts and statistics
    """
    try:
        all_flags = FeatureFlags.get_all_flags()
        
        # Count by type
        type_counts = {"bool": 0, "int": 0, "str": 0}
        # Count by source
        source_counts = {"runtime": 0, "environment": 0, "file": 0}
        # Count enabled flags
        enabled_count = 0
        
        for metadata in all_flags.values():
            flag_type = metadata.get("type", "")
            if flag_type in type_counts:
                type_counts[flag_type] += 1
            
            source = metadata.get("source", "")
            if source in source_counts:
                source_counts[source] += 1
            
            if metadata.get("type") == "bool" and metadata.get("value") is True:
                enabled_count += 1
        
        return {
            "total": len(all_flags),
            "enabled": enabled_count,
            "by_type": type_counts,
            "by_source": source_counts,
        }
        
    except Exception as e:
        logger.error(f"Failed to get feature flags summary: {e}", exc_info=True)
        return {
            "error": str(e),
            "total": 0,
        }
