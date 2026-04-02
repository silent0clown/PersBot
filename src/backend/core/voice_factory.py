import logging
from typing import Optional

from .asr.providers import STTProvider, WhisperLocalSTT, AzureSTT
from .tts.providers import TTSProvider, EdgeTTS, AzureTTS, Pyttsx3TTS

logger = logging.getLogger(__name__)


def create_stt_provider(config: dict) -> Optional[STTProvider]:
    """根据配置创建 STT provider"""
    provider = config.get("stt_provider", "whisper_local")
    
    if provider == "whisper_local":
        model_size = config.get("stt_whisper_model", "base")
        stt = WhisperLocalSTT(model_size)
        if stt.is_available():
            logger.info(f"STT provider created: whisper_local ({model_size})")
            return stt
        logger.warning("Whisper not available, STT disabled")
        return None
    
    elif provider == "azure":
        api_key = config.get("azure_api_key")
        region = config.get("azure_region", "eastus")
        if api_key:
            stt = AzureSTT(api_key, region)
            logger.info("STT provider created: azure")
            return stt
        logger.warning("Azure API key not set")
        return None
    
    return None


def create_tts_provider(config: dict) -> Optional[TTSProvider]:
    """根据配置创建 TTS provider"""
    provider = config.get("tts_provider", "edge_tts")
    
    if provider == "edge_tts":
        voice = config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        tts = EdgeTTS(voice)
        if tts.is_available():
            logger.info(f"TTS provider created: edge_tts ({voice})")
            return tts
        logger.warning("Edge TTS not available")
        return None
    
    elif provider == "azure":
        api_key = config.get("azure_api_key")
        region = config.get("azure_region", "eastus")
        voice = config.get("tts_voice", "zh-CN-XiaoxiaoNeural")
        if api_key:
            tts = AzureTTS(api_key, region, voice)
            logger.info("TTS provider created: azure")
            return tts
        logger.warning("Azure API key not set")
        return None
    
    elif provider == "pyttsx3":
        tts = Pyttsx3TTS()
        if tts.is_available():
            logger.info("TTS provider created: pyttsx3")
            return tts
        logger.warning("pyttsx3 not available")
        return None
    
    return None
