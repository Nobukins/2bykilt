"""
SettingsPanel コンポーネント (Phase3 スケルトン)

フィーチャーフラグ状態、エンジン情報、ENABLE_LLM ステータスを
統合表示する設定パネルコンポーネント。

Phase3 スコープ:
- フラグ状態の表示（読み取り専用）
- エンジン選択 UI（将来的に切替可能に）
- ENABLE_LLM 状態と隔離準備状況の表示

Phase4 拡張予定:
- 管理者権限でのフラグトグル
- リアルタイム更新
- シークレット管理状態の表示

関連:
- docs/plan/cdp-webui-modernization.md (Section 5.3)
"""

import gradio as gr
from typing import Optional
from src.ui.services.feature_flag_service import get_feature_flag_service
from src.llm import get_llm_gateway


class SettingsPanel:
    """
    設定パネルコンポーネント
    
    Gradio UI として統合し、フィーチャーフラグや
    ENABLE_LLM 状態を可視化します。
    """
    
    def __init__(self):
        self.flag_service = get_feature_flag_service()
        self.llm_gateway = get_llm_gateway()
    
    def render(self) -> gr.Column:
        """
        Gradio コンポーネントをレンダリング
        
        Returns:
            gr.Column: 設定パネル UI
        """
        with gr.Column(visible=True) as panel:
            gr.Markdown("## ⚙️ 設定 / Settings")
            
            # エンジン設定
            with gr.Group():
                gr.Markdown("### ブラウザエンジン")
                
                state = self.flag_service.get_current_state()
                current_engine = state.runner_engine
                
                engine_info = f"""
**現在のエンジン**: `{current_engine}`

- **Playwright**: 安定版、フル機能サポート
- **CDP**: 実験版、低レベル制御（Phase2）

エンジン切替は環境変数 `RUNNER_ENGINE` で制御します。
                """
                gr.Markdown(engine_info)
                
                # Phase4 で実装予定: エンジン切替ドロップダウン
                # engine_dropdown = gr.Dropdown(
                #     choices=["playwright", "cdp"],
                #     value=current_engine,
                #     label="エンジン選択",
                #     interactive=False  # Phase3 では読み取り専用
                # )
            
            # LLM 設定
            with gr.Group():
                gr.Markdown("### LLM 機能")
                
                llm_enabled = self.llm_gateway.is_enabled()
                status_icon = "🟢" if llm_enabled else "⚪"
                status_text = "有効" if llm_enabled else "無効"
                
                llm_info = f"""
{status_icon} **ステータス**: {status_text}

**現在の状態**:
- LLM 機能は{'有効化' if llm_enabled else '無効化'}されています
- {'サンドボックス実装は Phase3-4 で完成予定' if llm_enabled else '有効化するには環境変数 `ENABLE_LLM=true` を設定'}

**利用可能な機能**:
- {'AI アシスト、プロンプト最適化（Phase3 実装後）' if llm_enabled else 'ブラウザ自動化、unlock-future 実行'}
                """
                gr.Markdown(llm_info)
                
                # Phase3-4 で実装予定:
                # - サンドボックス隔離状態の表示
                # - ボルト設定状況の確認
                # - セキュリティアラートの表示（非管理者は参照のみ）
            
            # UI 設定
            with gr.Group():
                gr.Markdown("### UI オプション")
                
                visibility = self.flag_service.get_ui_visibility_config()
                
                ui_info = f"""
**表示設定**:
- トレースビューア: {'表示' if visibility['trace_viewer'] else '非表示'}
- 実行履歴: {'表示' if visibility['run_history'] else '非表示'}
- 近代化レイアウト: {'有効' if state.ui_modern_layout else '無効'}

UI 設定は環境変数で制御します:
- `UI_MODERN_LAYOUT=true`
- `UI_TRACE_VIEWER=true`
                """
                gr.Markdown(ui_info)
        
        return panel
    
    def get_status_summary(self) -> str:
        """
        設定状態のサマリーを取得（ログやメトリクス用）
        
        Returns:
            str: ステータスサマリー
        """
        state = self.flag_service.get_current_state()
        llm_enabled = self.llm_gateway.is_enabled()
        
        return f"Engine={state.runner_engine}, LLM={'ON' if llm_enabled else 'OFF'}, ModernUI={'ON' if state.ui_modern_layout else 'OFF'}"


def create_settings_panel() -> SettingsPanel:
    """
    SettingsPanel インスタンスを生成（ファクトリ関数）
    
    Returns:
        SettingsPanel: パネルインスタンス
    """
    return SettingsPanel()
