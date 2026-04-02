import asyncio
import json
import logging
from typing import Dict, Any, Callable, Optional
from fastapi import FastAPI, Request
import lark_oapi as lark
from lark_oapi.api.im.v1 import *
import threading

from ..protocol import PetRequest, PetResponse, ChannelType

logger = logging.getLogger(__name__)


class FeishuMessage:
    def __init__(self, event: Dict[str, Any]):
        self.sender_id = event.get("sender", {}).get("sender_id", {}).get("open_id", "")
        self.user_id = self.sender_id
        self.message_id = event.get("message", {}).get("message_id", "")
        self.message_type = event.get("message", {}).get("message_type", "text")
        self.chat_id = event.get("message", {}).get("chat_id", "")
        self.chat_type = event.get("message", {}).get("chat_type", "")
        self.content = event.get("message", {}).get("content", "{}")
        self._raw = event
        
    def get_text(self) -> str:
        try:
            content = json.loads(self.content)
            return content.get("text", "")
        except:
            return self.content

    def to_pet_request(self) -> PetRequest:
        """转换为统一请求格式"""
        return PetRequest(
            user_id=self.user_id,
            channel=ChannelType.FEISHU.value,
            message_type=self.message_type,
            content=self.get_text(),
            session_id=self.chat_id,
            metadata={
                "message_id": self.message_id,
                "chat_id": self.chat_id,
                "chat_type": self.chat_type
            }
        )


class FeishuChannel:
    def __init__(
        self,
        app_id: str,
        app_secret: str,
        verification_token: str = None,
        encrypt_key: str = None,
        domain: str = "https://open.feishu.cn"
    ):
        self.app_id = app_id
        self.app_secret = app_secret
        self.verification_token = verification_token
        self.encrypt_key = encrypt_key
        self.domain = domain
        self._message_handler: Optional[Callable] = None
        self._client: Optional[lark.Client] = None
        self._ws_client: Optional[lark.ws.Client] = None
        self._event_handler: Optional[lark.EventDispatcherHandler] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._processed_messages: set = set()
        self._lock = threading.Lock()

    @property
    def channel_name(self) -> str:
        return ChannelType.FEISHU.value
        
    def _init_client(self):
        """Initialize Feishu client"""
        self._client = lark.Client.builder() \
            .app_id(self.app_id) \
            .app_secret(self.app_secret) \
            .domain(self.domain) \
            .build()
            
    def _init_event_handler(self):
        """Initialize event handler for WebSocket"""
        self._event_handler = lark.EventDispatcherHandler.builder(
            self.verification_token,
            self.encrypt_key
        ).register_p2_im_message_receive_v1(self._on_message_receive) \
         .build()
         
    def _on_message_receive(self, event: P2ImMessageReceiveV1):
        """Handle message receive event"""
        try:
            message_id = event.event.message.message_id if event.event.message else ""
            
            with self._lock:
                if message_id in self._processed_messages:
                    logger.debug(f"Skipping duplicate message: {message_id}")
                    return
                self._processed_messages.add(message_id)
                if len(self._processed_messages) > 1000:
                    self._processed_messages.clear()
            
            event_data = {
                "sender": {
                    "sender_id": {
                        "open_id": event.event.sender.sender_id.open_id if event.event.sender else ""
                    }
                },
                "message": {
                    "message_id": message_id,
                    "message_type": event.event.message.message_type if event.event.message else "text",
                    "chat_id": event.event.message.chat_id if event.event.message else "",
                    "chat_type": event.event.message.chat_type if event.event.message else "",
                    "content": event.event.message.content if event.event.message else "{}"
                }
            }
            
            message = FeishuMessage(event_data)
            
            if self._message_handler:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        asyncio.create_task(self._message_handler(message))
                    else:
                        loop.run_until_complete(self._message_handler(message))
                except RuntimeError:
                    asyncio.run(self._message_handler(message))
                
        except Exception as e:
            logger.error(f"Error handling message event: {e}")
            
    def _init_ws_client(self):
        """Initialize WebSocket client"""
        self._ws_client = lark.ws.Client(
            app_id=self.app_id,
            app_secret=self.app_secret,
            log_level=lark.LogLevel.DEBUG,
            event_handler=self._event_handler,
            domain=self.domain
        )
        
    def start(self):
        """Start WebSocket client in background thread"""
        if self._running:
            logger.warning("Feishu channel already running")
            return
            
        try:
            self._init_client()
            self._init_event_handler()
            self._init_ws_client()
            
            self._running = True
            self._thread = threading.Thread(target=self._run_ws, daemon=True)
            self._thread.start()
            
            logger.info("Feishu WebSocket client started")
        except Exception as e:
            logger.error(f"Failed to start Feishu channel: {e}")
            self._running = False
            
    def _run_ws(self):
        """Run WebSocket client"""
        try:
            self._ws_client.start()
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            self._running = False
            
    def stop(self):
        """Stop WebSocket client"""
        if self._ws_client:
            self._ws_client.stop()
        self._running = False
        logger.info("Feishu channel stopped")
        
    def on_message(self, handler: Callable):
        """Set message handler"""
        self._message_handler = handler
        
    def receive(self, raw_input: Any) -> PetRequest:
        """将飞书消息转为统一请求"""
        if isinstance(raw_input, FeishuMessage):
            return raw_input.to_pet_request()
        return PetRequest(
            user_id="",
            channel=self.channel_name,
            content=""
        )
        
    def send(self, response: PetResponse):
        """将统一响应转为飞书消息并发出"""
        if not self._client:
            logger.error("Feishu client not initialized")
            return
        
        metadata = response.metadata or {}
        receive_id = metadata.get("user_id")
        message_id = metadata.get("message_id")
        
        if message_id:
            self.reply_text(message_id, response.text)
        elif receive_id:
            self.send_text(receive_id, response.text)
        
    def send_text(self, receive_id: str, text: str, receive_id_type: str = "open_id") -> bool:
        """Send text message"""
        if not self._client:
            logger.error("Feishu client not initialized")
            return False
            
        try:
            content = json.dumps({"text": text})
            
            request_builder = CreateMessageRequest.builder() \
                .receive_id_type(receive_id_type)
                
            request = request_builder.build()
            
            message_body = CreateMessageRequestBody.builder() \
                .receive_id(receive_id) \
                .msg_type("text") \
                .content(content) \
                .build()
                
            response = self._client.im.v1.message.create(
                request,
                request_body=message_body
            )
            
            if response.success():
                logger.info(f"Message sent to {receive_id}")
                return True
            else:
                logger.error(f"Failed to send message: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False
            
    def reply_text(self, message_id: str, text: str) -> bool:
        """Reply to a message"""
        if not self._client:
            logger.error("Feishu client not initialized")
            return False
            
        try:
            content = json.dumps({"text": text})
            
            message_body = ReplyMessageRequestBody.builder() \
                .msg_type("text") \
                .content(content) \
                .build()
            
            request = ReplyMessageRequest.builder() \
                .message_id(message_id) \
                .request_body(message_body) \
                .build()
                
            response = self._client.im.v1.message.reply(request)
            
            if response.success():
                logger.info(f"Reply sent to message {message_id}")
                return True
            else:
                logger.error(f"Failed to reply: {response.code} - {response.msg}")
                return False
                
        except Exception as e:
            logger.error(f"Error replying to message: {e}")
            return False
            
    def register_routes(self, app: FastAPI):
        """Register health check route (WebSocket doesn't need webhook routes)"""
        
        @app.get("/feishu/health")
        async def feishu_health():
            return {
                "status": "ok" if self._running else "stopped",
                "connection": "websocket"
            }
