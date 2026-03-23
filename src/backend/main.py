import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from core.config import get_settings
from core.wake_word.wake_word_detector import WakeWordDetector
from core.asr.asr_engine import ASREngine
from core.llm.llm_client import LLMClient
from core.tts.tts_engine import TTSEngine
from core.controller.app_controller import AppController
from core.channels import FeishuChannel

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - %(name)s - %(message)s'
)
logger = logging.getLogger(__name__)

settings = get_settings()
app = FastAPI(title="PersBot Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_message(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"Error sending message: {e}")

manager = ConnectionManager()

wake_word_detector: Optional[WakeWordDetector] = None
asr_engine: Optional[ASREngine] = None
llm_client: Optional[LLMClient] = None
tts_engine: Optional[TTSEngine] = None
app_controller: Optional[AppController] = None
feishu_channel: Optional[FeishuChannel] = None

async def initialize_components():
    global wake_word_detector, asr_engine, llm_client, tts_engine, app_controller, feishu_channel
    
    logger.info("Initializing components...")
    
    try:
        wake_word_detector = WakeWordDetector()
        logger.info("Wake word detector initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize wake word detector: {e}")
    
    try:
        asr_engine = ASREngine()
        logger.info("ASR engine initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize ASR engine: {e}")
    
    try:
        llm_client = LLMClient()
        logger.info("LLM client initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM client: {e}")
    
    try:
        tts_engine = TTSEngine()
        logger.info("TTS engine initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize TTS engine: {e}")
    
    try:
        app_controller = AppController()
        logger.info("App controller initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize app controller: {e}")
    
    # Initialize Feishu channel if enabled
    logger.info(f"Feishu config - enabled: {settings.feishu.enabled}, app_id: {settings.feishu.app_id[:8] if settings.feishu.app_id else 'None'}...")
    
    if settings.feishu.enabled and settings.feishu.app_id and settings.feishu.app_secret:
        try:
            logger.info("Initializing Feishu channel...")
            feishu_channel = FeishuChannel(
                app_id=settings.feishu.app_id,
                app_secret=settings.feishu.app_secret,
                verification_token=settings.feishu.verification_token,
                encrypt_key=settings.feishu.encrypt_key,
                domain=settings.feishu.domain
            )
            
            # Set message handler
            feishu_channel.on_message(handle_feishu_message)
            
            # Start WebSocket client
            feishu_channel.start()
            
            logger.info("Feishu channel initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Feishu channel: {e}")
    else:
        logger.warning("Feishu channel not enabled or missing app_id/app_secret")

async def handle_feishu_message(message):
    """Handle incoming Feishu message"""
    global feishu_channel
    try:
        text = message.get_text()
        if not text:
            return
        
        logger.info(f"Received Feishu message from {message.sender_id}: {text}")
        
        # Process message with LLM
        if llm_client:
            response = await llm_client.chat(text)
            
            # Send response back via Feishu (reply to original message)
            if feishu_channel:
                feishu_channel.reply_text(
                    message_id=message.message_id,
                    text=response
                )
                logger.info(f"Sent Feishu reply to message {message.message_id}")
    except Exception as e:
        logger.error(f"Error handling Feishu message: {e}")


@app.on_event("startup")
async def startup_event():
    await initialize_components()
    
    # Register Feishu webhook routes if enabled
    if feishu_channel:
        feishu_channel.register_routes(app)
        logger.info(f"Feishu webhook registered at {settings.feishu.webhook_path}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "audio":
                if wake_word_detector:
                    is_wake = wake_word_detector.detect(message.get("data"))
                    if is_wake:
                        await manager.send_message({"type": "wake_word"})
            elif message.get("type") == "stop_wake":
                if wake_word_detector:
                    wake_word_detector.stop()
                    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

@app.post("/api/chat")
async def chat(request: ChatRequest):
    try:
        await manager.send_message({"type": "thinking"})
        
        response = await llm_client.chat(request.message)
        
        await manager.send_message({
            "type": "response",
            "content": response
        })
        
        # 仅返回文本响应，不触发TTS
        logger.info(f"Chat response: {response}")
        return {"response": response}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        await manager.send_message({"type": "error", "message": str(e)})
        return {"error": str(e)}

@app.post("/api/control")
async def control_app(command: str):
    try:
        if app_controller:
            result = await app_controller.execute(command)
            return {"success": True, "result": result}
        return {"error": "Controller not initialized"}
    except Exception as e:
        logger.error(f"Control error: {e}")
        return {"error": str(e)}

@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "components": {
            "wake_word": wake_word_detector is not None,
            "asr": asr_engine is not None,
            "llm": llm_client is not None,
            "tts": tts_engine is not None,
            "controller": app_controller is not None,
            "feishu": feishu_channel is not None
        }
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload
    )
