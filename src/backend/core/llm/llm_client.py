import logging
from typing import Optional, List, Dict

from core.config import get_settings, LLMConfig

logger = logging.getLogger(__name__)

llm_settings = get_settings().llm

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
        self.conversation_history: List[Dict[str, str]] = []
    
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
