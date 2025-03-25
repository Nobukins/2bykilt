import logging
import uuid
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class SessionManager:
    """ブラウザセッションを管理するクラス"""
    
    def __init__(self):
        self.active_session_id = None
        self.sessions = {}
    
    def create_session(self, browser_info: Dict[str, Any] = None) -> str:
        """新しいセッションを作成し、IDを返す"""
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "browser_info": browser_info or {},
            "created_at": __import__('datetime').datetime.now().isoformat()
        }
        self.active_session_id = session_id
        logger.info(f"新しいブラウザセッションを作成: {session_id}")
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """セッション情報を取得"""
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, browser_info: Dict[str, Any]) -> bool:
        """セッション情報を更新"""
        if session_id in self.sessions:
            self.sessions[session_id]["browser_info"] = browser_info
            self.sessions[session_id]["updated_at"] = __import__('datetime').datetime.now().isoformat()
            return True
        return False
    
    def remove_session(self, session_id: str) -> bool:
        """セッションを削除"""
        if session_id in self.sessions:
            del self.sessions[session_id]
            if self.active_session_id == session_id:
                self.active_session_id = None
            logger.info(f"ブラウザセッションを削除: {session_id}")
            return True
        return False
    
    def get_active_session(self) -> Optional[Dict[str, Any]]:
        """現在アクティブなセッションを取得"""
        if self.active_session_id:
            return self.get_session(self.active_session_id)
        return None
