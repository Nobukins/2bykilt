#!/usr/bin/env python3
"""CDP デモスクリプト

CDP エンジン経由で unlock-future コマンドを実行し、
スクリーンショットとトレースを生成するサンプル。

チュートリアル: docs/tutorial/cdp-use-workflow.md#3-unlock-future-コマンドを-cdp-経路で実行する

使い方:
  RUNNER_ENGINE=cdp python myscript/bin/run_cdp_demo.py
"""

import asyncio
import sys
from pathlib import Path

# プロジェクトルートを PYTHONPATH に追加
project_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(project_root))

from src.browser.engine.browser_engine import LaunchContext
from src.browser.engine.loader import EngineLoader
from src.browser.unlock_future_adapter import UnlockFutureAdapter
from src.utils.app_logger import logger

JSON_PATH = project_root / "myscript" / "templates" / "cdp_demo.json"


async def main() -> None:
    """メイン実行ロジック"""
    logger.info("🚀 CDP デモスクリプト開始")
    
    # CDP エンジンをロード
    logger.info("📦 EngineLoader で CDP エンジンを取得...")
    engine = EngineLoader.load_engine("cdp")
    adapter = UnlockFutureAdapter(engine)
    
    try:
        # エンジンを起動（headless、トレース有効）
        logger.info("🌐 CDP エンジンを起動中...")
        launch_ctx = LaunchContext(
            headless=False,  # デバッグ用にブラウザを表示
            trace_enabled=True,
            viewport={"width": 1280, "height": 720}
        )
        await engine.launch(launch_ctx)
        logger.info("✅ CDP エンジン起動完了")
        
        # unlock-future JSON を読み込み
        logger.info(f"📂 JSON ファイルをロード: {JSON_PATH}")
        commands_data = UnlockFutureAdapter.load_unlock_future_json(str(JSON_PATH))
        commands = commands_data if isinstance(commands_data, list) else commands_data.get("commands", [])
        
        # コマンドを実行
        logger.info(f"▶️ {len(commands)} 個のコマンドを実行します...")
        results = await adapter.execute_unlock_future_commands(
            commands,
            keep_tab_open=False,  # 実行後に自動クローズ
            delay_between_commands=2.0
        )
        
        # 結果サマリー
        logger.info("\n" + "=" * 60)
        logger.info("📊 実行結果サマリー")
        logger.info("=" * 60)
        for i, result in enumerate(results, start=1):
            status = "✅" if result.success else "❌"
            logger.info(
                f"{status} Step {i}: {result.action_type} "
                f"({result.duration_ms:.1f}ms)"
            )
            if result.error:
                logger.error(f"   ⚠️ Error: {result.error}")
        logger.info("=" * 60)
        
        success_count = sum(1 for r in results if r.success)
        logger.info(f"\n🎯 成功: {success_count}/{len(results)} 個のコマンド")
        
    except Exception as e:
        logger.error(f"❌ エラーが発生しました: {e}")
        import traceback
        logger.error(traceback.format_exc())
        sys.exit(1)
    finally:
        logger.info("🧹 CDP エンジンをシャットダウン中...")
        await engine.shutdown()
        logger.info("✅ シャットダウン完了")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n⚠️ ユーザーによる中断")
        sys.exit(130)
