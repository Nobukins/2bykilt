"""
FastAPI and Gradio Integration Module
This module handles the integration between FastAPI and Gradio interface
"""

import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from gradio.routes import mount_gradio_app
import uvicorn
import nest_asyncio
import os
from src.browser.browser_config import BrowserConfig
from src.utils.log_ui import create_log_tab  # Correct import from log_ui instead of app_logger
from src.utils.app_logger import logger
import gradio as gr

# Simplified CSP middleware
class CSPMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src *; img-src * data:; font-src * data:; style-src * 'unsafe-inline'; script-src * 'unsafe-inline' 'unsafe-eval';"
        )
        return response

def create_fastapi_app(demo, args):
    """Create and configure the FastAPI application with Gradio integration
    
    Args:
        demo (gr.Blocks): The Gradio interface to mount
        args (argparse.Namespace): Command line arguments
        
    Returns:
        FastAPI: The configured FastAPI application
    """
    app = FastAPI()
    
    # CORS設定（環境変数 ALLOWED_ORIGINS を利用、デフォルトは http://localhost:7788 ）
    allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:7788").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"]
    )
    
    # CSPミドルウェアを追加
    app.add_middleware(CSPMiddleware)
    
    # 静的ファイル提供の設定
    assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
    if os.path.exists(assets_dir):
        app.mount("/static", StaticFiles(directory=assets_dir), name="static")
        logger.info(f"静的ファイルディレクトリをマウント: {assets_dir}")
    
    # デバッグ用のルートエンドポイント
    @app.get("/api/status")
    async def root():
        return {"message": "APIサーバーは正常に動作しています"}
    
    # 簡易的なコマンド一覧取得用エンドポイント（エラー処理を簡略化）
    @app.get("/api/commands-simple")
    async def get_commands_simple():
        from src.ui.command_helper import CommandHelper
        helper = CommandHelper()
        return helper.get_commands_for_display()
    
    # APIのみを直接テストするためのHTML
    @app.get("/api-test")
    async def api_test():
        return HTMLResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Test</title>
        </head>
        <body>
            <h1>API テストページ</h1>
            <button id="testBtn">コマンド取得テスト</button>
            <pre id="result" style="border:1px solid #ccc; padding:10px; margin-top:10px;"></pre>
            
            <script>
            document.getElementById('testBtn').addEventListener('click', async () => {
                const resultEl = document.getElementById('result');
                resultEl.textContent = "リクエスト中...";
                try {
                    const response = await fetch('/api/commands-simple');
                    if (!response.ok) {
                        throw new Error(`ステータス: ${response.status}`);
                    }
                    const data = await response.json();
                    resultEl.textContent = JSON.stringify(data, null, 2);
                } catch (err) {
                    resultEl.textContent = `エラー: ${err.message}`;
                }
            });
            </script>
        </body>
        </html>
        """)
    
    # グローバル変数チェック用エンドポイント（デバッグ用）
    @app.get("/api/debug-info")
    async def get_debug_info():
        """デバッグ情報を返すエンドポイント"""
        from src.ui.command_helper import CommandHelper
        helper = CommandHelper()
        commands = helper.get_all_commands()
        
        import platform
        import sys
        
        debug_info = {
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "commands_count": len(commands),
            "api_status": "active"
        }
        
        return JSONResponse(
            content=debug_info,
            headers={"Access-Control-Allow-Origin": "*"}
        )
    
    # GradioアプリをFastAPIにマウント
    mount_gradio_app(app, demo, path="/")
    
    return app

browser_config = BrowserConfig()

def log_browser_startup_message():
    """Log startup message for the selected browser."""
    settings = browser_config.get_browser_settings()
    browser_name = "Edge" if settings["browser_type"] == "edge" else "Chrome"
    logger.info(f"注意: {browser_name}の自動化を使用する場合は、以下のコマンドで{browser_name}を起動してください:")
    logger.info(f"  open -a \"{browser_name}\" --args --remote-debugging-port={settings['debugging_port']}")

def run_app(app, args):
    """Run the FastAPI application
    
    Args:
        app (FastAPI): The FastAPI application to run
        args (argparse.Namespace): Command line arguments
    """
    # 拡張ロギング情報
    logger.info(f"サーバーを起動します: {args.ip}:{args.port}")
    logger.info(f"Gradio UI: http://{args.ip}:{args.port}/")
    logger.info(f"API テスト: http://{args.ip}:{args.port}/api-test")
    
    # システム情報
    import platform
    logger.info(f"実行環境: Python {platform.python_version()} on {platform.system()} {platform.release()}")
    
    # ブラウザ接続に関する注意事項
    log_browser_startup_message()
    
    # FastAPIの実行
    nest_asyncio.apply()
    
    # サーバー起動（エラーハンドリング追加）
    try:
        uvicorn.run(app, host=args.ip, port=args.port)
    except Exception as e:
        logger.error(f"サーバー起動エラー: {str(e)}")
        import sys
        sys.exit(1)

def create_ui():
    """Create basic Gradio UI without log tab."""
    with gr.Blocks() as demo:
        pass  # Add other necessary UI elements if needed
    return demo

if __name__ == "__main__":
    logger.info("Starting application", emoji=True)
    ui = create_ui()
    ui.launch()
