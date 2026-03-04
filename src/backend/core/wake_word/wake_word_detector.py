import logging
from typing import Optional
import numpy as np

logger = logging.getLogger(__name__)

class WakeWordDetector:
    def __init__(self, keywords: list[str] = None):
        self.keywords = keywords or ["jarvis", "贾维斯"]
        self.is_listening = False
        self Porcupine = None
        self.porcupine = None
        self._init_porcupine()
    
    def _init_porcupine(self):
        try:
            import pvporcupine
            self.Porcupine = pvporcupine
            self.porcupine = pvporcupine.create(
                keywords=self.keywords,
                sensitivities=[0.5] * len(self.keywords)
            )
            logger.info(f"Wake word detector initialized with keywords: {self.keywords}")
        except Exception as e:
            logger.warning(f"Porcupine not available: {e}")
            self.porcupine = None
    
    def detect(self, audio_data: bytes) -> bool:
        if not self.porcupine:
            return False
        
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            audio_float = audio_array.astype(np.float32) / 32768.0
            result = self.porcupine.process(audio_float)
            return result >= 0
        except Exception as e:
            logger.error(f"Wake word detection error: {e}")
            return False
    
    def start(self):
        self.is_listening = True
        logger.info("Wake word detection started")
    
    def stop(self):
        self.is_listening = False
        logger.info("Wake word detection stopped")
    
    def __del__(self):
        if self.porcupine:
            self.porcupine.delete()
