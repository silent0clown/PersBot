from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional, List, Dict, Any


@dataclass
class ModelInfo:
    """模型能力描述"""
    name: str
    provider: str  # "claude" | "openai" | "ollama"
    max_context_tokens: int
    supports_tools: bool
    supports_vision: bool = False
    cost_per_1k_input: float = 0.0
    cost_per_1k_output: float = 0.0


@dataclass
class LLMResponse:
    """统一响应格式"""
    content: str
    tool_calls: List[Dict[str, Any]]
    usage: Dict[str, int]  # {"input": x, "output": y}
    model: str
    finish_reason: str  # "stop" | "tool_use" | "length"


class LLMProvider(ABC):
    """LLM提供者抽象基类"""

    @abstractmethod
    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """统一对话接口"""

    @abstractmethod
    def get_model_info(self) -> ModelInfo:
        """返回模型能力信息"""

    @abstractmethod
    def health_check(self) -> bool:
        """检查服务是否可用"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供者名称: claude | openai | ollama"""