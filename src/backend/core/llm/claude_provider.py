import logging
from typing import Optional, List, Dict, Any

from .base import LLMProvider, LLMResponse, ModelInfo

logger = logging.getLogger(__name__)


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API (支持官方及第三方中转)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.anthropic.com",
        model: str = "claude-sonnet-4-20250514"
    ):
        self.api_key = api_key or ""
        self.base_url = base_url
        self.model = model
        self._client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            logger.warning("Claude API key not set")
            return
        try:
            import anthropic
            self._client = anthropic.Anthropic(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info(f"Claude provider initialized: {self.model} at {self.base_url}")
        except ImportError:
            logger.error("anthropic package not installed")
        except Exception as e:
            logger.error(f"Failed to init Claude client: {e}")

    @property
    def provider_name(self) -> str:
        return "claude"

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="claude",
            max_context_tokens=200000,
            supports_tools=True,
            supports_vision=True,
            cost_per_1k_input=0.003 if "sonnet" in self.model else 0.015,
            cost_per_1k_output=0.015 if "sonnet" in self.model else 0.075
        )

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True
        except Exception as e:
            logger.warning(f"Claude health check failed: {e}")
            return False

    def chat(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> LLMResponse:
        if not self._client:
            return LLMResponse(
                content="抱歉，Claude 服务暂不可用",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )

        try:
            anthropic_messages = self._convert_messages(messages)

            extra_kwargs = {}
            if tools:
                extra_kwargs["tools"] = tools

            response = self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=anthropic_messages,
                **extra_kwargs
            )

            content = ""
            tool_calls = []

            for block in response.content:
                if block.type == "text":
                    content += block.text
                elif block.type == "tool_use":
                    tool_calls.append({
                        "id": block.id,
                        "name": block.name,
                        "arguments": block.input
                    })

            finish_reason = "tool_use" if tool_calls else "stop"

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage={"input": response.usage.input_tokens, "output": response.usage.output_tokens},
                model=self.model,
                finish_reason=finish_reason
            )

        except Exception as e:
            logger.error(f"Claude chat error: {e}")
            return LLMResponse(
                content=f"发生错误: {str(e)}",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )

    def _convert_messages(self, messages: List[Dict[str, Any]]) -> List[Dict]:
        """Convert messages to Anthropic format"""
        converted = []
        for msg in messages:
            role = msg.get("role", "user")
            if role == "assistant":
                role = "assistant"
            elif role == "system":
                role = "user"
                msg = {**msg, "content": f"[System: {msg['content']}]"}
            converted.append(msg)
        return converted