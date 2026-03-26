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
from core.mcp import MCPManager, MCPServerInfo
from core.agent.orchestrator import AgentOrchestrator, set_orchestrator, get_orchestrator
from core.agent.permission import get_permission_manager, set_permission_manager
from core.agent.conversation import get_conversation_manager


class ColoredFormatter(logging.Formatter):
    """Custom formatter with colored log levels"""
    
    COLORS = {
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'RESET': '\033[0m'
    }
    
    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message


handler = logging.StreamHandler()
handler.setFormatter(ColoredFormatter(
    '%(asctime)s - [%(levelname)s] - %(message)s[%(filename)s:%(lineno)d]'
))
logging.basicConfig(level=logging.INFO, handlers=[handler])
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
    session_id: str = "default"

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
mcp_manager: Optional[MCPManager] = None
orchestrator: Optional[AgentOrchestrator] = None

async def initialize_components():
    global wake_word_detector, asr_engine, llm_client, tts_engine, app_controller, feishu_channel
    global mcp_manager, orchestrator
    
    logger.info("Initializing components...")
    alerts = []
    
    try:
        wake_word_detector = WakeWordDetector()
        logger.info("Wake word detector initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize wake word detector: {e}")
        alerts.append(f"语音唤醒初始化失败: {e}")
    
    try:
        asr_engine = ASREngine()
        logger.info("ASR engine initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize ASR engine: {e}")
        alerts.append(f"语音识别初始化失败: {e}")
    
    try:
        llm_client = LLMClient()
        if llm_client.client is None:
            logger.error("LLM client failed to connect to Ollama")
            alerts.append(f"连接 Ollama 失败，请确保 Ollama 服务正在运行")
        else:
            logger.info("LLM client initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize LLM client: {e}")
        alerts.append(f"LLM客户端初始化失败: {e}")
    
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
    
    # Initialize MCP Manager
    try:
        mcp_servers = settings.mcp.servers
        server_infos = [
            MCPServerInfo(
                name=s.name,
                enabled=s.enabled,
                command=s.command,
                args=s.args,
                env=s.env,
                url=s.url
            )
            for s in mcp_servers
        ]
        mcp_manager = MCPManager(server_infos)
        await mcp_manager.initialize()
        logger.info(f"MCP Manager initialized with {len(mcp_manager.get_connected_servers())} servers")
    except Exception as e:
        logger.warning(f"Failed to initialize MCP Manager: {e}")
    
    # Initialize Agent Orchestrator
    try:
        if llm_client:
            orchestrator = AgentOrchestrator(llm_client, mcp_manager)
            await orchestrator.initialize()
            set_orchestrator(orchestrator)
            logger.info("Agent Orchestrator initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize Agent Orchestrator: {e}")
        alerts.append(f"Agent协调器初始化失败: {e}")
    
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
            
            feishu_channel.on_message(handle_feishu_message)
            feishu_channel.start()
            
            logger.info("Feishu channel initialized")
        except Exception as e:
            logger.warning(f"Failed to initialize Feishu channel: {e}")
            alerts.append(f"飞书通道初始化失败: {e}")
    else:
        logger.warning("Feishu channel not enabled or missing app_id/app_secret")
    
    if alerts:
        for alert in alerts:
            await manager.send_message({"type": "alert", "message": alert})


async def handle_feishu_message(message):
    """Handle incoming Feishu message"""
    global feishu_channel, orchestrator
    try:
        text = message.get_text()
        if not text:
            return
        
        logger.info(f"Received Feishu message from {message.sender_id}: {text}")
        
        # 使用飞书 sender_id 作为 session_id
        session_id = f"feishu_{message.sender_id}"
        
        if orchestrator:
            agent_response = await orchestrator.process(text, session_id=session_id)
            response_text = agent_response.content
        elif llm_client:
            response_text = await llm_client.chat(text)
        else:
            response_text = "抱歉，AI服务暂不可用"
        
        if feishu_channel:
            feishu_channel.reply_text(
                message_id=message.message_id,
                text=response_text
            )
            logger.info(f"Sent Feishu reply to message {message.message_id}")
    except Exception as e:
        logger.error(f"Error handling Feishu message: {e}")


@app.on_event("startup")
async def startup_event():
    await initialize_components()
    
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
        
        session_id = request.session_id or "default"
        
        # 使用 Agent Orchestrator 处理消息
        if orchestrator:
            agent_response = await orchestrator.process(
                request.message,
                session_id=session_id
            )
            response_content = agent_response.content
            
            if agent_response.tool_calls:
                logger.info(f"Tool calls: {agent_response.tool_calls}")
            if agent_response.tool_results:
                logger.info(f"Tool results: {agent_response.tool_results}")
        elif llm_client:
            response_content = await llm_client.chat(request.message)
        else:
            response_content = "抱歉，AI服务暂不可用"
        
        await manager.send_message({
            "type": "response",
            "content": response_content
        })
        
        logger.info(f"Chat response: {response_content[:100]}...")
        return {"response": response_content}
    except Exception as e:
        logger.error(f"Chat error: {e}")
        await manager.send_message({"type": "error", "message": str(e)})
        return {"error": str(e)}


class PermissionResponse(BaseModel):
    request_id: str
    approved: bool
    remember: bool = False


@app.post("/api/permission/respond")
async def respond_to_permission(response: PermissionResponse):
    """处理权限请求响应"""
    permission_manager = get_permission_manager()
    permission_manager.handle_response(
        response.request_id,
        response.approved,
        response.remember
    )
    return {"success": True}

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
            "feishu": feishu_channel is not None,
            "mcp": mcp_manager is not None,
            "orchestrator": orchestrator is not None
        },
        "mcp_servers": mcp_manager.get_connected_servers() if mcp_manager else [],
        "tools": orchestrator.registry.list_tool_names() if orchestrator else []
    }

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=settings.server.host,
        port=settings.server.port,
        reload=settings.server.reload
    )
