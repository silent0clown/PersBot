from abc import ABC, abstractmethod
from typing import Optional


class STTProvider(ABC):
    """语音转文字 provider 抽象基类"""

    @property
    @abstractmethod
    def name(self) -> str:
        """provider 名称"""

    @abstractmethod
    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        """将音频数据转为文字"""

    @abstractmethod
    async def transcribe_file(self, file_path: str, language: str = "zh") -> str:
        """将音频文件转为文字"""

    def is_available(self) -> bool:
        """检查 provider 是否可用"""
        return True


class WhisperLocalSTT(STTProvider):
    """使用 OpenAI Whisper 本地模型"""

    def __init__(self, model_size: str = "base"):
        self._model_size = model_size
        self._model = None
        self._init_model()

    @property
    def name(self) -> str:
        return f"whisper_local_{self._model_size}"

    def _init_model(self):
        try:
            from faster_whisper import WhisperModel
            try:
                self._model = WhisperModel(
                    self._model_size,
                    device="cuda",
                    compute_type="float16"
                )
            except:
                self._model = WhisperModel(
                    self._model_size,
                    device="cpu",
                    compute_type="int8"
                )
        except ImportError:
            pass

    def is_available(self) -> bool:
        return self._model is not None

    async def transcribe(self, audio_data: bytes, language: str = "zh") -> str:
        if not self._model:
            return ""

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            segments, _ = self._model.transcribe(
                temp_path,
                language=language,
                beam_size=5,
                vad_filter=True
            )
            text = " ".join([s.text for s in segments])
            return text
        except Exception as e:
            return ""
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)

    async def transcribe_file(self, file_path: str, language: str = "zh") -> str:
        if not self._model:
            return ""

        try:
            segments, _ = self._model.transcribe(
                file_path,
                language=language,
                beam_size=5
            )
            text = " ".join([s.text for s in segments])
            return text
        except Exception as e:
            return ""


class AzureSTT(STTProvider):
    """使用 Azure Speech Service"""

    def __init__(self, api_key: str, region: str = "eastus"):
        self._api_key = api_key
        self._region = region
        self._client = None

    @property
    def name(self) -> str:
        return "azure_stt"

    def is_available(self) -> bool:
        return bool(self._api_key)

    async def transcribe(self, audio_data: bytes, language: str = "zh-CN") -> str:
        try:
            import azure.cognitiveservices.speech as speech
            speech_config = speech.SpeechConfig(
                subscription=self._api_key,
                region=self._region
            )
            speech_config.speech_recognition_language = language
            audio_config = speech.AudioDataStream(audio_data)
            recognizer = speech.SpeechRecognizer(speech_config=speech_config)
            result = recognizer.recognize_once()
            return result.text if result.reason == speech.ResultReason.RecognizedSpeech else ""
        except Exception:
            return ""

    async def transcribe_file(self, file_path: str, language: str = "zh-CN") -> str:
        try:
            import azure.cognitiveservices.speech as speech
            speech_config = speech.SpeechConfig(
                subscription=self._api_key,
                region=self._region
            )
            speech_config.speech_recognition_language = language
            audio_input = speech.AudioConfig(filename=file_path)
            recognizer = speech.SpeechRecognizer(speech_config=speech_config, audio_config=audio_input)
            result = recognizer.recognize_once()
            return result.text if result.reason == speech.ResultReason.RecognizedSpeech else ""
        except Exception:
            return ""
