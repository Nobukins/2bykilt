import gradio as gr
import os
import json
import glob

class DebugPanel:
    """デバッグ情報を表示・分析するためのGradioコンポーネント"""
    
    @staticmethod
    def create_debug_tab():
        """デバッグ情報タブを作成"""
        with gr.Tab("🔍 デバッグ情報"):
            with gr.Row():
                with gr.Column():
                    gr.Markdown("### ブラウザ診断")
                    
                    capture_button = gr.Button("現在のブラウザ状態を診断", variant="primary")
                    diagnosis_output = gr.JSON(label="診断結果")
                    
                    gr.Markdown("### 過去の診断記録")
                    refresh_button = gr.Button("診断履歴を更新")
                    diag_files = gr.Dropdown(
                        label="診断ファイル", 
                        choices=DebugPanel._get_diagnostic_files(),
                        allow_custom_value=False
                    )
                    history_viewer = gr.JSON(label="診断履歴データ")
                    
                    # 環境変数の表示
                    gr.Markdown("### 環境変数")
                    env_output = gr.JSON(DebugPanel._get_browser_env_vars())
            
            # イベントハンドラの設定
            capture_button.click(
                DebugPanel._run_browser_diagnostics,
                inputs=[],
                outputs=[diagnosis_output]
            )
            
            refresh_button.click(
                DebugPanel._refresh_diagnostic_files,
                inputs=[],
                outputs=[diag_files]
            )
            
            diag_files.change(
                DebugPanel._load_diagnostic_file,
                inputs=[diag_files],
                outputs=[history_viewer]
            )
    
    @staticmethod
    def _get_diagnostic_files():
        """診断ファイルの一覧を取得"""
        diag_pattern = "logs/browser_diagnostics/*.json"
        files = sorted(glob.glob(diag_pattern), reverse=True)
        return [os.path.basename(f) for f in files]
    
    @staticmethod
    def _refresh_diagnostic_files():
        """診断ファイルの一覧を更新"""
        return DebugPanel._get_diagnostic_files()
    
    @staticmethod
    def _load_diagnostic_file(filename):
        """選択した診断ファイルを読み込む"""
        if not filename:
            return None
        
        full_path = f"logs/browser_diagnostics/{filename}"
        try:
            with open(full_path, 'r') as f:
                data = json.load(f)
            return data
        except Exception as e:
            return {"error": f"ファイル読み込みエラー: {str(e)}"}
    
    @staticmethod
    def _run_browser_diagnostics():
        """ブラウザ診断を実行"""
        from src.browser.browser_diagnostic import BrowserDiagnostic
        result = BrowserDiagnostic.capture_browser_state("manual_check")
        return result["diagnostic_data"]
    
    @staticmethod
    def _get_browser_env_vars():
        """ブラウザ関連の環境変数を取得"""
        return {
            "CHROME_PATH": os.getenv("CHROME_PATH", "未設定"),
            "CHROME_USER_DATA": os.getenv("CHROME_USER_DATA", "未設定"),
            "CHROME_DEBUGGING_PORT": os.getenv("CHROME_DEBUGGING_PORT", "未設定"),
            "EDGE_PATH": os.getenv("EDGE_PATH", "未設定"),
            "EDGE_USER_DATA": os.getenv("EDGE_USER_DATA", "未設定"),
            "EDGE_DEBUGGING_PORT": os.getenv("EDGE_DEBUGGING_PORT", "未設定")
        }
