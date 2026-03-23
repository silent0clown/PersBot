from functools import lru_cache
from typing import Optional, List, Dict, Any
from pathlib import Path
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import yaml
import os


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
        
        config_file = info.data.get('config_file') or os.getenv('MCP_CONFIG_FILE', 'mcp_servers.yaml')
        yaml_path = Path(config_file)
        
        if yaml_path.exists():
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                servers_data = data.get('servers', {})
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
    provider: str = Field(default="ollama", description="LLM provider: ollama, openai, other")
    model: str = Field(default="qwen3.5:2b", description="Model name")
    base_url: str = Field(default="http://localhost:11434", description="API base URL")
    api_key: Optional[str] = Field(default=None, description="API key")
    temperature: float = Field(default=0.7, description="Generation temperature")
    max_tokens: int = Field(default=2048, description="Max tokens")

    model_config = SettingsConfigDict(
        env_file=Path(__file__).parent.parent / ".env",
        env_prefix="OLLAMA_",
        extra="ignore"
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