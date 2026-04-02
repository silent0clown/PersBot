from abc import ABC, abstractmethod
from typing import Any, Optional, Callable
import logging

from .protocol import PetRequest, PetResponse

logger = logging.getLogger(__name__)


class ChannelAdapter(ABC):
    """各端适配器基类"""

    def __init__(self):
        self._message_handler: Optional[Callable] = None
        self._running = False

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """渠道名称"""

    @abstractmethod
    def receive(self, raw_input: Any) -> PetRequest:
        """将平台原始输入转为统一请求"""

    @abstractmethod
    def send(self, response: PetResponse):
        """将统一响应转为平台格式并发出"""

    @abstractmethod
    def start(self):
        """启动监听 (webhook/轮询/GUI事件循环)"""

    @abstractmethod
    def stop(self):
        """停止监听"""

    def on_message(self, handler: Callable):
        """设置消息处理器"""
        self._message_handler = handler

    async def _handle_message(self, request: PetRequest):
        """内部消息处理"""
        if self._message_handler:
            try:
                await self._message_handler(request)
            except Exception as e:
                logger.error(f"Error handling message: {e}")

    def is_running(self) -> bool:
        return self._running

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} channel={self.channel_name}>"
