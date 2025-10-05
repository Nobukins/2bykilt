"""
CDPEngine アダプター (Phase2 実装)

Chrome DevTools Protocol (CDP) を直接利用したブラウザエンジン実装。
cdp-use>=0.6.0 ライブラリを使用し、Playwright よりも低レベルで
細かい制御を可能にします。

Phase2 スコープ:
- 基本アクション (navigate, click, type, screenshot)
- トレース取得
- サンドボックス準備（network_mode=none, read-only mounts）

Phase4 拡張予定:
- ネットワークインターセプト
- ファイルアップロード
- 高度なデバッグ機能

関連:
- Issue #53
- docs/engine/browser-engine-contract.md
"""

import logging
import time
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

from .browser_engine import (
    BrowserEngine,
    EngineType,
    LaunchContext,
    ActionResult,
    EngineLaunchError,
    ActionExecutionError,
    ArtifactCaptureError,
)

logger = logging.getLogger(__name__)


class CDPEngine(BrowserEngine):
    """
    Chrome DevTools Protocol (CDP) ベースのブラウザエンジン実装
    
    Phase2 では最小限のアクションセットを実装し、
    Phase4 で高度な機能（ネットワーク制御等）を追加予定。
    
    注意:
        cdp-use>=0.6.0 が必要です。未インストール環境では
        EngineLoader が ImportError を検出し、このエンジンを
        利用可能リストから除外します。
    """
    
    def __init__(self, engine_type: EngineType = EngineType.CDP):
        super().__init__(engine_type)
        self._cdp_client = None
        self._browser_process = None
        self._page_id = None
        self._trace_data = []
    
    async def launch(self, context: LaunchContext) -> None:
        """
        CDP クライアントを初期化しブラウザプロセスを起動
        
        Args:
            context: 起動パラメータ
            
        Raises:
            EngineLaunchError: 起動失敗時
        """
        try:
            logger.info(f"Launching CDP browser (headless={context.headless})")
            
            # cdp-use のインポート（遅延インポートでオプショナル依存を実現）
            try:
                from cdp_use import CDPClient  # type: ignore
            except ImportError as e:
                raise EngineLaunchError(
                    "cdp-use library not installed. "
                    "Install with: pip install cdp-use>=0.6.0"
                ) from e
            
            # CDP クライアント初期化
            # Phase2 では簡易実装、Phase4 でサンドボックス強化
            self._cdp_client = CDPClient()
            
            # ブラウザプロセス起動
            # TODO: サンドボックスモードの適用 (Phase4)
            #   - network_mode=none
            #   - read-only filesystem mounts
            #   - seccomp/apparmor profiles
            await self._cdp_client.connect(
                headless=context.headless,
                timeout=context.timeout_ms
            )
            
            # ページ作成
            self._page_id = await self._cdp_client.create_page()
            
            logger.info("CDP browser launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to launch CDP browser: {e}")
            await self.shutdown(capture_final_state=False)
            raise EngineLaunchError(f"CDP launch failed: {e}") from e
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> ActionResult:
        """
        指定URLへ遷移
        
        Args:
            url: 遷移先URL
            wait_until: 待機条件（CDP では load イベントで判定）
            
        Returns:
            ActionResult: 実行結果
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError("navigate", "Engine not launched")
        
        start_time = time.time()
        
        try:
            logger.info(f"Navigating to: {url}")
            
            # CDP Page.navigate コマンド送信
            result = await self._cdp_client.send_command(
                "Page.navigate",
                page_id=self._page_id,
                params={"url": url}
            )
            
            # ロード完了待機
            await self._cdp_client.wait_for_event(
                "Page.loadEventFired",
                page_id=self._page_id,
                timeout=30000
            )
            
            duration_ms = (time.time() - start_time) * 1000
            
            action_result = ActionResult(
                success=True,
                action_type="navigate",
                duration_ms=duration_ms,
                metadata={"url": url, "frame_id": result.get("frameId")}
            )
            self._update_metrics(action_result)
            
            logger.info(f"Navigation successful ({duration_ms:.1f}ms)")
            return action_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Navigation failed: {error_msg}")
            
            action_result = ActionResult(
                success=False,
                action_type="navigate",
                duration_ms=duration_ms,
                error=error_msg,
                metadata={"url": url}
            )
            self._update_metrics(action_result)
            
            raise ActionExecutionError("navigate", error_msg, e) from e
    
    async def dispatch(self, action: Dict[str, Any]) -> ActionResult:
        """
        汎用アクション実行
        
        Phase2 実装範囲:
            - click: Input.dispatchMouseEvent
            - fill: Runtime.evaluate で要素に値設定
            - screenshot: Page.captureScreenshot
        
        Args:
            action: アクション定義
            
        Returns:
            ActionResult: 実行結果
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError("dispatch", "Engine not launched")
        
        action_type = action.get("type", "unknown")
        start_time = time.time()
        
        try:
            if action_type == "click":
                selector = action["selector"]
                # CDP では座標計算が必要だが Phase2 では evaluate でフォールバック
                await self._cdp_client.send_command(
                    "Runtime.evaluate",
                    page_id=self._page_id,
                    params={
                        "expression": f"document.querySelector('{selector}').click()"
                    }
                )
                logger.info(f"Clicked: {selector} (via Runtime.evaluate)")
                
            elif action_type == "fill":
                selector = action["selector"]
                text = action["text"]
                escaped_text = text.replace("'", "\\'").replace("\n", "\\n")
                await self._cdp_client.send_command(
                    "Runtime.evaluate",
                    page_id=self._page_id,
                    params={
                        "expression": f"document.querySelector('{selector}').value = '{escaped_text}'"
                    }
                )
                logger.info(f"Filled '{selector}' with text (length={len(text)})")
                
            elif action_type == "screenshot":
                path = action.get("path", f"screenshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png")
                result = await self._cdp_client.send_command(
                    "Page.captureScreenshot",
                    page_id=self._page_id,
                    params={"format": "png"}
                )
                
                # Base64 データをファイルに保存
                import base64
                screenshot_data = base64.b64decode(result["data"])
                Path(path).parent.mkdir(parents=True, exist_ok=True)
                Path(path).write_bytes(screenshot_data)
                
                logger.info(f"Screenshot saved: {path}")
                duration_ms = (time.time() - start_time) * 1000
                action_result = ActionResult(
                    success=True,
                    action_type=action_type,
                    duration_ms=duration_ms,
                    artifacts={"screenshot_path": path}
                )
                self._update_metrics(action_result)
                return action_result
                
            else:
                raise ActionExecutionError(action_type, f"Unsupported action type in Phase2: {action_type}")
            
            duration_ms = (time.time() - start_time) * 1000
            action_result = ActionResult(
                success=True,
                action_type=action_type,
                duration_ms=duration_ms,
                metadata=action
            )
            self._update_metrics(action_result)
            return action_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Action '{action_type}' failed: {error_msg}")
            
            action_result = ActionResult(
                success=False,
                action_type=action_type,
                duration_ms=duration_ms,
                error=error_msg,
                metadata=action
            )
            self._update_metrics(action_result)
            
            raise ActionExecutionError(action_type, error_msg, e) from e
    
    async def capture_artifacts(self, artifact_types: List[str]) -> Dict[str, Any]:
        """
        アーティファクトを取得
        
        Phase2 実装範囲:
            - screenshot: Page.captureScreenshot
            - trace: 収集したイベントログ（簡易実装）
        
        Args:
            artifact_types: アーティファクトタイプリスト
            
        Returns:
            Dict[str, Any]: アーティファクトデータ
        """
        artifacts = {}
        
        try:
            if "screenshot" in artifact_types and self._cdp_client and self._page_id:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"artifacts/screenshots/cdp_final_{timestamp}.png"
                
                result = await self._cdp_client.send_command(
                    "Page.captureScreenshot",
                    page_id=self._page_id,
                    params={"format": "png"}
                )
                
                import base64
                screenshot_data = base64.b64decode(result["data"])
                Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                Path(screenshot_path).write_bytes(screenshot_data)
                
                artifacts["screenshot"] = screenshot_path
                logger.info(f"Captured screenshot: {screenshot_path}")
            
            if "trace" in artifact_types:
                # Phase2 では簡易トレース（イベントログ）
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                trace_path = f"artifacts/traces/cdp_trace_{timestamp}.json"
                
                import json
                trace_content = {
                    "engine": "cdp",
                    "events": self._trace_data,
                    "captured_at": timestamp
                }
                
                Path(trace_path).parent.mkdir(parents=True, exist_ok=True)
                Path(trace_path).write_text(json.dumps(trace_content, indent=2), encoding="utf-8")
                
                artifacts["trace"] = trace_path
                logger.info(f"Captured trace: {trace_path}")
            
            return artifacts
            
        except Exception as e:
            logger.error(f"Failed to capture artifacts: {e}")
            raise ArtifactCaptureError(f"Artifact capture failed: {e}") from e
    
    async def shutdown(self, capture_final_state: bool = True) -> None:
        """
        エンジンをシャットダウン
        
        Args:
            capture_final_state: 終了時に最終状態をキャプチャ
        """
        logger.info("Shutting down CDPEngine")
        
        try:
            if capture_final_state and self._cdp_client:
                try:
                    await self.capture_artifacts(["screenshot", "trace"])
                except Exception as e:
                    logger.warning(f"Failed to capture final state: {e}")
            
            if self._cdp_client:
                await self._cdp_client.disconnect()
                self._cdp_client = None
            
            self._page_id = None
            self._metrics.shutdown_at = datetime.now(timezone.utc)
            logger.info("CDPEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
    
    def supports_action(self, action_type: str) -> bool:
        """
        サポートするアクションタイプを確認
        
        Phase2 では基本アクションのみ
        
        Returns:
            bool: サポート可否
        """
        supported_phase2 = {"click", "fill", "screenshot", "navigate"}
        return action_type in supported_phase2
