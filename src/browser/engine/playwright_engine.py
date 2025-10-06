"""
PlaywrightEngine アダプター

既存の execution_debug_engine.py の Playwright ロジックを
BrowserEngine インターフェース準拠で再実装します。

フェーズ1 スコープ:
- 基本アクション（navigate, click, fill, keyboard_press, screenshot）
- unlock-future 互換性維持
- トレース取得機能

関連:
- Issue #53
- docs/engine/browser-engine-contract.md
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime, timezone

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

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


class PlaywrightEngine(BrowserEngine):
    """
    Playwright ベースのブラウザエンジン実装
    
    既存の execution_debug_engine.py の動作を可能な限り踏襲しつつ、
    BrowserEngine 契約を満たす形で実装。
    """
    
    def __init__(self, engine_type: EngineType = EngineType.PLAYWRIGHT):
        super().__init__(engine_type)
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._trace_path: Optional[Path] = None
    
    async def launch(self, context: LaunchContext) -> None:
        """
        Playwright ブラウザを起動
        
        Args:
            context: 起動パラメータ
            
        Raises:
            EngineLaunchError: 起動失敗時
        """
        try:
            logger.info(f"Launching Playwright browser (type={context.browser_type}, headless={context.headless})")
            
            self._playwright = await async_playwright().start()
            
            # ブラウザタイプ選択
            if context.browser_type == "chromium":
                browser_launcher = self._playwright.chromium
            elif context.browser_type == "firefox":
                browser_launcher = self._playwright.firefox
            elif context.browser_type == "webkit":
                browser_launcher = self._playwright.webkit
            else:
                raise EngineLaunchError(f"Unsupported browser type: {context.browser_type}")
            
            # ブラウザ起動
            launch_args = {
                "headless": context.headless,
            }
            if context.extra_args:
                launch_args["args"] = context.extra_args
            
            self._browser = await browser_launcher.launch(**launch_args)
            
            # コンテキスト作成
            context_args = {}
            if context.viewport:
                context_args["viewport"] = context.viewport
            if context.user_agent:
                context_args["user_agent"] = context.user_agent
            if context.proxy:
                context_args["proxy"] = context.proxy
            
            self._context = await self._browser.new_context(**context_args)
            self._context.set_default_timeout(context.timeout_ms)
            
            # トレース有効化
            if context.trace_enabled:
                trace_dir = Path("artifacts/traces")
                trace_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                self._trace_path = trace_dir / f"trace_{timestamp}.zip"
                await self._context.tracing.start(screenshots=True, snapshots=True, sources=True)
                logger.info(f"Trace recording started: {self._trace_path}")
            
            # ページ作成
            self._page = await self._context.new_page()
            logger.info("Playwright browser launched successfully")

            self._on_launch_success(context)
            
        except Exception as e:
            logger.error(f"Failed to launch Playwright browser: {e}")
            self._on_launch_failure(e)
            await self.shutdown(capture_final_state=False)
            raise EngineLaunchError(f"Playwright launch failed: {e}") from e
    
    async def navigate(self, url: str, wait_until: str = "domcontentloaded") -> ActionResult:
        """
        指定URLへ遷移
        
        Args:
            url: 遷移先URL
            wait_until: 待機条件
            
        Returns:
            ActionResult: 実行結果
        """
        if not self._page:
            raise ActionExecutionError("navigate", "Engine not launched")
        
        start_time = time.time()
        
        try:
            logger.info(f"Navigating to: {url}")
            await self._page.goto(url, wait_until=wait_until)
            
            # networkidle 待機（unlock-future 互換）
            if wait_until != "networkidle":
                await self._page.wait_for_load_state("networkidle", timeout=10000)
            
            duration_ms = (time.time() - start_time) * 1000
            
            result = ActionResult(
                success=True,
                action_type="navigate",
                duration_ms=duration_ms,
                metadata={"url": url, "wait_until": wait_until}
            )
            self._update_metrics(result)
            
            logger.info(f"Navigation successful ({duration_ms:.1f}ms)")
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Navigation failed: {error_msg}")
            
            result = ActionResult(
                success=False,
                action_type="navigate",
                duration_ms=duration_ms,
                error=error_msg,
                metadata={"url": url}
            )
            self._update_metrics(result)
            
            raise ActionExecutionError("navigate", error_msg, e) from e
    
    async def dispatch(self, action: Dict[str, Any]) -> ActionResult:
        """
        汎用アクション実行
        
        Args:
            action: アクション定義
                - type: "click" | "fill" | "keyboard_press" | "extract_content" | "screenshot" | "evaluate"
                - selector: CSS セレクター（type, click, fill）
                - text: 入力テキスト（fill）
                - key: キーボードキー（keyboard_press）
                - code: JavaScript コード（evaluate）
                
        Returns:
            ActionResult: 実行結果
        """
        if not self._page:
            raise ActionExecutionError("dispatch", "Engine not launched")
        
        action_type = action.get("type", "unknown")
        start_time = time.time()
        
        try:
            if action_type == "click":
                selector = action["selector"]
                timeout = action.get("timeout", 30000)
                await self._page.click(selector, timeout=timeout)
                logger.info(f"Clicked: {selector}")
                
            elif action_type == "fill":
                selector = action["selector"]
                text = action["text"]
                await self._page.fill(selector, text)
                logger.info(f"Filled '{selector}' with text (length={len(text)})")
                
            elif action_type == "keyboard_press":
                key = action["key"]
                await self._page.keyboard.press(key)
                logger.info(f"Pressed key: {key}")
                
            elif action_type == "extract_content":
                selectors = action.get("selectors", ["h1"])
                content = {}
                for selector in selectors:
                    elements = await self._page.query_selector_all(selector)
                    texts = [await elem.text_content() for elem in elements]
                    texts = [t.strip() for t in texts if t and t.strip()]
                    content[selector] = texts
                logger.info(f"Extracted content from {len(selectors)} selectors")
                duration_ms = (time.time() - start_time) * 1000
                result = ActionResult(
                    success=True,
                    action_type=action_type,
                    duration_ms=duration_ms,
                    artifacts={"extracted_content": content}
                )
                self._update_metrics(result)
                return result
                
            elif action_type == "screenshot":
                path = action.get("path", f"screenshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png")
                await self._page.screenshot(path=path)
                logger.info(f"Screenshot saved: {path}")
                duration_ms = (time.time() - start_time) * 1000
                result = ActionResult(
                    success=True,
                    action_type=action_type,
                    duration_ms=duration_ms,
                    artifacts={"screenshot_path": path}
                )
                self._update_metrics(result)
                return result
                
            elif action_type == "evaluate":
                code = action["code"]
                eval_result = await self._page.evaluate(code)
                logger.info(f"Evaluated JavaScript (result type: {type(eval_result).__name__})")
                duration_ms = (time.time() - start_time) * 1000
                result = ActionResult(
                    success=True,
                    action_type=action_type,
                    duration_ms=duration_ms,
                    artifacts={"eval_result": eval_result}
                )
                self._update_metrics(result)
                return result
                
            else:
                raise ActionExecutionError(action_type, f"Unsupported action type: {action_type}")
            
            duration_ms = (time.time() - start_time) * 1000
            result = ActionResult(
                success=True,
                action_type=action_type,
                duration_ms=duration_ms,
                metadata=action
            )
            self._update_metrics(result)
            return result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Action '{action_type}' failed: {error_msg}")
            
            result = ActionResult(
                success=False,
                action_type=action_type,
                duration_ms=duration_ms,
                error=error_msg,
                metadata=action
            )
            self._update_metrics(result)
            
            raise ActionExecutionError(action_type, error_msg, e) from e
    
    async def capture_artifacts(self, artifact_types: List[str]) -> Dict[str, Any]:
        """
        アーティファクトを取得
        
        Args:
            artifact_types: ["screenshot", "trace", "console_logs", "html"]
            
        Returns:
            Dict[str, Any]: アーティファクトデータ
        """
        artifacts = {}
        
        try:
            if "screenshot" in artifact_types and self._page:
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"artifacts/screenshots/final_{timestamp}.png"
                Path(screenshot_path).parent.mkdir(parents=True, exist_ok=True)
                await self._page.screenshot(path=screenshot_path, full_page=True)
                artifacts["screenshot"] = screenshot_path
                logger.info(f"Captured screenshot: {screenshot_path}")
            
            if "trace" in artifact_types and self._context and self._trace_path:
                await self._context.tracing.stop(path=str(self._trace_path))
                artifacts["trace"] = str(self._trace_path)
                logger.info(f"Captured trace: {self._trace_path}")
            
            if "html" in artifact_types and self._page:
                html_content = await self._page.content()
                timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
                html_path = f"artifacts/html/page_{timestamp}.html"
                Path(html_path).parent.mkdir(parents=True, exist_ok=True)
                Path(html_path).write_text(html_content, encoding="utf-8")
                artifacts["html"] = html_path
                logger.info(f"Captured HTML: {html_path}")
            
            if "console_logs" in artifact_types:
                # フェーズ2 で実装予定（コンソールログ収集機構）
                artifacts["console_logs"] = "(not yet implemented)"
            
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
        logger.info("Shutting down PlaywrightEngine")
        
        try:
            if capture_final_state and self._page:
                try:
                    await self.capture_artifacts(["screenshot", "trace"])
                except Exception as e:
                    logger.warning(f"Failed to capture final state: {e}")
            
            if self._context:
                await self._context.close()
                self._context = None
            
            if self._browser:
                await self._browser.close()
                self._browser = None
            
            if self._playwright:
                await self._playwright.stop()
                self._playwright = None
            
            self._page = None
            logger.info("PlaywrightEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._on_shutdown()
    
    def supports_action(self, action_type: str) -> bool:
        """
        サポートするアクションタイプを確認
        
        Returns:
            bool: サポート可否
        """
        supported = {
            "click", "fill", "keyboard_press", "extract_content",
            "screenshot", "evaluate", "navigate"
        }
        return action_type in supported
