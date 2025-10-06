"""
unlock-future アダプター

既存の unlock-future JSON 形式のアクション定義を BrowserEngine の
dispatch() 形式へ変換し、実行する薄いラッパー層。

unlock-future JSON 例:
{
  "commands": [
    {"action": "command", "args": ["https://example.com"]},
    {"action": "fill_form", "args": ["#search", "test"]},
    {"action": "click", "args": ["#submit"]},
    {"action": "screenshot", "args": ["result.png"]}
  ],
  "action_type": "unlock-future"
}

関連:
- Issue #53
- docs/engine/browser-engine-contract.md
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

from src.browser.engine.browser_engine import BrowserEngine, ActionResult

logger = logging.getLogger(__name__)


class UnlockFutureAdapter:
    """
    unlock-future JSON を BrowserEngine へ変換するアダプター
    
    既存の execution_debug_engine.py の execute_commands() ロジックと
    同等の動作を BrowserEngine インターフェース経由で実現。
    """
    
    def __init__(self, engine: BrowserEngine):
        """
        Args:
            engine: BrowserEngine 実装インスタンス
        """
        self.engine = engine
    
    async def execute_unlock_future_commands(
        self,
        commands: List[Dict[str, Any]],
        keep_tab_open: bool = True,
        delay_between_commands: float = 3.0
    ) -> List[ActionResult]:
        """
        unlock-future コマンドリストを実行
        
        Args:
            commands: unlock-future 形式のコマンドリスト
            keep_tab_open: 実行後にタブを開いたままにするか
            delay_between_commands: コマンド間の待機時間（秒）
            
        Returns:
            List[ActionResult]: 実行結果のリスト
        """
        results = []
        
        logger.info(f"Executing {len(commands)} unlock-future commands")
        
        for i, cmd in enumerate(commands, 1):
            action = cmd.get("action", "unknown")
            args = cmd.get("args", [])
            
            logger.info(f"[{i}/{len(commands)}] {action}: {args}")
            
            try:
                result = await self._execute_single_command(action, args)
                results.append(result)
                
                if not result.success:
                    logger.warning(f"Command failed, stopping execution: {result.error}")
                    break
                
                # コマンド間遅延（最後のコマンドでは不要）
                if i < len(commands):
                    import asyncio
                    logger.debug(f"Waiting {delay_between_commands}s before next command...")
                    await asyncio.sleep(delay_between_commands)
                
            except Exception as e:
                logger.error(f"Unexpected error executing command '{action}': {e}")
                results.append(ActionResult(
                    success=False,
                    action_type=action,
                    duration_ms=0.0,
                    error=str(e)
                ))
                break
        
        logger.info(f"Execution complete: {len(results)} commands executed")
        return results
    
    async def _execute_single_command(self, action: str, args: List[Any]) -> ActionResult:
        """
        単一の unlock-future コマンドを実行
        
        Args:
            action: アクション名 ("command", "fill_form", "click", etc.)
            args: アクション引数
            
        Returns:
            ActionResult: 実行結果
        """
        # "command" with URL → navigate
        if action == "command" and args and isinstance(args[0], str) and args[0].startswith("http"):
            url = args[0]
            return await self.engine.navigate(url)
        
        # "wait_for_navigation" → networkidle 待機
        elif action == "wait_for_navigation":
            # navigate 時に既に networkidle 待機しているため、ここでは no-op
            logger.debug("wait_for_navigation: already handled in navigate()")
            return ActionResult(
                success=True,
                action_type="wait_for_navigation",
                duration_ms=0.0
            )
        
        # "fill_form" → fill dispatch
        elif action == "fill_form" and len(args) >= 2:
            selector, text = args[0], args[1]
            return await self.engine.dispatch({
                "type": "fill",
                "selector": selector,
                "text": text
            })
        
        # "click" → click dispatch
        elif action == "click" and args:
            selector = args[0]
            timeout = args[1] if len(args) > 1 else 30000
            return await self.engine.dispatch({
                "type": "click",
                "selector": selector,
                "timeout": timeout
            })
        
        # "keyboard_press" → keyboard_press dispatch
        elif action == "keyboard_press" and args:
            key = args[0]
            return await self.engine.dispatch({
                "type": "keyboard_press",
                "key": key
            })
        
        # "extract_content" → extract_content dispatch
        elif action == "extract_content":
            selectors = args if args else ["h1"]
            return await self.engine.dispatch({
                "type": "extract_content",
                "selectors": selectors
            })
        
        # "screenshot" → screenshot dispatch
        elif action == "screenshot":
            path = args[0] if args else None
            dispatch_action = {"type": "screenshot"}
            if path:
                dispatch_action["path"] = path
            return await self.engine.dispatch(dispatch_action)
        
        # "close_tab" → 即座に終了フラグ
        elif action == "close_tab":
            logger.info("close_tab: marking execution for termination")
            return ActionResult(
                success=True,
                action_type="close_tab",
                duration_ms=0.0,
                metadata={"terminate": True}
            )
        
        # 未知のアクション → 汎用 dispatch へフォールバック
        else:
            logger.warning(f"Unknown unlock-future action: {action}, attempting generic dispatch")
            return await self.engine.dispatch({
                "type": action,
                "args": args
            })
    
    @staticmethod
    def load_unlock_future_json(json_path: str) -> Dict[str, Any]:
        """
        unlock-future JSON ファイルを読み込み
        
        Args:
            json_path: JSON ファイルパス
            
        Returns:
            Dict: パース済み JSON データ
        """
        import json
        path = Path(json_path)
        if not path.exists():
            raise FileNotFoundError(f"unlock-future JSON not found: {json_path}")
        
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        
        logger.info(f"Loaded unlock-future JSON: {json_path}")
        return data
