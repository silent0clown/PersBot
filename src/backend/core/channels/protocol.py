from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class MessageType(str, Enum):
    TEXT = "text"
    VOICE = "voice"


class ChannelType(str, Enum):
    CLI = "cli"
    FEISHU = "feishu"
    WECHAT = "wechat"
    DESKTOP = "desktop"


@dataclass
class PetRequest:
    """统一请求格式 — 所有端发给 Agent Core 的消息"""
    user_id: str
    channel: str
    message_type: str = "text"
    content: str = ""
    audio_data: Optional[bytes] = None
    session_id: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "PetRequest":
        return PetRequest(
            user_id=data.get("user_id", ""),
            channel=data.get("channel", ""),
            message_type=data.get("message_type", "text"),
            content=data.get("content", ""),
            audio_data=data.get("audio_data"),
            session_id=data.get("session_id", ""),
            timestamp=data.get("timestamp", datetime.now()),
            metadata=data.get("metadata", {})
        )


@dataclass
class PetResponse:
    """统一响应格式 — Agent Core 返回给各端的消息"""
    text: str = ""
    audio_data: Optional[bytes] = None
    emotion: str = "neutral"
    actions: list = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "emotion": self.emotion,
            "actions": self.actions,
            "metadata": self.metadata
        }
