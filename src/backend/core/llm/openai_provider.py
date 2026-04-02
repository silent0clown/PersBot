import logging
from typing import Optional, List, Dict, Any

from .base import LLMProvider, LLMResponse, ModelInfo

logger = logging.getLogger(__name__)


class OpenAIProvider(LLMProvider):
    """OpenAI API (支持官方/Azure/第三方中转/本地兼容服务)"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini"
    ):
        self.api_key = api_key or ""
        self.base_url = base_url
        self.model = model
        self._client = None
        self._init_client()

    def _init_client(self):
        if not self.api_key:
            logger.warning("OpenAI API key not set")
            return
        try:
            from openai import OpenAI
            self._client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"OpenAI provider initialized: {self.model} at {self.base_url}")
        except ImportError:
            logger.error("openai package not installed")
        except Exception as e:
            logger.error(f"Failed to init OpenAI client: {e}")

    @property
    def provider_name(self) -> str:
        return "openai"

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="openai",
            max_context_tokens=128000 if "gpt-4" in self.model else 16385,
            supports_tools=True,
            supports_vision=True if "gpt-4" in self.model else False,
            cost_per_1k_input=0.003 if "mini" in self.model else 0.01,
            cost_per_1k_output=0.003 if "mini" in self.model else 0.03
        )

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.chat.completions.create(
                model=self.model,
                max_tokens=1,
                messages=[{"role": "user", "content": "hi"}]
            )
            return True
        except Exception as e:
            logger.warning(f"OpenAI health check failed: {e}")
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
                content="抱歉，OpenAI 服务暂不可用",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }

            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"

            response = self._client.chat.completions.create(**kwargs)
            choice = response.choices[0]
            message = choice.message

            content = message.content or ""
            tool_calls = []

            if message.tool_calls:
                for tc in message.tool_calls:
                    args = tc.function.arguments
                    if isinstance(args, str):
                        import json
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}

                    tool_calls.append({
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": args
                    })

            finish_reason = choice.finish_reason or ("tool_use" if tool_calls else "stop")

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage={
                    "input": response.usage.prompt_tokens if response.usage else 0,
                    "output": response.usage.completion_tokens if response.usage else 0
                },
                model=self.model,
                finish_reason=finish_reason
            )

        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            return LLMResponse(
                content=f"发生错误: {str(e)}",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )