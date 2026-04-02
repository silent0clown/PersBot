from functools import lru_cache
from typing import Optional, List, Dict, Any
from pathlib import Path
import logging
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
import os

logger = logging.getLogger(__name__)

class MCPServerConfig(BaseSettings):
    name: str = Field(default="", description="Server name")
    command: str = Field(default="", description="Command to run server (for stdio)")
    args: List[str] = Field(default_factory=list, description="Command arguments")
    env: Dict[str, str] = Field(default_factory=dict, description="Environment variables")
    url: Optional[str] = Field(default=None, description="HTTP URL (for streamable-http)")
    enabled: bool = Field(default=True, description="Enable this server")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="MCP_",
        extra="ignore"
    )


class MCPConfig(BaseSettings):
    servers: List[MCPServerConfig] = Field(default_factory=list, description="MCP servers")
    timeout: int = Field(default=30, description="Tool call timeout in seconds")
    config_file: Optional[str] = Field(default=None, description="Path to mcp_servers.yaml")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="MCP_",
        extra="ignore"
    )

    @field_validator('servers', mode='before')
    @classmethod
    def load_from_yaml(cls, v, info):
        if v is not None and len(v) > 0:
            return v
        
        config_file = info.data.get('config_file') or os.getenv('MCP_CONFIG_FILE', 'config/mcp_servers.yaml')
        # If config_file is an absolute path, use it directly
        yaml_path = Path(config_file)
        if not yaml_path.is_absolute():
            # First, try relative to the script directory (src/backend)
            script_dir = Path(__file__).parent.parent
            candidate = script_dir / config_file
            if candidate.exists():
                yaml_path = candidate
            else:
                # Fallback to current working directory
                yaml_path = Path(config_file)
        
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                servers_data = data.get('servers', {})
                # If servers_data is None (e.g., empty YAML), treat as empty dict
                if servers_data is None:
                    servers_data = {}
                servers = []
                for name, config in servers_data.items():
                    if isinstance(config, dict):
                        servers.append(MCPServerConfig(
                            name=config.get('name', name),
                            command=config.get('command', ''),
                            args=config.get('args', []),
                            env=config.get('env', {}),
                            url=config.get('url'),
                            enabled=config.get('enabled', True)
                        ))
                return servers
        return []


class LLMConfig(BaseSettings):
    provider: str = Field(default="ollama", validation_alias="LLM_PROVIDER", description="LLM provider: ollama, openai, other")
    model: str = Field(default="qwen3.5:2b", validation_alias="LLM_MODEL", description="Model name")
    base_url: str = Field(default="http://localhost:11434", validation_alias="LLM_BASE_URL", description="API base URL")
    api_key: Optional[str] = Field(default=None, validation_alias="LLM_API_KEY", description="API key")
    temperature: float = Field(default=0.7, validation_alias="LLM_TEMPERATURE", description="Generation temperature")
    max_tokens: int = Field(default=2048, validation_alias="LLM_MAX_TOKENS", description="Max tokens")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="",  # 不使用前缀
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True  # 允许使用字段名或别名
    )


class OpenAIConfig(BaseSettings):
    model: str = Field(default="gpt-3.5-turbo")
    base_url: str = Field(default="https://api.openai.com/v1")
    api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="OPENAI_",
        extra="ignore"
    )


class OtherAPIConfig(BaseSettings):
    model: str = Field(default="")
    base_url: str = Field(default="")
    api_key: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="OTHER_",
        extra="ignore"
    )


class WakeWordConfig(BaseSettings):
    keywords: list[str] = Field(default=["jarvis", "贾维斯"], description="Wake keywords")
    sensitivity: float = Field(default=0.5, description="Detection sensitivity")
    access_key: Optional[str] = Field(default=None, description="Porcupine access key")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="WAKE_",
        extra="ignore"
    )


class ASRConfig(BaseSettings):
    model_size: str = Field(default="base", description="Whisper model size: tiny, base, small, medium, large")
    language: Optional[str] = Field(default=None, description="Language (auto-detect if None)")
    device: str = Field(default="auto", description="Device: auto, cpu, cuda")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="ASR_",
        extra="ignore"
    )


class TTSConfig(BaseSettings):
    voice: str = Field(default="xiaoxiao", description="Edge-TTS voice")
    rate: str = Field(default="+0%", description="Speech rate")
    volume: str = Field(default="+0%", description="Volume")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="TTS_",
        extra="ignore"
    )


class AppConfig(BaseSettings):
    hotkey: str = Field(default="ctrl+shift+space", description="Global hotkey")
    start_minimized: bool = Field(default=False, description="Start minimized to tray")
    auto_start: bool = Field(default=False, description="Auto start on system boot")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="APP_",
        extra="ignore"
    )


