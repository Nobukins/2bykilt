"""
FastAPI and Gradio Integration Module
This module handles the integration between FastAPI and Gradio interface
"""

import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from gradio.routes import mount_gradio_app
import uvicorn
import nest_asyncio

from src.ui.command_helper import CommandHelper

# Configure logging
logger = logging.getLogger(__name__)

def create_fastapi_app(demo, args):
    """Create and configure the FastAPI application with Gradio integration
    
    Args:
        demo (gr.Blocks): The Gradio interface to mount
        args (argparse.Namespace): Command line arguments
        
    Returns:
        FastAPI: The configured FastAPI application
    """
    app = FastAPI()
    
    # CORSを全ドメインに許可
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # デバッグ用のルートエンドポイント
    @app.get("/api/status")
    async def root():
        return {"message": "APIサーバーは正常に動作しています"}
    
    # コマンド一覧を取得するAPIエンドポイント - デバッグ情報追加
    @app.get("/api/commands")
    async def get_commands():
        try:
            helper = CommandHelper()
            commands = helper.get_all_commands()
            logger.info(f"APIリクエスト: /api/commands - {len(commands)}件のコマンドを返します")
            
            # 追加デバッグ情報をログに出力
            if commands:
                logger.info(f"最初のコマンド例: {commands[0]}")
            else:
                logger.warning("コマンドが0件です")
            
            # CORS設定を明示的に追加
            headers = {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
            return JSONResponse(content=commands, headers=headers)
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"APIエラー: {str(e)}\n{error_details}")
            return JSONResponse(
                content={"error": str(e), "details": error_details},
                status_code=500
            )
    
    # 簡易的なコマンド一覧取得用エンドポイント（エラー処理を簡略化）
    @app.get("/api/commands-simple")
    async def get_commands_simple():
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
                    const response = await fetch('/api/commands');
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
    
    # GradioアプリをFastAPIにマウント
    mount_gradio_app(app, demo, path="/")
    
    return app

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
    
    # Chrome接続に関する注意事項
    logger.info("注意: Chromeの自動化を使用する場合は、以下のコマンドでChromeを起動してください:")
    if platform.system() == "Darwin":  # macOS
        logger.info("  open -a \"Google Chrome\" --args --remote-debugging-port=9222")
    elif platform.system() == "Windows":
        logger.info("  start chrome --remote-debugging-port=9222")
    else:  # Linux
        logger.info("  google-chrome --remote-debugging-port=9222")
    
    # FastAPIの実行
    nest_asyncio.apply()
    
    # サーバー起動（エラーハンドリング追加）
    try:
        uvicorn.run(app, host=args.ip, port=args.port)
    except Exception as e:
        logger.error(f"サーバー起動エラー: {str(e)}")
        import sys
        sys.exit(1)
