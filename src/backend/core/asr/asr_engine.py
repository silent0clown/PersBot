import logging
from typing import Optional

logger = logging.getLogger(__name__)

class ASREngine:
    def __init__(self, model_size: str = "base", language: str = "zh"):
        self.model_size = model_size
        self.language = language
        self.model = None
        self._init_model()
    
    def _init_model(self):
        try:
            from faster_whisper import WhisperModel
            self.model = WhisperModel(
                self.model_size,
                device="cuda",
                compute_type="float16"
            )
            logger.info(f"ASR model loaded: {self.model_size}")
        except Exception as e:
            logger.warning(f"Failed to load Whisper model: {e}")
            try:
                self.model = WhisperModel(
                    self.model_size,
                    device="cpu",
                    compute_type="int8"
                )
                logger.info(f"ASR model loaded (CPU): {self.model_size}")
            except Exception as e2:
                logger.error(f"Failed to load ASR model: {e2}")
    
    async def transcribe(self, audio_data: bytes) -> str:
        if not self.model:
            return ""
        
        try:
            import tempfile
            import numpy as np
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
                f.write(audio_data)
                temp_path = f.name
            
            segments, info = self.model.transcribe(
                temp_path,
                language=self.language,
                beam_size=5,
                vad_filter=True
            )
            
            text = " ".join([segment.text for segment in segments])
            logger.info(f"Transcribed: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""
    
    async def transcribe_file(self, file_path: str) -> str:
        if not self.model:
            return ""
        
        try:
            segments, info = self.model.transcribe(
                file_path,
                language=self.language,
                beam_size=5
            )
            text = " ".join([segment.text for segment in segments])
            return text
        except Exception as e:
            logger.error(f"File transcription error: {e}")
            return ""
