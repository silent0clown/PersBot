import logging
import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .base import LLMProvider
from .circuit_breaker import CircuitBreaker, CircuitState

logger = logging.getLogger(__name__)


@dataclass
class RouterConfig:
    """模型路由配置"""
    simple: str = "ollama"
    medium: str = "openai"
    complex: str = "claude"
    fallback: str = "ollama"
    fallback_chain: Dict[str, List[str]] = None

    def __post_init__(self):
        if self.fallback_chain is None:
            self.fallback_chain = {
                "claude": ["openai", "ollama"],
                "openai": ["ollama"],
                "ollama": []
            }

    def get_provider_for_level(self, level: str) -> str:
        level_map = {
            "simple": self.simple,
            "medium": self.medium,
            "complex": self.complex
        }
        return level_map.get(level, self.fallback)


class ModelRouter:
    """根据任务复杂度选择模型"""

    def __init__(
        self,
        providers: Dict[str, LLMProvider],
        config: RouterConfig,
        failure_threshold: int = 3,
        cooldown_seconds: int = 300
    ):
        self.providers = providers
        self.config = config

        self.breakers = {
            name: CircuitBreaker(
                name,
                failure_threshold=failure_threshold,
                cooldown_seconds=cooldown_seconds
            )
            for name in providers
        }

        logger.info(f"ModelRouter initialized with providers: {list(providers.keys())}")

    def route(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Optional[LLMProvider]:
        explicit = self._check_user_override(messages)
        if explicit and explicit.provider_name in self.providers:
            if self.breakers[explicit.provider_name].allow_request():
                logger.info(f"User explicitly requested: {explicit.provider_name}")
                return explicit

        level = self._assess_complexity(messages, tools)
        target_name = self.config.get_provider_for_level(level)
        logger.debug(f"Assessed complexity: {level}, target provider: {target_name}")

        return self._with_fallback(target_name)

    def _check_user_override(self, messages: List[Dict[str, Any]]) -> Optional[LLMProvider]:
        if not messages:
            return None

        last_msg = messages[-1].get("content", "")

        if "@claude" in last_msg.lower() and "claude" in self.providers:
            return self.providers["claude"]
        if "@openai" in last_msg.lower() or "@gpt" in last_msg.lower():
            if "openai" in self.providers:
                return self.providers["openai"]
        if "@local" in last_msg.lower() or "@ollama" in last_msg.lower():
            if "ollama" in self.providers:
                return self.providers["ollama"]

        return None

    def _assess_complexity(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]]
    ) -> str:
        if tools:
            return "complex"

        last_msg = messages[-1].get("content", "") if messages else ""
        if len(last_msg) < 20 and not self._has_question_or_command(last_msg):
            return "simple"

        total_tokens = self._estimate_tokens(messages)
        if total_tokens > 2000:
            return "complex"

        return "medium"

    def _has_question_or_command(self, text: str) -> bool:
        question_patterns = [
            r"什么|怎么|为什么|如何|哪|谁的|多少|几",
            r"who|what|why|how|when|where|which",
            r"\?|？"
        ]
        command_patterns = [
            r"帮我|请|给我|帮我做",
            r"execute|run|do|make|create|write|read"
        ]

        text_lower = text.lower()
        for pattern in question_patterns + command_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:
        total = 0
        for msg in messages:
            content = msg.get("content", "")
            total += len(content) // 4
        return total

    def _with_fallback(self, target_name: str) -> Optional[LLMProvider]:
        chain = self.config.fallback_chain.get(target_name, [self.config.fallback])

        if target_name in self.providers:
            breaker = self.breakers[target_name]
            if breaker.allow_request():
                return self.providers[target_name]

        for fallback_name in chain:
            if fallback_name in self.providers:
                breaker = self.breakers[fallback_name]
                if breaker.allow_request():
                    logger.info(f"Falling back from {target_name} to {fallback_name}")
                    return self.providers[fallback_name]

        logger.warning(f"All providers unavailable, target was: {target_name}")
        return None

    def report_result(self, provider_name: str, success: bool):
        if provider_name not in self.breakers:
            return

        breaker = self.breakers[provider_name]
        if success:
            breaker.record_success()
        else:
            breaker.record_failure()

    def get_health_status(self) -> List[Dict]:
        status = []
        for name, breaker in self.breakers.items():
            info = breaker.get_status()
            if name in self.providers:
                provider = self.providers[name]
                info["model"] = provider.model if hasattr(provider, 'model') else "unknown"
                info["healthy"] = provider.health_check()
            status.append(info)
        return status