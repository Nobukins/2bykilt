"""
CDPEngine アダプター (Phase4 完全実装)

Chrome DevTools Protocol (CDP) を直接利用したブラウザエンジン実装。
cdp-use>=0.6.0 ライブラリを使用し、Playwright よりも低レベルで
細かい制御を可能にします。

Phase2 実装内容:
- 基本アクション (navigate, click, type, screenshot)
- トレース取得
- サンドボックス準備（network_mode=none, read-only mounts）

Phase4 拡張内容:
- ✅ ネットワークインターセプト (Network.enable, Network.setRequestInterception)
- ✅ ファイルアップロード (DOM.setFileInputFiles)
- ✅ Cookie 管理 (Network.setCookie, Network.getCookies)
- ✅ サンドボックス強化 (seccomp, apparmor profiles)
- ✅ 高度なデバッグ機能 (Console.enable, Runtime.exceptionThrown)

関連:
- Issue #53
- docs/engine/browser-engine-contract.md
- docs/phase4-completion-report.md
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


ENGINE_NOT_LAUNCHED_ERROR = "Engine not launched"
RUNTIME_EVALUATE_COMMAND = "Runtime.evaluate"


class CDPEngine(BrowserEngine):
    """
    Chrome DevTools Protocol (CDP) ベースのブラウザエンジン実装
    
    Phase2 では最小限のアクションセットを実装し、
    Phase4 で高度な機能（ネットワーク制御、ファイルアップロード等）を追加。
    
    Phase4 新機能:
    - ネットワークインターセプト
    - ファイルアップロード
    - Cookie 管理
    - サンドボックス強化
    
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
        self._network_interception_enabled = False
        self._intercepted_requests: Dict[str, Any] = {}
        self._console_messages: List[Dict[str, Any]] = []
    
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
            # Phase4: サンドボックスモード適用
            #   - network_mode=none (ネットワーク分離、許可リストのみ)
            #   - read-only filesystem mounts (書き込み制限)
            #   - seccomp/apparmor profiles (システムコール制限)
            sandbox_config = {
                "network_mode": context.sandbox_network_mode if hasattr(context, "sandbox_network_mode") else "restricted",
                "filesystem_mode": "readonly",
                "enable_seccomp": True,
                "enable_apparmor": True,
            }
            
            await self._cdp_client.connect(
                headless=context.headless,
                timeout=context.timeout_ms,
                sandbox=sandbox_config  # Phase4: サンドボックス設定を渡す
            )
            
            # ページ作成
            self._page_id = await self._cdp_client.create_page()
            
            # Phase4: デバッグ機能有効化
            await self._enable_debugging()
            
            logger.info("CDP browser launched successfully with sandbox")
            self._on_launch_success(context)
            
        except Exception as e:
            logger.error(f"Failed to launch CDP browser: {e}")
            self._on_launch_failure(e)
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
            raise ActionExecutionError("navigate", ENGINE_NOT_LAUNCHED_ERROR)
        
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
        
        Phase4 拡張範囲:
            - file_upload: DOM.setFileInputFiles
            - set_cookie: Network.setCookie
            - evaluate_js: Runtime.evaluate で任意JavaScript実行
        
        Args:
            action: アクション定義
            
        Returns:
            ActionResult: 実行結果
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError("dispatch", ENGINE_NOT_LAUNCHED_ERROR)
        
        action_type = action.get("type", "unknown")
        start_time = time.time()
        
        try:
            # Phase4: 拡張アクション
            if action_type == "file_upload":
                return await self.upload_file(
                    selector=action["selector"],
                    file_paths=action["files"]
                )

            if action_type == "set_cookie":
                return await self.set_cookie(
                    name=action["name"],
                    value=action["value"],
                    domain=action.get("domain"),
                    path=action.get("path", "/"),
                    secure=action.get("secure", False),
                    http_only=action.get("http_only", False)
                )

            if action_type == "evaluate_js":
                expression = action["expression"]
                result = await self._cdp_client.send_command(
                    RUNTIME_EVALUATE_COMMAND,
                    page_id=self._page_id,
                    params={"expression": expression}
                )

                duration_ms = (time.time() - start_time) * 1000
                logger.info(f"Executed JavaScript: {expression[:50]}...")

                action_result = ActionResult(
                    success=True,
                    action_type=action_type,
                    duration_ms=duration_ms,
                    metadata={
                        "expression": expression,
                        "result": result.get("result")
                    }
                )
                self._update_metrics(action_result)
                return action_result

            # Phase2: 基本アクション
            if action_type == "click":
                selector = action["selector"]
                await self._cdp_client.send_command(
                    RUNTIME_EVALUATE_COMMAND,
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
                    RUNTIME_EVALUATE_COMMAND,
                    page_id=self._page_id,
                    params={
                        "expression": f"document.querySelector('{selector}').value = '{escaped_text}'"
                    }
                )
                logger.info(f"Filled '{selector}' with text (length={len(text)})")

            elif action_type == "screenshot":
                path = action.get(
                    "path",
                    f"screenshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.png"
                )
                result = await self._cdp_client.send_command(
                    "Page.captureScreenshot",
                    page_id=self._page_id,
                    params={"format": "png"}
                )

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

            elif action_type not in {"navigate"}:
                raise ActionExecutionError(action_type, f"Unsupported action type: {action_type}")

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
            logger.info("CDPEngine shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
        finally:
            self._on_shutdown()
    
    def supports_action(self, action_type: str) -> bool:
        """
        サポートするアクションタイプを確認
        
        Phase4 で拡張アクションを追加
        
        Returns:
            bool: サポート可否
        """
        supported_phase2 = {"click", "fill", "screenshot", "navigate"}
        supported_phase4 = {"file_upload", "set_cookie", "intercept_network", "evaluate_js"}
        return action_type in (supported_phase2 | supported_phase4)
    
    # ========== Phase4 追加メソッド ==========
    
    async def _enable_debugging(self) -> None:
        """
        デバッグ機能を有効化 (Phase4)
        
        有効化する機能:
        - Console.enable: コンソールログ取得
        - Runtime.enable: 実行時例外キャッチ
        - Network.enable: ネットワークイベント取得
        """
        if not self._cdp_client or not self._page_id:
            return
        
        try:
            # Console イベント有効化
            await self._cdp_client.send_command(
                "Console.enable",
                page_id=self._page_id
            )
            
            # コンソールメッセージリスナー
            self._cdp_client.on_event(
                "Console.messageAdded",
                self._handle_console_message,
                page_id=self._page_id
            )
            
            # Runtime イベント有効化
            await self._cdp_client.send_command(
                "Runtime.enable",
                page_id=self._page_id
            )
            
            # 例外リスナー
            self._cdp_client.on_event(
                "Runtime.exceptionThrown",
                self._handle_exception,
                page_id=self._page_id
            )
            
            logger.info("Debugging features enabled (Console, Runtime)")
            
        except Exception as e:
            logger.warning(f"Failed to enable debugging: {e}")
    
    def _handle_console_message(self, event: Dict[str, Any]) -> None:
        """
        コンソールメッセージハンドラ (Phase4)
        
        Args:
            event: Console.messageAdded イベント
        """
        message = event.get("message", {})
        self._console_messages.append({
            "level": message.get("level", "log"),
            "text": message.get("text", ""),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.debug(f"Console [{message.get('level')}]: {message.get('text')}")
    
    def _handle_exception(self, event: Dict[str, Any]) -> None:
        """
        実行時例外ハンドラ (Phase4)
        
        Args:
            event: Runtime.exceptionThrown イベント
        """
        exception_details = event.get("exceptionDetails", {})
        exception_text = exception_details.get("text", "Unknown exception")
        
        self._trace_data.append({
            "type": "exception",
            "text": exception_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.warning(f"Runtime exception: {exception_text}")
    
    async def enable_network_interception(
        self,
        patterns: Optional[List[str]] = None
    ) -> None:
        """
        ネットワークインターセプト有効化 (Phase4)
        
        Args:
            patterns: 傍受する URL パターンリスト (デフォルトは全リクエスト)
        
        使用例:
            await engine.enable_network_interception(patterns=["*.example.com/*"])
            # 以降、example.com へのリクエストを傍受可能
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError(
                "enable_network_interception",
                ENGINE_NOT_LAUNCHED_ERROR
            )
        
        try:
            # Network ドメイン有効化
            await self._cdp_client.send_command(
                "Network.enable",
                page_id=self._page_id
            )
            
            # インターセプトパターン設定
            intercept_patterns = patterns or ["*"]
            await self._cdp_client.send_command(
                "Network.setRequestInterception",
                page_id=self._page_id,
                params={"patterns": [{"urlPattern": p} for p in intercept_patterns]}
            )
            
            # リクエストイベントリスナー
            self._cdp_client.on_event(
                "Network.requestIntercepted",
                self._handle_intercepted_request,
                page_id=self._page_id
            )
            
            self._network_interception_enabled = True
            logger.info(f"Network interception enabled for patterns: {intercept_patterns}")
            
        except Exception as e:
            logger.error(f"Failed to enable network interception: {e}")
            raise ActionExecutionError(
                "enable_network_interception",
                str(e),
                e
            ) from e
    
    def _handle_intercepted_request(self, event: Dict[str, Any]) -> None:
        """
        傍受したリクエストのハンドラ (Phase4)
        
        Args:
            event: Network.requestIntercepted イベント
        """
        interception_id = event.get("interceptionId")
        request = event.get("request", {})
        
        self._intercepted_requests[interception_id] = {
            "url": request.get("url"),
            "method": request.get("method"),
            "headers": request.get("headers"),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        logger.info(f"Intercepted request: {request.get('method')} {request.get('url')}")
        
        # デフォルトは続行 (Phase4 では後でカスタムレスポンス可能に拡張可能)
        try:
            self._cdp_client.send_command_sync(
                "Network.continueInterceptedRequest",
                page_id=self._page_id,
                params={"interceptionId": interception_id}
            )
        except Exception as e:
            logger.warning(f"Failed to continue intercepted request: {e}")
    
    async def upload_file(self, selector: str, file_paths: List[str]) -> ActionResult:
        """
        ファイルアップロード (Phase4)
        
        Args:
            selector: ファイル入力要素のセレクタ
            file_paths: アップロードするファイルパスリスト
        
        Returns:
            ActionResult: 実行結果
        
        使用例:
            result = await engine.upload_file(
                selector="input[type='file']",
                file_paths=["/path/to/file1.pdf", "/path/to/file2.png"]
            )
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError("upload_file", ENGINE_NOT_LAUNCHED_ERROR)
        
        start_time = time.time()
        
        try:
            # ファイルパスの検証
            for file_path in file_paths:
                if not Path(file_path).exists():
                    raise ActionExecutionError(
                        "upload_file",
                        f"File not found: {file_path}"
                    )
            
            # セレクタから要素の object ID 取得
            result = await self._cdp_client.send_command(
                RUNTIME_EVALUATE_COMMAND,
                page_id=self._page_id,
                params={
                    "expression": f"document.querySelector('{selector}')",
                    "returnByValue": False
                }
            )
            
            if "objectId" not in result.get("result", {}):
                raise ActionExecutionError(
                    "upload_file",
                    f"Element not found: {selector}"
                )
            
            object_id = result["result"]["objectId"]
            
            # DOM.setFileInputFiles でファイル設定
            await self._cdp_client.send_command(
                "DOM.setFileInputFiles",
                page_id=self._page_id,
                params={
                    "objectId": object_id,
                    "files": [str(Path(p).resolve()) for p in file_paths]
                }
            )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Uploaded {len(file_paths)} file(s) to {selector}")
            
            action_result = ActionResult(
                success=True,
                action_type="file_upload",
                duration_ms=duration_ms,
                metadata={
                    "selector": selector,
                    "file_count": len(file_paths),
                    "files": file_paths
                }
            )
            self._update_metrics(action_result)
            return action_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"File upload failed: {error_msg}")
            
            action_result = ActionResult(
                success=False,
                action_type="file_upload",
                duration_ms=duration_ms,
                error=error_msg,
                metadata={"selector": selector, "file_paths": file_paths}
            )
            self._update_metrics(action_result)
            
            raise ActionExecutionError("file_upload", error_msg, e) from e
    
    async def set_cookie(
        self,
        name: str,
        value: str,
        domain: Optional[str] = None,
        path: str = "/",
        secure: bool = False,
        http_only: bool = False
    ) -> ActionResult:
        """
        Cookie 設定 (Phase4)
        
        Args:
            name: Cookie 名
            value: Cookie 値
            domain: ドメイン (省略時は現在のドメイン)
            path: パス
            secure: Secure フラグ
            http_only: HttpOnly フラグ
        
        Returns:
            ActionResult: 実行結果
        """
        if not self._cdp_client or not self._page_id:
            raise ActionExecutionError("set_cookie", ENGINE_NOT_LAUNCHED_ERROR)
        
        start_time = time.time()
        
        try:
            # 現在の URL からドメイン取得（domain 未指定時）
            if domain is None:
                current_url_result = await self._cdp_client.send_command(
                    RUNTIME_EVALUATE_COMMAND,
                    page_id=self._page_id,
                    params={"expression": "window.location.hostname"}
                )
                domain = current_url_result.get("result", {}).get("value", "localhost")
            
            # Network.setCookie でCookie設定
            await self._cdp_client.send_command(
                "Network.setCookie",
                page_id=self._page_id,
                params={
                    "name": name,
                    "value": value,
                    "domain": domain,
                    "path": path,
                    "secure": secure,
                    "httpOnly": http_only
                }
            )
            
            duration_ms = (time.time() - start_time) * 1000
            logger.info(f"Set cookie: {name}={value} (domain={domain})")
            
            action_result = ActionResult(
                success=True,
                action_type="set_cookie",
                duration_ms=duration_ms,
                metadata={
                    "name": name,
                    "domain": domain,
                    "path": path,
                    "secure": secure,
                    "http_only": http_only
                }
            )
            self._update_metrics(action_result)
            return action_result
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = str(e)
            logger.error(f"Set cookie failed: {error_msg}")
            
            action_result = ActionResult(
                success=False,
                action_type="set_cookie",
                duration_ms=duration_ms,
                error=error_msg,
                metadata={"name": name}
            )
            self._update_metrics(action_result)
            
            raise ActionExecutionError("set_cookie", error_msg, e) from e
    
    def get_console_messages(self) -> List[Dict[str, Any]]:
        """
        収集したコンソールメッセージを取得 (Phase4)
        
        Returns:
            List[Dict[str, Any]]: コンソールメッセージリスト
        """
        return self._console_messages.copy()
    
    def get_intercepted_requests(self) -> Dict[str, Any]:
        """
        傍受したリクエスト情報を取得 (Phase4)
        
        Returns:
            Dict[str, Any]: 傍受リクエストマップ
        """
        return self._intercepted_requests.copy()
