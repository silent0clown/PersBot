from typing import List, Dict, Any, Optional, Callable
from pydantic import BaseModel, Field
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import logging

logger = logging.getLogger(__name__)


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    role: MessageRole
    content: str
    tool_call_id: Optional[str] = None
    tool_name: Optional[str] = None
    timestamp: float = Field(default_factory=lambda: __import__('time').time())
    metadata: Dict[str, Any] = Field(default_factory=dict)
    importance: float = 1.0


@dataclass
class ContextWindow:
    messages: List[Message] = field(default_factory=list)
    max_tokens: int = 4096
    current_tokens: int = 0
    
    def add(self, message: Message):
        self.messages.append(message)
        self._recalculate_tokens()
        
    def _recalculate_tokens(self):
        self.current_tokens = sum(self._estimate_tokens(m.content) for m in self.messages)
        
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        return len(text) // 4
    
    def is_full(self) -> bool:
        return self.current_tokens >= self.max_tokens
    
    def clear(self):
        self.messages.clear()
        self.current_tokens = 0


class CompressionStrategy(str, Enum):
    NONE = "none"
    TRUNCATE = "truncate"
    SUMMARY = "summary"
    SLIDING_WINDOW = "sliding_window"
    IMPORTANCE_FILTER = "importance_filter"
    HYBRID = "hybrid"


class ContextCompactor:
    def __init__(
        self,
        max_tokens: int = 4096,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        summarize_fn: Optional[Callable[[List[Message]], str]] = None
    ):
        self.max_tokens = max_tokens
        self.strategy = strategy
        self.summarize_fn = summarize_fn
        self._window = ContextWindow(max_tokens=max_tokens)
        self._summary: Optional[str] = None
        
    def add_message(self, message: Message):
        if self.strategy == CompressionStrategy.NONE:
            self._window.add(message)
            return
            
        if self._window.is_full():
            self._compress()
            
        self._window.add(message)
        
    def _compress(self):
        if self.strategy == CompressionStrategy.TRUNCATE:
            self._truncate()
        elif self.strategy == CompressionStrategy.SLIDING_WINDOW:
            self._sliding_window()
        elif self.strategy == CompressionStrategy.IMPORTANCE_FILTER:
            self._importance_filter()
        elif self.strategy == CompressionStrategy.SUMMARY:
            self._summary_compress()
        elif self.strategy == CompressionStrategy.HYBRID:
            self._hybrid_compress()
            
    def _truncate(self):
        keep_count = len(self._window.messages) // 2
        self._window.messages = self._window.messages[-keep_count:]
        self._window._recalculate_tokens()
        
    def _sliding_window(self):
        keep_count = min(len(self._window.messages), 10)
        self._window.messages = self._window.messages[-keep_count:]
        self._window._recalculate_tokens()
        
    def _importance_filter(self):
        sorted_msgs = sorted(self._window.messages, key=lambda m: m.importance, reverse=True)
        keep = [m for m in sorted_msgs if m.importance >= 0.5]
        self._window.messages = keep[:20]
        self._window._recalculate_tokens()
        
    def _summary_compress(self):
        if self.summarize_fn:
            old_messages = self._window.messages[:-5]
            summary = self.summarize_fn(old_messages)
            self._summary = summary
            self._window.messages = self._window.messages[-5:]
            self._window.messages.insert(0, Message(
                role=MessageRole.SYSTEM,
                content=f"[Previous conversation summary]: {summary}"
            ))
            self._window._recalculate_tokens()
            
    def _hybrid_compress(self):
        self._sliding_window()
        if self._window.current_tokens > self.max_tokens * 0.8:
            self._importance_filter()
            
    def get_messages(self) -> List[Dict[str, Any]]:
        result = []
        if self._summary:
            result.append({"role": "system", "content": f"[Summary]: {self._summary}"})
            
        for msg in self._window.messages:
            result.append({
                "role": msg.role.value,
                "content": msg.content,
                **({"tool_call_id": msg.tool_call_id} if msg.tool_call_id else {}),
                **({"name": msg.tool_name} if msg.tool_name else {})
            })
        return result
    
    def get_token_count(self) -> int:
        return self._window.current_tokens
    
    def clear(self):
        self._window.clear()
        self._summary = None
        
    def get_stats(self) -> Dict[str, Any]:
        return {
            "strategy": self.strategy.value,
            "max_tokens": self.max_tokens,
            "current_tokens": self._window.current_tokens,
            "message_count": len(self._window.messages),
            "has_summary": self._summary is not None
        }


class ContextManager:
    def __init__(
        self,
        max_tokens: int = 4096,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID
    ):
        self._compactor = ContextCompactor(max_tokens, strategy)
        self._history: List[Message] = []
        self._session_id = hashlib.md5(str(time.time()).encode()).hexdigest()[:8]
        
    def add_user_message(self, content: str, importance: float = 1.0):
        msg = Message(role=MessageRole.USER, content=content, importance=importance)
        self._history.append(msg)
        self._compactor.add_message(msg)
        
    def add_assistant_message(self, content: str, importance: float = 1.0):
        msg = Message(role=MessageRole.ASSISTANT, content=content, importance=importance)
        self._history.append(msg)
        self._compactor.add_message(msg)
        
    def add_system_message(self, content: str):
        msg = Message(role=MessageRole.SYSTEM, content=content, importance=0.5)
        self._history.append(msg)
        self._compactor.add_message(msg)
        
    def add_tool_message(self, tool_name: str, tool_call_id: str, content: str):
        msg = Message(
            role=MessageRole.TOOL,
            content=content,
            tool_name=tool_name,
            tool_call_id=tool_call_id,
            importance=0.8
        )
        self._history.append(msg)
        self._compactor.add_message(msg)
        
    def get_context(self) -> List[Dict[str, Any]]:
        return self._compactor.get_messages()
    
    def get_full_history(self) -> List[Message]:
        return self._history.copy()
    
    def clear(self):
        self._history.clear()
        self._compactor.clear()
        
    def get_stats(self) -> Dict[str, Any]:
        return {
            "session_id": self._session_id,
            "total_messages": len(self._history),
            "compactor": self._compactor.get_stats()
        }


import time