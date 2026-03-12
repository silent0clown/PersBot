import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class TTSEngine:
    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self.voice = voice
        self.edge_tts_available = False
        self._init_tts()
    
    def _init_tts(self):
        try:
            import edge_tts
            self.edge_tts = edge_tts
            self.edge_tts_available = True
            logger.info("Edge TTS initialized")
        except ImportError:
            logger.warning("Edge TTS not available, falling back to pyttsx3")
            self.edge_tts_available = False
            try:
                import pyttsx3
                self.pyttsx3_engine = pyttsx3.init()
                self.pyttsx3_engine.setProperty('rate', 150)
                self.pyttsx3_engine.setProperty('volume', 0.9)
                logger.info("pyttsx3 initialized")
            except Exception as e:
                logger.error(f"Failed to initialize TTS: {e}")
    
    async def synthesize(self, text: str) -> Optional[bytes]:
        if self.edge_tts_available:
            return await self._edge_tts_synthesize(text)
        else:
            return await self._pyttsx3_synthesize(text)
    
    async def _edge_tts_synthesize(self, text: str) -> Optional[bytes]:
        try:
            import tempfile
            import asyncio
            
            communicate = self.edge_tts.Communicate(text, self.voice)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name
            
            await communicate.save(temp_path)
            
            with open(temp_path, "rb") as f:
                audio_data = f.read()
            
            import os
            os.unlink(temp_path)
            
            return audio_data
            
        except Exception as e:
            logger.error(f"Edge TTS error: {e}")
            return None
    
    async def _pyttsx3_synthesize(self, text: str) -> Optional[bytes]:
        def _synthesize():
            import tempfile
            import os
            
            # 使用 NamedTemporaryFile 安全创建临时文件
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                temp_path = tmp_file.name
            
            try:
                self.pyttsx3_engine.save_to_file(text, temp_path)
                self.pyttsx3_engine.runAndWait()
                
                with open(temp_path, "rb") as f:
                    data = f.read()
                return data
            finally:
                # 确保临时文件被清理
                if os.path.exists(temp_path):
                    os.unlink(temp_path)
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _synthesize)
    
    def get_available_voices(self) -> list:
        if hasattr(self, 'pyttsx3_engine'):
            voices = self.pyttsx3_engine.getProperty('voices')
            return [v.name for v in voices]
        return []
