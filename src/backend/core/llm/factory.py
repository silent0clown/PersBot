import logging
from typing import Dict, Optional

from .base import LLMProvider
from .claude_provider import ClaudeProvider
from .openai_provider import OpenAIProvider
from .ollama_provider import OllamaProvider
from .router import ModelRouter, RouterConfig
from .token_budget import TokenBudgetManager, TokenBudgetConfig

logger = logging.getLogger(__name__)


class LLMProviderFactory:
    """LLM Provider 工厂类，根据配置创建和初始化所有 providers"""
    
    @staticmethod
    def create_providers(config_loader) -> Dict[str, LLMProvider]:
        """根据配置创建所有可用的 LLM Providers"""
        providers = {}
        
        # 获取各个 provider 的配置
        providers_config = {
            "ollama": {
                "base_url": config_loader.get("llm.base_url", "http://localhost:11434"),
                "model": config_loader.get("llm.model", "qwen3.5:2b"),
                "api_key": None  # Ollama 不需要 API key
            },
            "openai": {
                "base_url": config_loader.get("openai.base_url", "https://api.openai.com/v1"),
                "model": config_loader.get("openai.model", "gpt-4o-mini"),
                "api_key": config_loader.get("openai.api_key") or config_loader.get("llm.api_key") or None
            },
            "claude": {
                "base_url": config_loader.get("claude.base_url", "https://api.anthropic.com"),
                "model": config_loader.get("claude.model", "claude-sonnet-4-20250514"),
                "api_key": config_loader.get("claude.api_key") or config_loader.get("llm.api_key") or None
            }
        }
        
        # 从环境变量读取 API keys (优先级最高)
        import os
        if os.getenv("OPENAI_API_KEY"):
            providers_config["openai"]["api_key"] = os.getenv("OPENAI_API_KEY")
        if os.getenv("CLAUDE_API_KEY"):
            providers_config["claude"]["api_key"] = os.getenv("CLAUDE_API_KEY")
        
        # 创建 Ollama Provider (总是创建，本地免费)
        try:
            ollama_cfg = providers_config["ollama"]
            providers["ollama"] = OllamaProvider(
                base_url=ollama_cfg["base_url"],
                model=ollama_cfg["model"]
            )
            logger.info("Created Ollama provider")
        except Exception as e:
            logger.warning(f"Failed to create Ollama provider: {e}")
        
        # 创建 OpenAI Provider (如果有 API key)
        openai_cfg = providers_config["openai"]
        if openai_cfg["api_key"]:
            try:
                providers["openai"] = OpenAIProvider(
                    api_key=openai_cfg["api_key"],
                    base_url=openai_cfg["base_url"],
                    model=openai_cfg["model"]
                )
                logger.info("Created OpenAI provider")
            except Exception as e:
                logger.warning(f"Failed to create OpenAI provider: {e}")
        
        # 创建 Claude Provider (如果有 API key)
        claude_cfg = providers_config["claude"]
        if claude_cfg["api_key"]:
            try:
                providers["claude"] = ClaudeProvider(
                    api_key=claude_cfg["api_key"],
                    base_url=claude_cfg["base_url"],
                    model=claude_cfg["model"]
                )
                logger.info("Created Claude provider")
            except Exception as e:
                logger.warning(f"Failed to create Claude provider: {e}")
        
        return providers
    
    @staticmethod
    def create_router(
        providers: Dict[str, LLMProvider],
        config_loader
    ) -> ModelRouter:
        """创建模型路由器"""
        router_cfg = config_loader.get("router", {})
        cb_cfg = config_loader.get("circuit_breaker", {})
        
        config = RouterConfig(
            simple=router_cfg.get("simple", "ollama"),
            medium=router_cfg.get("medium", "openai"),
            complex=router_cfg.get("complex", "claude"),
            fallback=router_cfg.get("fallback", "ollama"),
            fallback_chain=router_cfg.get("fallback_chain", {
                "claude": ["openai", "ollama"],
                "openai": ["ollama"],
                "ollama": []
            })
        )
        
        return ModelRouter(
            providers=providers,
            config=config,
            failure_threshold=cb_cfg.get("failure_threshold", 3),
            cooldown_seconds=cb_cfg.get("cooldown_seconds", 300)
        )
    
    @staticmethod
    def create_token_budget_manager(config_loader) -> TokenBudgetManager:
        """创建 Token 预算管理器"""
        tb_cfg = config_loader.get("token_budget", {})
        
        config = TokenBudgetConfig(
            simple=tb_cfg.get("simple", 500),
            medium=tb_cfg.get("medium", 2000),
            complex=tb_cfg.get("complex", 4000),
            tool_intensive=tb_cfg.get("tool_intensive", 6000)
        )
        
        return TokenBudgetManager(config)


def create_llm_system(config_loader) -> tuple[Dict[str, LLMProvider], ModelRouter, TokenBudgetManager]:
    """创建完整的 LLM 系统 (providers + router + budget)"""
    providers = LLMProviderFactory.create_providers(config_loader)
    router = LLMProviderFactory.create_router(providers, config_loader)
    budget = LLMProviderFactory.create_token_budget_manager(config_loader)
    
    logger.info(f"LLM System initialized with {len(providers)} providers")
    return providers, router, budget