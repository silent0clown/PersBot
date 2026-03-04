import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from core.wake_word.wake_word_detector import WakeWordDetector
from core.asr.asr_engine import ASREngine
from core.llm.llm_client import LLMClient
from core.tts.tts_engine import TTSEngine
from core.controller.app_controller import AppController

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

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

async def initialize_components():
    global wake_word_detector, asr_engine, llm_client, tts_engine, app_controller
    
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

@app.on_event("startup")
async def startup_event():
    await initialize_components()

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
            elif message.get("type") == "stop_wake"):
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
        
        if tts_engine:
            audio_data = await tts_engine.synthesize(response)
            await manager.send_message({
                "type": "audio",
                "data": audio_data
            })
        
        await manager.send_message({"type": "idle"})
        
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
            "controller": app_controller is not None
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
