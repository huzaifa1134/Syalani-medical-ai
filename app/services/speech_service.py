from app.models.schemas import Language
from logging import error
import httpx
from google.cloud import speech
from google.cloud import texttospeech
from app.models.schemas import STTRequest, STTResponse, TTSRequest, TTSResponse
from app.config import get_settings
import structlog

logger = structlog.get_logger()
settings = get_settings()

class SpeechService:
    """Handles Speech-to-Text and Text-to-Speech operations"""

    def __init__(self):
        # If the variable exists (Local), use the file. If not (Cloud), use default auth.
        if settings.GOOGLE_APPLICATION_CREDENTIALS:
            self.stt_client = speech.SpeechClient.from_service_account_file(settings.GOOGLE_APPLICATION_CREDENTIALS)
            self.tts_client = texttospeech.TextToSpeechClient.from_service_account_file(settings.GOOGLE_APPLICATION_CREDENTIALS)
        else:
            self.stt_client = speech.SpeechClient()  # Automatically uses Cloud Run's identity
            self.tts_client = texttospeech.TextToSpeechClient()  # Automatically uses Cloud Run's identity

    async def download_audio(self, audio_url: str) -> bytes:
        """Download audio url form Whatsapp"""
        try:
            async with httpx.AsyncClient() as client:
                headers = {
                        "Authorization": f"Bearer {settings.WABA_ACCESS_TOKEN}"
                    }
                response = await client.get(audio_url, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.content
        except Exception as e:
            logger.error("audio_download_failed", error=str(e), url=audio_url)
            raise

    async def speech_to_text(self, request: STTRequest) -> STTResponse:
        """Convert speech to text using google cloud STT"""
        try:
            audio_content = await self.download_audio(request.audio_url)

            audio = speech.RecognitionAudio(content=audio_content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
                sample_rate_hertz=16000,
                language_code=request.language,
                enable_automatic_punctuation=True,
                model="default"
            )

            response = self.stt_client.recognize(config=config, audio=audio)

            if not request.results:
                logger.warning("no_speech_detected", audio_url=request.audio_url)
                return STTResponse(
                    transcript="",
                    confidence=0.0,
                    language=request.language
                )

            result = response.results[0]
            transcript=result.alternatives[0].transcript
            confidence=result.alternatives[0].confidence

            logger.info(
                "stt_success",
                transcript=transcript,
                confidence=confidence,
                language=request.language
            )

            return STTResponse(
                transcript=transcript,
                confidence=confidence,
                language=request.language
            )

        except Exception as e:
            logger.error("stt_failed", error=str(e), audio_url=request.audio_url)
            raise

    async def text_to_speech(self, request: TTSRequest) -> TTSResponse:
        """COnvert text to speech using google cloud tts"""
        try:
            synthesis_input = texttospeech.SynthesisInput(text=request.text)

            voice = texttospeech.VoiceSelectionParams(
                language_code=request.language,
                name=request.voice_name 
            )

            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.OGG_OPUS,
                speaking_rate=1.0,
                pitch=0.0
            )

            response = self.tts_client.synthesize_speech(
                input=synthesis_input,
                voice=voice,
                audio_config=audio_config
            )

            logger.info(
                "tts_success",
                text_length=len(request.text),
                language=request.language
            )

            return TTSResponse(
                audio_content=response.audio_content,
                duration=len(response.audio_content) / 16000
            )

        
        except Exception as e:
            logger.error("tts_failed", error=error, text=request.text[:50])
            raise

speech_service = SpeechService()
