import os
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent.parent


class ConfigLoader:
    """统一配置加载器：合并 .env (敏感) + config.json (非敏感)"""
    
    _instance: Optional["ConfigLoader"] = None
    _config: Dict[str, Any] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._load()
        return cls._instance
    
    def _load(self):
        # 1. 加载 .env (敏感信息)
        env_path = BASE_DIR / ".env"
        if env_path.exists():
            load_dotenv(env_path)
            logger.info(f"Loaded .env from {env_path}")
        else:
            logger.warning(f".env not found at {env_path}")
        
        # 2. 加载 config.json (非敏感配置)
        config_path = BASE_DIR / "config" / "config.json"
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                self._config = json.load(f)
            logger.info(f"Loaded config.json from {config_path}")
        else:
            logger.warning(f"config.json not found at {config_path}")
            self._config = {}
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点号分隔的路径，如 'llm.model'"""
        keys = key.split(".")
        value = self._config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default
    
    def get_all(self) -> Dict[str, Any]:
        """获取完整配置"""
        return self._config.copy()
    
    def reload(self):
        """重新加载配置"""
        self._load()


# 全局配置实例
_config_loader = ConfigLoader()


def get_config() -> ConfigLoader:
    """获取配置加载器实例"""
    return _config_loader


# ============== 配置数据类 ==============

@dataclass
class LLMProviderConfig:
    """LLM Provider 配置"""
    model: str = "qwen3.5:2b"
    base_url: str = "http://localhost:11434"
    api_key: Optional[str] = None
    temperature: float = 0.7
    max_tokens: int = 2048
    
    @classmethod
    def from_config(cls, provider: str) -> "LLMProviderConfig":
        """从配置加载器创建"""
        config = get_config()
        
        if provider == "openai":
            return cls(
                model=config.get("openai.model", "gpt-3.5-turbo"),
                base_url=config.get("openai.base_url", "https://api.openai.com/v1"),
                api_key=os.getenv("OPENAI_API_KEY"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048"))
            )
        elif provider == "claude":
            return cls(
                model=config.get("claude.model", "claude-sonnet-4-20250514"),
                base_url=config.get("claude.base_url", "https://api.anthropic.com"),
                api_key=os.getenv("CLAUDE_API_KEY"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048"))
            )
        elif provider == "ollama":
            return cls(
                model=config.get("llm.model", "qwen3.5:2b"),
                base_url=config.get("llm.base_url", "http://localhost:11434"),
                api_key=None,  # Ollama 不需要 API key
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048"))
            )
        else:  # other (如 OpenRouter, 智谱等)
            return cls(
                model=config.get("other_api.model", "qwen3.5:2b"),
                base_url=config.get("other_api.base_url", "http://localhost:11434"),
                api_key=os.getenv("OTHER_API_KEY"),
                temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
                max_tokens=int(os.getenv("LLM_MAX_TOKENS", "2048"))
            )


@dataclass
class RouterConfig:
    """模型路由配置"""
    simple: str = "ollama"
    medium: str = "openai"
    complex: str = "claude"
    fallback: str = "ollama"
    fallback_chain: Dict[str, list] = field(default_factory=dict)
    failure_threshold: int = 3
    cooldown_seconds: int = 300
    
    @classmethod
    def from_config(cls) -> "RouterConfig":
        config = get_config()
        router_cfg = config.get("router", {})
        cb_cfg = config.get("circuit_breaker", {})
        
        return cls(
            simple=router_cfg.get("simple", "ollama"),
            medium=router_cfg.get("medium", "openai"),
            complex=router_cfg.get("complex", "claude"),
            fallback=router_cfg.get("fallback", "ollama"),
            fallback_chain=router_cfg.get("fallback_chain", {
                "claude": ["openai", "ollama"],
                "openai": ["ollama"],
                "ollama": []
            }),
            failure_threshold=cb_cfg.get("failure_threshold", 3),
            cooldown_seconds=cb_cfg.get("cooldown_seconds", 300)
        )


@dataclass
class TokenBudgetConfig:
    """Token 预算配置"""
    simple: int = 500
    medium: int = 2000
    complex: int = 4000
    tool_intensive: int = 6000
    
    @classmethod
    def from_config(cls) -> "TokenBudgetConfig":
        config = get_config()
        tb_cfg = config.get("token_budget", {})
        
        return cls(
            simple=tb_cfg.get("simple", 500),
            medium=tb_cfg.get("medium", 2000),
            complex=tb_cfg.get("complex", 4000),
            tool_intensive=tb_cfg.get("tool_intensive", 6000)
        )


@dataclass  
class FeishuConfig:
    """飞书配置"""
    app_id: str = ""
    app_secret: str = ""
    verification_token: Optional[str] = None
    encrypt_key: Optional[str] = None
    domain: str = "https://open.feishu.cn"
    webhook_path: str = "/webhook/feishu"
    enabled: bool = False
    
    @classmethod
    def from_config(cls) -> "FeishuConfig":
        config = get_config()
        fs_cfg = config.get("feishu", {})
        
        return cls(
            app_id=fs_cfg.get("app_id", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
            verification_token=os.getenv("FEISHU_VERIFICATION_TOKEN"),
            encrypt_key=os.getenv("FEISHU_ENCRYPT_KEY"),
            domain=fs_cfg.get("domain", "https://open.feishu.cn"),
            webhook_path=fs_cfg.get("webhook_path", "/webhook/feishu"),
            enabled=fs_cfg.get("enabled", False)
        )


@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    reload: bool = False
    
    @classmethod
    def from_config(cls) -> "ServerConfig":
        config = get_config()
        sv_cfg = config.get("server", {})
        
        return cls(
            host=sv_cfg.get("host", "0.0.0.0"),
            port=sv_cfg.get("port", 8000),
            reload=sv_cfg.get("reload", False)
        )


# ============== 便捷访问函数 ==============

def get_llm_provider_type() -> str:
    """获取默认 LLM Provider 类型"""
    return get_config().get("llm.provider", "ollama")

def get_router_config() -> RouterConfig:
    return RouterConfig.from_config()

def get_token_budget_config() -> TokenBudgetConfig:
    return TokenBudgetConfig.from_config()

def get_feishu_config() -> FeishuConfig:
    return FeishuConfig.from_config()

def get_server_config() -> ServerConfig:
    return ServerConfig.from_config()

def get_llm_provider_config(provider: str = None) -> LLMProviderConfig:
    if provider is None:
        provider = get_llm_provider_type()
    return LLMProviderConfig.from_config(provider)