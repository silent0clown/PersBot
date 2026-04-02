import logging
from typing import Optional, Dict, Any, List, Callable
from dataclasses import dataclass, field
from datetime import datetime

from ..channels import PetRequest, PetResponse, ChannelAdapter
from ..channels.protocol import ChannelType
from ..persona import get_persona_manager, build_system_prompt
from ..memory.short_term import ShortTermMemory
from ..memory.long_term import LongTermMemory
from ..memory.retriever import MemoryRetriever
from ..voice_factory import create_stt_provider, create_tts_provider
from ..llm.factory import create_llm_system
from ..security.permission import PermissionManager
from ..tools.registry import ToolRegistry
from .orchestrator import AgentOrchestrator
from .loop_detector import LoopDetector
from ..tools.types import ToolResult

logger = logging.getLogger(__name__)


@dataclass
class AgentConfig:
    """Agent 配置"""
    stt_provider: str = "whisper_local"
    stt_model: str = "base"
    tts_provider: str = "edge_tts"
    tts_voice: str = "zh-CN-XiaoxiaoNeural"
    max_tool_iterations: int = 10


class AgentStore:
    """运行时状态管理"""

    def __init__(self, initial_state: Dict[str, Any] = None):
        self._state: Dict[str, Any] = initial_state or {}
        self._listeners: List[Callable] = []

    def get_state(self) -> Dict[str, Any]:
        return self._state.copy()

    def get(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set_state(self, partial: Dict[str, Any]):
        """合并更新状态"""
        self._state = {**self._state, **partial}
        for listener in self._listeners:
            listener(self._state)

    def subscribe(self, listener: Callable):
        self._listeners.append(listener)


class PetAgent:
    """电子宠物智能体主控引擎"""

    def __init__(self, config: AgentConfig):
        self.config = config

        self.store = AgentStore({
            "permission_mode": "default",
            "current_channel": None,
            "session_id": ""
        })

        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory()
        self.retriever = MemoryRetriever(self.long_memory)

        self.loop_detector = LoopDetector()

        self._stt_provider = None
        self._tts_provider = None

        self._orchestrator: Optional[AgentOrchestrator] = None

    def initialize(self, llm_config: dict, mcp_manager=None):
        """初始化 Agent"""
        self._stt_provider = create_stt_provider(llm_config)
        self._tts_provider = create_tts_provider(llm_config)

        if llm_config.get("provider"):
            from ..config_loader import get_config
            config_loader = get_config()
            llm_system = create_llm_system(config_loader)
            if llm_system:
                from ..llm.llm_client import LLMClient
                self._llm_client = LLMClient(llm_system=llm_system)
                self._orchestrator = AgentOrchestrator(self._llm_client, mcp_manager)

        logger.info("PetAgent initialized")

    async def handle(self, request: PetRequest) -> PetResponse:
        """处理请求的完整流程"""

        if request.message_type == "voice" and request.audio_data and self._stt_provider:
            request.content = await self._stt_provider.transcribe(request.audio_data)

        system_prompt = self._build_system_prompt(request.content)

        self.short_memory.add("user", request.content)

        if self._orchestrator:
            agent_response = await self._orchestrator.process(
                request.content,
                session_id=request.session_id
            )
            response_text = agent_response.content
        else:
            response_text = "抱歉，AI服务暂不可用"

        self._extract_and_store_memories(request.content, response_text)

        self._archive_chat(request, response_text)

        response = PetResponse(text=response_text)

        if request.channel == ChannelType.DESKTOP.value and self._tts_provider:
            response.audio_data = await self._tts_provider.synthesize(response_text)

        return response

    def _build_system_prompt(self, user_message: str) -> str:
        """构建系统提示词"""
        persona = get_persona_manager().get_persona()
        base_prompt = build_system_prompt(persona)
        return self.retriever.inject_memories(user_message, base_prompt)

    def _extract_and_store_memories(self, user_message: str, response: str):
        """记忆提取"""
        combined = f"用户: {user_message}\n助手: {response}"
        self.long_memory.store(
            content=combined,
            importance=0.5,
            source="conversation"
        )

    def _archive_chat(self, request: PetRequest, response: str):
        """对话归档"""
        self.short_memory.add("assistant", response)

    def set_permission_mode(self, mode: str):
        """设置权限模式"""
        self.store.set_state({"permission_mode": mode})

    def get_permission_mode(self) -> str:
        return self.store.get("permission_mode", "default")


_agent: Optional[PetAgent] = None


def get_pet_agent() -> PetAgent:
    global _agent
    if _agent is None:
        _agent = PetAgent(AgentConfig())
    return _agent


def set_pet_agent(agent: PetAgent):
    global _agent
    _agent = agent
