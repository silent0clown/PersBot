import logging
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self, model: str = "qwen:7b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url
        self.client = None
        self._init_client()
        self.conversation_history: List[Dict[str, str]] = []
    
    def _init_client(self):
        try:
            from ollama import Client
            self.client = Client(host=self.base_url)
            logger.info(f"LLM client initialized: {self.model}")
        except ImportError:
            logger.warning("Ollama not installed, trying OpenAI compatibility")
            try:
                from openai import OpenAI
                self.client = OpenAI(base_url=f"{self.base_url}/v1", api_key="dummy")
                logger.info("OpenAI-compatible LLM client initialized")
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
