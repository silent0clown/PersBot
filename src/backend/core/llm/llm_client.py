import json
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from core.config import get_settings, persona_manager

logger = logging.getLogger(__name__)

llm_settings = get_settings().llm


@dataclass
class ToolCall:
    """工具调用"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class AgentTurn:
    """Agent 一轮对话的结果"""
    content: str = ""
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = ""  # "stop", "tool_calls", "max_iterations"


class LLMClient:
    def __init__(self):
        self.provider = llm_settings.provider
        self.model = llm_settings.model
        self.base_url = llm_settings.base_url
        self.api_key = llm_settings.api_key
        self.temperature = llm_settings.temperature
        self.max_tokens = llm_settings.max_tokens

        if self.provider == "openai":
            openai_cfg = get_settings().openai
            self.model = openai_cfg.model
            self.base_url = openai_cfg.base_url
            self.api_key = openai_cfg.api_key
        elif self.provider == "other":
            other_cfg = get_settings().other_api
            self.model = other_cfg.model
            self.base_url = other_cfg.base_url
            self.api_key = other_cfg.api_key

        self.client = None
        self._init_client()

    def _init_client(self):
        try:
            if self.provider == "ollama":
                from ollama import Client
                self.client = Client(host=self.base_url)
                try:
                    response = self.client.list()
                    model_list = response.models if hasattr(response, 'models') else []
                    model_names = [m.model for m in model_list]
                    if self.model not in model_names:
                        logger.warning(f"Model '{self.model}' not found in Ollama. Available: {model_names}")
                    else:
                        logger.info(f"Ollama connected: {self.model} at {self.base_url}")
                except Exception as conn_error:
                    logger.error(f"Failed to connect to Ollama at {self.base_url}: {conn_error}")
                    self.client = None
                    return
            elif self.provider in ["openai", "other"]:
                if not self.api_key:
                    logger.error(f"API key required for {self.provider}")
                    return
                from openai import OpenAI
                self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
                logger.info(f"OpenAI-compatible client: {self.model} at {self.base_url}")
            else:
                logger.error(f"Unsupported LLM provider: {self.provider}")
                return
        except ImportError as e:
            logger.error(f"Required package not installed: {e}")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")

    async def chat(self, message: str, system_prompt: str = None, history: List[Dict] = None) -> str:
        """普通对话（无工具调用）"""
        if not self.client:
            return "抱歉，AI服务暂不可用"

        messages = self._build_messages(system_prompt, history)
        messages.append({"role": "user", "content": message})

        try:
            if self.provider == "ollama" and callable(getattr(self.client, 'chat', None)):
                response = self.client.chat(model=self.model, messages=messages)
                return response['message']['content']
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Chat error: {e}")
            return f"发生错误: {str(e)}"

    async def chat_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        system_prompt: str = None,
        max_iterations: int = 5
    ) -> AgentTurn:
        """
        支持 function calling 的对话循环

        Args:
            messages: 对话历史 [{"role": "user", "content": "..."}, ...]
            tools: OpenAI 格式的工具列表
            system_prompt: 系统提示词
            max_iterations: 最大工具调用轮数

        Returns:
            AgentTurn: 包含最终回复和工具调用记录
        """
        if not self.client:
            return AgentTurn(content="抱歉，AI服务暂不可用")

        # 构建完整消息列表
        full_messages = self._build_messages(system_prompt)
        full_messages.extend(messages)

        all_tool_calls = []
        all_tool_results = []

        for iteration in range(max_iterations):
            try:
                turn = self._call_llm(full_messages, tools)

                if turn.finish_reason == "tool_calls" and turn.tool_calls:
                    all_tool_calls.extend(turn.tool_calls)

                    # 把 assistant 的 tool_calls 消息加入历史
                    assistant_msg = {
                        "role": "assistant",
                        "content": turn.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "type": "function",
                                "function": {
                                    "name": tc.name,
                                    "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                                }
                            }
                            for tc in turn.tool_calls
                        ]
                    }
                    full_messages.append(assistant_msg)

                    # 返回给调用者执行工具，由调用者把结果加入消息后继续
                    return AgentTurn(
                        content=turn.content,
                        tool_calls=turn.tool_calls,
                        finish_reason="tool_calls"
                    )
                else:
                    # LLM 给出了最终回答
                    return AgentTurn(
                        content=turn.content,
                        tool_calls=all_tool_calls,
                        finish_reason="stop"
                    )

            except Exception as e:
                logger.error(f"LLM call error (iteration {iteration}): {e}")
                if iteration == 0:
                    return AgentTurn(content=f"发生错误: {str(e)}")
                break

        return AgentTurn(
            content=all_tool_calls[-1].arguments.get("content", "") if all_tool_calls else "处理超时",
            tool_calls=all_tool_calls,
            finish_reason="max_iterations"
        )

    async def continue_with_tool_result(
        self,
        messages: List[Dict[str, Any]],
        tool_call_id: str,
        tool_result: Any,
        tools: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> AgentTurn:
        """
        在工具调用后继续对话

        Args:
            messages: 之前的对话历史（包含 tool_calls 的 assistant 消息）
            tool_call_id: 工具调用 ID
            tool_result: 工具返回结果
            tools: 工具列表
            system_prompt: 系统提示词
        """
        if not self.client:
            return AgentTurn(content="抱歉，AI服务暂不可用")

        full_messages = self._build_messages(system_prompt)
        full_messages.extend(messages)

        # 添加工具结果消息
        result_content = json.dumps(tool_result, ensure_ascii=False) if not isinstance(tool_result, str) else tool_result
        full_messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": result_content
        })

        try:
            turn = self._call_llm(full_messages, tools)

            if turn.finish_reason == "tool_calls" and turn.tool_calls:
                return AgentTurn(
                    content=turn.content,
                    tool_calls=turn.tool_calls,
                    finish_reason="tool_calls"
                )
            else:
                return AgentTurn(
                    content=turn.content,
                    finish_reason="stop"
                )
        except Exception as e:
            logger.error(f"Continue chat error: {e}")
            return AgentTurn(content=f"发生错误: {str(e)}")

    def _call_llm(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]] = None
    ) -> AgentTurn:
        """调用 LLM，支持 function calling"""
        if self.provider == "ollama":
            return self._call_ollama(messages, tools)
        else:
            return self._call_openai_compatible(messages, tools)

    def _call_ollama(self, messages: List[Dict], tools: List[Dict] = None) -> AgentTurn:
        """调用 Ollama"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "options": {
                "temperature": self.temperature,
                "num_predict": self.max_tokens
            }
        }

        if tools:
            # Ollama 的 tools 格式与 OpenAI 一致
            kwargs["tools"] = tools

        response = self.client.chat(**kwargs)
        message = response.get("message", {})

        content = message.get("content", "")
        raw_tool_calls = message.get("tool_calls", [])

        tool_calls = []
        if raw_tool_calls:
            for tc in raw_tool_calls:
                func = tc.get("function", {})
                args = func.get("arguments", {})
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                tool_calls.append(ToolCall(
                    id=tc.get("id", f"call_{id(tc)}"),
                    name=func.get("name", ""),
                    arguments=args
                ))

        finish_reason = "tool_calls" if tool_calls else "stop"
        return AgentTurn(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason
        )

    def _call_openai_compatible(self, messages: List[Dict], tools: List[Dict] = None) -> AgentTurn:
        """调用 OpenAI 兼容 API"""
        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        message = choice.message

        content = message.content or ""
        raw_tool_calls = message.tool_calls

        tool_calls = []
        if raw_tool_calls:
            for tc in raw_tool_calls:
                args = tc.function.arguments
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except json.JSONDecodeError:
                        args = {}

                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    arguments=args
                ))

        finish_reason = choice.finish_reason or ("tool_calls" if tool_calls else "stop")
        return AgentTurn(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason
        )

    def _build_messages(
        self,
        system_prompt: str = None,
        history: List[Dict] = None
    ) -> List[Dict]:
        """构建消息列表"""
        messages = []
        prompt = system_prompt or persona_manager.system_prompt
        if prompt:
            messages.append({"role": "system", "content": prompt})
        if history:
            messages.extend(history)
        return messages

    def get_available_models(self) -> List[str]:
        try:
            if hasattr(self.client, 'list'):
                models = self.client.list()
                return [m['name'] for m in models.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []
