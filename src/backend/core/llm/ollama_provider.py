import logging
from typing import Optional, List, Dict, Any

from .base import LLMProvider, LLMResponse, ModelInfo

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    """Ollama 本地模型"""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "qwen2.5:7b"
    ):
        self.base_url = base_url
        self.model = model
        self._client = None
        self._init_client()

    def _init_client(self):
        try:
            from ollama import Client
            self._client = Client(host=self.base_url)
            try:
                response = self._client.list()
                models = response.models if hasattr(response, 'models') else []
                model_names = [m.model for m in models]
                if self.model not in model_names:
                    logger.warning(f"Model '{self.model}' not found. Available: {model_names}")
                else:
                    logger.info(f"Ollama provider initialized: {self.model} at {self.base_url}")
            except Exception as conn_error:
                logger.error(f"Failed to connect to Ollama at {self.base_url}: {conn_error}")
                self.client = None
        except ImportError:
            logger.error("ollama package not installed")
        except Exception as e:
            logger.error(f"Failed to init Ollama client: {e}")

    @property
    def provider_name(self) -> str:
        return "ollama"

    def get_model_info(self) -> ModelInfo:
        return ModelInfo(
            name=self.model,
            provider="ollama",
            max_context_tokens=8192,
            supports_tools=False,
            supports_vision=False,
            cost_per_1k_input=0.0,
            cost_per_1k_output=0.0
        )

    def health_check(self) -> bool:
        if not self._client:
            return False
        try:
            self._client.chat(
                model=self.model,
                messages=[{"role": "user", "content": "hi"}],
                options={"num_predict": 1}
            )
            return True
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
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
                content="抱歉，Ollama 服务暂不可用",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )

        try:
            kwargs = {
                "model": self.model,
                "messages": messages,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }

            response = self._client.chat(**kwargs)
            message = response.get("message", {})

            content = message.get("content", "")
            tool_calls = []

            raw_tool_calls = message.get("tool_calls", [])
            if raw_tool_calls:
                import json
                for tc in raw_tool_calls:
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except json.JSONDecodeError:
                            args = {}

                    tool_calls.append({
                        "id": tc.get("id", f"call_{id(tc)}"),
                        "name": func.get("name", ""),
                        "arguments": args
                    })

            finish_reason = "tool_use" if tool_calls else "stop"

            estimated_input = sum(len(m.get("content", "")) // 4 for m in messages)
            estimated_output = len(content) // 4

            return LLMResponse(
                content=content,
                tool_calls=tool_calls,
                usage={"input": estimated_input, "output": estimated_output},
                model=self.model,
                finish_reason=finish_reason
            )

        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            return LLMResponse(
                content=f"发生错误: {str(e)}",
                tool_calls=[],
                usage={"input": 0, "output": 0},
                model=self.model,
                finish_reason="error"
            )