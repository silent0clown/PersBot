from abc import ABC, abstractmethod
from typing import Optional


class TTSProvider(ABC):
    """文字转语音 provider 抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """provider 名称"""

    @abstractmethod
    async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
        """将文字转为音频数据"""

    @abstractmethod
    def get_available_voices(self) -> list:
        """获取可用的音色列表"""

    def is_available(self) -> bool:
        """检查 provider 是否可用"""
        return True


class EdgeTTS(TTSProvider):
    """使用 Microsoft Edge TTS"""

    VOICES = {
        "zh-CN-XiaoxiaoNeural": "女声-温柔",
        "zh-CN-YunxiNeural": "男声-阳光",
        "zh-CN-YunyangNeural": "男声-专业",
        "zh-CN-XiaoyiNeural": "女声-活泼",
    }

    def __init__(self, voice: str = "zh-CN-XiaoxiaoNeural"):
        self._voice = voice
        self._edge_tts = None
        self._init_tts()

    @property
    def name(self) -> str:
        return "edge_tts"

    def _init_tts(self):
        try:
            import edge_tts
            self._edge_tts = edge_tts
        except ImportError:
            pass

    def is_available(self) -> bool:
        return self._edge_tts is not None

    async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
        if not self._edge_tts:
            return None

        voice = voice or self._voice
        try:
            import tempfile
            import os

            communicate = self._edge_tts.Communicate(text, voice)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
                temp_path = f.name

            await communicate.save(temp_path)

            with open(temp_path, "rb") as f:
                audio_data = f.read()

            os.unlink(temp_path)
            return audio_data

        except Exception:
            return None

    def get_available_voices(self) -> list:
        return list(self.VOICES.keys())


class AzureTTS(TTSProvider):
    """使用 Azure Speech Service"""

    def __init__(self, api_key: str, region: str = "eastus", voice: str = "zh-CN-XiaoxiaoNeural"):
        self._api_key = api_key
        self._region = region
        self._voice = voice

    @property
    def name(self) -> str:
        return "azure_tts"

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
        try:
            import azure.cognitiveservices.speech as speech
            speech_config = speech.SpeechConfig(
                subscription=self._api_key,
                region=self._region
            )
            speech_config.speech_synthesis_voice_name = voice or self._voice

            synthesizer = speech.SpeechSynthesizer(speech_config=speech_config)
            result = synthesizer.speak_text_async(text).get()

            if result.reason == speech.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
        except Exception:
            pass
        return None

    def get_available_voices(self) -> list:
        return ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural", "zh-CN-YunyangNeural"]


class Pyttsx3TTS(TTSProvider):
    """使用 pyttsx3 离线 TTS"""

    def __init__(self, voice: str = None):
        self._voice = voice
        self._engine = None
        self._init_tts()

    @property
    def name(self) -> str:
        return "pyttsx3"

    def _init_tts(self):
        try:
            import pyttsx3
            self._engine = pyttsx3.init()
            self._engine.setProperty('rate', 150)
            self._engine.setProperty('volume', 0.9)
        except Exception:
            pass

    def is_available(self) -> bool:
        return self._engine is not None

    async def synthesize(self, text: str, voice: str = None) -> Optional[bytes]:
        if not self._engine:
            return None

        import tempfile
        import os

        def _synthesize():
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
                temp_path = f.name

            self._engine.save_to_file(text, temp_path)
            self._engine.runAndWait()

            with open(temp_path, "rb") as f:
                return f.read()

        try:
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, _synthesize)
        except Exception:
            return None

    def get_available_voices(self) -> list:
        if not self._engine:
            return []
        try:
            voices = self._engine.getProperty('voices')
            return [v.name for v in voices]
        except Exception:
            return []