class ServerConfig(BaseSettings):
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    reload: bool = Field(default=False, description="Enable auto-reload")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="SERVER_",
        extra="ignore"
    )


class MemoryConfig(BaseSettings):
    workspace: str = Field(default="~/.persbot/workspace", description="Memory workspace directory")
    citations: str = Field(default="auto", description="Citation mode: auto, on, off")
    auto_index: bool = Field(default=True, description="Auto index memory files on startup")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="MEMORY_",
        extra="ignore"
    )


class PersonaConfig(BaseSettings):
    """角色配置 - 定义 AI 的灵魂"""
    name: str = Field(default="小P", description="角色名称")
    personality: str = Field(default="友善、幽默、乐于助人", description="性格特点")
    speaking_style: str = Field(default="轻松自然，偶尔调皮", description="说话风格")
    background: str = Field(default="", description="角色背景故事")
    system_prompt: str = Field(default="", description="完整的系统提示词（优先级最高）")
    config_file: Optional[str] = Field(default="config/persona.yaml", description="角色配置文件路径")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="PERSONA_",
        extra="ignore"
    )


class PersonaManager:
    """角色管理器 - 加载和管理角色配置"""

    def __init__(self, config: PersonaConfig):
        self.config = config
        self._persona_data = None
        self._load_persona()

    def _load_persona(self):
        """从 YAML 文件加载角色配置"""
        yaml_path = Path(self.config.config_file)
        if not yaml_path.exists():
            yaml_path = Path(__file__).parent.parent / self.config.config_file

        if yaml_path.exists():
            try:
                with open(yaml_path, 'r', encoding='utf-8') as f:
                    self._persona_data = yaml.safe_load(f) or {}
                logger.info(f"Loaded persona from {yaml_path}")
            except Exception as e:
                logger.warning(f"Failed to load persona config: {e}")
                self._persona_data = {}
        else:
            self._persona_data = {}

    @property
    def name(self) -> str:
        return self._persona_data.get('name') or self.config.name

    @property
    def personality(self) -> str:
        return self._persona_data.get('personality') or self.config.personality

    @property
    def speaking_style(self) -> str:
        return self._persona_data.get('speaking_style') or self.config.speaking_style

    @property
    def background(self) -> str:
        return self._persona_data.get('background') or self.config.background

    @property
    def system_prompt(self) -> str:
        """获取系统提示词"""
        # 优先使用 YAML 中的完整 system_prompt
        if self._persona_data and self._persona_data.get('system_prompt'):
            return self._persona_data['system_prompt']

        # 其次使用配置中的 system_prompt
        if self.config.system_prompt:
            return self.config.system_prompt

        # 最后根据属性生成默认提示词
        return self._build_default_prompt()

    def _build_default_prompt(self) -> str:
        """根据配置生成默认系统提示词"""
        name = self.name
        personality = self.personality
        style = self.speaking_style
        background = self.background

        prompt = f"""你是{name}，一个AI助手。

性格特点：{personality}
说话风格：{style}
"""
        if background:
            prompt += f"\n背景：{background}\n"

        prompt += f"""
重要规则：
1. 你就是{name}，不要提及你是某个AI模型或由某个公司开发
2. 始终以{name}的身份回答问题
3. 保持你的性格特点和说话风格
4. 如果用户问你是谁，回答你是{name}
5. 友善、真诚地对待用户"""

        return prompt


class FeishuConfig(BaseSettings):
    app_id: str = Field(default="", description="Feishu app ID")
    app_secret: str = Field(default="", description="Feishu app secret")
    verification_token: Optional[str] = Field(default=None, description="Feishu verification token")
    encrypt_key: Optional[str] = Field(default=None, description="Feishu encrypt key")
    domain: str = Field(default="https://open.feishu.cn", description="Feishu API domain")
    enabled: bool = Field(default=False, description="Enable Feishu channel")
    webhook_path: str = Field(default="/webhook/feishu", description="Feishu webhook path")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="FEISHU_",
        extra="ignore"
    )


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)
    other_api: OtherAPIConfig = Field(default_factory=OtherAPIConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    persona: PersonaConfig = Field(default_factory=PersonaConfig)
    wake_word: WakeWordConfig = Field(default_factory=WakeWordConfig)
    asr: ASRConfig = Field(default_factory=ASRConfig)
    tts: TTSConfig = Field(default_factory=TTSConfig)
    app: AppConfig = Field(default_factory=AppConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    feishu: FeishuConfig = Field(default_factory=FeishuConfig)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# 创建角色管理器实例
persona_manager = PersonaManager(settings.persona)