import logging
import os
from typing import Optional, List, Dict

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Load configuration from environment variables
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.model = self._get_env_var("OLLAMA_MODEL", "qwen:7b")
        self.base_url = self._get_env_var("OLLAMA_BASE_URL", "http://localhost:11434")
        self.api_key = None
        
        # Override with provider-specific settings
        if self.provider == "openai":
            self.model = self._get_env_var("OPENAI_MODEL", "gpt-3.5-turbo")
            self.base_url = self._get_env_var("OPENAI_BASE_URL", "https://api.openai.com/v1")
            self.api_key = self._get_env_var("OPENAI_API_KEY")
        elif self.provider == "other":
            self.model = self._get_env_var("OTHER_MODEL", "qwen:7b")
            self.base_url = self._get_env_var("OTHER_BASE_URL", "http://localhost:11434")
            self.api_key = self._get_env_var("OTHER_API_KEY")
        
        self.client = None
        self._init_client()
        self.conversation_history: List[Dict[str, str]] = []
    
    def _get_env_var(self, key: str, default: str = None) -> str:
        """Get environment variable with optional default value"""
        value = os.getenv(key)
        return value if value is not None else default
    
    def _init_client(self):
        try:
            if self.provider == "ollama":
                from ollama import Client
                self.client = Client(host=self.base_url)
                logger.info(f"Ollama client initialized: {self.model} at {self.base_url}")
            elif self.provider in ["openai", "other"]:
                if not self.api_key:
                    logger.error(f"API key required for {self.provider} provider but not found in environment variables")
                    return
                
                from openai import OpenAI
                self.client = OpenAI(base_url=self.base_url, api_key=self.api_key)
                logger.info(f"OpenAI-compatible client initialized: {self.model} at {self.base_url}")
            else:
                logger.error(f"Unsupported LLM provider: {self.provider}")
                return
                
        except ImportError as e:
            logger.error(f"Required package not installed: {e}")
            if "ollama" in str(e).lower():
                logger.info("To use Ollama, install: pip install ollama")
            if "openai" in str(e).lower():
                logger.info("To use OpenAI API, install: pip install openai")
        except Exception as e:
            logger.error(f"Failed to initialize LLM client: {e}")
    
    async def chat(self, message: str, system_prompt: str = None) -> str:
        if not self.client:
            return "抱歉，AI服务暂不可用"
        
        self.conversation_history.append({"role": "user", "content": message})
        
        try:
            if hasattr(self.client, 'chat'):
                response = self.client.chat(
                    model=self.model,
                    messages=self._build_messages(system_prompt)
                )
                reply = response['message']['content']
            else:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=self._build_messages(system_prompt)
                )
                reply = response.choices[0].message.content
            
            self.conversation_history.append({"role": "assistant", "content": reply})
            return reply
            
        except Exception as e:
            logger.error(f"Chat error: {e}")
            self.conversation_history.pop()
            return f"发生错误: {str(e)}"
    
    def _build_messages(self, system_prompt: str = None) -> List[Dict[str, str]]:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.conversation_history[-10:])
        return messages
    
    def clear_history(self):
        self.conversation_history = []
        logger.info("Conversation history cleared")
    
    def get_available_models(self) -> List[str]:
        try:
            if hasattr(self.client, 'list'):
                models = self.client.list()
                return [m['name'] for m in models.get('models', [])]
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
        return []
