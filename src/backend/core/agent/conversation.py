"""
会话管理器 - 管理多轮对话状态
"""
import logging
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class SessionState(Enum):
    """会话状态"""
    IDLE = "idle"                       # 空闲
    AWAITING_INSTALL = "awaiting_install"   # 等待用户确认安装
    AWAITING_API_KEY = "awaiting_api_key"   # 等待用户提供 API Key
    PROCESSING = "processing"           # 处理中


@dataclass
class PendingInstall:
    """待安装信息"""
    tool_id: str
    tool_name: str
    missing_env: List[Dict[str, str]] = field(default_factory=list)
    waiting_for_key: Optional[str] = None  # 正在等待的环境变量名
    original_message: str = ""  # 用户原始请求


@dataclass
class ConversationSession:
    """对话会话"""
    session_id: str
    messages: List[Dict[str, Any]] = field(default_factory=list)
    state: SessionState = SessionState.IDLE
    pending_install: Optional[PendingInstall] = None
    context: Dict[str, Any] = field(default_factory=dict)  # 上下文信息
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    turn_count: int = 0

    def add_message(self, role: str, content: str, tool_calls: List[Dict] = None, tool_results: List[Dict] = None):
        """添加消息到历史"""
        msg = {"role": role, "content": content}
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if tool_results:
            msg["tool_results"] = tool_results
        self.messages.append(msg)
        self.updated_at = datetime.now()
        if role == "user":
            self.turn_count += 1

    def get_history(self, max_messages: int = 20) -> List[Dict]:
        """获取对话历史（限制长度）"""
        return self.messages[-max_messages:]

    def clear(self):
        """清除会话"""
        self.messages.clear()
        self.state = SessionState.IDLE
        self.pending_install = None
        self.context.clear()
        self.turn_count = 0
        self.updated_at = datetime.now()


class ConversationManager:
    """会话管理器"""

    def __init__(self, max_history: int = 20, session_ttl_hours: int = 24):
        self._sessions: Dict[str, ConversationSession] = {}
        self._max_history = max_history
        self._session_ttl_hours = session_ttl_hours

    def get_or_create_session(self, session_id: str) -> ConversationSession:
        """获取或创建会话"""
        if session_id not in self._sessions:
            self._sessions[session_id] = ConversationSession(session_id=session_id)
            logger.info(f"Created new session: {session_id}")
        return self._sessions[session_id]

    def get_session(self, session_id: str) -> Optional[ConversationSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    def add_user_message(self, session_id: str, content: str) -> ConversationSession:
        """添加用户消息"""
        session = self.get_or_create_session(session_id)
        session.add_message("user", content)
        return session

    def add_assistant_message(
        self,
        session_id: str,
        content: str,
        tool_calls: List[Dict] = None,
        tool_results: List[Dict] = None
    ):
        """添加助手消息"""
        session = self.get_or_create_session(session_id)
        session.add_message("assistant", content, tool_calls, tool_results)

    def set_state(self, session_id: str, state: SessionState, **kwargs):
        """设置会话状态"""
        session = self.get_or_create_session(session_id)
        session.state = state
        for key, value in kwargs.items():
            if hasattr(session, key):
                setattr(session, key, value)

    def set_pending_install(self, session_id: str, pending: PendingInstall):
        """设置待安装信息"""
        session = self.get_or_create_session(session_id)
        session.pending_install = pending
        session.state = SessionState.AWAITING_INSTALL

    def clear_pending_install(self, session_id: str):
        """清除待安装信息"""
        session = self.get_or_create_session(session_id)
        session.pending_install = None
        session.state = SessionState.IDLE

    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self._sessions:
            self._sessions[session_id].clear()
            logger.info(f"Cleared session: {session_id}")

    def remove_session(self, session_id: str):
        """移除会话"""
        self._sessions.pop(session_id, None)

    def get_all_session_ids(self) -> List[str]:
        """获取所有会话 ID"""
        return list(self._sessions.keys())


# 全局实例
_conversation_manager: Optional[ConversationManager] = None


def get_conversation_manager() -> ConversationManager:
    """获取全局会话管理器"""
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager


def set_conversation_manager(manager: ConversationManager):
    """设置全局会话管理器"""
    global _conversation_manager
    _conversation_manager = manager
